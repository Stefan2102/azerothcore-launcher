export type ServiceId = "mysql" | "authserver" | "worldserver" | "ollama";
export type ServiceState = "idle" | "starting" | "running" | "stopping";

export interface ServiceSnapshot {
  serviceId: ServiceId;
  state: ServiceState;
}

export interface LauncherSnapshot {
  services: ServiceSnapshot[];
  needsFirstRunSetup: boolean;
}

export interface SettingsView {
  sqlHost: string;
  sqlPort: number;
  sqlUser: string;
  sqlPassword: string;
  clientPath: string;
  mysqlPath: string;
  authServerPath: string;
  worldServerPath: string;
}

export type SettingsInput = SettingsView;

export type BackendEvent =
  | { event: "output"; data: { serviceId: ServiceId; text: string } }
  | {
      event: "stateChanged";
      data: { serviceId: ServiceId; state: ServiceState };
    }
  | {
      event: "error";
      data: {
        serviceId: ServiceId | null;
        title: string;
        message: string;
      };
    };

export const serviceOrder: ServiceId[] = [
  "mysql",
  "authserver",
  "worldserver",
  "ollama",
];

export const serviceLabels: Record<ServiceId, string> = {
  mysql: "MySQL",
  authserver: "Authserver",
  worldserver: "Worldserver",
  ollama: "Ollama",
};

export function createIdleStates(): Record<ServiceId, ServiceState> {
  return {
    mysql: "idle",
    authserver: "idle",
    worldserver: "idle",
    ollama: "idle",
  };
}

export function actionLabel(
  serviceId: ServiceId,
  state: ServiceState,
): string {
  const label = serviceLabels[serviceId];
  if (state === "starting") return `Starting ${label}`;
  if (state === "stopping") return `Stopping ${label}`;
  return `${state === "running" ? "Stop" : "Start"} ${label}`;
}
