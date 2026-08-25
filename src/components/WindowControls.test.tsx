import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WindowControls } from "./WindowControls";

describe("WindowControls", () => {
  it("routes window actions through the supplied handlers", () => {
    const onClose = vi.fn();
    const onMinimize = vi.fn();
    render(
      <WindowControls
        onClose={onClose}
        onMinimize={onMinimize}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Minimize window" }));
    fireEvent.click(screen.getByRole("button", { name: "Close window" }));

    for (const button of screen.getAllByRole("button")) {
      expect(button).toHaveClass("control-button", "window-control");
    }
    expect(screen.getByRole("button", { name: "Close window" })).toHaveClass(
      "window-control--close",
    );
    expect(onMinimize).toHaveBeenCalledOnce();
    expect(onClose).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: /maximize|restore/i })).not.toBeInTheDocument();
  });
});
