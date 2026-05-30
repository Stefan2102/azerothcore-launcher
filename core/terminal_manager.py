from __future__ import annotations

from typing import Protocol

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal, Slot

from core.config_manager import ConfigManager
from core.paths import resolve_config_path
from core.process_manager import PtyProcess
from core.service_controller import (
    ServiceConfigurationError,
    ServiceId,
    build_mysqladmin_shutdown,
    build_service_definition,
    launch_wow,
)


# ==========================================
# TERMINAL REGISTRY
# ==========================================


class TerminalSurface(Protocol):
    def bind_process(self, process: PtyProcess | None) -> None: ...
    def append_output(self, text: str) -> None: ...
    def reset_for_start(self) -> None: ...
    def set_running(self, running: bool) -> None: ...
    def write_command(self, text: str) -> None: ...


_SHUTDOWN_ORDER: tuple[ServiceId, ...] = (
    ServiceId.WORLDSERVER,
    ServiceId.AUTHSERVER,
    ServiceId.MYSQL,
    ServiceId.OLLAMA,
)


class TerminalManager(QObject):
    service_state_changed = Signal(str, bool)
    service_error = Signal(str, str)
    wow_launch_failed = Signal(str)

    def __init__(self, config_manager: ConfigManager) -> None:
        super().__init__()
        self._config_manager = config_manager
        self._terminals: dict[ServiceId, TerminalSurface] = {}
        self._processes: dict[ServiceId, PtyProcess] = {}
        self._stopping: set[ServiceId] = set()
        self._finishing: set[ServiceId] = set()
        self._mysql_shutdown: QProcess | None = None
        self._state_timer = QTimer(self)
        self._state_timer.setInterval(1000)
        self._state_timer.timeout.connect(self._reconcile_processes)
        self._state_timer.start()

    def register(self, service_id: ServiceId, terminal: TerminalSurface) -> None:
        self._terminals[service_id] = terminal

    def start(self, service_id: ServiceId) -> None:
        if self.is_running(service_id):
            return

        self._abandon_process(self._processes.pop(service_id, None))

        terminal = self._terminal(service_id)
        process: PtyProcess | None = None
        try:
            definition = build_service_definition(service_id, self._config_manager.load())
            process = PtyProcess(definition.title, parent=self)
            self._wire_process(service_id, terminal, process)
            terminal.reset_for_start()
            process.start(definition.command, definition.cwd)
        except (ServiceConfigurationError, OSError, RuntimeError) as exc:
            self._fail_start(service_id, terminal, process, str(exc))
            return

        self._processes[service_id] = process
        self._stopping.discard(service_id)
        self._finishing.discard(service_id)
        terminal.set_running(True)
        self.service_state_changed.emit(service_id.value, True)

    def stop_service(self, service_id: ServiceId) -> None:
        if service_id in self._stopping:
            return

        process = self._processes.get(service_id)
        if not process or not process.is_alive():
            return

        terminal = self._terminal(service_id)
        self._stopping.add(service_id)

        try:
            if service_id == ServiceId.MYSQL:
                self._shutdown_mysql()
            elif service_id == ServiceId.WORLDSERVER:
                terminal.write_command("server shutdown 1")
            else:
                process.send_ctrl_c()
        except ServiceConfigurationError as exc:
            self._stopping.discard(service_id)
            self.service_error.emit(service_id.value, str(exc))

    def send_ctrl_c(self, service_id: ServiceId) -> None:
        self.stop_service(service_id)

    def toggle(self, service_id: ServiceId) -> None:
        if self.is_running(service_id):
            self.stop_service(service_id)
        else:
            self.start(service_id)

    def launch_world_of_warcraft(self) -> None:
        try:
            launch_wow(self._config_manager.load())
        except ServiceConfigurationError as exc:
            self.wow_launch_failed.emit(str(exc))
        except (OSError, RuntimeError) as exc:
            self.wow_launch_failed.emit(f"Failed to launch World of Warcraft: {exc}")

    def running_services(self) -> list[ServiceId]:
        return [service_id for service_id in _SHUTDOWN_ORDER if self.is_running(service_id)]

    def finalize_if_idle(self) -> None:
        self._state_timer.stop()
        if self._mysql_shutdown and self._mysql_shutdown.state() != QProcess.ProcessState.NotRunning:
            self._mysql_shutdown.kill()
            self._mysql_shutdown.waitForFinished(2000)
        self._cleanup_processes()

    def is_running(self, service_id: ServiceId) -> bool:
        process = self._processes.get(service_id)
        return bool(process and process.is_alive())

    def _wire_process(
        self,
        service_id: ServiceId,
        terminal: TerminalSurface,
        process: PtyProcess,
    ) -> None:
        process.output_ready.connect(
            lambda text, sid=service_id, term=terminal: self._on_process_output(sid, term, text)
        )
        process.finished.connect(
            lambda _code, sid=service_id: self._handle_finished(sid)
        )
        terminal.bind_process(process)

    def _fail_start(
        self,
        service_id: ServiceId,
        terminal: TerminalSurface,
        process: PtyProcess | None,
        message: str,
    ) -> None:
        self._abandon_process(process)
        self.service_error.emit(service_id.value, message)
        terminal.bind_process(None)
        terminal.set_running(False)
        self.service_state_changed.emit(service_id.value, False)

    def _abandon_process(self, process: PtyProcess | None) -> None:
        if process is None:
            return
        process.abandon()

    def _shutdown_mysql(self) -> None:
        config = self._config_manager.load()
        command, env = build_mysqladmin_shutdown(config)
        mysqld = resolve_config_path(config.mysql_path)
        cwd = mysqld.parent.parent if mysqld.parent.name.lower() == "bin" else mysqld.parent

        if self._mysql_shutdown and self._mysql_shutdown.state() != QProcess.ProcessState.NotRunning:
            return

        process = QProcess(self)
        process.setProgram(command[0])
        process.setArguments(command[1:])
        process.setWorkingDirectory(str(cwd))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        qenv = QProcessEnvironment.systemEnvironment()
        for key, value in env.items():
            qenv.insert(key, value)
        process.setProcessEnvironment(qenv)

        process.finished.connect(self._on_mysqladmin_finished)
        self._mysql_shutdown = process
        process.start()

    @Slot(int, QProcess.ExitStatus)
    def _on_mysqladmin_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        process = self._mysql_shutdown
        self._mysql_shutdown = None
        if process is None:
            return

        output = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace").strip()
        if exit_code == 0:
            return

        self._stopping.discard(ServiceId.MYSQL)
        message = f"mysqladmin shutdown failed with code {exit_code}."
        if output:
            message = f"{message}\n{output}"
        self.service_error.emit("mysql", message)

    def _cleanup_processes(self) -> None:
        for service_id in list(self._processes):
            process = self._processes.get(service_id)
            if process and not process.is_alive():
                self._handle_finished(service_id)
        for process in list(self._processes.values()):
            process.join_reader()
            process.abandon()
        self._processes.clear()
        self._stopping.clear()
        self._finishing.clear()

    def _terminal(self, service_id: ServiceId) -> TerminalSurface:
        return self._terminals[service_id]

    def _accepts_output(self, service_id: ServiceId) -> bool:
        return (
            service_id in self._processes
            or service_id in self._stopping
            or service_id in self._finishing
        )

    def _on_process_output(self, service_id: ServiceId, terminal: TerminalSurface, text: str) -> None:
        if not self._accepts_output(service_id):
            return
        try:
            terminal.append_output(text)
        except Exception:
            return

    @Slot()
    def _handle_finished(self, service_id: ServiceId) -> None:
        if service_id in self._finishing or service_id not in self._processes:
            return
        self._finishing.add(service_id)
        QTimer.singleShot(0, lambda: self._finalize_service_stop(service_id))

    def _finalize_service_stop(self, service_id: ServiceId) -> None:
        process = self._processes.pop(service_id, None)
        self._finishing.discard(service_id)
        if not process:
            return

        terminal = self._terminal(service_id)
        terminal.bind_process(None)
        terminal.set_running(False)
        self._stopping.discard(service_id)
        self.service_state_changed.emit(service_id.value, False)
        self._abandon_process(process)

    def _reconcile_processes(self) -> None:
        if not self._processes:
            return
        for service_id, process in list(self._processes.items()):
            if service_id in self._processes and service_id not in self._finishing and not process.is_alive():
                self._handle_finished(service_id)
