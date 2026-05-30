from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.paths import config_path
from core.secrets import decrypt_password, encrypt_password


# ==========================================
# CONFIGURATION
# ==========================================


@dataclass(slots=True)
class LauncherConfig:
    sql_host: str = "127.0.0.1"
    sql_port: int = 3306
    sql_user: str = "acore"
    sql_password_encrypted: str = ""

    client_path: str = ""

    mysql_path: str = r".\mysql\bin\mysqld.exe"
    auth_server_path: str = r".\authserver.exe"
    world_server_path: str = r".\worldserver.exe"
    settings_completed: bool = False

    def sql_password(self) -> str:
        if not self.sql_password_encrypted:
            return "acore"
        return decrypt_password(self.sql_password_encrypted)

    def set_sql_password(self, plain_text: str) -> None:
        self.sql_password_encrypted = encrypt_password(plain_text) if plain_text else ""

    def needs_first_run_setup(self) -> bool:
        return not self.settings_completed


class ConfigManager:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or config_path()

    def load(self) -> LauncherConfig:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            config = LauncherConfig()
            config.set_sql_password("acore")
            config.settings_completed = False
            self.save(config)
            return config

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}

        return self._from_mapping(data)

    def save(self, config: LauncherConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._to_mapping(config), indent=2, ensure_ascii=False)
        tmp_path = self.path.with_suffix(".json.tmp")
        tmp_path.write_text(payload + "\n", encoding="utf-8")
        os.replace(tmp_path, self.path)

    @staticmethod
    def _to_mapping(config: LauncherConfig) -> dict[str, Any]:
        return {
            "sql_host": config.sql_host,
            "sql_port": config.sql_port,
            "sql_user": config.sql_user,
            "sql_password_encrypted": config.sql_password_encrypted,
            "client_path": config.client_path,
            "mysql_path": config.mysql_path,
            "auth_server_path": config.auth_server_path,
            "world_server_path": config.world_server_path,
            "settings_completed": config.settings_completed,
        }

    @staticmethod
    def _from_mapping(data: dict[str, Any]) -> LauncherConfig:
        if "mysql_path" in data or "sql_host" in data:
            return LauncherConfig(
                sql_host=str(data.get("sql_host", "127.0.0.1") or "127.0.0.1"),
                sql_port=int(data.get("sql_port", 3306) or 3306),
                sql_user=str(data.get("sql_user", "acore") or "acore"),
                sql_password_encrypted=str(data.get("sql_password_encrypted", "") or ""),
                client_path=str(data.get("client_path", "") or ""),
                mysql_path=str(data.get("mysql_path", r".\mysql\bin\mysqld.exe") or r".\mysql\bin\mysqld.exe"),
                auth_server_path=str(data.get("auth_server_path", r".\authserver.exe") or r".\authserver.exe"),
                world_server_path=str(data.get("world_server_path", r".\worldserver.exe") or r".\worldserver.exe"),
                settings_completed=bool(data.get("settings_completed", False)),
            )

        return ConfigManager._migrate_legacy(data)

    @staticmethod
    def _migrate_legacy(data: dict[str, Any]) -> LauncherConfig:
        config = LauncherConfig()
        mysql_dir = str(data.get("mysql_dir", "") or "")
        server_dir = str(data.get("server_dir", "") or "")
        wow_dir = str(data.get("wow_dir", "") or "")

        if mysql_dir:
            config.mysql_path = str(Path(mysql_dir) / "bin" / "mysqld.exe")
        if server_dir:
            config.auth_server_path = str(Path(server_dir) / "authserver.exe")
            config.world_server_path = str(Path(server_dir) / "worldserver.exe")
        if wow_dir:
            wow_exe = Path(wow_dir) / "Wow.exe"
            config.client_path = str(wow_exe) if wow_exe.is_file() else wow_dir

        if not config.sql_password_encrypted:
            config.set_sql_password("acore")
        return config
