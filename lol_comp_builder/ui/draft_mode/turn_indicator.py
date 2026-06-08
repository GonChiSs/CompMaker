from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from logic.draft_state import DRAFT_ORDER, DraftState


class TurnIndicator(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.label = QLabel("Esperando draft...")
        self.label.setStyleSheet(
            "color: #C9A84C; font-size: 13px; font-weight: 800; letter-spacing: 3px; font-family: 'Barlow Condensed', 'Arial Narrow', Arial;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self._animation: QPropertyAnimation | None = None

    def update_turn(self, draft_state: DraftState) -> None:
        team, action, idx = draft_state.current_action()
        if team == "COMPLETE":
            self.label.setText("Draft completado")
            return

        side_count = sum(
            1
            for turn_team, turn_action, _ in DRAFT_ORDER[: draft_state.current_turn + 1]
            if turn_team == team and turn_action == action
        )
        if draft_state.is_user_turn():
            self.label.setText(f"[ TU TURNO ]  {action} {side_count}")
            self.label.setStyleSheet(
                "color: #C9A84C; font-size: 13px; font-weight: 800; letter-spacing: 3px; font-family: 'Barlow Condensed', 'Arial Narrow', Arial;"
            )
        else:
            color = "#1E90FF" if team == "BLUE" else "#FF3B3B"
            self.label.setText(f"[ TURNO {team} ]  {action} {side_count}")
            self.label.setStyleSheet(
                f"color: {color}; font-size: 13px; font-weight: 800; letter-spacing: 3px; font-family: 'Barlow Condensed', 'Arial Narrow', Arial;"
            )
        self.animate_slide_in()

    def animate_slide_in(self) -> None:
        self._animation = QPropertyAnimation(self, b"pos")
        self._animation.setDuration(200)
        self._animation.setStartValue(self.pos() - QPoint(0, 12))
        self._animation.setEndValue(self.pos())
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()
