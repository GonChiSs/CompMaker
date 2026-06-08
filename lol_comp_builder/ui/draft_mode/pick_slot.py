from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ui.image_utils import build_rounded_cover_pixmap


class PickSlot(QWidget):
    def __init__(self, role: str, side: str) -> None:
        super().__init__()
        self.setObjectName("pickSlot")
        self.role = role
        self.side = side
        self._pulse_on = False
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._toggle_pulse)

        self.image_label = QLabel()
        self.image_label.setFixedSize(80, 80)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.role_label = QLabel(role)
        self.role_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.role_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 2px;
            """
        )
        self.name_label = QLabel("Sin asignar")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet("color: #E8E0D0; font-size: 11px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.role_label)
        layout.addWidget(self.name_label)

        self.set_empty(role, side)

    def set_empty(self, role: str, side: str) -> None:
        self._pulse_timer.stop()
        color = "#0A1420" if side == "BLUE" else "#1A0808"
        self.setStyleSheet(
            f"""
            QWidget#pickSlot {{
                background-color: #080D14;
                border: 1px solid {color};
                border-radius: 3px;
            }}
            """
        )
        self.role_label.setText(role)
        self.name_label.setText("Pendiente")
        self.image_label.clear()

    def set_active(self, side: str) -> None:
        self.side = side
        self.name_label.setText("Eligiendo...")
        self._pulse_timer.start(450)
        self._apply_active_style(1.0)

    def _toggle_pulse(self) -> None:
        self._pulse_on = not self._pulse_on
        self._apply_active_style(1.0 if self._pulse_on else 0.45)

    def _apply_active_style(self, alpha_scale: float) -> None:
        color = "#1E90FF" if self.side == "BLUE" else "#FF3B3B"
        self.setStyleSheet(
            f"""
            QWidget#pickSlot {{
                background-color: {'#06141E' if self.side == 'BLUE' else '#160808'};
                border: 1px solid {color};
                border-radius: 3px;
            }}
            """
        )
        self.name_label.setStyleSheet(
            f"color: {color}; font-size: 9px; font-weight: 700; letter-spacing: 2px;"
        )

    def set_hovering(self, champion: dict, pixmap, side: str) -> None:
        self._pulse_timer.stop()
        self.side = side
        self._apply_active_style(0.8)
        self.image_label.setPixmap(build_rounded_cover_pixmap(pixmap, 80, 14))
        self.name_label.setText(f"{champion['name']} ?")

    def set_filled(self, champion: dict, role: str, pixmap) -> None:
        self._pulse_timer.stop()
        self.setStyleSheet(
            """
            QWidget#pickSlot {
                background-color: #080D14;
                border: 1px solid #0A2535;
                border-radius: 3px;
            }
            """
        )
        self.role_label.setText(role)
        self.name_label.setText(champion["name"])
        self.name_label.setStyleSheet("color: #E8E0D0; font-size: 11px; font-weight: 700;")
        self.image_label.setPixmap(build_rounded_cover_pixmap(pixmap, 80, 14))
