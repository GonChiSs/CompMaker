from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ui.image_utils import build_rounded_cover_pixmap


class BanSlot(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("banSlot")
        self.setFixedSize(48, 48)
        self.image_label = QLabel("BAN")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("color: #2A4A6A; font-size: 8px; letter-spacing: 1px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.image_label)

        self.set_empty()

    def set_empty(self) -> None:
        self.setStyleSheet(
            """
            QWidget#banSlot {
                background-color: #080D14;
                border: 1px solid #0A1420;
                border-radius: 2px;
            }
            """
        )
        self.image_label.setText("BAN")
        self.image_label.clear()
        self.image_label.setText("BAN")

    def set_banned(self, champion_name: str, pixmap) -> None:
        self.setStyleSheet(
            """
            QWidget#banSlot {
                background-color: #080D14;
                border: 1px solid #1A0808;
                border-radius: 2px;
            }
            """
        )
        self.image_label.setPixmap(build_rounded_cover_pixmap(pixmap, 44, 10))
        self.image_label.setToolTip(champion_name)

    def set_active(self, side: str) -> None:
        color = "#1E90FF" if side == "BLUE" else "#FF3B3B"
        self.setStyleSheet(
            f"""
            QWidget#banSlot {{
                background-color: {'#06141E' if side == 'BLUE' else '#160808'};
                border: 1px solid {color};
                border-radius: 2px;
            }}
            """
        )
