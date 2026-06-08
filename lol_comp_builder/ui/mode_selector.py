from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

MODE_BUTTONS = [
    ("01", "ASISTENTE"),
    ("02", "GENERADOR"),
    ("03", "RANDOM"),
    ("04", "SIMULADOR"),
    ("05", "GUARDADAS"),
    ("06", "TIERLIST"),
    ("07", "PIZARRA"),
    ("08", "MATCHUP"),
]


class ModeSelector(QWidget):
    mode_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.current_mode = "ASISTENTE"
        self.buttons: dict[str, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        for code, mode in MODE_BUTTONS:
            button = QPushButton(f"{code}  {mode}")
            button.clicked.connect(lambda checked=False, target_mode=mode: self.set_mode(target_mode))
            self.buttons[mode] = button
            layout.addWidget(button)
        self._sync_styles()

    def set_mode(self, mode: str) -> None:
        if self.current_mode == mode:
            return
        self.current_mode = mode
        self._sync_styles()
        self.mode_changed.emit(mode)

    def _sync_styles(self) -> None:
        for mode, button in self.buttons.items():
            button.setProperty("active", "true" if self.current_mode == mode else "false")
            if button.property("active") == "true":
                button.setStyleSheet(
                    """
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        border-bottom: 2px solid #C9A84C;
                        color: #C9A84C;
                        font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                        font-size: 11px;
                        font-weight: 700;
                        letter-spacing: 1.8px;
                        padding: 10px 16px 8px 16px;
                        border-radius: 0px;
                    }
                    """
                )
            else:
                button.setStyleSheet(
                    """
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        border-bottom: 2px solid transparent;
                        color: #2A4A6A;
                        font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                        font-size: 11px;
                        font-weight: 700;
                        letter-spacing: 1.8px;
                        padding: 10px 16px 8px 16px;
                        border-radius: 0px;
                    }
                    QPushButton:hover {
                        color: #5A9ABF;
                        border-bottom: 2px solid #0A7A9A;
                        background-color: #060D16;
                    }
                    """
                )
            button.style().unpolish(button)
            button.style().polish(button)
