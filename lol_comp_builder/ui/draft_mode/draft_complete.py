from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from logic.composition import ROLES
from logic.synergy_engine import compute_team_synergy_mode1
from ui.draft_mode.pick_slot import PickSlot


class DraftCompleteScreen(QWidget):
    restart_requested = pyqtSignal()

    def __init__(self, data_loader) -> None:
        super().__init__()
        self.data_loader = data_loader
        self.title = QLabel("// DRAFT COMPLETADO")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet(
            "color:#C9A84C; font-size:18px; font-weight:800; letter-spacing:4px; font-family: 'Barlow Condensed', 'Arial Narrow', Arial;"
        )
        self.summary = QLabel("Sin datos")
        self.summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet(
            "color:#E8E0D0; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size:14px; font-weight:700; letter-spacing:1px;"
        )
        self.insights = QLabel("")
        self.insights.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.insights.setWordWrap(True)
        self.insights.setStyleSheet("color:#5A7A9A; font-size:13px;")
        restart = QPushButton("Nuevo draft")
        restart.setStyleSheet(
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
                padding: 9px 24px;
            }
            QPushButton:hover {
                border-color: #00D4FF;
                color: #00D4FF;
                background-color: #06141E;
            }
            """
        )
        restart.clicked.connect(self.restart_requested.emit)

        self.blue_panel = self._build_team_panel("BLUE")
        self.red_panel = self._build_team_panel("RED")

        center_layout = QVBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(self.title)
        center_layout.addWidget(self.summary)
        center_layout.addWidget(self.insights)
        center_layout.addWidget(restart, alignment=Qt.AlignmentFlag.AlignCenter)
        center_layout.addStretch()

        content = QHBoxLayout()
        content.setContentsMargins(24, 10, 24, 10)
        content.setSpacing(28)
        content.addWidget(self.blue_panel)
        content.addLayout(center_layout, 1)
        content.addWidget(self.red_panel)

        layout = QVBoxLayout(self)
        layout.addLayout(content)

    def _build_team_panel(self, side: str) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(220)
        panel.setObjectName(f"complete{side.title()}Panel")
        panel.setStyleSheet(
            f"""
            QWidget#complete{side.title()}Panel {{
                background-color: {'#060D16' if side == 'BLUE' else '#0D0608'};
                {'border-right: 1px solid #0A1E2A;' if side == 'BLUE' else 'border-left: 1px solid #1A0808;'}
                border-radius: 3px;
            }}
            """
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel(f"EQUIPO {side}")
        title.setStyleSheet(
            f"color:{'#1A4A7A' if side == 'BLUE' else '#7A1A1A'}; font-weight:700; font-size:10px; letter-spacing:3px;"
        )
        layout.addWidget(title)

        slots = {}
        for role in ROLES:
            slot = PickSlot(role, side)
            slot.setDisabled(True)
            layout.addWidget(slot)
            slots[role] = slot
        layout.addStretch()

        if side == "BLUE":
            self.blue_slots = slots
        else:
            self.red_slots = slots
        return panel

    def compute_draft_advantage(self, blue_team, red_team) -> dict:
        blue_result = compute_team_synergy_mode1(blue_team)
        red_result = compute_team_synergy_mode1(red_team)
        advantage = blue_result["total_score"] - red_result["total_score"]
        if advantage > 10:
            return {"winner": "BLUE", "text": f"Ventaja Azul +{advantage:.1f}", "margin": abs(advantage)}
        if advantage < -10:
            return {"winner": "RED", "text": f"Ventaja Roja +{abs(advantage):.1f}", "margin": abs(advantage)}
        return {"winner": "NEUTRAL", "text": "Draft equilibrado", "margin": abs(advantage)}

    def set_result(self, blue_team: list[dict], red_team: list[dict]) -> None:
        result = self.compute_draft_advantage(blue_team, red_team)
        self.summary.setText(result["text"])
        blue_score = compute_team_synergy_mode1(blue_team)["total_score"] if len(blue_team) >= 2 else 0
        red_score = compute_team_synergy_mode1(red_team)["total_score"] if len(red_team) >= 2 else 0
        self.insights.setText(
            f"Sinergia azul: {blue_score:.1f} | Sinergia roja: {red_score:.1f}"
        )
        self._fill_team_slots(self.blue_slots, blue_team, "BLUE")
        self._fill_team_slots(self.red_slots, red_team, "RED")

    def _fill_team_slots(self, slots: dict[str, PickSlot], team: list[dict], side: str) -> None:
        team_by_role = {
            champion.get("assigned_role"): champion
            for champion in team
            if champion.get("assigned_role")
        }
        for role in ROLES:
            slot = slots[role]
            champion = team_by_role.get(role)
            if champion is None:
                slot.set_empty(role, side)
                slot.setDisabled(True)
                continue
            pixmap = self.data_loader.get_champion_pixmap(champion["name"], 80)
            slot.set_filled(champion, role, pixmap)
            slot.setDisabled(True)
