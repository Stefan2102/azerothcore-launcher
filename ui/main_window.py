from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QMainWindow, QMessageBox, QWidget

from core.config_manager import ConfigManager
from core.service_controller import ServiceId
from core.terminal_manager import TerminalManager
from ui.logo import make_window_icon
from ui.settings_dialog import SettingsDialog
from ui.sidebar import Sidebar
from ui.terminal_widget import TerminalWidget

_SERVICE_LABELS: dict[ServiceId, str] = {
    ServiceId.WORLDSERVER: "Worldserver",
    ServiceId.AUTHSERVER: "Authserver",
    ServiceId.MYSQL: "MySQL",
    ServiceId.OLLAMA: "Ollama",
}


# ==========================================
# MAIN WINDOW
# ==========================================


class MainWindow(QMainWindow):
    def __init__(self, config_manager: ConfigManager) -> None:
        super().__init__()
        self._config_manager = config_manager
        self._terminal_manager = TerminalManager(config_manager)
        self._terminals: dict[ServiceId, TerminalWidget] = {}
        self.setObjectName("MainWindow")
        self.setWindowTitle("AzerothCore Launcher")
        self.setWindowIcon(make_window_icon())
        self.setMinimumSize(1180, 720)
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self._build_ui()
        self._wire_events()
        self._open_settings_on_first_run()

    def closeEvent(self, event: QCloseEvent) -> None:
        running = self._terminal_manager.running_services()
        if not running:
            self._terminal_manager.finalize_if_idle()
            super().closeEvent(event)
            return

        names = "\n".join(
            f"  • {_SERVICE_LABELS.get(service_id, service_id.value)}"
            for service_id in running
        )
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("Services still running")
        dialog.setText(
            "Some services are still running and should be shut down before you close the launcher."
        )
        dialog.setInformativeText(names)
        quit_button = dialog.addButton("Exit anyway", QMessageBox.ButtonRole.AcceptRole)
        cancel_button = dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(cancel_button)
        dialog.exec()

        if dialog.clickedButton() is cancel_button:
            event.ignore()
            return

        self._terminal_manager.finalize_if_idle()
        super().closeEvent(event)

    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("Central")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar(central)
        root.addWidget(self.sidebar)

        self.content = QFrame(central)
        self.content.setObjectName("Content")
        root.addWidget(self.content, 1)

        grid = QGridLayout(self.content)
        grid.setContentsMargins(20, 26, 20, 20)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self._add_terminal(grid, ServiceId.MYSQL, "MySQL", "green", 0, 0)
        self._add_terminal(grid, ServiceId.AUTHSERVER, "Authserver", "blue", 0, 1)
        self._add_terminal(grid, ServiceId.WORLDSERVER, "Worldserver", "purple", 1, 0)
        self._add_terminal(grid, ServiceId.OLLAMA, "Ollama", "orange", 1, 1)

    def _add_terminal(
        self,
        grid: QGridLayout,
        service_id: ServiceId,
        title: str,
        accent: str,
        row: int,
        column: int,
    ) -> None:
        terminal = TerminalWidget(
            title,
            accent,
            input_enabled=service_id == ServiceId.WORLDSERVER,
            parent=self.content,
        )
        self._terminals[service_id] = terminal
        self._terminal_manager.register(service_id, terminal)
        terminal.ctrl_c_requested.connect(lambda sid=service_id: self._terminal_manager.send_ctrl_c(sid))
        grid.addWidget(terminal, row, column)

    def _wire_events(self) -> None:
        self.sidebar.service_requested.connect(self._terminal_manager.toggle)
        self.sidebar.wow_requested.connect(self._terminal_manager.launch_world_of_warcraft)
        self.sidebar.exit_requested.connect(self.close)
        self.sidebar.settings_requested.connect(self._open_settings)
        self._terminal_manager.service_state_changed.connect(self._handle_service_state)
        self._terminal_manager.wow_launch_failed.connect(self._handle_wow_error)
        self._terminal_manager.service_error.connect(self._handle_service_error)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._config_manager, self)
        dialog.exec()

    def _open_settings_on_first_run(self) -> None:
        config = self._config_manager.load()
        if not config.needs_first_run_setup():
            return
        QTimer.singleShot(350, self._open_settings)

    def _handle_service_state(self, service_value: str, running: bool) -> None:
        service_id = ServiceId(service_value)
        self.sidebar.set_service_running(service_id, running)

    def _handle_wow_error(self, message: str) -> None:
        QMessageBox.warning(self, "World of Warcraft", message)

    def _handle_service_error(self, service_value: str, message: str) -> None:
        QMessageBox.warning(self, service_value.title(), message)
