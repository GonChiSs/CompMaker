from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class SideButton(QPushButton):
    def __init__(self, side: str, background: str, accent: str, icon: str, subtitle: str) -> None:
        super().__init__()
        self.side = side
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(320, 520)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {background};
                border: 1px solid {accent};
                border-radius: 3px;
                color: #E8E0D0;
                text-align: left;
                padding: 28px 32px;
            }}
            QPushButton:hover {{
                border-color: #C9A84C;
            }}
            """
        )
        layout = QVBoxLayout(self)
        label = QLabel(f"{side} SIDE")
        label.setStyleSheet(
            "font-size: 28px; font-weight: 800; color: #E8E0D0; letter-spacing: 4px; font-family: 'Barlow Condensed', 'Arial Narrow', Arial;"
        )
        text = QLabel(subtitle)
        text.setWordWrap(True)
        text.setStyleSheet(
            f"font-size: 15px; color: {accent}; font-weight: 700; letter-spacing: 2px;"
        )
        info = QLabel("Haz clic para empezar el draft competitivo.")
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 13px; color: #5A7A9A;")
        layout.addStretch()
        layout.addWidget(label)
        layout.addWidget(text)
        layout.addWidget(info)
        layout.addStretch()


class SideSelectionScreen(QWidget):
    side_selected = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet("QWidget { background-color: #04080F; }")
        title = QLabel("ELIGE TU LADO")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color:#C9A84C; font-size:18px; font-weight:800; letter-spacing:5px; font-family: 'Barlow Condensed', 'Arial Narrow', Arial;"
        )

        blue_btn = SideButton(
            "BLUE",
            "#060D16",
            "#1E90FF",
            "",
            "PRIMER PICK Y CONTROL DE LA APERTURA.",
        )
        red_btn = SideButton(
            "RED",
            "#0D0608",
            "#FF3B3B",
            "",
            "RESPUESTA DE DRAFT Y ULTIMO PICK.",
        )
        blue_btn.clicked.connect(lambda: self.side_selected.emit("BLUE"))
        red_btn.clicked.connect(lambda: self.side_selected.emit("RED"))

        row = QHBoxLayout()
        row.setSpacing(24)
        row.addWidget(blue_btn)
        row.addWidget(red_btn)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(title)
        layout.addSpacing(18)
        layout.addLayout(row)
        layout.addStretch()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#04080F"))
        painter.end()
        super().paintEvent(event)
