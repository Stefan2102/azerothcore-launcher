import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { createIdleStates } from "../types/launcher";
import { Sidebar } from "./Sidebar";

describe("Sidebar", () => {
  it("requests a service action and reflects running state", () => {
    const onServiceAction = vi.fn();
    const states = { ...createIdleStates(), mysql: "running" as const };
    render(
      <Sidebar
        onExit={vi.fn()}
        onLaunchWow={vi.fn()}
        onOpenSettings={vi.fn()}
        onServiceAction={onServiceAction}
        states={states}
      />,
    );

    const mysql = screen.getByRole("button", { name: "Stop MySQL" });
    expect(mysql).toHaveClass("control-button", "side-button");
    expect(mysql).toHaveAttribute("data-running", "true");
    fireEvent.click(mysql);
    expect(onServiceAction).toHaveBeenCalledWith("mysql");
  });

  it("disables a service button during transitions", () => {
    render(
      <Sidebar
        onExit={vi.fn()}
        onLaunchWow={vi.fn()}
        onOpenSettings={vi.fn()}
        onServiceAction={vi.fn()}
        states={{ ...createIdleStates(), ollama: "stopping" }}
      />,
    );
    const ollama = screen.getByRole("button", { name: "Stopping Ollama" });
    expect(ollama).toBeDisabled();
    expect(ollama).toHaveAttribute("data-transitioning", "true");
  });

  it("uses shared controls and reserves the danger variant for exit", () => {
    render(
      <Sidebar
        onExit={vi.fn()}
        onLaunchWow={vi.fn()}
        onOpenSettings={vi.fn()}
        onServiceAction={vi.fn()}
        states={createIdleStates()}
      />,
    );

    for (const button of screen.getAllByRole("button")) {
      expect(button).toHaveClass("control-button", "side-button");
    }
    expect(screen.getByRole("button", { name: "Exit" })).toHaveClass(
      "side-button--danger",
    );
    expect(screen.getByRole("button", { name: "Settings" })).not.toHaveClass(
      "side-button--danger",
    );
  });

  it("keeps the brand non-interactive in a fixed maximized window", () => {
    const { container } = render(
      <Sidebar
        onExit={vi.fn()}
        onLaunchWow={vi.fn()}
        onOpenSettings={vi.fn()}
        onServiceAction={vi.fn()}
        states={createIdleStates()}
      />,
    );

    const brand = container.querySelector(".brand");
    expect(brand).not.toHaveAttribute("data-tauri-drag-region");
    expect(screen.getByAltText("AzerothCore")).toHaveAttribute(
      "draggable",
      "false",
    );
  });
});
