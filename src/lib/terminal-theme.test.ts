import { describe, expect, it } from "vitest";
import { terminalTheme } from "./terminal-theme";

describe("terminal theme", () => {
  it("uses the fixed Icy Blue canvas and themed scrollbar", () => {
    expect(terminalTheme.background).toBe("#04172a");
    expect(terminalTheme.background).not.toBe("#000000");
    expect(terminalTheme.cursor).toBe(terminalTheme.background);
    expect(terminalTheme.scrollbarSliderBackground).toBe("#1678a9aa");
  });
});
