import type { ITheme } from "@xterm/xterm";

const ansiColors = {
  black: "#101820",
  red: "#ff5b65",
  green: "#62d9a5",
  yellow: "#e7c86d",
  blue: "#78b9ec",
  magenta: "#d08fe8",
  cyan: "#75d7df",
  white: "#e8f8ff",
  brightBlack: "#718795",
  brightRed: "#ff7a82",
  brightGreen: "#83e6ba",
  brightYellow: "#f1d989",
  brightBlue: "#9acbf1",
  brightMagenta: "#dda9ef",
  brightCyan: "#96e4e9",
  brightWhite: "#ffffff",
} satisfies ITheme;

// xterm draws to a canvas and cannot inherit the CSS tokens used by DOM
// controls. This fixed Icy Blue value keeps terminal rendering in sync with
// the launcher palette while preserving stable ANSI service-log colors.
export const terminalTheme: ITheme = {
  ...ansiColors,
  background: "#04172a",
  foreground: "#e9fbff",
  cursor: "#04172a",
  cursorAccent: "#e9fbff",
  overviewRulerBorder: "#04172a",
  selectionBackground: "#1678a999",
  scrollbarSliderBackground: "#1678a9aa",
  scrollbarSliderHoverBackground: "#2de1ffcc",
  scrollbarSliderActiveBackground: "#8cf2ffee",
};
