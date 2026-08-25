import { Channel, invoke } from "@tauri-apps/api/core";
import type {
  BackendEvent,
  LauncherSnapshot,
  ServiceId,
  SettingsInput,
  SettingsView,
} from "../types/launcher";

export interface BackendSubscription {
  snapshot: LauncherSnapshot;
  dispose: () => void;
}

export async function initializeBackend(
  onEvent: (event: BackendEvent) => void,
): Promise<BackendSubscription> {
  const channel = new Channel<BackendEvent>();
  channel.onmessage = onEvent;
  const snapshot = await invoke<LauncherSnapshot>("initialize", {
    onEvent: channel,
  });
  return {
    snapshot,
    dispose: () => {
      // Replacing the callback breaks retained React references if the webview
      // remains alive while the component tree is remounted during development.
      channel.onmessage = () => undefined;
    },
  };
}

export const launcherBackend = {
  loadSettings: () => invoke<SettingsView>("load_settings"),
  saveSettings: (settings: SettingsInput) =>
    invoke<SettingsView>("save_settings", { settings }),
  validateExecutablePath: (value: string) =>
    invoke<boolean>("validate_executable_path", { value }),
  startService: (
    serviceId: ServiceId,
    columns: number,
    rows: number,
  ) => invoke<void>("start_service", { serviceId, columns, rows }),
  stopService: (serviceId: ServiceId) =>
    invoke<void>("stop_service", { serviceId }),
  writeService: (serviceId: ServiceId, text: string) =>
    invoke<void>("write_service", { serviceId, text }),
  writeTerminalInput: (serviceId: ServiceId, data: string) =>
    invoke<void>("write_terminal_input", { serviceId, data }),
  resizeService: (
    serviceId: ServiceId,
    columns: number,
    rows: number,
  ) => invoke<void>("resize_service", { serviceId, columns, rows }),
  launchWorldOfWarcraft: () => invoke<void>("launch_world_of_warcraft"),
  runningServices: () => invoke<ServiceId[]>("running_services"),
  exitApplication: (force: boolean) =>
    invoke<void>("exit_application", { force }),
};

export function errorMessage(error: unknown): string {
  if (typeof error === "string") return error;
  if (error instanceof Error) return error.message;
  return "An unexpected launcher error occurred.";
}
