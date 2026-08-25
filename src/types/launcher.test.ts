import { describe, expect, it } from "vitest";
import { actionLabel, createIdleStates } from "./launcher";

describe("launcher service presentation", () => {
  it("creates an independent idle state for every service", () => {
    expect(createIdleStates()).toEqual({
      mysql: "idle",
      authserver: "idle",
      worldserver: "idle",
      ollama: "idle",
    });
  });

  it("describes stable and transitional actions", () => {
    expect(actionLabel("mysql", "idle")).toBe("Start MySQL");
    expect(actionLabel("mysql", "running")).toBe("Stop MySQL");
    expect(actionLabel("worldserver", "starting")).toBe("Starting Worldserver");
    expect(actionLabel("ollama", "stopping")).toBe("Stopping Ollama");
  });
});
