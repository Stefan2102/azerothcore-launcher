import { useCallback } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { errorMessage } from "../lib/backend";

interface UseNativeWindowResult {
  minimize: () => Promise<void>;
}

type WindowErrorHandler = (title: string, message: string) => void;

function isTauriRuntime() {
  return "__TAURI_INTERNALS__" in window;
}

export function useNativeWindow(
  onError: WindowErrorHandler,
): UseNativeWindowResult {
  const reportError = useCallback(
    (action: string, error: unknown) => {
      onError("Window controls", `Could not ${action}: ${errorMessage(error)}`);
    },
    [onError],
  );

  const minimize = useCallback(async () => {
    if (!isTauriRuntime()) return;
    try {
      await getCurrentWindow().minimize();
    } catch (error) {
      reportError("minimize the window", error);
    }
  }, [reportError]);

  return { minimize };
}
