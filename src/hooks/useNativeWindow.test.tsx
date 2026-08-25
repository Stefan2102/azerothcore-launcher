import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useNativeWindow } from "./useNativeWindow";

const minimize = vi.fn();

vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: () => ({ minimize }),
}));

function Harness({ onError }: { onError: (title: string, message: string) => void }) {
  const nativeWindow = useNativeWindow(onError);
  return (
    <button onClick={() => void nativeWindow.minimize()} type="button">
      Minimize
    </button>
  );
}

describe("useNativeWindow", () => {
  beforeEach(() => {
    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {},
    });
    minimize.mockReset().mockResolvedValue(undefined);
  });

  afterEach(() => Reflect.deleteProperty(window, "__TAURI_INTERNALS__"));

  it("invokes the only supported native window action", async () => {
    render(<Harness onError={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Minimize" }));
    await waitFor(() => expect(minimize).toHaveBeenCalledOnce());
  });

  it("reports minimize failures through the application alert handler", async () => {
    const onError = vi.fn();
    minimize.mockRejectedValue(new Error("access denied"));
    render(<Harness onError={onError} />);

    fireEvent.click(screen.getByRole("button", { name: "Minimize" }));

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(
        "Window controls",
        "Could not minimize the window: access denied",
      );
    });
  });
});
