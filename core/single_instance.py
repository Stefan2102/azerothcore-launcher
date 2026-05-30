from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QWidget

_INSTANCE_KEY = "AzerothCore.Launcher.SingleInstance"
_ACTIVATE = b"activate"


class SingleInstanceGuard(QObject):
    """Ensure only one launcher process; secondary starts activate the existing window."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._server: QLocalServer | None = None
        self._window: QWidget | None = None

    def try_acquire(self) -> bool:
        """Return True if this process is the primary instance."""
        socket = QLocalSocket()
        socket.connectToServer(_INSTANCE_KEY)
        if socket.waitForConnected(400):
            socket.write(_ACTIVATE)
            socket.flush()
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
            return False

        QLocalServer.removeServer(_INSTANCE_KEY)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_connection)
        return self._server.listen(_INSTANCE_KEY)

    def set_window(self, window: QWidget) -> None:
        self._window = window

    def _on_connection(self) -> None:
        if not self._server:
            return
        pending = self._server.nextPendingConnection()
        if not pending:
            return
        pending.readyRead.connect(lambda sock=pending: self._handle_activate(sock))

    def _handle_activate(self, socket: QLocalSocket) -> None:
        if socket.readAll() != _ACTIVATE or not self._window:
            return
        self._window.showMaximized()
        self._window.raise_()
        self._window.activateWindow()
