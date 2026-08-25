import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { launcherBackend } from "../lib/backend";
import { SettingsModal } from "./SettingsModal";

const dialogMocks = vi.hoisted(() => ({ open: vi.fn() }));
vi.mock("@tauri-apps/plugin-dialog", () => ({ open: dialogMocks.open }));

const loadedSettings = {
  sqlHost: "127.0.0.1",
  sqlPort: 3306,
  sqlUser: "acore",
  sqlPassword: "acore",
  clientPath: "",
  mysqlPath: ".\\mysql\\bin\\mysqld.exe",
  authServerPath: ".\\authserver.exe",
  worldServerPath: ".\\worldserver.exe",
};

function renderSettingsModal(overrides: Partial<React.ComponentProps<typeof SettingsModal>> = {}) {
  const props = {
    onCancel: vi.fn(),
    onError: vi.fn(),
    onSaved: vi.fn(),
    ...overrides,
  };
  render(<SettingsModal {...props} />);
  return props;
}

describe("SettingsModal", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    dialogMocks.open.mockReset();
  });

  it("renders configuration controls in semantic sections without a theme selector", async () => {
    vi.spyOn(launcherBackend, "loadSettings").mockResolvedValue(loadedSettings);
    renderSettingsModal();

    const save = await screen.findByRole("button", { name: "Save" });
    expect(screen.queryByRole("radiogroup", { name: "Launcher theme" })).not.toBeInTheDocument();
    expect(save).toHaveClass("control-button", "button--primary");
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveClass(
      "control-button",
      "button--secondary",
    );
    for (const browse of screen.getAllByRole("button", { name: "Browse…" })) {
      expect(browse).toHaveClass("control-button", "browse-button");
    }
    expect(screen.getByRole("heading", { name: "Database" })).toBeInTheDocument();
    expect(
      screen.getByText("Connection details used for the MySQL shutdown helper."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "World of Warcraft client" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Server executables" })).toBeInTheDocument();
    expect(document.querySelector("fieldset.settings-section")).not.toBeInTheDocument();
  });

  it("saves settings through the existing command", async () => {
    vi.spyOn(launcherBackend, "loadSettings").mockResolvedValue(loadedSettings);
    const saveSettings = vi
      .spyOn(launcherBackend, "saveSettings")
      .mockResolvedValue(loadedSettings);
    const props = renderSettingsModal();

    fireEvent.click(await screen.findByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(saveSettings).toHaveBeenCalledWith(
        expect.objectContaining({ sqlHost: "127.0.0.1" }),
      ),
    );
    expect(props.onSaved).toHaveBeenCalledWith(loadedSettings);
  });

  it("reveals and re-hides the SQL password without changing its value", async () => {
    vi.spyOn(launcherBackend, "loadSettings").mockResolvedValue(loadedSettings);
    renderSettingsModal();

    const password = await screen.findByLabelText("SQL Server Password");
    expect(password).toHaveAttribute("type", "password");
    fireEvent.click(screen.getByRole("button", { name: "Show SQL Server Password" }));
    expect(password).toHaveAttribute("type", "text");
    expect(password).toHaveValue("acore");
    fireEvent.click(screen.getByRole("button", { name: "Hide SQL Server Password" }));
    expect(password).toHaveAttribute("type", "password");
  });

  it("routes Cancel and modal close through the same restoration callback", async () => {
    vi.spyOn(launcherBackend, "loadSettings").mockResolvedValue(loadedSettings);
    const props = renderSettingsModal();

    fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    fireEvent.click(screen.getByRole("button", { name: "Close dialog" }));
    expect(props.onCancel).toHaveBeenCalledTimes(2);
  });

  it("keeps the form open after a failed save", async () => {
    vi.spyOn(launcherBackend, "loadSettings").mockResolvedValue(loadedSettings);
    vi.spyOn(launcherBackend, "saveSettings").mockRejectedValue("write failed");
    const props = renderSettingsModal();

    fireEvent.click(await screen.findByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(props.onError).toHaveBeenCalledWith("Settings", "write failed"),
    );
    expect(screen.getByRole("dialog", { name: "Launcher Settings" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(props.onCancel).toHaveBeenCalledOnce();
    expect(props.onSaved).not.toHaveBeenCalled();
  });

  it("closes without exposing defaults when settings loading fails", async () => {
    vi.spyOn(launcherBackend, "loadSettings").mockRejectedValue("read failed");
    const props = renderSettingsModal();

    await waitFor(() =>
      expect(props.onError).toHaveBeenCalledWith("Settings", "read failed"),
    );
    expect(props.onCancel).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
  });

  it("ignores stale path validation after the field changes", async () => {
    vi.spyOn(launcherBackend, "loadSettings").mockResolvedValue(loadedSettings);
    let resolveValidation: (exists: boolean) => void = () => undefined;
    vi.spyOn(launcherBackend, "validateExecutablePath").mockReturnValue(
      new Promise((resolve) => {
        resolveValidation = resolve;
      }),
    );
    renderSettingsModal();
    const clientPath = await screen.findByLabelText("Client Path");

    fireEvent.change(clientPath, { target: { value: "missing.exe" } });
    fireEvent.blur(clientPath);
    fireEvent.change(clientPath, { target: { value: "new.exe" } });
    resolveValidation(false);

    await waitFor(() => expect(clientPath).toHaveValue("new.exe"));
    expect(screen.queryByText("Executable not found at this path.")).not.toBeInTheDocument();
  });

  it("reports native executable-picker failures", async () => {
    vi.spyOn(launcherBackend, "loadSettings").mockResolvedValue(loadedSettings);
    dialogMocks.open.mockRejectedValue("picker failed");
    const props = renderSettingsModal();

    const browseButtons = await screen.findAllByRole("button", { name: "Browse…" });
    fireEvent.click(browseButtons[0]);

    await waitFor(() =>
      expect(props.onError).toHaveBeenCalledWith(
        "Executable picker",
        "picker failed",
      ),
    );
  });
});
