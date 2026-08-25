import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { AlertDialog } from "./components/AlertDialog";
import { ExitDialog } from "./components/ExitDialog";
import { SettingsModal } from "./components/SettingsModal";
import { Sidebar } from "./components/Sidebar";
import {
  TerminalPanel,
  type TerminalPanelHandle,
} from "./components/TerminalPanel";
import { WindowControls } from "./components/WindowControls";
import { useNativeWindow } from "./hooks/useNativeWindow";
import {
  errorMessage,
  initializeBackend,
  launcherBackend,
} from "./lib/backend";
import { TerminalOutputRouter } from "./lib/terminal-output";
import {
  createIdleStates,
  serviceOrder,
  type BackendEvent,
  type ServiceId,
  type ServiceState,
} from "./types/launcher";

interface AlertState {
  title: string;
  message: string;
}

export default function App() {
  const [states, setStates] = useState<Record<ServiceId, ServiceState>>(
    createIdleStates,
  );
  const [ready, setReady] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [alert, setAlert] = useState<AlertState | null>(null);
  const [exitServices, setExitServices] = useState<ServiceId[] | null>(null);
  const terminalRefs = useRef<Record<ServiceId, TerminalPanelHandle | null>>({
    mysql: null,
    authserver: null,
    worldserver: null,
    ollama: null,
  });
  const outputRouterRef = useRef<TerminalOutputRouter | null>(null);
  if (!outputRouterRef.current) {
    outputRouterRef.current = new TerminalOutputRouter();
  }

  const terminalRefCallbacks = useMemo(() => {
    const bind =
      (serviceId: ServiceId) => (handle: TerminalPanelHandle | null) => {
        terminalRefs.current[serviceId] = handle;
        outputRouterRef.current?.attach(serviceId, handle);
      };
    return {
      mysql: bind("mysql"),
      authserver: bind("authserver"),
      worldserver: bind("worldserver"),
      ollama: bind("ollama"),
    };
  }, []);

  const showError = useCallback((title: string, message: string) => {
    setAlert({ title, message });
  }, []);
  const nativeWindow = useNativeWindow(showError);

  const handleBackendEvent = useCallback((event: BackendEvent) => {
    switch (event.event) {
      case "output":
        // The router writes directly when xterm is attached and buffers during
        // brief mount/commit gaps, without putting log traffic in React state.
        outputRouterRef.current?.write(event.data.serviceId, event.data.text);
        break;
      case "stateChanged":
        setStates((current) => ({
          ...current,
          [event.data.serviceId]: event.data.state,
        }));
        break;
      case "error":
        setAlert({ title: event.data.title, message: event.data.message });
        break;
    }
  }, []);

  useEffect(() => {
    // The channel subscription belongs to this mount. The active flag prevents
    // an asynchronous initialization result from updating an unmounted tree.
    let active = true;
    let dispose: () => void = () => undefined;
    let firstRunTimer: ReturnType<typeof setTimeout> | undefined;

    void initializeBackend(handleBackendEvent)
      .then((subscription) => {
        if (!active) {
          subscription.dispose();
          return;
        }
        dispose = subscription.dispose;
        setStates((current) => {
          const next = { ...current };
          for (const service of subscription.snapshot.services) {
            next[service.serviceId] = service.state;
          }
          return next;
        });
        setReady(true);
        if (subscription.snapshot.needsFirstRunSetup) {
          // Let the maximized window finish its first layout before placing focus
          // inside the modal; this avoids a visible focus jump at startup.
          firstRunTimer = setTimeout(() => setSettingsOpen(true), 350);
        }
      })
      .catch((error) => {
        if (active) {
          setReady(true);
          showError("Launcher initialization", errorMessage(error));
        }
      });

    return () => {
      active = false;
      clearTimeout(firstRunTimer);
      dispose();
    };
  }, [handleBackendEvent, showError]);

  const requestExit = useCallback(async () => {
    try {
      const running = await launcherBackend.runningServices();
      if (running.length > 0) {
        setExitServices(running);
      } else {
        await launcherBackend.exitApplication(false);
      }
    } catch (error) {
      showError("Exit", errorMessage(error));
    }
  }, [showError]);

  const cancelSettings = useCallback(() => setSettingsOpen(false), []);

  useEffect(() => {
    // Browser-based UI tests do not have a native window. Register the close
    // interception only inside Tauri while keeping the same React bundle testable.
    if (!("__TAURI_INTERNALS__" in window)) {
      return undefined;
    }
    const unlistenPromise = getCurrentWindow().onCloseRequested((event) => {
      event.preventDefault();
      void requestExit();
    });
    return () => {
      void unlistenPromise.then((unlisten) => unlisten());
    };
  }, [requestExit]);

  async function serviceAction(serviceId: ServiceId) {
    try {
      if (states[serviceId] === "idle") {
        const terminal = terminalRefs.current[serviceId];
        // Preserve logs after a process exits for diagnosis, but start every new
        // process with a clean panel so sessions cannot be confused.
        outputRouterRef.current?.clear(serviceId);
        terminal?.clear();
        const dimensions = terminal?.dimensions() ?? { columns: 80, rows: 24 };
        await launcherBackend.startService(
          serviceId,
          dimensions.columns,
          dimensions.rows,
        );
      } else if (states[serviceId] === "running") {
        await launcherBackend.stopService(serviceId);
      }
    } catch (error) {
      showError(`${serviceId} service`, errorMessage(error));
    }
  }

  return (
    <div className="app-shell" aria-busy={!ready}>
      <WindowControls
        onClose={() => void requestExit()}
        onMinimize={() => void nativeWindow.minimize()}
      />

      <Sidebar
        onExit={() => void requestExit()}
        onLaunchWow={() => {
          void launcherBackend
            .launchWorldOfWarcraft()
            .catch((error) => showError("World of Warcraft", errorMessage(error)));
        }}
        onOpenSettings={() => setSettingsOpen(true)}
        onServiceAction={(serviceId) => void serviceAction(serviceId)}
        states={states}
      />

      <main className="terminal-grid">
        {serviceOrder.map((serviceId) => (
          <TerminalPanel
            key={serviceId}
            onCommand={async (text) => {
              try {
                await launcherBackend.writeService(serviceId, text);
                return true;
              } catch (error) {
                showError("Worldserver command", errorMessage(error));
                return false;
              }
            }}
            onCopyError={(error) =>
              showError("Terminal copy", errorMessage(error))
            }
            onCtrlC={() => {
              if (states[serviceId] === "running") {
                void launcherBackend
                  .stopService(serviceId)
                  .catch((error) =>
                    showError(`${serviceId} service`, errorMessage(error)),
                  );
              }
            }}
            onResize={(columns, rows) => {
              void launcherBackend
                .resizeService(serviceId, columns, rows)
                .catch((error) =>
                  showError(`${serviceId} terminal`, errorMessage(error)),
                );
            }}
            onTerminalData={(data) => {
              void launcherBackend
                .writeTerminalInput(serviceId, data)
                .catch((error) =>
                  showError(`${serviceId} terminal`, errorMessage(error)),
                );
            }}
            ref={terminalRefCallbacks[serviceId]}
            serviceId={serviceId}
            state={states[serviceId]}
          />
        ))}
      </main>

      {!ready && <div className="startup-overlay">Starting launcher…</div>}

      {settingsOpen && (
        <SettingsModal
          onCancel={cancelSettings}
          onError={showError}
          onSaved={() => {
            setSettingsOpen(false);
          }}
        />
      )}
      {exitServices && (
        <ExitDialog
          onCancel={() => setExitServices(null)}
          onConfirm={() => {
            void launcherBackend
              .exitApplication(true)
              .catch((error) => showError("Exit", errorMessage(error)));
          }}
          services={exitServices}
        />
      )}
      {alert && (
        <AlertDialog
          message={alert.message}
          onClose={() => setAlert(null)}
          title={alert.title}
        />
      )}
    </div>
  );
}
