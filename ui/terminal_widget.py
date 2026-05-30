from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal, QStringListModel
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QKeyEvent,
    QKeySequence,
    QTextCharFormat,
    QTextCursor,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QCompleter,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_ACCOUNT_TEMPLATES = (
    "account create name password",
    "account set gmlevel name 3 -1",
)

from core.process_manager import PtyProcess
from ui.terminal_emulator import StyledRun, TerminalEmulator


TERMINAL_FONT_FAMILY = "Cascadia Mono"
TERMINAL_FONT_POINT_SIZE = 9
MIN_TERMINAL_COLUMNS = 40


# ==========================================
# OUTPUT VIEW
# ==========================================


class TerminalOutput(QPlainTextEdit):
    ctrl_c_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setUndoRedoEnabled(False)
        self.setObjectName("TerminalOutput")
        font = QFont(TERMINAL_FONT_FAMILY, TERMINAL_FONT_POINT_SIZE)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.setFont(font)
        self.document().setDocumentMargin(6)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        is_ctrl_c = (
            event.key() == Qt.Key.Key_C
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        )
        is_copy = event.matches(QKeySequence.StandardKey.Copy) or (
            event.key() == Qt.Key.Key_Insert
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        )
        if is_ctrl_c or is_copy:
            if self.textCursor().hasSelection():
                self.copy()
            elif is_ctrl_c:
                self.ctrl_c_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            event.accept()
            return
        super().wheelEvent(event)


# ==========================================
# TERMINAL PANEL
# ==========================================


MAX_HISTORY_BLOCKS = 5000
RENDER_INTERVAL_MS = 33


class TerminalWidget(QFrame):
    ctrl_c_requested = Signal()
    resized = Signal(int, int)

    def __init__(
        self,
        title: str,
        accent: str,
        input_enabled: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._accent = accent
        self._input_enabled = input_enabled
        self._process: PtyProcess | None = None
        self._emulator = TerminalEmulator()
        self._render_pending = False
        self._auto_scroll = True
        self._scroll_programmatic = False
        self._committed_scrollback = 0
        self._live_document_pos = 0
        self._format_cache: dict[tuple[str | None, str | None, bool], QTextCharFormat] = {}
        self._last_columns = 0
        self._last_rows = 0
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(80)
        self._resize_timer.timeout.connect(self._sync_terminal_geometry)
        self.setObjectName("TerminalPanel")
        self.setProperty("accent", accent)
        self._build_ui()

    def bind_process(self, process: PtyProcess | None) -> None:
        self._process = process
        if process:
            columns, rows = self._terminal_size()
            self._emulator.resize(columns, rows)
            process.resize(columns, rows)

    def append_output(self, text: str) -> None:
        try:
            self._emulator.feed(text)
            self._schedule_render()
        except Exception:
            return

    def reset_for_start(self) -> None:
        """Reset the display when a new process is started."""
        self._emulator.reset()
        self.output.clear()
        self._committed_scrollback = 0
        self._live_document_pos = 0
        self._render_pending = False
        self._auto_scroll = True
        self._format_cache.clear()
        self._last_columns = 0
        self._last_rows = 0

    def set_running(self, running: bool) -> None:
        self.status_dot.setProperty("state", "running" if running else "idle")
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)
        self.status_label.setText("Running" if running else "Idle")

    def send_ctrl_c(self) -> None:
        self.ctrl_c_requested.emit()

    def write_command(self, text: str) -> None:
        if self._process and self._process.is_alive():
            self._process.write(text + "\r\n")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._resize_timer.start()

    def _sync_terminal_geometry(self) -> None:
        columns, rows = self._terminal_size()
        if columns == self._last_columns and rows == self._last_rows:
            return
        self._last_columns = columns
        self._last_rows = rows
        self._emulator.resize(columns, rows)
        if self._process and self._process.is_alive():
            self._process.resize(columns, rows)
        self._rebuild_document()
        self.resized.emit(columns, rows)

    # --- rendering ---------------------------------------------------------

    def _schedule_render(self) -> None:
        if self._render_pending:
            return
        self._render_pending = True
        QTimer.singleShot(RENDER_INTERVAL_MS, self, self._render)

    def _render(self) -> None:
        self._render_pending = False
        scroll_bar = self.output.verticalScrollBar()

        reserved = self._emulator.visible_line_count() + 8
        max_scrollback = max(100, MAX_HISTORY_BLOCKS - reserved)
        excess = self._emulator.scrollback_line_count() - max_scrollback
        if excess > 0:
            self._emulator.drop_oldest_scrollback(excess)
            self._trim_document_from_start(excess)
            self._committed_scrollback = max(0, self._committed_scrollback - excess)

        doc = self.output.document()
        doc_chars = doc.characterCount()
        if self._live_document_pos > doc_chars:
            self._live_document_pos = doc_chars

        cursor = self.output.textCursor()

        cursor.setPosition(self._live_document_pos)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()

        scrollback_count = self._emulator.scrollback_line_count()
        if scrollback_count > self._committed_scrollback:
            cursor.setPosition(self._live_document_pos)
            lines = self._emulator.scrollback_lines_between(self._committed_scrollback, scrollback_count)
            for line in lines:
                self._append_display_line(cursor, line)
            self._committed_scrollback = scrollback_count

        self._live_document_pos = cursor.position()

        cursor.movePosition(QTextCursor.MoveOperation.End)
        for line in self._emulator.live_lines():
            self._append_display_line(cursor, line)

        if self._auto_scroll:
            self._set_scroll_position(scroll_bar.maximum())

    def _rebuild_document(self) -> None:
        self._committed_scrollback = 0
        self._live_document_pos = 0
        self.output.clear()
        self._render()

    def _trim_document_from_start(self, line_count: int) -> None:
        if line_count <= 0:
            return
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.movePosition(QTextCursor.MoveOperation.NextBlock, QTextCursor.MoveMode.KeepAnchor, line_count)
        removed = cursor.position()
        cursor.removeSelectedText()
        self._live_document_pos = max(0, self._live_document_pos - removed)

    def _append_display_line(self, cursor: QTextCursor, runs: list[StyledRun]) -> None:
        if cursor.position() > 0:
            cursor.insertText("\n")
        if runs:
            self._insert_runs(cursor, runs)

    def _set_scroll_position(self, value: int) -> None:
        scroll_bar = self.output.verticalScrollBar()
        self._scroll_programmatic = True
        scroll_bar.setValue(value)
        self._scroll_programmatic = False

    def _on_scroll_changed(self, value: int) -> None:
        """User scrolled the log view; pause tail-follow until they return to the bottom."""
        if self._scroll_programmatic:
            return
        scroll_bar = self.output.verticalScrollBar()
        self._auto_scroll = value >= scroll_bar.maximum() - 3

    def _insert_runs(self, cursor: QTextCursor, runs: list[StyledRun]) -> None:
        for run in runs:
            cursor.insertText(run.text, self._format_for(run))

    def _format_for(self, run: StyledRun) -> QTextCharFormat:
        key = (run.fg, run.bg, run.bold)
        fmt = self._format_cache.get(key)
        if fmt is None:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(run.fg or "#D8E6F2"))
            if run.bg:
                fmt.setBackground(QColor(run.bg))
            fmt.setFontWeight(700 if run.bold else 400)
            self._format_cache[key] = fmt
        return fmt

    # --- ui ----------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(7)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(7)

        self.status_dot = QFrame(self)
        self.status_dot.setObjectName("StatusDot")
        self.status_dot.setProperty("state", "idle")
        self.status_dot.setFixedSize(9, 9)
        header.addWidget(self.status_dot)

        title = QLabel(self._title, self)
        title.setObjectName("TerminalTitle")
        header.addWidget(title)

        self.status_label = QLabel("Idle", self)
        self.status_label.setObjectName("TerminalStatus")
        header.addWidget(self.status_label)
        header.addStretch(1)
        root.addLayout(header)

        self.output = TerminalOutput(self)
        self.output.ctrl_c_requested.connect(self.send_ctrl_c)
        scroll_bar = self.output.verticalScrollBar()
        scroll_bar.valueChanged.connect(self._on_scroll_changed)
        root.addWidget(self.output, 1)

        self.input_container = QWidget(self)
        input_row = QHBoxLayout(self.input_container)
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(8)
        self.input = QLineEdit(self)
        self.input.setObjectName("TerminalInput")
        self.input.setFont(QFont(TERMINAL_FONT_FAMILY, TERMINAL_FONT_POINT_SIZE))
        self.input.setPlaceholderText(
            "Type a command and press Enter..."
        )
        self.send_button = QPushButton(">", self)
        self.send_button.setObjectName("TerminalSendButton")
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.send_button)
        self.input_container.setVisible(self._input_enabled)
        root.addWidget(self.input_container)

        self.input.returnPressed.connect(self._submit_input)
        self.send_button.clicked.connect(self._submit_input)
        if self._input_enabled:
            self._setup_account_completer()

    def _setup_account_completer(self) -> None:
        self._account_completer = QCompleter(list(_ACCOUNT_TEMPLATES), self)
        self._account_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._account_completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self._account_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.input.textChanged.connect(self._update_account_completer)

    def _update_account_completer(self, text: str) -> None:
        if text.lower().startswith("account"):
            self.input.setCompleter(self._account_completer)
            self._account_completer.setCompletionPrefix(text)
        else:
            self.input.setCompleter(None)

    def _submit_input(self) -> None:
        text = self.input.text()
        if not text:
            return
        if self._process and self._process.is_alive():
            self._process.write(text + "\r\n")
        self.input.clear()

    def _terminal_size(self) -> tuple[int, int]:
        metrics = QFontMetrics(self.output.font())
        char_width = max(1, metrics.horizontalAdvance("M"))
        line_height = max(1, metrics.lineSpacing())
        viewport = self.output.viewport().size()
        horizontal_margin = int(self.output.document().documentMargin() * 2)
        columns = max(MIN_TERMINAL_COLUMNS, (viewport.width() - horizontal_margin) // char_width)
        rows = max(5, viewport.height() // line_height)
        return columns, rows
