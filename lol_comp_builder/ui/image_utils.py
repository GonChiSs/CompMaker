from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QPainter, QPainterPath, QPixmap


def build_rounded_cover_pixmap(source: QPixmap, size: int, radius: float) -> QPixmap:
    """Renderiza una imagen centrada tipo cover dentro de un rectangulo redondeado."""
    target = QPixmap(size, size)
    target.fill(Qt.GlobalColor.transparent)

    if source.isNull():
        return target

    source_ratio = source.width() / max(source.height(), 1)
    target_ratio = 1.0

    if source_ratio > target_ratio:
        scaled_height = source.height()
        scaled_width = int(scaled_height * target_ratio)
        source_x = max((source.width() - scaled_width) // 2, 0)
        source_rect = QRectF(source_x, 0, scaled_width, scaled_height)
    else:
        scaled_width = source.width()
        scaled_height = int(scaled_width / target_ratio)
        source_y = max((source.height() - scaled_height) // 2, 0)
        source_rect = QRectF(0, source_y, scaled_width, scaled_height)

    painter = QPainter(target)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(QRectF(0, 0, size, size), source, source_rect)
    painter.end()
    return target
