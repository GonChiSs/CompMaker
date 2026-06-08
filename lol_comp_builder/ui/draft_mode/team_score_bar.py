from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from logic.synergy_engine import compute_team_synergy_mode1
from ui.synergy_panel import SynergyPanel


class TeamScoreBar(QWidget):
    def __init__(self, side: str) -> None:
        super().__init__()
        self.side = side
        self.score_label = QLabel("SINERGIA: --")
        self.score_label.setStyleSheet(
            "color:#2A4A6A; font-family: 'Barlow Condensed', 'Arial Narrow', Arial; font-size:9px; font-weight:700; letter-spacing:2px;"
        )
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(4)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.score_label)
        layout.addWidget(self.bar)
        self.hide()

    def update_team(self, team_picks: list[dict]) -> None:
        if len(team_picks) < 2:
            self.hide()
            return
        result = compute_team_synergy_mode1(team_picks)
        score = result["total_score"]
        color = SynergyPanel.lerp_color_gradient(score)
        self.score_label.setText(f"SINERGIA: {score:.1f}")
        self.bar.setValue(int(score))
        self.bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: #0F172A;
                border: 1px solid #223047;
                border-radius: 6px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 6px;
            }}
            """
        )
        self.show()
