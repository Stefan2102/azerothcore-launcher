import { beforeEach, describe, expect, it, vi } from "vitest";

const invoke = vi.fn();
const channels: Array<{ onmessage: (event: unknown) => void }> = [];

vi.mock("@tauri-apps/api/core", () => ({
  invoke,
  Channel: class {
    onmessage = () => undefined;
    constructor() {
      channels.push(this);
    }
  },
}));

describe("backend subscription", () => {
  beforeEach(() => {
    invoke.mockReset();
    channels.length = 0;
  });

  it("passes channel events to React and releases its callback", async () => {
    invoke.mockResolvedValue({
      services: [],
      needsFirstRunSetup: false,
    });
    const onEvent = vi.fn();
    const { initializeBackend } = await import("./backend");

    const subscription = await initializeBackend(onEvent);
    const event = { event: "output", data: { serviceId: "mysql", text: "ready" } };
    channels[0].onmessage(event);
    expect(onEvent).toHaveBeenCalledWith(event);

    subscription.dispose();
    channels[0].onmessage(event);
    expect(onEvent).toHaveBeenCalledTimes(1);
  });
});
