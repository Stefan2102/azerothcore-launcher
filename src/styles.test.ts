import { describe, expect, it } from "vitest";
import styles from "./styles.css?raw";

describe("forged-glass control styles", () => {
  it("defines one fixed Icy Blue palette while keeping terminal surfaces dark", () => {
    expect(styles).toContain("--canvas: #041a33");
    expect(styles).toContain("--workspace-background: #061f3b");
    expect(styles).toMatch(
      /\.terminal-grid\s*\{[\s\S]*?background: var\(--workspace-background\);/,
    );
    expect(styles).toMatch(
      /\.terminal-panel\s*\{[\s\S]*?background: linear-gradient\(180deg, var\(--panel-top\), var\(--panel-bottom\)\);/,
    );
    expect(styles).toContain("--terminal: #04172a");
    expect(styles).not.toContain("brightFrost");
    expect(styles).not.toContain("midnightFrost");
    expect(styles).not.toContain("--brand-red");
    expect(styles).not.toContain("--burgundy");
  });

  it("does not retain the removed theme-picker styling", () => {
    expect(styles).not.toContain(".theme-options");
    expect(styles).not.toContain(".theme-option");
  });

  it("separates the brand from controls with a non-interactive divider", () => {
    expect(styles).toContain("--brand-divider: rgb(var(--accent-rgb) / 24%)");
    expect(styles).toMatch(
      /\.brand\s*\{[\s\S]*?position: relative;[\s\S]*?min-height: 174px;[\s\S]*?margin-bottom: 18px;[\s\S]*?padding-bottom: 8px;/,
    );
    expect(styles).toMatch(
      /\.brand::after\s*\{[\s\S]*?background: linear-gradient\([\s\S]*?var\(--brand-divider\)[\s\S]*?pointer-events: none;/,
    );
  });

  it("does not add an outer glow to running terminal panels", () => {
    const runningRule = styles.match(
      /\.terminal-panel\[data-state="running"\]\s*\{([^}]*)\}/,
    )?.[1];

    expect(runningRule).toBeDefined();
    expect(runningRule).toContain("border-color: var(--border)");
    expect(runningRule).not.toContain("0 0 17px");
    expect(runningRule).toContain("0 7px 22px var(--panel-shadow)");
  });

  it("centralizes compact geometry and interaction timing", () => {
    expect(styles).toContain("--control-motion-fast: 130ms");
    expect(styles).toContain("--control-motion: 150ms");
    expect(styles).toMatch(/\.side-button\s*\{[\s\S]*?height: 44px;/);
    expect(styles).toMatch(/\.sidebar__actions,[\s\S]*?gap: 7px;/);
    expect(styles).toMatch(
      /\.settings-form__actions \.button\s*\{[\s\S]*?min-width: 80px;[\s\S]*?height: 34px;/,
    );
  });

  it("uses calm section dividers instead of outlined settings fieldsets", () => {
    expect(styles).toContain("--settings-divider: rgb(45 225 255 / 25%)");
    expect(styles).toContain("--settings-heading: #dff9ff");
    expect(styles).toContain("--settings-description: #8ebcd0");
    expect(styles).toMatch(
      /\.settings-section \+ \.settings-section\s*\{[\s\S]*?border-top: 1px solid var\(--settings-divider\);/,
    );
    expect(styles).not.toContain(".settings-section legend");
    expect(styles).not.toContain("--section-background");
  });

  it("keeps settings fields readable while tightening their vertical rhythm", () => {
    expect(styles).toMatch(
      /\.settings-field input\s*\{[\s\S]*?font-size: 13px;/,
    );
    expect(styles).toMatch(
      /\.settings-section__fields\s*\{[\s\S]*?gap: 6px 14px;/,
    );
    expect(styles).toMatch(
      /\.settings-section--paths \.settings-section__fields\s*\{[\s\S]*?gap: 8px;/,
    );
    expect(styles).toContain(".settings-password-toggle");
  });

  it("keeps field focus inside the existing control boundary", () => {
    expect(styles).toMatch(/input:focus-visible\s*\{\s*outline: none;/);
    expect(styles).toContain("--important-action-top: #1a9dcc");
    expect(styles).toMatch(/\.button--primary,[\s\S]*?\.button--danger\s*\{/);
    expect(styles).toContain(".terminal-panel__host .xterm-rows");
  });

  it("owns modal scrollbar rendering without native arrow controls", () => {
    expect(styles).toContain("--ui-scrollbar-thumb: #1678a9");
    expect(styles).not.toContain("scrollbar-gutter: stable");
    expect(styles).toMatch(/\.modal::-webkit-scrollbar\s*\{[\s\S]*?width: 7px;/);
    expect(styles).toContain(".modal::-webkit-scrollbar-thumb:hover");
    expect(styles).toContain(".modal::-webkit-scrollbar-button");
    expect(styles).toMatch(
      /\.modal::-webkit-scrollbar-button,[\s\S]*?display: none;/,
    );
    expect(styles).toContain(".modal::backdrop");
    expect(styles).not.toContain(".modal-backdrop");
  });

  it("keeps settings number fields spinner-free and modal controls aligned", () => {
    expect(styles).toMatch(
      /\.settings-field input\[type="number"\]\s*\{[\s\S]*?appearance: textfield;/,
    );
    expect(styles).toContain(
      ".settings-field input[type=\"number\"]::-webkit-inner-spin-button",
    );
    expect(styles).toMatch(
      /\.modal__header\s*\{[\s\S]*?padding: 18px 10px 18px 20px;/,
    );
  });

  it("keeps service transition surfaces inside the selected palette", () => {
    expect(styles).toContain("--control-transition-top");
    expect(styles).toContain("--control-transition-bottom");
    expect(styles).toMatch(
      /\.side-button\[data-transitioning="true"\][\s\S]*?var\(--control-transition-top\)[\s\S]*?var\(--control-transition-bottom\)/,
    );
    expect(styles).toMatch(
      /\.side-button\[data-transitioning="true"\]::before[\s\S]*?background: var\(--accent\);/,
    );
  });

  it("provides hover, press, transition, and reduced-motion states", () => {
    expect(styles).toContain(".control-button:hover:not(:disabled)");
    expect(styles).toContain(".control-button:active:not(:disabled)");
    expect(styles).toContain(".control-button:disabled");
    expect(styles).toContain("button:focus-visible");
    expect(styles).toContain('.side-button[data-transitioning="true"]');
    expect(styles).toContain("@media (prefers-reduced-motion: reduce)");
    expect(styles).toContain("transform: none !important");
  });
});
