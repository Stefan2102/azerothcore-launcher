import { describe, expect, it, vi } from "vitest";
import { TerminalOutputRouter } from "./terminal-output";

describe("TerminalOutputRouter", () => {
  it("replays startup output in order when a terminal attaches", () => {
    const router = new TerminalOutputRouter();
    const write = vi.fn();

    router.write("authserver", "first ");
    router.write("authserver", "second");
    router.attach("authserver", { write });

    expect(write).toHaveBeenCalledTimes(1);
    expect(write).toHaveBeenCalledWith("first second");
  });

  it("buffers output received while a terminal is being replaced", () => {
    const router = new TerminalOutputRouter();
    const firstWrite = vi.fn();
    const replacementWrite = vi.fn();

    router.attach("mysql", { write: firstWrite });
    router.write("mysql", "live");
    router.attach("mysql", null);
    router.write("mysql", "during commit");
    router.attach("mysql", { write: replacementWrite });

    expect(firstWrite).toHaveBeenCalledWith("live");
    expect(replacementWrite).toHaveBeenCalledWith("during commit");
  });
});
