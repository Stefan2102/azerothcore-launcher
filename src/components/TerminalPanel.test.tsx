import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import "../styles.css";
import { TerminalPanel } from "./TerminalPanel";

const terminalMocks = vi.hoisted(() => ({
  options: undefined as Record<string, unknown> | undefined,
  onData: undefined as ((data: string) => void) | undefined,
  keyHandler: undefined as ((event: KeyboardEvent) => boolean) | undefined,
  dataDispose: vi.fn(),
  terminalDispose: vi.fn(),
  fit: vi.fn(),
  resizeDisconnect: vi.fn(),
  openedHost: undefined as HTMLElement | undefined,
  selection: "",
}));

vi.mock("@xterm/xterm", () => ({
  Terminal: class {
    cols = 80;
    rows = 24;
    textarea = document.createElement("textarea");
    options: Record<string, unknown>;

    constructor(options: Record<string, unknown>) {
      this.options = options;
      terminalMocks.options = options;
    }

    loadAddon() {}
    open(host: HTMLElement) {
      terminalMocks.openedHost = host;
      host.appendChild(this.textarea);
    }
    onData(callback: (data: string) => void) {
      terminalMocks.onData = callback;
      return { dispose: terminalMocks.dataDispose };
    }
    attachCustomKeyEventHandler(
      callback: (event: KeyboardEvent) => boolean,
    ) {
      terminalMocks.keyHandler = callback;
    }
    getSelection() {
      return terminalMocks.selection;
    }
    clear() {}
    write() {}
    dispose() {
      terminalMocks.terminalDispose();
    }
  },
}));

vi.mock("@xterm/addon-fit", () => ({
  FitAddon: class {
    fit = terminalMocks.fit;
  },
}));

class ResizeObserverMock {
  observe() {}
  disconnect = terminalMocks.resizeDisconnect;
}

describe("TerminalPanel", () => {
  beforeEach(() => {
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    vi.useFakeTimers();
    terminalMocks.options = undefined;
    terminalMocks.onData = undefined;
    terminalMocks.keyHandler = undefined;
    terminalMocks.dataDispose.mockClear();
    terminalMocks.terminalDispose.mockClear();
    terminalMocks.fit.mockClear();
    terminalMocks.resizeDisconnect.mockClear();
    terminalMocks.openedHost = undefined;
    terminalMocks.selection = "";
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  function renderWorldserver() {
    const callbacks = {
      onCommand: vi.fn().mockResolvedValue(true),
      onCopyError: vi.fn(),
      onCtrlC: vi.fn(),
      onResize: vi.fn(),
      onTerminalData: vi.fn(),
    };
    const result = render(
      <TerminalPanel
        {...callbacks}
        serviceId="worldserver"
        state="running"
      />,
    );
    return {
      ...result,
      ...callbacks,
    };
  }

  it("uses a hidden cursor and a measured four-pixel scrollbar", () => {
    renderWorldserver();

    expect(terminalMocks.options).toMatchObject({
      cursorInactiveStyle: "none",
      disableStdin: false,
      overviewRuler: { width: 4 },
      scrollback: 5000,
      theme: {
        cursor: "#04172a",
        overviewRulerBorder: "#04172a",
        scrollbarSliderBackground: "#1678a9aa",
      },
    });
  });

  it("fits xterm inside a borderless host within the decorated frame", () => {
    renderWorldserver();

    const host = screen.getByLabelText("Worldserver terminal output");
    expect(host).toHaveClass("terminal-panel__host");
    expect(host.parentElement).toHaveClass("terminal-panel__viewport");
    expect(host).toHaveStyle("--terminal-scrollbar-width: 4px");
    expect(terminalMocks.openedHost).toBe(host);
  });

  it("uses only the status dot for visible service state", () => {
    renderWorldserver();

    expect(screen.queryByText("Running")).not.toBeInTheDocument();
    expect(
      screen.getByRole("status", { name: "Worldserver running" }),
    ).toHaveClass("status-dot");
  });

  it("defines distinct idle, transition, and running status colors", () => {
    renderWorldserver();

    const tokens = getComputedStyle(document.documentElement);
    expect(tokens.getPropertyValue("--status-idle").trim()).toBe("#6f8390");
    expect(tokens.getPropertyValue("--status-transition").trim()).toBe(
      "#f0a14a",
    );
    expect(tokens.getPropertyValue("--status-running").trim()).toBe(
      "#62d9a5",
    );
  });

  it("keeps command entry free-form without account suggestions", () => {
    renderWorldserver();
    const input = screen.getByRole("textbox", { name: "Worldserver command" });

    expect(input).toHaveAttribute("autocomplete", "off");
    expect(input).not.toHaveAttribute("list");
    fireEvent.change(input, { target: { value: "account" } });
    expect(input).toHaveValue("account");
    expect(document.querySelector("datalist")).not.toBeInTheDocument();
  });

  it("uses the shared compact control for Worldserver command submission", () => {
    renderWorldserver();

    const send = screen.getByRole("button", {
      name: "Send Worldserver command",
    });
    expect(send).toHaveClass("control-button", "terminal-input__send");
    expect(send).toBeDisabled();

    fireEvent.change(
      screen.getByRole("textbox", { name: "Worldserver command" }),
      {
      target: { value: "server info" },
      },
    );
    expect(send).toBeEnabled();
  });

  it("retains a command when native submission fails", async () => {
    const { onCommand } = renderWorldserver();
    onCommand.mockResolvedValue(false);
    const input = screen.getByRole("textbox", { name: "Worldserver command" });
    fireEvent.change(input, { target: { value: "server info" } });
    fireEvent.click(screen.getByRole("button", { name: "Send Worldserver command" }));

    await vi.waitFor(() => expect(onCommand).toHaveBeenCalledWith("server info"));
    expect(input).toHaveValue("server info");
  });

  it("reports clipboard failures", async () => {
    const copyError = new Error("clipboard denied");
    const writeText = vi.fn().mockRejectedValue(copyError);
    vi.stubGlobal("navigator", {
      ...navigator,
      clipboard: { writeText },
    });
    terminalMocks.selection = "selected output";
    const { onCopyError } = renderWorldserver();

    terminalMocks.keyHandler?.(
      new KeyboardEvent("keydown", { ctrlKey: true, key: "c" }),
    );

    await vi.waitFor(() => expect(onCopyError).toHaveBeenCalledWith(copyError));
  });

  it("reports when clipboard access is unavailable", () => {
    vi.stubGlobal("navigator", { ...navigator, clipboard: undefined });
    terminalMocks.selection = "selected output";
    const { onCopyError } = renderWorldserver();

    terminalMocks.keyHandler?.(
      new KeyboardEvent("keydown", { ctrlKey: true, key: "c" }),
    );

    expect(onCopyError).toHaveBeenCalledWith(
      expect.objectContaining({ message: "Clipboard access is unavailable." }),
    );
  });

  it("forwards terminal protocol replies and disposes owned resources", () => {
    const addListener = vi.spyOn(EventTarget.prototype, "addEventListener");
    const removeListener = vi.spyOn(EventTarget.prototype, "removeEventListener");
    const { onTerminalData, unmount } = renderWorldserver();

    terminalMocks.onData?.("\u001b[1;1R");
    expect(onTerminalData).toHaveBeenCalledWith("\u001b[1;1R");

    unmount();
    for (const eventName of ["beforeinput", "paste", "drop"]) {
      expect(addListener).toHaveBeenCalledWith(
        eventName,
        expect.any(Function),
        true,
      );
      expect(removeListener).toHaveBeenCalledWith(
        eventName,
        expect.any(Function),
        true,
      );
    }
    expect(terminalMocks.dataDispose).toHaveBeenCalledOnce();
    expect(terminalMocks.resizeDisconnect).toHaveBeenCalledOnce();
    expect(terminalMocks.terminalDispose).toHaveBeenCalledOnce();
    addListener.mockRestore();
    removeListener.mockRestore();
  });
});
