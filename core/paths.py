from __future__ import annotations

import os
import sys
from pathlib import Path


# ==========================================
# PATHS
# ==========================================

APP_NAME = "AzerothCore Launcher"


def appdata_dir() -> Path:
    base = os.environ.get("APPDATA")
    if not base:
        base = str(Path.home() / "AppData" / "Roaming")
    return Path(base) / APP_NAME


def config_path() -> Path:
    return appdata_dir() / "config.json"


def resource_path(*parts: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return root.joinpath(*parts)


def project_path(*parts: str) -> Path:
    return Path(__file__).resolve().parents[1].joinpath(*parts)


def launcher_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def resolve_config_path(path_value: str) -> Path:
    path = Path(path_value.strip())
    if not path_value.strip():
        return path
    if path.is_absolute():
        return path.resolve()
    return (launcher_base_dir() / path).resolve()
