from __future__ import annotations

from functools import partial

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from logic.composition import ROLES
from logic.draft_recommender import get_draft_recommendations
from logic.draft_state import DraftState
from ui.draft_mode.ban_slot import BanSlot
from ui.draft_mode.draft_complete import DraftCompleteScreen
from ui.draft_mode.pick_slot import PickSlot
from ui.draft_mode.team_score_bar import TeamScoreBar
from ui.draft_mode.turn_indicator import TurnIndicator
from ui.image_utils import build_rounded_cover_pixmap

RECOMMENDATION_MODE_NONE = "NONE"
RECOMMENDATION_MODE_STANDARD = "STANDARD"
RECOMMENDATION_MODE_BOTH = "BOTH"

RECOMMENDATION_MODE_LABELS = {
    RECOMMENDATION_MODE_NONE: "Sin recomendaciones",
    RECOMMENDATION_MODE_STANDARD: "Estandar",
    RECOMMENDATION_MODE_BOTH: "Ambos",
}


def resolve_recommendation_state_for_turn(
    draft_state: DraftState,
    recommendation_mode: str,
) -> DraftState | None:
    team, action, _ = draft_state.current_action()
    if team == "COMPLETE" or action == "COMPLETE":
        return None
    if recommendation_mode == RECOMMENDATION_MODE_NONE:
        return None
    if recommendation_mode == RECOMMENDATION_MODE_STANDARD:
        return draft_state if team == draft_state.user_side else None
    if recommendation_mode == RECOMMENDATION_MODE_BOTH:
        return draft_state.clone_for_side(team)
    return None


class DraftChampionCard(QPushButton):
    hovered = pyqtSignal(str)

    def __init__(self, champion: dict, pixmap) -> None:
        super().__init__()
        self.champion = champion
        self.scores: dict | None = None
        self.setObjectName("draftCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(92, 112)
        self.setStyleSheet(
            """
            QPushButton {
                background-color: #0C1420;
                border: 1px solid #0A1420;
                border-radius: 2px;
                color: #E8E0D0;
            }
            QPushButton:hover {
                background-color: #0E1A28;
                border-color: #0A3A55;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self.rank_badge = QLabel("")
        self.rank_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rank_badge.setStyleSheet(
            "background:#00D4FF; color:#03050A; border-radius:2px; font-weight:800; font-family:'JetBrains Mono','Courier New',monospace; font-size:8px; padding:1px 3px;"
        )
        self.rank_badge.hide()
        portrait = QLabel()
        portrait.setAlignment(Qt.AlignmentFlag.AlignCenter)
        portrait.setPixmap(build_rounded_cover_pixmap(pixmap, 48, 10))
        name = QLabel(champion["name"])
        name.setWordWrap(True)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet("font-size:10px; font-weight:700; color:#5A7A9A; letter-spacing:0.5px;")
        layout.addWidget(self.rank_badge)
        layout.addWidget(portrait)
        layout.addWidget(name)

    def set_state(self, state: str, rank: int = 0, scores: dict | None = None) -> None:
        self.scores = scores
        self.setEnabled(True)
        if state == "RECOMMENDED":
            self.setStyleSheet(
                """
                QPushButton {
                    border: 1px solid #00D4FF;
                    border-radius: 2px;
                    background: #06141E;
                    color: #E8E0D0;
                }
                """
            )
            self.rank_badge.setText(f"{rank:02d}")
            self.rank_badge.setStyleSheet(
                "background:#00D4FF; color:#03050A; border-radius:2px; font-weight:800; font-family:'JetBrains Mono','Courier New',monospace; font-size:8px; padding:1px 3px;"
            )
            self.rank_badge.show()
        elif state == "BAN_PRIORITY":
            self.setStyleSheet(
                """
                QPushButton {
                    border: 1px solid #FF3B3B;
                    border-radius: 2px;
                    background: #160808;
                    color: #E8E0D0;
                }
                """
            )
            self.rank_badge.setText("BAN")
            self.rank_badge.setStyleSheet(
                "background:#FF3B3B; color:#03050A; border-radius:2px; font-weight:800; font-family:'JetBrains Mono','Courier New',monospace; font-size:8px; padding:1px 3px;"
            )
            self.rank_badge.show()
        elif state == "UNAVAILABLE":
            self.setEnabled(False)
            self.setStyleSheet(
                """
                QPushButton {
                    border: 1px solid #080D14;
                    border-radius: 2px;
                    background: #06080C;
                    color: #6B7280;
                }
                """
            )
            self.rank_badge.hide()
        else:
            self.rank_badge.hide()

    def enterEvent(self, event) -> None:
        self.hovered.emit(self.champion["name"])
        if self.scores:
            self.setToolTip(
                "Total: {total:.1f}\nSinergia: {synergy:.1f}\nMatchup: {matchup:.1f}\nFlex: {flex:.1f}\n{reason}".format(
                    **self.scores
                )
            )
        super().enterEvent(event)


class DraftSettingsDialog(QDialog):
    def __init__(self, current_mode: str, parent=None) -> None:
        super().__init__(parent)
        self.selected_mode = current_mode
        self.setWindowTitle("Ajustes de recomendaciones")
        self.setModal(True)
        self.setFixedSize(360, 240)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #080D14;
                border: 1px solid #0A2535;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        title = QLabel("// AJUSTES DE RECOMENDACION")
        title.setStyleSheet(
            """
            color: #C89B3C;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 3px;
            """
        )
        layout.addWidget(title)

        helper = QLabel(
            "Elige si el simulador no recomienda, recomienda solo para tu lado o muestra recomendaciones para ambos equipos."
        )
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #5A7A9A; font-size: 11px; font-weight: 700;")
        layout.addWidget(helper)

        self.option_group = QButtonGroup(self)
        for mode in (
            RECOMMENDATION_MODE_NONE,
            RECOMMENDATION_MODE_STANDARD,
            RECOMMENDATION_MODE_BOTH,
        ):
            button = QPushButton(RECOMMENDATION_MODE_LABELS[mode])
            button.setCheckable(True)
            button.setChecked(mode == current_mode)
            button.setFixedHeight(38)
            button.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    border: 1px solid #0A2535;
                    border-radius: 2px;
                    color: #5A7A9A;
                    font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                    font-size: 11px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    padding: 0px 12px;
                    text-align: left;
                }
                QPushButton:hover {
                    border-color: #00D4FF;
                    color: #00D4FF;
                    background-color: #06141E;
                }
                QPushButton:checked {
                    border-color: #C89B3C;
                    color: #C89B3C;
                    background-color: #110D04;
                }
                """
            )
            button.clicked.connect(lambda checked=False, selected_mode=mode: self._select_mode(selected_mode))
            self.option_group.addButton(button)
            layout.addWidget(button)

    def _select_mode(self, mode: str) -> None:
        self.selected_mode = mode
        self.accept()

    @classmethod
    def get_mode(cls, current_mode: str, parent=None) -> str | None:
        dialog = cls(current_mode=current_mode, parent=parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_mode
        return None


class DraftScreen(QWidget):
    restart_requested = pyqtSignal()

    def __init__(self, data_loader, champion_pool: dict[str, dict], user_side: str) -> None:
        super().__init__()
        self.data_loader = data_loader
        self.champion_pool = champion_pool
        self.state = DraftState(user_side=user_side)
        self.state.assign_phase()
        self.current_role_filter: str | None = None
        self.recommendation_mode = RECOMMENDATION_MODE_STANDARD

        self.stack = QStackedWidget()
        self.main_page = QWidget()
        self.complete_page = DraftCompleteScreen(self.data_loader)
        self.complete_page.restart_requested.connect(self.restart_requested.emit)
        self.stack.addWidget(self.main_page)
        self.stack.addWidget(self.complete_page)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.stack)

        self._build_main_ui()
        self._update_settings_button_text()
        self._refresh_everything()

    def _build_main_ui(self) -> None:
        self.main_page.setStyleSheet("QWidget { background-color: #04080F; color: #E8E0D0; }")
        main_layout = QVBoxLayout(self.main_page)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        header = QHBoxLayout()
        self.blue_title = QLabel("EQUIPO AZUL")
        self.blue_title.setStyleSheet("color:#1A4A7A; font-size:10px; font-weight:700; letter-spacing:3px;")
        self.red_title = QLabel("EQUIPO ROJO")
        self.red_title.setStyleSheet("color:#7A1A1A; font-size:10px; font-weight:700; letter-spacing:3px;")
        center_title = QLabel("SIMULADOR DE DRAFT")
        center_title.setStyleSheet("color:#C89B3C; font-size:18px; font-weight:800; letter-spacing:4px;")
        self.settings_button = QPushButton()
        self.settings_button.setFixedHeight(30)
        self.settings_button.clicked.connect(self._open_settings_dialog)
        self.settings_button.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #0A2535;
                border-radius: 2px;
                color: #5A7A9A;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 0 12px;
            }
            QPushButton:hover {
                border-color: #00D4FF;
                color: #00D4FF;
                background-color: #06141E;
            }
            """
        )
        header.addWidget(self.blue_title)
        header.addStretch()
        header.addWidget(center_title)
        header.addStretch()
        header.addWidget(self.settings_button)
        header.addWidget(self.red_title)
        main_layout.addLayout(header)

        bans_row = QHBoxLayout()
        self.blue_ban_slots = [BanSlot() for _ in range(5)]
        self.red_ban_slots = [BanSlot() for _ in range(5)]
        left_bans = QHBoxLayout()
        right_bans = QHBoxLayout()
        for slot in self.blue_ban_slots:
            left_bans.addWidget(slot)
        for slot in self.red_ban_slots:
            right_bans.addWidget(slot)
        bans_row.addLayout(left_bans)
        bans_row.addStretch()
        bans_row.addLayout(right_bans)
        main_layout.addLayout(bans_row)

        content = QHBoxLayout()
        content.setSpacing(14)
        self.blue_panel = self._build_team_panel("BLUE")
        self.center_panel = self._build_center_panel()
        self.red_panel = self._build_team_panel("RED")
        content.addWidget(self.blue_panel, 0)
        content.addWidget(self.center_panel, 1)
        content.addWidget(self.red_panel, 0)
        main_layout.addLayout(content, 1)

    def _build_team_panel(self, side: str) -> QWidget:
        panel = QWidget()
        panel.setObjectName(f"{side.lower()}Panel")
        panel.setFixedWidth(220)
        panel.setStyleSheet(
            f"QWidget#{side.lower()}Panel {{ background-color: {'#060D16' if side == 'BLUE' else '#0D0608'}; {'border-right: 1px solid #0A1E2A;' if side == 'BLUE' else 'border-left: 1px solid #1A0808;'} border-radius: 3px; }}"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        title = QLabel(f"EQUIPO {side}")
        title.setStyleSheet(
            f"color:{'#1A4A7A' if side == 'BLUE' else '#7A1A1A'}; font-weight:700; font-size:10px; letter-spacing:3px;"
        )
        layout.addWidget(title)
        slots = {}
        for role in ROLES:
            slot = PickSlot(role, side)
            layout.addWidget(slot)
            slots[role] = slot
        score_bar = TeamScoreBar(side)
        layout.addStretch()
        layout.addWidget(score_bar)
        if side == "BLUE":
            self.blue_pick_slots = slots
            self.blue_score_bar = score_bar
        else:
            self.red_pick_slots = slots
            self.red_score_bar = score_bar
        return panel

    def _build_center_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("QWidget { background-color: #09111C; border-radius: 3px; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.turn_indicator = TurnIndicator()
        layout.addWidget(self.turn_indicator)

        search_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar campeon...")
        self.search_box.textChanged.connect(self._refresh_grid)
        search_row.addWidget(self.search_box)

        self.role_group = QButtonGroup(self)
        for role in ["TODOS"] + ROLES:
            button = QPushButton(role)
            button.setCheckable(True)
            if role == "TODOS":
                button.setChecked(True)
            button.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    border: 1px solid #0A1E2A;
                    border-radius: 2px;
                    color: #2A4A6A;
                    font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    padding: 4px 10px;
                }
                QPushButton:hover {
                    border-color: #0A7A9A;
                    color: #5A9ABF;
                }
                QPushButton:checked {
                    border-color: #00D4FF;
                    color: #00D4FF;
                    background-color: #06141E;
                }
                """
            )
            button.clicked.connect(partial(self._set_role_filter, None if role == "TODOS" else role))
            self.role_group.addButton(button)
            search_row.addWidget(button)
        layout.addLayout(search_row)

        self.grid_host = QWidget()
        self.grid_layout = QGridLayout(self.grid_host)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.grid_host)
        layout.addWidget(scroll, 1)
        return panel

    def _set_role_filter(self, role: str | None) -> None:
        self.current_role_filter = role
        self._refresh_grid()

    def _refresh_everything(self) -> None:
        self.turn_indicator.update_turn(self.state)
        self._refresh_bans()
        self._refresh_picks()
        self._refresh_scores()
        self._refresh_recommendations()
        self._refresh_grid()
        self._maybe_finish_draft()

    def _refresh_bans(self) -> None:
        for index, slot in enumerate(self.blue_ban_slots):
            if index < len(self.state.blue_bans):
                champ = self.state.blue_bans[index]
                slot.set_banned(champ["name"], self.data_loader.get_champion_pixmap(champ["name"], 44))
            else:
                slot.set_empty()
        for index, slot in enumerate(self.red_ban_slots):
            if index < len(self.state.red_bans):
                champ = self.state.red_bans[index]
                slot.set_banned(champ["name"], self.data_loader.get_champion_pixmap(champ["name"], 44))
            else:
                slot.set_empty()

        team, action, slot_index = self.state.current_action()
        if action == "BAN" and slot_index >= 0:
            if team == "BLUE" and slot_index < len(self.blue_ban_slots):
                self.blue_ban_slots[slot_index].set_active("BLUE")
            if team == "RED" and slot_index < len(self.red_ban_slots):
                self.red_ban_slots[slot_index].set_active("RED")

    def _refresh_picks(self) -> None:
        blue_map = self.state.role_map_for_side("BLUE")
        red_map = self.state.role_map_for_side("RED")
        for role in ROLES:
            blue_slot = self.blue_pick_slots[role]
            red_slot = self.red_pick_slots[role]
            if role in blue_map:
                blue_slot.set_filled(
                    blue_map[role],
                    role,
                    self.data_loader.get_champion_pixmap(blue_map[role]["name"], 80),
                )
            else:
                blue_slot.set_empty(role, "BLUE")
            if role in red_map:
                red_slot.set_filled(
                    red_map[role],
                    role,
                    self.data_loader.get_champion_pixmap(red_map[role]["name"], 80),
                )
            else:
                red_slot.set_empty(role, "RED")

        team, action, _ = self.state.current_action()
        if action == "PICK":
            target_slots = self.blue_pick_slots if team == "BLUE" else self.red_pick_slots
            filled = set(self.state.filled_roles_for_side(team))
            for role in ROLES:
                if role not in filled:
                    target_slots[role].set_active(team)
                    break

    def _refresh_scores(self) -> None:
        self.blue_score_bar.update_team(self.state.blue_picks)
        self.red_score_bar.update_team(self.state.red_picks)

    def _refresh_recommendations(self) -> None:
        recommendation_state = self._recommendation_state_for_active_turn()
        if recommendation_state is None:
            self.current_recommendations = []
            return
        _, action, _ = recommendation_state.current_action()
        target_role = self.current_role_filter if action == "PICK" and self.current_role_filter else None
        self.current_recommendations = get_draft_recommendations(
            recommendation_state,
            self.champion_pool,
            target_role=target_role,
        )

    def _recommendation_state_for_active_turn(self) -> DraftState | None:
        return resolve_recommendation_state_for_turn(self.state, self.recommendation_mode)

    def _open_settings_dialog(self) -> None:
        selected_mode = DraftSettingsDialog.get_mode(self.recommendation_mode, parent=self)
        if not selected_mode or selected_mode == self.recommendation_mode:
            return
        self.recommendation_mode = selected_mode
        self._update_settings_button_text()
        self._refresh_recommendations()
        self._refresh_grid()

    def _update_settings_button_text(self) -> None:
        label = RECOMMENDATION_MODE_LABELS.get(self.recommendation_mode, "Estandar")
        self.settings_button.setText(f"AJUSTES | {label.upper()}")

    def _refresh_grid(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        query = self.search_box.text().strip().lower()
        unavailable = self.state.get_unavailable()
        recs = getattr(self, "current_recommendations", [])
        rec_lookup = {rec["champion"]["name"]: rec for rec in recs}
        top_names = [rec["champion"]["name"] for rec in recs[:5]]
        action = self.state.current_action()[1]
        candidates = []
        for name, champion in sorted(self.champion_pool.items()):
            if query and query not in name.lower():
                continue
            if self.current_role_filter and self.current_role_filter not in champion.get("roles", []):
                continue
            candidates.append(champion)

        candidates.sort(key=lambda champ: (0 if champ["name"] in top_names else 1, champ["name"]))

        for index, champion in enumerate(candidates):
            card = DraftChampionCard(champion, self.data_loader.get_champion_pixmap(champion["name"], 48))
            if champion["name"] in unavailable:
                card.set_state("UNAVAILABLE")
            elif champion["name"] in top_names:
                rec = rec_lookup[champion["name"]]
                state = "BAN_PRIORITY" if action == "BAN" else "RECOMMENDED"
                card.set_state(
                    state,
                    rank=top_names.index(champion["name"]) + 1,
                    scores={
                        "total": rec["total_score"],
                        "synergy": rec["synergy_score"],
                        "matchup": rec["matchup_score"],
                        "flex": rec["flex_score"],
                        "reason": rec["reason"],
                    },
                )
            card.clicked.connect(partial(self._handle_card_selection, champion["name"]))
            card.hovered.connect(self._handle_hover)
            self.grid_layout.addWidget(card, index // 8, index % 8)

    def _handle_hover(self, champion_name: str) -> None:
        self.state.hovered_champion = self.champion_pool.get(champion_name)
        team, action, _ = self.state.current_action()
        if action != "PICK" or not self.state.hovered_champion:
            return
        target_slots = self.blue_pick_slots if team == "BLUE" else self.red_pick_slots
        free_roles = self.state.free_roles_for_side(team)
        if free_roles:
            role = free_roles[0]
            target_slots[role].set_hovering(
                self.state.hovered_champion,
                self.data_loader.get_champion_pixmap(champion_name, 80),
                team,
            )

    def _handle_card_selection(self, champion_name: str) -> None:
        champion = self.champion_pool[champion_name]
        team, action, _ = self.state.current_action()
        if champion_name in self.state.get_unavailable():
            return

        if action == "BAN":
            self.state.add_ban(team, champion)
            self._refresh_everything()
            self.search_box.clear()
            self.search_box.setFocus()
            return

        chosen_role = RoleAssignDialog.get_role(
            parent=self,
            champion_name=champion_name,
            filled_roles=set(self.state.filled_roles_for_side(team)),
        )
        if not chosen_role:
            return

        self.state.add_pick(team, champion, chosen_role)
        self._refresh_everything()
        self.search_box.clear()
        self.search_box.setFocus()

    def _maybe_finish_draft(self) -> None:
        team, action, _ = self.state.current_action()
        if team == "COMPLETE":
            self.complete_page.set_result(self.state.blue_picks, self.state.red_picks)
            self.stack.setCurrentWidget(self.complete_page)


class RoleAssignDialog(QDialog):
    def __init__(self, champion_name: str, filled_roles: set[str], parent=None) -> None:
        super().__init__(parent)
        self.selected_role: str | None = None
        self.filled_roles = set(filled_roles)
        self.setWindowTitle("Asignar posicion")
        self.setModal(True)
        self.setFixedSize(360, 220)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #080D14;
                border: 1px solid #0A2535;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        title = QLabel("// ASIGNAR POSICION")
        title.setStyleSheet(
            """
            color: #C89B3C;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 3px;
            """
        )
        layout.addWidget(title)

        subtitle = QLabel(f"Elige la posicion para {champion_name.upper()}")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #5A7A9A; font-size: 11px; font-weight: 700;")
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        for index, role in enumerate(ROLES):
            button = QPushButton(role)
            button.setFixedHeight(38)
            is_filled = role in self.filled_roles
            button.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {'#141A24' if is_filled else '#0C1420'};
                    border: 1px solid {'#7A4A1A' if is_filled else '#0A2535'};
                    border-radius: 2px;
                    color: {'#D9B36C' if is_filled else '#E8EEF4'};
                    font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                    font-size: 11px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    border-color: {'#F0C36E' if is_filled else '#00D4FF'};
                    color: {'#F0C36E' if is_filled else '#00D4FF'};
                }}
                """
            )
            button.clicked.connect(lambda checked=False, chosen_role=role: self._select_role(chosen_role))
            grid.addWidget(button, index // 3, index % 3)

        layout.addLayout(grid)

        hint = QLabel("Puedes asignar cualquier campeon a cualquier posicion. Si eliges una ocupada, el pick anterior se mueve a un hueco libre.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #2A4A6A; font-size: 10px;")
        layout.addWidget(hint)

    def _select_role(self, role: str) -> None:
        self.selected_role = role
        self.accept()

    @classmethod
    def get_role(cls, parent, champion_name: str, filled_roles: set[str]) -> str | None:
        dialog = cls(champion_name=champion_name, filled_roles=filled_roles, parent=parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_role
        return None
