import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const mocks = vi.hoisted(() => ({
  dispose: vi.fn(),
  initializeBackend: vi.fn(),
}));

vi.mock("./lib/backend", () => ({
  errorMessage: (error: unknown) => String(error),
  initializeBackend: mocks.initializeBackend,
  launcherBackend: {
    exitApplication: vi.fn(),
    launchWorldOfWarcraft: vi.fn(),
    resizeService: vi.fn(),
    runningServices: vi.fn().mockResolvedValue([]),
    startService: vi.fn(),
    stopService: vi.fn(),
    writeService: vi.fn(),
    writeTerminalInput: vi.fn(),
  },
}));
vi.mock("./hooks/useNativeWindow", () => ({
  useNativeWindow: () => ({
    minimize: vi.fn(),
  }),
}));
vi.mock("./components/WindowControls", () => ({ WindowControls: () => null }));
vi.mock("./components/TerminalPanel", () => ({ TerminalPanel: () => null }));
vi.mock("./components/Sidebar", () => ({
  Sidebar: ({ onOpenSettings }: { onOpenSettings: () => void }) => (
    <button onClick={onOpenSettings} type="button">
      Open settings
    </button>
  ),
}));
vi.mock("./components/SettingsModal", () => ({
  SettingsModal: ({
    onCancel,
    onSaved,
  }: {
    onCancel: () => void;
    onSaved: () => void;
  }) => (
    <div>
      <button onClick={onCancel} type="button">
        Cancel settings
      </button>
      <button onClick={onSaved} type="button">
        Save settings
      </button>
    </div>
  ),
}));

describe("application settings ownership", () => {
  afterEach(() => vi.clearAllMocks());

  it("initializes without a theme snapshot and closes settings after save or cancel", async () => {
    mocks.initializeBackend.mockResolvedValue({
      dispose: mocks.dispose,
      snapshot: { needsFirstRunSetup: false, services: [] },
    });
    const { container, unmount } = render(<App />);
    await waitFor(() =>
      expect(container.querySelector(".app-shell")).toHaveAttribute(
        "aria-busy",
        "false",
      ),
    );
    expect(container.querySelector(".app-shell")).not.toHaveAttribute("data-theme");

    fireEvent.click(screen.getByRole("button", { name: "Open settings" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancel settings" }));
    fireEvent.click(screen.getByRole("button", { name: "Open settings" }));
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));
    expect(screen.queryByRole("button", { name: "Cancel settings" })).not.toBeInTheDocument();

    unmount();
    expect(mocks.dispose).toHaveBeenCalledOnce();
  });
});
