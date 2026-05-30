from __future__ import annotations

from dataclasses import dataclass

from pyte import Stream
from pyte.screens import Char, Margins, Screen


# ==========================================
# COLOR PALETTE (Wrath of the Lich King)
# ==========================================


DEFAULT_FG = "#D8E6F2"
DEFAULT_BG = "#050B14"

NAME_TO_HEX = {
    "black": "#1F2937",
    "red": "#F0707C",
    "green": "#5FE8C8",
    "brown": "#E5C66B",
    "blue": "#74C7F2",
    "magenta": "#B69BE8",
    "cyan": "#88E2F2",
    "white": "#D8E6F2",
    "brightblack": "#6F8AA5",
    "brightred": "#FF8A93",
    "brightgreen": "#7AF0D3",
    "brightbrown": "#F0D77F",
    "brightblue": "#9AD9FF",
    "brightmagenta": "#D2B6FF",
    "brightcyan": "#9FECFA",
    "brightwhite": "#F0F6FC",
}

_BLANK = Char(data=" ")


@dataclass(slots=True)
class StyledRun:
    text: str
    fg: str | None
    bg: str | None
    bold: bool


# ==========================================
# CAPTURING SCREEN
# ==========================================


class _CaptureScreen(Screen):
    """Screen that keeps every line scrolled above the top edge."""

    def __init__(self, columns: int, lines: int) -> None:
        self.scrolled_off: list[dict[int, Char]] = []
        super().__init__(columns, lines)

    def index(self) -> None:
        top, bottom = self.margins or Margins(0, self.lines - 1)
        if self.cursor.y == bottom:
            self.scrolled_off.append(dict(self.buffer[top]))
        super().index()


# ==========================================
# TERMINAL EMULATOR
# ==========================================


class TerminalEmulator:
    """Interprets raw ConPTY output the same way a console host does.

    The screen buffer handles cursor moves, erases, scrolling and SGR colors,
    so rendered output matches cmd instead of a stripped-down text stream.
    """

    def __init__(self, columns: int = 100, lines: int = 30) -> None:
        self._screen = _CaptureScreen(max(2, columns), max(2, lines))
        self._stream = Stream(self._screen)

    def feed(self, data: str) -> None:
        self._stream.feed(data)

    def feed_external(self, data: str) -> None:
        """Append plain-text output (e.g. mysqladmin) on new lines without carriage-return glitches."""
        if not data:
            return
        text = data.replace("\r\n", "\n").replace("\r", "\n")
        if not text.endswith("\n"):
            text += "\n"
        self._stream.feed(text)

    def resize(self, columns: int, lines: int) -> None:
        self._screen.resize(max(2, lines), max(2, columns))

    def reset(self) -> None:
        self._screen.reset()
        self._screen.scrolled_off.clear()

    def visible_line_count(self) -> int:
        return self._screen.lines

    def scrollback_line_count(self) -> int:
        return len(self._screen.scrolled_off)

    def drop_oldest_scrollback(self, count: int) -> None:
        if count <= 0:
            return
        self._screen.scrolled_off = self._screen.scrolled_off[count:]

    def scrollback_lines_between(self, start: int, end: int) -> list[list[StyledRun]]:
        return [self._row_to_runs(row) for row in self._screen.scrolled_off[start:end]]

    def live_lines(self) -> list[list[StyledRun]]:
        lines = [self._row_to_runs(self._screen.buffer[y]) for y in range(self._screen.lines)]
        while lines and not lines[-1]:
            lines.pop()
        return lines

    def all_lines(self) -> list[list[StyledRun]]:
        lines: list[list[StyledRun]] = []
        for row in self._screen.scrolled_off:
            lines.append(self._row_to_runs(row))
        lines.extend(self.live_lines())
        return lines

    def _row_to_runs(self, row) -> list[StyledRun]:
        columns = self._screen.columns
        last = -1
        for x in range(columns):
            char = row.get(x, _BLANK)
            if char.data != " " or char.bg != "default" or char.reverse:
                last = x
        if last < 0:
            return []

        runs: list[StyledRun] = []
        current: StyledRun | None = None
        for x in range(last + 1):
            fg, bg, bold = self._cell_style(row.get(x, _BLANK))
            data = row.get(x, _BLANK).data or ""
            if current and current.fg == fg and current.bg == bg and current.bold == bold:
                current.text += data
            else:
                current = StyledRun(data, fg, bg, bold)
                runs.append(current)
        return runs

    @staticmethod
    def _cell_style(char: Char) -> tuple[str | None, str | None, bool]:
        fg = _resolve(char.fg, DEFAULT_FG)
        bg = _resolve(char.bg, None)
        if char.reverse:
            fg, bg = (bg or DEFAULT_BG), (fg or DEFAULT_FG)
        return fg, bg, bool(char.bold)


def _resolve(name: str, default: str | None) -> str | None:
    if name == "default":
        return default
    mapped = NAME_TO_HEX.get(name)
    if mapped:
        return mapped
    if len(name) == 6 and all(c in "0123456789abcdefABCDEF" for c in name):
        return f"#{name}"
    return default
