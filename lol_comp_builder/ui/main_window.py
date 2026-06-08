from __future__ import annotations

import random
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QMainWindow,
)

from logic.composition import CompositionState, ROLES
from logic.game_curve import evaluate_team_curve
from logic.saved_compositions import save_composition
from logic.synergy_engine import SynergyEngine
from ui.archetype_cards import ArchetypeCards
from ui.champion_picker import ChampionPicker
from ui.draft_board import DraftBoard, SaveCompoDialog
from ui.draft_mode.draft_screen import DraftScreen
from ui.draft_mode.side_selection import SideSelectionScreen
from ui.mode_selector import ModeSelector
from ui.matchup_mode import MatchupMode
from ui.pizarra_mode import PizarraMode
from ui.random_champ import RandomChampWidget
from ui.saved_mode import SavedMode
from ui.synergy_panel import SynergyPanel
from ui.tierlist_mode import TierlistMode


class MainWindow(QMainWindow):
    def __init__(self, data_bundle: dict, data_loader) -> None:
        super().__init__()
        self.data_loader = data_loader
        self.champion_pool = data_bundle["champion_pool"]
        self.state = CompositionState()
        self.engine = SynergyEngine(self.champion_pool)
        self.current_generator_archetype = "Wombo Combo"
        self.generator_variant_limit = 250
        self.generator_pools: dict[str, list[dict]] = {}
        self.generator_pool_indexes: dict[str, int] = {}
        self.pending_role = "TOP"
        self.all_champion_names = sorted(self.champion_pool)
        self.champion_images = {
            champion_name: self.data_loader.get_champion_pixmap(champion_name, 64)
            for champion_name in self.all_champion_names
        }
        self.mode1_peak_score = 0.0
        self.mode1_peak_pick_count = 0
        self.mode1_peak_signature = ()

        self.setWindowTitle("CompMaker")
        self.resize(1280, 800)
        self.setMinimumSize(1280, 800)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.setWindowIcon(QIcon(str(data_bundle["icon_path"])))

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        self.mode_selector = ModeSelector()
        self.mode_selector.mode_changed.connect(self._switch_mode)
        self.help_button = QPushButton("?")
        self.help_button.setFixedSize(28, 28)
        self.help_button.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #0A2535;
                border-radius: 14px;
                color: #2A4A6A;
                font-size: 12px;
                font-weight: 700;
                padding: 0px;
            }
            QPushButton:hover {
                border-color: #00D4FF;
                color: #00D4FF;
                background-color: #060F18;
            }
            """
        )
        self.help_button.clicked.connect(self._show_help)

        header = QHBoxLayout()
        title = QLabel("CompMaker")
        title.setObjectName("TitleLabel")
        title.setText("COMPMAKER")
        title_font = QFont("Barlow Condensed", 22, QFont.Weight.ExtraBold)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.0)
        title.setFont(title_font)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.mode_selector)
        header.addWidget(self.help_button)

        self.draft_board = DraftBoard()
        self.draft_board.role_clicked.connect(self._open_picker_for_role)
        self.draft_board.role_cleared.connect(self._clear_role)
        self.picker = ChampionPicker(self.data_loader, self.champion_pool)
        self.picker.champion_selected.connect(self._assign_pending_pick)

        self.suggestions_label = QLabel()
        self.suggestions_label.setObjectName("suggestionsPanel")
        self.suggestions_label.setWordWrap(True)
        self.suggestions_label.setStyleSheet(
            """
            QLabel#suggestionsPanel {
                background-color: #080D14;
                border: 1px solid #0A1E2A;
                border-radius: 3px;
                padding: 8px 12px;
                color: #5A7A9A;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 12px;
                letter-spacing: 0.3px;
            }
            """
        )
        self.reset_assistant_button = QPushButton("Reiniciar composicion")
        self.reset_assistant_button.clicked.connect(self._reset_assistant_comp)
        self.save_comp_button = QPushButton("// GUARDAR COMPO")
        self.save_comp_button.setFixedHeight(32)
        self.save_comp_button.setEnabled(False)
        self.save_comp_button.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #7A6030;
                border-radius: 2px;
                color: #7A6030;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 0 16px;
            }
            QPushButton:hover {
                border-color: #C9A84C;
                color: #C9A84C;
                background-color: #0E0C04;
            }
            QPushButton:disabled {
                border-color: #1A1A1A;
                color: #1A1A1A;
            }
            """
        )
        self.save_comp_button.clicked.connect(self.open_save_dialog)

        self.assistant_page = QWidget()
        assistant_layout = QVBoxLayout(self.assistant_page)
        assistant_layout.addWidget(self.draft_board)
        assistant_header = QHBoxLayout()
        suggestions_header = QLabel("// SUGERENCIAS INTELIGENTES")
        suggestions_header.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 2px;
            padding: 0 2px;
            """
        )
        assistant_header.addWidget(suggestions_header)
        assistant_header.addStretch()
        assistant_header.addWidget(self.reset_assistant_button)
        assistant_header.addWidget(self.save_comp_button)
        assistant_layout.addLayout(assistant_header)
        assistant_layout.addWidget(self.suggestions_label)

        self.generator_page = QWidget()
        generator_layout = QVBoxLayout(self.generator_page)
        self.archetype_cards = ArchetypeCards(self.data_loader)
        self.archetype_cards.archetype_selected.connect(self._generate_archetype)
        self.archetype_cards.regenerate_button.clicked.connect(self._regenerate_current)
        generator_layout.addWidget(self.archetype_cards)

        self.random_page = QWidget()
        random_layout = QVBoxLayout(self.random_page)
        self.random_widget = RandomChampWidget()
        self.random_widget.reroll_requested.connect(self._roll_random_champion)
        random_layout.addWidget(self.random_widget)

        self.saved_mode = SavedMode(self.champion_pool)
        self.saved_mode.load_requested.connect(self.load_comp_into_mode1)

        self.tierlist_mode = TierlistMode(self.champion_pool, self.champion_images)
        self.matchup_mode = MatchupMode(self.champion_pool, self.champion_images)
        self.pizarra_mode = PizarraMode(self.champion_pool, self.champion_images)

        self.draft_container = QStackedWidget()
        self.side_selection_screen = SideSelectionScreen()
        self.side_selection_screen.side_selected.connect(self._start_draft_mode)
        self.draft_container.addWidget(self.side_selection_screen)
        self.current_draft_screen: DraftScreen | None = None

        self.mode_stack = QStackedWidget()
        self.mode_stack.addWidget(self.assistant_page)
        self.mode_stack.addWidget(self.generator_page)
        self.mode_stack.addWidget(self.random_page)
        self.mode_stack.addWidget(self.draft_container)
        self.mode_stack.addWidget(self.saved_mode)
        self.mode_stack.addWidget(self.tierlist_mode)
        self.mode_stack.addWidget(self.pizarra_mode)
        self.mode_stack.addWidget(self.matchup_mode)

        self.synergy_panel = SynergyPanel()
        self.synergy_panel.setFixedWidth(320)
        self.synergy_panel.set_data_meta(data_bundle.get("data_meta", {}))

        body = QHBoxLayout()
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.mode_stack)
        body.addLayout(left_layout, stretch=1)
        body.addWidget(self.synergy_panel)

        outer = QVBoxLayout(central)
        outer.addLayout(header)
        outer.addSpacing(10)
        outer.addLayout(body)

        self._refresh_all()
        self._show_random_intro()

    def _switch_mode(self, mode: str) -> None:
        self.mode_selector.current_mode = mode
        if mode == "ASISTENTE":
            self.mode_stack.setCurrentIndex(0)
            self.synergy_panel.setVisible(True)
        elif mode == "GENERADOR":
            self.mode_stack.setCurrentIndex(1)
            self.synergy_panel.setVisible(False)
        elif mode == "RANDOM":
            self.mode_stack.setCurrentIndex(2)
            self.synergy_panel.setVisible(False)
        elif mode == "SIMULADOR":
            self.mode_stack.setCurrentIndex(3)
            self.synergy_panel.setVisible(False)
        elif mode == "GUARDADAS":
            self.mode_stack.setCurrentIndex(4)
            self.synergy_panel.setVisible(False)
            self.saved_mode.refresh()
        elif mode == "TIERLIST":
            self.mode_stack.setCurrentIndex(5)
            self.synergy_panel.setVisible(False)
        elif mode == "MATCHUP":
            self.mode_stack.setCurrentIndex(7)
            self.synergy_panel.setVisible(False)
        elif mode == "PIZARRA":
            self.mode_stack.setCurrentIndex(6)
            self.synergy_panel.setVisible(False)
            self.pizarra_mode.setFocus()
        else:
            return
        self._refresh_all()

    def _start_draft_mode(self, side: str) -> None:
        if self.current_draft_screen is not None:
            self.current_draft_screen.deleteLater()
        self.current_draft_screen = DraftScreen(self.data_loader, self.champion_pool, side)
        self.current_draft_screen.restart_requested.connect(self._reset_draft_mode)
        if self.draft_container.count() > 1:
            old = self.draft_container.widget(1)
            self.draft_container.removeWidget(old)
            old.deleteLater()
        self.draft_container.addWidget(self.current_draft_screen)
        self.draft_container.setCurrentWidget(self.current_draft_screen)

    def _reset_draft_mode(self) -> None:
        self.draft_container.setCurrentWidget(self.side_selection_screen)

    def _open_picker_for_role(self, role: str) -> None:
        if self.mode_selector.current_mode != "ASISTENTE":
            return
        self.pending_role = role
        suggestions = self.engine.compute_suggestions(
            self.state.as_dict(),
            limit=10,
            pure_only=True,
            include_filled_roles=True,
        )
        self.picker.open_for_role(
            role,
            set(self.state.selected_champions()),
            suggestions.get(role, []),
            current_pick=self.state.get_pick(role),
        )

    def _assign_pending_pick(self, champion_name: str) -> None:
        self.state.set_pick(self.pending_role, champion_name)
        self._refresh_all()

    def _clear_role(self, role: str) -> None:
        self.state.set_pick(role, None)
        self._sync_mode1_score_state()
        self._refresh_all()

    def _reset_assistant_comp(self) -> None:
        self.state.clear()
        self._reset_mode1_score_state()
        self._refresh_all()

    def _refresh_all(self) -> None:
        for role in ROLES:
            champion_name = self.state.get_pick(role)
            pixmap = self.data_loader.get_champion_pixmap(champion_name) if champion_name else None
            self.draft_board.update_slot(role, champion_name, pixmap)
        self._update_save_button_state()
        self._refresh_suggestions()
        if self.mode_selector.current_mode == "ASISTENTE":
            raw_result = self.engine.analyze_team(self.state.as_dict(), pure_only=True)
            score_result = self._apply_mode1_score_floor(raw_result)
            score_result = {
                **score_result,
                "display_score": score_result.get("total_score", 0.0),
                "raw_total_score": raw_result.get("total_score", 0.0),
                "adjusted_raw_score": score_result.get("total_score", 0.0),
                "role_coherence_penalty": 0.0,
                "curve_adjustment": 0.0,
                "curve": evaluate_team_curve(self._current_mode1_team()),
            }
            self.synergy_panel.update_mode1(score_result)
        else:
            self.synergy_panel.update_mode2(self.engine.analyze_team(self.state.as_dict()))

    def _refresh_suggestions(self) -> None:
        suggestions = self.engine.compute_suggestions(
            self.state.as_dict(),
            limit=10,
            pure_only=(self.mode_selector.current_mode == "ASISTENTE"),
        )
        if not suggestions:
            self.suggestions_label.setText(
                "Completa algunas picks para ver recomendaciones por rol."
            )
            return
        lines = []
        for role, items in suggestions.items():
            names = []
            for item in items:
                names.append(f"{item['champion']['name']} ({item['total_score']:.1f})")
            lines.append(f"{role}: " + " | ".join(names))
        self.suggestions_label.setText("\n".join(lines))

    def _generate_archetype(self, archetype: str) -> None:
        self.current_generator_archetype = archetype
        pool = self._load_generator_pool(archetype, refresh=True)
        if pool:
            self.generator_pool_indexes[archetype] = 0
            self._apply_generated_picks(pool[0], variant_position=1, variant_total=len(pool))

    def _regenerate_current(self) -> None:
        archetype = self.current_generator_archetype
        pool = self._load_generator_pool(archetype)
        if not pool:
            return
        next_index = self.generator_pool_indexes.get(archetype, 0) + 1
        if next_index >= len(pool):
            pool = self._load_generator_pool(archetype, refresh=True)
            next_index = 0
        self.generator_pool_indexes[archetype] = next_index
        self._apply_generated_picks(pool[next_index], variant_position=next_index + 1, variant_total=len(pool))

    def _load_generator_pool(self, archetype: str, refresh: bool = False) -> list[dict]:
        if refresh or archetype not in self.generator_pools:
            self.generator_pools[archetype] = self.engine.generate_composition_pool(
                archetype,
                limit=self.generator_variant_limit,
            )
            self.generator_pool_indexes[archetype] = 0
        return self.generator_pools.get(archetype, [])

    def _apply_generated_picks(
        self,
        result: dict,
        variant_position: int | None = None,
        variant_total: int | None = None,
    ) -> None:
        self.state.clear()
        for role, champion_name in result["picks"].items():
            self.state.set_pick(role, champion_name)
        explanation = result["explanation"]
        if variant_position is not None and variant_total is not None:
            explanation = f"Variante {variant_position}/{variant_total}. " + explanation
        self.archetype_cards.show_generated_comp(
            result["picks"],
            explanation,
            result["archetype_score"],
        )
        self._refresh_all()

    def _roll_random_champion(self) -> None:
        champion_name = random.choice(self.all_champion_names)
        pixmap = self.data_loader.get_champion_pixmap(champion_name, 220)
        self.random_widget.set_champion(champion_name, pixmap)

    def _show_random_intro(self) -> None:
        inter_path = self.data_loader.inter_path
        if inter_path.exists():
            pixmap = QPixmap(str(inter_path))
            if not pixmap.isNull():
                self.random_widget.set_intro_image(pixmap)
                return
        self.random_widget.small_reroll_button.setText("TIRAR")

    def open_save_dialog(self) -> None:
        team = self._current_mode1_team()
        if len(team) < 2:
            return
        dialog = SaveCompoDialog(team, self.synergy_panel.current_score, parent=self)
        if dialog.exec():
            save_composition(dialog.saved_name, team, self.synergy_panel.current_score)
            self.save_comp_button.setText("// GUARDADO ✓")
            QTimer.singleShot(0, lambda: self.save_comp_button.setText("// GUARDADO OK"))
            QTimer.singleShot(1800, lambda: self.save_comp_button.setText("// GUARDAR COMPO"))

    def load_comp_into_mode1(self, entry: dict) -> None:
        self.state.clear()
        champions = entry.get("champions", [])
        used_names: set[str] = set()

        role_map = {
            champion.get("slot_role"): champion.get("name")
            for champion in champions
            if champion.get("slot_role")
        }
        if role_map:
            for role in ROLES:
                candidate_name = role_map.get(role)
                if candidate_name and candidate_name in self.champion_pool and candidate_name not in used_names:
                    self.state.set_pick(role, candidate_name)
                    used_names.add(candidate_name)
        else:
            for index, role in enumerate(ROLES):
                candidate_name = None
                if index < len(champions):
                    candidate_name = champions[index].get("name")
                if candidate_name and candidate_name in self.champion_pool and candidate_name not in used_names:
                    self.state.set_pick(role, candidate_name)
                    used_names.add(candidate_name)

        self.mode_selector.set_mode("ASISTENTE")
        self._refresh_all()

    def _current_mode1_team(self) -> list[dict]:
        team = []
        for role in ROLES:
            champion_name = self.state.get_pick(role)
            if not champion_name:
                continue
            champion = dict(self.champion_pool[champion_name])
            champion["name"] = champion_name
            champion["slot_role"] = role
            team.append(champion)
        return team

    def _update_save_button_state(self) -> None:
        self.save_comp_button.setEnabled(len(self.state.selected_champions()) >= 2)

    def _show_help(self) -> None:
        QMessageBox.information(
            self,
            "Ayuda de modos",
            (
                "Modo 1 - Asistente de Draft:\n"
                "Haz clic en un rol, elige un campeon y revisa las sugerencias inteligentes.\n\n"
                "Modo 2 - Generador de Compo:\n"
                "Selecciona un arquetipo para autogenerar una composicion completa con roles e iconos.\n\n"
                "Modo 3 - Random Champ:\n"
                "Pulsa volver a tirar para sacar un campeon aleatorio de toda la lista.\n\n"
                "Modo 4 - Simulador de Draft:\n"
                "Elige lado, juega bans y picks por turnos y usa las recomendaciones en vivo.\n\n"
                "Modo 5 - Guardadas:\n"
                "Revisa, renombra, elimina o carga tus composiciones guardadas.\n\n"
                "Modo 6 - Tierlist:\n"
                "Arrastra campeones a tiers S-A-B-C-D-F, exporta y usa auto-rank por rol.\n\n"
                "Modo 7 - Pizarra:\n"
                "Carga equipos, coloca fichas sobre el mapa y dibuja rutas, zonas, wards y pings.\n\n"
                "Modo 8 - Matchup:\n"
                "Elige rol, enemigo y revisa counters y build sugeridos en vivo.\n\n"
                "Tip: clic derecho en una casilla para quitar un campeon."
            ),
        )

    def _reset_mode1_score_state(self) -> None:
        self.mode1_peak_score = 0.0
        self.mode1_peak_pick_count = 0
        self.mode1_peak_signature = ()

    def _sync_mode1_score_state(self) -> None:
        pick_count = len(self.state.selected_champions())
        if pick_count < self.mode1_peak_pick_count:
            self._reset_mode1_score_state()

    def _apply_mode1_score_floor(self, result: dict) -> dict:
        picks_signature = tuple(
            (role, self.state.get_pick(role)) for role in ROLES if self.state.get_pick(role)
        )
        pick_count = len(picks_signature)
        if pick_count < 2:
            self._reset_mode1_score_state()
            return result

        if pick_count < self.mode1_peak_pick_count:
            self._reset_mode1_score_state()
        elif pick_count == self.mode1_peak_pick_count and picks_signature != self.mode1_peak_signature:
            self._reset_mode1_score_state()

        score = float(result.get("total_score", 0.0))
        adjusted_score = score
        if pick_count >= 3 and self.mode1_peak_score > 0:
            adjusted_score = max(score, max(0.0, self.mode1_peak_score - 8.0))

        self.mode1_peak_score = max(self.mode1_peak_score, adjusted_score)
        self.mode1_peak_pick_count = pick_count
        self.mode1_peak_signature = picks_signature

        if adjusted_score != score:
            return {**result, "total_score": round(adjusted_score, 1)}
        return result

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#03050A"))
        pen = QPen(QColor(255, 255, 255, 6))
        pen.setWidth(1)
        painter.setPen(pen)
        for y in range(0, self.height(), 3):
            painter.drawLine(0, y, self.width(), y)
        painter.end()
        super().paintEvent(event)
