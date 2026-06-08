from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ui.image_utils import build_rounded_cover_pixmap


class RandomChampWidget(QWidget):
    reroll_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.has_rolled = False
        title = QLabel("// CAMPEON ALEATORIO")
        title.setObjectName("SectionTitle")
        title.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 3px;
            """
        )
        subtitle = QLabel("Pulsa el boton para descubrir un campeon aleatorio.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #5A7A9A; font-size: 11px;")

        self.image_label = QLabel()
        self.image_label.setFixedSize(220, 220)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label = QLabel("")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet(
            """
            color: #C9A84C;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 28px;
            font-weight: 800;
            letter-spacing: 2px;
            """
        )

        self.small_reroll_button = QPushButton("TIRAR")
        self.small_reroll_button.setFixedWidth(220)
        self.small_reroll_button.setMinimumHeight(56)
        self.small_reroll_button.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #0A2535;
                border-radius: 2px;
                color: #2A4A6A;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 9px 28px;
            }
            QPushButton:hover {
                border-color: #C9A84C;
                color: #C9A84C;
                background-color: #0E0C04;
            }
            """
        )
        self.small_reroll_button.clicked.connect(self.reroll_requested.emit)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_label)
        layout.addWidget(self.small_reroll_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

    def set_champion(self, champion_name: str, pixmap) -> None:
        self.has_rolled = True
        self.name_label.setText(champion_name)
        self.image_label.setPixmap(build_rounded_cover_pixmap(pixmap, 220, 34))
        self.small_reroll_button.setText("Volver a tirar")
        self.update()

    def set_intro_image(self, pixmap) -> None:
        self.has_rolled = False
        self.name_label.setText("")
        self.image_label.setPixmap(build_rounded_cover_pixmap(pixmap, 220, 34))
        self.small_reroll_button.setText("TIRAR")
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.image_label.pixmap() is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#0A2535"), 1)
        painter.setPen(pen)
        rect = self.image_label.geometry().adjusted(-4, -4, 4, 4)
        size = 14
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        painter.drawLine(x, y, x + size, y)
        painter.drawLine(x, y, x, y + size)
        painter.drawLine(x + w - size, y, x + w, y)
        painter.drawLine(x + w, y, x + w, y + size)
        painter.drawLine(x, y + h - size, x, y + h)
        painter.drawLine(x, y + h, x + size, y + h)
        painter.drawLine(x + w - size, y + h, x + w, y + h)
        painter.drawLine(x + w, y + h - size, x + w, y + h)
        painter.end()
