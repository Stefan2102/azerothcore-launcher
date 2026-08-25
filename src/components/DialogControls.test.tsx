import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AlertDialog } from "./AlertDialog";
import { ExitDialog } from "./ExitDialog";
import { Modal } from "./Modal";

describe("dialog controls", () => {
  it("uses the shared icon control for modal close", () => {
    const onClose = vi.fn();
    render(
      <Modal onClose={onClose} title="Example">
        <p>Content</p>
      </Modal>,
    );

    const close = screen.getByRole("button", { name: "Close dialog" });
    expect(close).toHaveClass("control-button", "icon-button");
    fireEvent.click(close);
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("uses native cancellation and restores prior focus", () => {
    const origin = document.createElement("button");
    document.body.appendChild(origin);
    origin.focus();
    const onClose = vi.fn();
    const { unmount } = render(
      <Modal onClose={onClose} title="Native modal">
        <button type="button">Inside</button>
      </Modal>,
    );
    const dialog = screen.getByRole("dialog", { name: "Native modal" });

    fireEvent(dialog, new Event("cancel", { bubbles: false, cancelable: true }));
    expect(onClose).toHaveBeenCalledOnce();
    unmount();
    expect(origin).toHaveFocus();
    origin.remove();
  });

  it("routes cancellation only to the active stacked dialog", () => {
    const lowerClose = vi.fn();
    const upperClose = vi.fn();
    render(
      <>
        <Modal onClose={lowerClose} title="Lower dialog">
          <p>Lower</p>
        </Modal>
        <Modal onClose={upperClose} title="Upper dialog">
          <p>Upper</p>
        </Modal>
      </>,
    );

    const upper = screen.getByRole("dialog", { name: "Upper dialog" });
    fireEvent(upper, new Event("cancel", { bubbles: false, cancelable: true }));

    expect(upperClose).toHaveBeenCalledOnce();
    expect(lowerClose).not.toHaveBeenCalled();
  });

  it("uses the polished primary action for alerts", () => {
    render(
      <AlertDialog
        message="Something happened."
        onClose={vi.fn()}
        title="Alert"
      />,
    );

    expect(screen.getByRole("button", { name: "OK" })).toHaveClass(
      "control-button",
      "button",
      "button--primary",
    );
  });

  it("keeps cancel secondary and forced exit destructive", () => {
    const onCancel = vi.fn();
    const onConfirm = vi.fn();
    render(
      <ExitDialog
        onCancel={onCancel}
        onConfirm={onConfirm}
        services={["mysql"]}
      />,
    );

    const cancel = screen.getByRole("button", { name: "Cancel" });
    const confirm = screen.getByRole("button", { name: "Exit anyway" });
    expect(cancel).toHaveClass("control-button", "button--secondary");
    expect(confirm).toHaveClass("control-button", "button--danger");
    fireEvent.click(cancel);
    fireEvent.click(confirm);
    expect(onCancel).toHaveBeenCalledOnce();
    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
