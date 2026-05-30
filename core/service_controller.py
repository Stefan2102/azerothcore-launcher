from __future__ import annotations

import os
import shutil
import subprocess
from enum import StrEnum
from pathlib import Path

from core.config_manager import LauncherConfig
from core.paths import resolve_config_path


# ==========================================
# SERVICES
# ==========================================


class ServiceId(StrEnum):
    MYSQL = "mysql"
    AUTHSERVER = "authserver"
    WORLDSERVER = "worldserver"
    OLLAMA = "ollama"


class ServiceDefinition:
    def __init__(
        self,
        service_id: ServiceId,
        title: str,
        accent: str,
        command: list[str],
        cwd: str | None,
    ) -> None:
        self.service_id = service_id
        self.title = title
        self.accent = accent
        self.command = command
        self.cwd = cwd


class ServiceConfigurationError(RuntimeError):
    pass


def build_service_definition(service_id: ServiceId, config: LauncherConfig) -> ServiceDefinition:
    if service_id == ServiceId.MYSQL:
        return build_mysql(config)
    if service_id == ServiceId.AUTHSERVER:
        return build_authserver(config)
    if service_id == ServiceId.WORLDSERVER:
        return build_worldserver(config)
    if service_id == ServiceId.OLLAMA:
        return build_ollama()
    raise ServiceConfigurationError(f"Unknown service: {service_id}")


def build_mysql(config: LauncherConfig) -> ServiceDefinition:
    binary = _required_executable(config.mysql_path, "MySQL path (mysqld.exe)")
    cwd = binary.parent.parent if binary.parent.name.lower() == "bin" else binary.parent
    return ServiceDefinition(
        ServiceId.MYSQL,
        "MySQL",
        "green",
        [str(binary), "--console"],
        str(cwd),
    )


def build_authserver(config: LauncherConfig) -> ServiceDefinition:
    binary = _required_executable(config.auth_server_path, "Auth Server path")
    return ServiceDefinition(
        ServiceId.AUTHSERVER,
        "Authserver",
        "blue",
        [str(binary)],
        str(binary.parent),
    )


def build_worldserver(config: LauncherConfig) -> ServiceDefinition:
    binary = _required_executable(config.world_server_path, "World Server path")
    return ServiceDefinition(
        ServiceId.WORLDSERVER,
        "Worldserver",
        "purple",
        [str(binary)],
        str(binary.parent),
    )


def build_ollama() -> ServiceDefinition:
    executable = shutil.which("ollama") or "ollama"
    return ServiceDefinition(
        ServiceId.OLLAMA,
        "Ollama",
        "orange",
        [executable, "serve"],
        None,
    )


def build_mysqladmin_shutdown(config: LauncherConfig) -> tuple[list[str], dict[str, str]]:
    mysqld = _required_executable(config.mysql_path, "MySQL path (mysqld.exe)")
    mysqladmin = mysqld.parent / "mysqladmin.exe"
    _required_file(mysqladmin, "mysqladmin.exe")
    env = dict(os.environ)
    env["MYSQL_PWD"] = config.sql_password()
    return [
        str(mysqladmin),
        "-h",
        config.sql_host,
        "-P",
        str(config.sql_port),
        "-u",
        config.sql_user,
        "shutdown",
    ], env


def launch_wow(config: LauncherConfig) -> None:
    if not config.client_path.strip():
        raise ServiceConfigurationError("Client Path is not configured.")
    binary = resolve_config_path(config.client_path)
    if not binary.is_file():
        raise ServiceConfigurationError(f"World of Warcraft executable not found: {binary}")
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [str(binary)],
        cwd=str(binary.parent),
        creationflags=flags,
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _required_executable(path_value: str, label: str) -> Path:
    if not path_value.strip():
        raise ServiceConfigurationError(f"{label} is not configured.")
    path = resolve_config_path(path_value)
    _required_file(path, label)
    return path


def _required_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise ServiceConfigurationError(f"{label} not found: {path}")
