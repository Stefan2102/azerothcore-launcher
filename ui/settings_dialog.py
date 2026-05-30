from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.config_manager import ConfigManager, LauncherConfig
from core.paths import resolve_config_path
from ui.logo import make_window_icon


# ==========================================
# SETTINGS DIALOG
# ==========================================


class SettingsDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config_manager = config_manager
        self._config = config_manager.load()
        self._hints: dict[str, QLabel] = {}
        self.setObjectName("SettingsDialog")
        self.setWindowTitle("Settings")
        self.setWindowIcon(make_window_icon())
        self.setMinimumWidth(720)
        self._build_ui()
        self._load_values()
        self._validate()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(18)

        title = QLabel("Launcher Settings", self)
        title.setObjectName("DialogTitle")
        root.addWidget(title)

        panel = QFrame(self)
        panel.setObjectName("SettingsPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        db_grid = self._add_section(layout, "Database Connection Configuration")
        self.sql_host = self._add_field(db_grid, 0, "SQL Server IP:", "sql_host", placeholder="127.0.0.1")
        self.sql_port = self._add_port_field(db_grid, 1, "SQL Server Port:", "sql_port")
        self.sql_user = self._add_field(db_grid, 2, "SQL Server User:", "sql_user", placeholder="acore")
        self.sql_password = self._add_password_field(db_grid, 3, "SQL Server Password:", "sql_password")

        client_grid = self._add_section(layout, "Client Path Configuration")
        self.client_path = self._add_file_row(client_grid, 0, "Client Path:", "client_path", "World of Warcraft executable")

        server_grid = self._add_section(layout, "Server Configuration")
        self.mysql_path = self._add_file_row(server_grid, 0, "MySQL (mysqld.exe):", "mysql_path", "mysqld.exe")
        self.auth_server_path = self._add_file_row(
            server_grid, 1, "Authserver (authserver.exe):", "auth_server_path", "authserver.exe"
        )
        self.world_server_path = self._add_file_row(
            server_grid, 2, "Worldserver (worldserver.exe):", "world_server_path", "worldserver.exe"
        )

        root.addWidget(panel)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("Cancel", self)
        cancel.setObjectName("SecondaryButton")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save", self)
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self._save)
        actions.addWidget(cancel)
        actions.addWidget(save)
        root.addLayout(actions)

    def _add_section(self, parent_layout: QVBoxLayout, title: str) -> QGridLayout:
        heading = QLabel(title, self)
        heading.setObjectName("SettingsSection")
        parent_layout.addWidget(heading)

        section = QFrame(self)
        section.setObjectName("SettingsSectionPanel")
        grid = QGridLayout(section)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        parent_layout.addWidget(section)
        return grid

    def _add_field(
        self,
        grid: QGridLayout,
        row: int,
        label_text: str,
        key: str,
        placeholder: str = "",
    ) -> QLineEdit:
        label = QLabel(label_text, self)
        label.setObjectName("SettingsLabel")
        field = QLineEdit(self)
        field.setObjectName("SettingsField")
        field.setPlaceholderText(placeholder)
        hint = QLabel("", self)
        hint.setObjectName("SettingsHint")
        field.textChanged.connect(self._validate)

        grid.addWidget(label, row * 2, 0)
        grid.addWidget(field, row * 2, 1)
        grid.addWidget(hint, row * 2 + 1, 1)
        self._hints[key] = hint
        return field

    def _add_port_field(self, grid: QGridLayout, row: int, label_text: str, key: str) -> QSpinBox:
        label = QLabel(label_text, self)
        label.setObjectName("SettingsLabel")
        field = QSpinBox(self)
        field.setObjectName("SettingsSpin")
        field.setRange(1, 65535)
        field.setValue(3306)
        hint = QLabel("", self)
        hint.setObjectName("SettingsHint")
        field.valueChanged.connect(self._validate)

        grid.addWidget(label, row * 2, 0)
        grid.addWidget(field, row * 2, 1)
        grid.addWidget(hint, row * 2 + 1, 1)
        self._hints[key] = hint
        return field

    def _add_password_field(self, grid: QGridLayout, row: int, label_text: str, key: str) -> QLineEdit:
        field = self._add_field(grid, row, label_text, key, placeholder="acore")
        field.setEchoMode(QLineEdit.EchoMode.Password)
        return field

    def _add_file_row(
        self,
        grid: QGridLayout,
        row: int,
        label_text: str,
        key: str,
        dialog_title: str,
    ) -> QLineEdit:
        label = QLabel(label_text, self)
        label.setObjectName("SettingsLabel")
        field = QLineEdit(self)
        field.setObjectName("SettingsField")
        browse = QPushButton("Browse...", self)
        browse.setObjectName("BrowseButton")
        hint = QLabel("", self)
        hint.setObjectName("SettingsHint")
        browse.clicked.connect(lambda checked=False, target=field, title=dialog_title: self._browse_file(target, title))
        field.textChanged.connect(self._validate)

        grid.addWidget(label, row * 2, 0)
        grid.addWidget(field, row * 2, 1)
        grid.addWidget(browse, row * 2, 2)
        grid.addWidget(hint, row * 2 + 1, 1, 1, 2)
        self._hints[key] = hint
        return field

    def _load_values(self) -> None:
        self.sql_host.setText(self._config.sql_host)
        self.sql_port.setValue(self._config.sql_port)
        self.sql_user.setText(self._config.sql_user)
        self.sql_password.setText(self._config.sql_password())
        self.client_path.setText(self._config.client_path)
        self.mysql_path.setText(self._config.mysql_path)
        self.auth_server_path.setText(self._config.auth_server_path)
        self.world_server_path.setText(self._config.world_server_path)

    def _browse_file(self, target: QLineEdit, title: str) -> None:
        start_dir = str(Path(target.text()).parent) if target.text() else str(Path.home())
        selected, _ = QFileDialog.getOpenFileName(self, title, start_dir, "Executables (*.exe);;All files (*.*)")
        if selected:
            target.setText(selected)

    def _validate(self) -> None:
        checks = {
            "sql_host": (self.sql_host.text().strip(), lambda value: bool(value), "SQL Server IP is required."),
            "sql_port": (str(self.sql_port.value()), lambda _: True, ""),
            "sql_user": (self.sql_user.text().strip(), lambda value: bool(value), "SQL Server User is required."),
            "sql_password": (self.sql_password.text(), lambda _: True, ""),
            "client_path": (
                self.client_path.text().strip(),
                lambda value: not value or resolve_config_path(value).is_file(),
                "Executable not found at this path.",
            ),
            "mysql_path": (
                self.mysql_path.text().strip(),
                lambda value: not value or resolve_config_path(value).is_file(),
                "mysqld.exe not found at this path.",
            ),
            "auth_server_path": (
                self.auth_server_path.text().strip(),
                lambda value: not value or resolve_config_path(value).is_file(),
                "authserver.exe not found at this path.",
            ),
            "world_server_path": (
                self.world_server_path.text().strip(),
                lambda value: not value or resolve_config_path(value).is_file(),
                "worldserver.exe not found at this path.",
            ),
        }

        for key, (value, is_valid, message) in checks.items():
            hint = self._hints[key]
            if not value:
                hint.setText("")
                continue
            hint.setText("" if is_valid(value) else message)

    def _save(self) -> None:
        config = LauncherConfig(
            sql_host=self.sql_host.text().strip() or "127.0.0.1",
            sql_port=self.sql_port.value(),
            sql_user=self.sql_user.text().strip() or "acore",
            sql_password_encrypted="",
            client_path=self.client_path.text().strip(),
            mysql_path=self.mysql_path.text().strip() or r".\mysql\bin\mysqld.exe",
            auth_server_path=self.auth_server_path.text().strip() or r".\authserver.exe",
            world_server_path=self.world_server_path.text().strip() or r".\worldserver.exe",
        )
        config.set_sql_password(self.sql_password.text())
        config.settings_completed = True
        self._config_manager.save(config)
        self.accept()
