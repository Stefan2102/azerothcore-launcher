from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


# ==========================================
# ICONS
# ==========================================


COLORS = {
    "green": "#5FE8C8",
    "blue": "#74C7F2",
    "purple": "#B69BE8",
    "orange": "#E5C66B",
    "red": "#F0707C",
    "gold": "#E5C66B",
    "ice": "#9AD9FF",
    "silver": "#B8D4E8",
    "wow": "#D8E8C0",
    "icy_yellow": "#FFF0B0",
    "settings_white": "#F0F8FF",
    "exit_ice": "#E0B8C8",
}


def make_icon(kind: str, color_name: str, size: int = 26) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    color = QColor(COLORS[color_name])
    pen = QPen(color, max(2, size // 13))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    rect = QRectF(size * 0.16, size * 0.16, size * 0.68, size * 0.68)
    if kind == "database":
        _database(painter, rect, color)
    elif kind == "shield":
        _shield(painter, rect, color)
    elif kind == "globe":
        _globe(painter, rect, color)
    elif kind == "spark":
        _spark(painter, rect, color)
    elif kind == "sword":
        _sword(painter, rect, color)
    elif kind == "power":
        _power(painter, rect, color)
    elif kind == "settings":
        _settings(painter, rect, color)
    elif kind == "clear":
        _clear(painter, rect, color)
    else:
        painter.drawEllipse(rect)

    painter.end()
    return QIcon(pixmap)


def _database(painter: QPainter, rect: QRectF, color: QColor) -> None:
    painter.drawEllipse(QRectF(rect.left(), rect.top(), rect.width(), rect.height() * 0.32))
    painter.drawLine(rect.left(), rect.top() + rect.height() * 0.16, rect.left(), rect.bottom() - rect.height() * 0.16)
    painter.drawLine(rect.right(), rect.top() + rect.height() * 0.16, rect.right(), rect.bottom() - rect.height() * 0.16)
    painter.drawEllipse(QRectF(rect.left(), rect.bottom() - rect.height() * 0.32, rect.width(), rect.height() * 0.32))
    painter.drawArc(QRectF(rect.left(), rect.center().y() - rect.height() * 0.16, rect.width(), rect.height() * 0.32), 0, -180 * 16)
    painter.setBrush(QColor(color.red(), color.green(), color.blue(), 32))
    painter.drawRoundedRect(rect, 6, 6)


def _shield(painter: QPainter, rect: QRectF, color: QColor) -> None:
    path = QPainterPath()
    path.moveTo(rect.center().x(), rect.top())
    path.lineTo(rect.right(), rect.top() + rect.height() * 0.22)
    path.lineTo(rect.right() - rect.width() * 0.14, rect.bottom() - rect.height() * 0.22)
    path.quadTo(rect.center().x(), rect.bottom(), rect.left() + rect.width() * 0.14, rect.bottom() - rect.height() * 0.22)
    path.lineTo(rect.left(), rect.top() + rect.height() * 0.22)
    path.closeSubpath()
    painter.setBrush(QColor(color.red(), color.green(), color.blue(), 28))
    painter.drawPath(path)
    painter.drawLine(rect.center().x(), rect.top() + 3, rect.center().x(), rect.bottom() - 5)


def _globe(painter: QPainter, rect: QRectF, color: QColor) -> None:
    painter.drawEllipse(rect)
    painter.drawLine(rect.left(), rect.center().y(), rect.right(), rect.center().y())
    painter.drawArc(rect, 65 * 16, 230 * 16)
    painter.drawArc(rect, -115 * 16, 230 * 16)
    painter.drawArc(QRectF(rect.left(), rect.top() + rect.height() * 0.18, rect.width(), rect.height() * 0.64), 0, 180 * 16)
    painter.drawArc(QRectF(rect.left(), rect.top() + rect.height() * 0.18, rect.width(), rect.height() * 0.64), 0, -180 * 16)


def _spark(painter: QPainter, rect: QRectF, color: QColor) -> None:
    path = QPainterPath()
    path.moveTo(rect.center().x(), rect.top())
    path.lineTo(rect.center().x() + rect.width() * 0.13, rect.center().y() - rect.height() * 0.13)
    path.lineTo(rect.right(), rect.center().y())
    path.lineTo(rect.center().x() + rect.width() * 0.13, rect.center().y() + rect.height() * 0.13)
    path.lineTo(rect.center().x(), rect.bottom())
    path.lineTo(rect.center().x() - rect.width() * 0.13, rect.center().y() + rect.height() * 0.13)
    path.lineTo(rect.left(), rect.center().y())
    path.lineTo(rect.center().x() - rect.width() * 0.13, rect.center().y() - rect.height() * 0.13)
    path.closeSubpath()
    painter.setBrush(QColor(color.red(), color.green(), color.blue(), 34))
    painter.drawPath(path)


def _sword(painter: QPainter, rect: QRectF, color: QColor) -> None:
    painter.drawLine(rect.left() + rect.width() * 0.25, rect.bottom(), rect.right() - rect.width() * 0.12, rect.top() + rect.height() * 0.12)
    painter.drawLine(rect.left() + rect.width() * 0.15, rect.bottom() - rect.height() * 0.2, rect.left() + rect.width() * 0.45, rect.bottom() - rect.height() * 0.05)
    painter.drawLine(rect.left() + rect.width() * 0.17, rect.bottom() - rect.height() * 0.03, rect.left() + rect.width() * 0.32, rect.bottom() - rect.height() * 0.18)


def _power(painter: QPainter, rect: QRectF, color: QColor) -> None:
    painter.drawEllipse(rect.adjusted(1, 1, -1, -1))
    painter.drawLine(rect.center().x(), rect.top() - rect.height() * 0.08, rect.center().x(), rect.center().y())


def _settings(painter: QPainter, rect: QRectF, color: QColor) -> None:
    center = rect.center()
    outer = rect.width() * 0.34
    inner = rect.width() * 0.16
    for angle in range(0, 360, 45):
        painter.save()
        painter.translate(center)
        painter.rotate(angle)
        painter.drawLine(0, -outer, 0, -inner)
        painter.restore()
    painter.setBrush(QColor(color.red(), color.green(), color.blue(), 28))
    painter.drawEllipse(center, inner, inner)


def _clear(painter: QPainter, rect: QRectF, color: QColor) -> None:
    body = QRectF(rect.left() + rect.width() * 0.18, rect.top() + rect.height() * 0.28, rect.width() * 0.64, rect.height() * 0.58)
    painter.setBrush(QColor(color.red(), color.green(), color.blue(), 24))
    painter.drawRoundedRect(body, 3, 3)
    painter.drawLine(body.left() + body.width() * 0.18, body.top(), body.right() - body.width() * 0.18, body.bottom())
    lid = QRectF(rect.left() + rect.width() * 0.12, rect.top() + rect.height() * 0.18, rect.width() * 0.76, rect.height() * 0.14)
    painter.drawRoundedRect(lid, 2, 2)
    painter.drawLine(rect.center().x(), lid.top(), rect.center().x(), rect.top() + rect.height() * 0.08)
