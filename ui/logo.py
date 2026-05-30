from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

from core.paths import resource_path


# ==========================================
# ASSETS
# ==========================================

def _row_has_content(image, y: int, alpha_threshold: int) -> bool:
    width = image.width()
    for x in range(width):
        if image.pixelColor(x, y).alpha() > alpha_threshold:
            return True
    return False


def _trim_transparent_edges(pixmap: QPixmap, alpha_threshold: int = 4) -> QPixmap:
    image = pixmap.toImage()
    width = image.width()
    height = image.height()
    if width == 0 or height == 0:
        return pixmap

    top = 0
    for y in range(height):
        if _row_has_content(image, y, alpha_threshold):
            top = y
            break

    bottom = height - 1
    for y in range(height - 1, -1, -1):
        if _row_has_content(image, y, alpha_threshold):
            bottom = y
            break

    if bottom < top:
        return pixmap

    return pixmap.copy(0, top, width, bottom - top + 1)


def render_logo_pixmap(width: int = 316) -> QPixmap:
    pixmap = QPixmap(str(resource_path("assets", "wow_logo.png")))
    if pixmap.isNull():
        return QPixmap(width, 120)
    scaled = pixmap.scaledToWidth(
        width,
        Qt.TransformationMode.SmoothTransformation,
    )
    return _trim_transparent_edges(scaled)


def make_window_icon() -> QIcon:
    return QIcon(str(resource_path("assets", "wow_icon.ico")))
