from __future__ import annotations

import sys
import signal
from ctypes import WINFUNCTYPE, windll
from ctypes.wintypes import BOOL, DWORD

from PySide6.QtWidgets import QApplication

from core.config_manager import ConfigManager
from core.paths import resource_path
from core.single_instance import SingleInstanceGuard
from ui.logo import make_window_icon
from ui.main_window import MainWindow


# ==========================================
# APPLICATION
# ==========================================

_CTRL_HANDLER = None


def _protect_gui_from_console_events() -> None:
    """Keep console control events (often raised when a ConPTY child exits) from killing the GUI."""
    if sys.platform != "win32":
        return

    kernel32 = windll.kernel32
    try:
        kernel32.FreeConsole()
    except OSError:
        pass

    @WINFUNCTYPE(BOOL, DWORD)
    def handler(_event: int) -> bool:
        return True

    global _CTRL_HANDLER
    _CTRL_HANDLER = handler
    kernel32.SetConsoleCtrlHandler(_CTRL_HANDLER, True)


def main() -> int:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, signal.SIG_IGN)
    _protect_gui_from_console_events()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    app.setApplicationName("AzerothCore Launcher")
    app.setOrganizationName("AzerothCore Launcher")
    app.setStyle("Fusion")
    app.setWindowIcon(make_window_icon())

    theme_path = resource_path("ui", "theme.qss")
    if theme_path.exists():
        app.setStyleSheet(theme_path.read_text(encoding="utf-8"))

    instance_guard = SingleInstanceGuard()
    if not instance_guard.try_acquire():
        return 0

    config_manager = ConfigManager()
    config_manager.load()

    window = MainWindow(config_manager)
    instance_guard.set_window(window)
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
