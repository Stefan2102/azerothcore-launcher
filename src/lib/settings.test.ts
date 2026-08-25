import { describe, expect, it } from "vitest";
import { fieldError } from "./settings";

describe("settings", () => {
  it("accepts valid connection values", () => {
    expect(fieldError("sqlHost", "127.0.0.1")).toBe("");
  });

  it("rejects missing connection identity and out-of-range ports", () => {
    expect(fieldError("sqlHost", "")).toBe("SQL Server IP is required.");
    expect(fieldError("sqlUser", " ")).toBe("SQL Server User is required.");
    expect(fieldError("sqlPort", 65536)).toBe(
      "Port must be between 1 and 65535.",
    );
  });
});
