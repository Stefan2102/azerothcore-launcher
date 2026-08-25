import type { ServiceId } from "../types/launcher";

const MAX_PENDING_TERMINAL_CHARACTERS = 1_048_576;

export interface TerminalOutputSink {
  write: (text: string) => void;
}

export class TerminalOutputRouter {
  private readonly sinks = new Map<ServiceId, TerminalOutputSink>();
  private readonly pending = new Map<ServiceId, string>();

  attach(serviceId: ServiceId, sink: TerminalOutputSink | null): void {
    if (!sink) {
      this.sinks.delete(serviceId);
      return;
    }

    this.sinks.set(serviceId, sink);
    const buffered = this.pending.get(serviceId);
    if (buffered) {
      // A terminal can temporarily detach during a React commit. Flush its
      // backlog as one ordered write as soon as the replacement is available.
      sink.write(buffered);
      this.pending.delete(serviceId);
    }
  }

  write(serviceId: ServiceId, text: string): void {
    const sink = this.sinks.get(serviceId);
    if (sink) {
      sink.write(text);
      return;
    }

    // Startup output can arrive immediately after the process is spawned and
    // before React attaches the imperative xterm handle. Keep a bounded tail so
    // that timing never turns a successful native read into a blank panel.
    const buffered = (this.pending.get(serviceId) ?? "") + text;
    this.pending.set(
      serviceId,
      buffered.slice(-MAX_PENDING_TERMINAL_CHARACTERS),
    );
  }

  clear(serviceId: ServiceId): void {
    this.pending.delete(serviceId);
  }
}
