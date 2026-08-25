import type { SettingsInput } from "../types/launcher";

export const executableFields = [
  "clientPath",
  "mysqlPath",
  "authServerPath",
  "worldServerPath",
] as const satisfies readonly (keyof SettingsInput)[];

export type ExecutableField = (typeof executableFields)[number];

export function fieldError(
  key: keyof SettingsInput,
  value: string | number,
): string {
  if (key === "sqlHost" && !String(value).trim()) {
    return "SQL Server IP is required.";
  }
  if (key === "sqlUser" && !String(value).trim()) {
    return "SQL Server User is required.";
  }
  if (key === "sqlPort" && (Number(value) < 1 || Number(value) > 65535)) {
    return "Port must be between 1 and 65535.";
  }
  return "";
}
