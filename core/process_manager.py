from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Mapping

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from winpty import PtyProcess as WinPtyProcess

READER_JOIN_MS = 250


def _qt_exit_code(raw: object) -> int:
    """Map a Windows exit status into a signed 32-bit int for Qt signals."""
    try:
        code = int(raw or 0)
    except (TypeError, ValueError):
        return 0
    if code > 2_147_483_647:
        code -= 0x1_0000_0000
    elif code < -2_147_483_648:
        code = 0
    return code


# ==========================================
# PTY READER
# ==========================================


class PtyReader(QObject):
    output_ready = Signal(str)
    finished = Signal(int)

    def __init__(self, process: WinPtyProcess) -> None:
        super().__init__()
        self._process = process
        self._reading = True

    @Slot()
    def run(self) -> None:
        status = 0
        try:
            while self._reading:
                if not self._is_alive():
                    break
                try:
                    self._read_available()
                except EOFError:
                    break

            self._drain_output()

            if hasattr(self._process, "exitstatus"):
                status = _qt_exit_code(getattr(self._process, "exitstatus"))
        except Exception:
            status = 1
        finally:
            self._close_pty()
            try:
                self.finished.emit(status)
            except OverflowError:
                self.finished.emit(1)

    def stop_reading(self) -> None:
        self._reading = False
        self._close_pty()

    def _read_available(self) -> None:
        try:
            chunk = self._process.read()
        except (EOFError, OSError):
            raise EOFError from None
        if chunk:
            self.output_ready.emit(str(chunk))

    def _drain_output(self) -> None:
        while self._reading:
            try:
                chunk = self._process.read()
            except (EOFError, OSError):
                break
            if chunk:
                self.output_ready.emit(str(chunk))

    def _close_pty(self) -> None:
        try:
            if hasattr(self._process, "close"):
                self._process.close()
        except (OSError, RuntimeError, EOFError):
            pass

    def _is_alive(self) -> bool:
        if hasattr(self._process, "isalive"):
            return bool(self._process.isalive())
        return True


# ==========================================
# PTY PROCESS
# ==========================================


class PtyProcess(QObject):
    output_ready = Signal(str)
    finished = Signal(int)

    def __init__(
        self,
        name: str,
        columns: int = 120,
        rows: int = 30,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.name = name
        self._columns = columns
        self._rows = rows
        self._process: WinPtyProcess | None = None
        self._thread: QThread | None = None
        self._reader: PtyReader | None = None
        self._exit_code = 0
        self._finished_emitted = False

    def start(
        self,
        command: list[str],
        cwd: str | Path | None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        if self.is_alive():
            return

        self._finished_emitted = False
        command_line = subprocess.list2cmdline(command)
        spawn_kwargs: dict[str, object] = {}
        if cwd:
            spawn_kwargs["cwd"] = str(cwd)
        if env:
            spawn_kwargs["env"] = dict(env)
        self._process = self._spawn(command_line, spawn_kwargs)
        self.resize(self._columns, self._rows)
        self._start_reader()

    def write(self, text: str) -> None:
        if not self._process or not self.is_alive():
            return
        try:
            self._process.write(text)
        except (OSError, RuntimeError, EOFError):
            return

    def request_interrupt(self) -> None:
        if not self._process or not self.is_alive():
            return
        self.write("\x03")

    def send_ctrl_c(self) -> None:
        if not self._process or not self.is_alive():
            return
        if hasattr(self._process, "sendintr"):
            try:
                self._process.sendintr()
                return
            except (OSError, RuntimeError, EOFError):
                pass
        self.request_interrupt()

    def resize(self, columns: int, rows: int) -> None:
        self._columns = max(20, columns)
        self._rows = max(5, rows)
        if not self._process or not self.is_alive():
            return

        try:
            if hasattr(self._process, "setwinsize"):
                self._process.setwinsize(self._rows, self._columns)
            elif hasattr(self._process, "set_size"):
                self._process.set_size(self._columns, self._rows)
        except (OSError, RuntimeError, EOFError):
            return

    def is_alive(self) -> bool:
        if not self._process or not hasattr(self._process, "isalive"):
            return False
        try:
            return bool(self._process.isalive())
        except (OSError, RuntimeError):
            return False

    def exit_code(self) -> int:
        if self._process and hasattr(self._process, "exitstatus"):
            return _qt_exit_code(getattr(self._process, "exitstatus"))
        return self._exit_code

    def disconnect_signals(self) -> None:
        self.blockSignals(True)
        try:
            self.output_ready.disconnect()
        except (RuntimeError, TypeError):
            pass
        try:
            self.finished.disconnect()
        except (RuntimeError, TypeError):
            pass

    def stop_reader(self) -> None:
        if self._reader:
            self._reader.stop_reading()
        thread = self._thread
        if thread and thread.isRunning():
            thread.quit()

    def join_reader(self, wait_ms: int = READER_JOIN_MS) -> None:
        """Block until the reader thread stops (app shutdown only)."""
        self.stop_reader()
        thread = self._thread
        if thread and thread.isRunning() and wait_ms > 0:
            thread.wait(wait_ms)

    def abandon(self, on_released: Callable[[], None] | None = None) -> None:
        """Detach from UI and delete once the reader thread has stopped (non-blocking)."""
        self.disconnect_signals()
        self.release_after_reader_stops(on_released)

    def release_after_reader_stops(self, on_released: Callable[[], None] | None = None) -> None:
        def finish() -> None:
            if on_released is not None:
                on_released()
            self.deleteLater()

        thread = self._thread
        if thread and thread.isRunning():
            thread.finished.connect(finish, Qt.ConnectionType.SingleShotConnection)
            return
        finish()

    def _spawn(self, command_line: str, kwargs: dict[str, object]) -> WinPtyProcess:
        try:
            return WinPtyProcess.spawn(
                command_line,
                dimensions=(self._rows, self._columns),
                **kwargs,
            )
        except TypeError:
            return WinPtyProcess.spawn(command_line, **kwargs)

    def _start_reader(self) -> None:
        if not self._process:
            return

        self._thread = QThread()
        self._reader = PtyReader(self._process)
        self._reader.moveToThread(self._thread)
        self._thread.started.connect(self._reader.run)
        self._reader.output_ready.connect(
            self.output_ready,
            Qt.ConnectionType.QueuedConnection,
        )
        self._reader.finished.connect(
            self._handle_finished,
            Qt.ConnectionType.QueuedConnection,
        )
        self._reader.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_reader_thread)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    @Slot(int)
    def _handle_finished(self, exit_code: int) -> None:
        if self._finished_emitted:
            return
        self._finished_emitted = True
        self._exit_code = exit_code
        self._process = None
        self.finished.emit(exit_code)

    @Slot()
    def _cleanup_reader_thread(self) -> None:
        self._reader = None
        self._thread = None
