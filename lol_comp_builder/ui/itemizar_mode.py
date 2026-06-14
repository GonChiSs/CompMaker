from __future__ import annotations

import html
import re
import threading

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget

from logic.genetic_build_optimizer import GA_GENERATIONS, GeneticBuildOptimizer, OptimizationTarget
from logic.item_data_loader import ItemDataLoader
from logic.lol_knowledge_base import KnowledgeBase
from logic.lol_data_fetcher import fetch_matchup_data, fetch_tier_list
from logic.rune_data_loader import RuneDataLoader
from logic.meta_build_fetcher import builds_are_similar, fetch_meta_build, infer_target_from_meta
from logic.ollama_client import OllamaClient, make_system_prompt, parse_icon_requests, strip_all_tokens
from logic.patch_context_store import PatchContextStore
from ui.model_manager_dialog import ModelManagerDialog

ROLE_OPTIONS = [
    ("top", "TOP"),
    ("jungle", "JGL"),
    ("middle", "MID"),
    ("bottom", "ADC"),
    ("support", "SUP"),
]


class OptimizerProgressBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ratio = 0.0
        self.setFixedHeight(6)

    def set_ratio(self, ratio: float) -> None:
        self._ratio = max(0.0, min(1.0, ratio))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0C1420"))
        filled = self.rect()
        filled.setWidth(int(self.width() * self._ratio))
        painter.fillRect(filled, QColor("#00D4FF"))
        painter.end()
        super().paintEvent(event)


class ItemCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(110)
        self.setStyleSheet(
            """
            QFrame {
                background-color: #07101A;
                border: 1px solid #0A2535;
                border-radius: 4px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(52, 52)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.order_label = QLabel("")
        self.order_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.order_label.setStyleSheet("color: #00D4FF; font-size: 10px; font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(self.order_label)

        self.name_label = QLabel("-")
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("color: #E8EEF4; font-size: 11px; font-weight: 700;")
        layout.addWidget(self.name_label)

        self.gold_label = QLabel("")
        self.gold_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gold_label.setStyleSheet("color: #C9A84C; font-size: 10px;")
        layout.addWidget(self.gold_label)

    def set_item(self, order_text: str, name: str, gold: int, pixmap) -> None:
        self.order_label.setText(order_text)
        self.name_label.setText(name)
        self.gold_label.setText(f"{gold}g" if gold else "")
        self.icon_label.setPixmap(pixmap)


class BuildDisplay(QWidget):
    def __init__(self, item_loader: ItemDataLoader, parent=None):
        super().__init__(parent)
        self.item_loader = item_loader
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label_lbl = QLabel("BUILD")
        self.label_lbl.setStyleSheet("color: #C9A84C; font-size: 11px; font-weight: 700; letter-spacing: 2px;")
        layout.addWidget(self.label_lbl)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.cards: list[ItemCard] = []
        for _ in range(6):
            card = ItemCard()
            self.cards.append(card)
            row.addWidget(card)
        row.addStretch()
        layout.addLayout(row)

        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet(
            "background-color: #080D14; border: 1px solid #0A2535; border-radius: 3px; padding: 8px 10px; color: #A8C1D8;"
        )
        layout.addWidget(self.summary)

    def set_label(self, text: str) -> None:
        self.label_lbl.setText(text)

    def set_build(self, items: list[dict], stats: dict, target_label: str, version: str) -> None:
        for index, card in enumerate(self.cards):
            if index < len(items):
                item = items[index]
                item_id = int(item.get("id", 0))
                pixmap = self.item_loader.get_item_pixmap(item_id, version, size=52)
                card.set_item(f"{index + 1}º", item.get("name", f"Item {item_id}"), int(item.get("gold", 0)), pixmap)
            else:
                card.set_item("", "-", 0, self.item_loader.get_item_pixmap(0, version, size=52))
        stats_text = " | ".join(f"{key}: {value}" for key, value in stats.items()) if stats else "Sin estadisticas de comparacion."
        self.summary.setText(f"{target_label}\n{stats_text}")


class RuneIconCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            """
            QFrame {
                background-color: #07101A;
                border: 1px solid #0A2535;
                border-radius: 4px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(36, 36)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.name_label = QLabel("-")
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("color: #E8EEF4; font-size: 10px; font-weight: 700;")
        layout.addWidget(self.name_label)

    def set_rune(self, name: str, pixmap) -> None:
        self.name_label.setText(name)
        self.icon_label.setPixmap(pixmap)


class RuneRow(QWidget):
    def __init__(self, title: str, card_count: int, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #2A89A8; font-size: 10px; font-weight: 700; letter-spacing: 2px;")
        layout.addWidget(self.title_label)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.cards: list[RuneIconCard] = []
        for _ in range(card_count):
            card = RuneIconCard()
            card.setFixedWidth(88)
            self.cards.append(card)
            row.addWidget(card)
        row.addStretch()
        layout.addLayout(row)

    def set_entries(self, entries: list[dict], rune_loader: RuneDataLoader, version: str) -> None:
        for index, card in enumerate(self.cards):
            if index < len(entries):
                entry = entries[index]
                rune_id = int(entry.get("id", 0))
                pixmap = rune_loader.get_rune_pixmap(rune_id, version, size=36)
                card.set_rune(str(entry.get("name", f"Rune {rune_id}")), pixmap)
                card.show()
            else:
                card.hide()


class RuneDisplay(QWidget):
    def __init__(self, rune_loader: RuneDataLoader, parent=None):
        super().__init__(parent)
        self.rune_loader = rune_loader
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label_lbl = QLabel("RUNAS MAS USADAS")
        self.label_lbl.setStyleSheet("color: #C9A84C; font-size: 11px; font-weight: 700; letter-spacing: 2px;")
        layout.addWidget(self.label_lbl)

        self.primary_row = RuneRow("PRIMARIA", 5)
        self.secondary_row = RuneRow("SECUNDARIA", 3)
        layout.addWidget(self.primary_row)
        layout.addWidget(self.secondary_row)

        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet(
            "background-color: #080D14; border: 1px solid #0A2535; border-radius: 3px; padding: 8px 10px; color: #A8C1D8;"
        )
        layout.addWidget(self.summary)

    def _infer_page(self, rune_payload: dict, rune_entries: dict[int, dict]) -> tuple[list[dict], list[dict], str]:
        stats = rune_payload.get("stats", {})
        if not isinstance(stats, dict) or not rune_entries:
            return [], [], "No se encontraron runas para esta combinacion."

        def row_tuple(rows, index: int) -> tuple[int, float]:
            if not isinstance(rows, list) or index >= len(rows):
                return (0, 0.0)
            row = rows[index]
            if not isinstance(row, list) or len(row) < 3:
                return (0, 0.0)
            try:
                return (int(row[2]), float(row[1]))
            except Exception:
                return (0, 0.0)

        styles: dict[int, dict] = {}
        for rune_id, entry in rune_entries.items():
            if entry.get("is_style"):
                styles[int(rune_id)] = entry

        primary_style_id = 0
        primary_score = (-1, -1.0)
        for style_id in styles:
            style_runes = [entry for entry in rune_entries.values() if int(entry.get("style_id", 0)) == style_id and not entry.get("is_style")]
            score_games = 0
            score_pick = 0.0
            for slot_index in range(4):
                best = max((row_tuple(stats.get(str(entry["id"])), 0) for entry in style_runes if int(entry.get("slot_index", -1)) == slot_index), default=(0, 0.0))
                score_games += best[0]
                score_pick += best[1]
            if (score_games, score_pick) > primary_score:
                primary_score = (score_games, score_pick)
                primary_style_id = style_id

        secondary_style_id = 0
        secondary_score = (-1, -1.0)
        for style_id in styles:
            if style_id == primary_style_id:
                continue
            style_runes = [entry for entry in rune_entries.values() if int(entry.get("style_id", 0)) == style_id and not entry.get("is_style")]
            score_games = 0
            score_pick = 0.0
            for slot_index in range(1, 4):
                best = max((row_tuple(stats.get(str(entry["id"])), 1) for entry in style_runes if int(entry.get("slot_index", -1)) == slot_index), default=(0, 0.0))
                score_games += best[0]
                score_pick += best[1]
            if (score_games, score_pick) > secondary_score:
                secondary_score = (score_games, score_pick)
                secondary_style_id = style_id

        primary_entries: list[dict] = []
        secondary_entries: list[dict] = []
        primary_style = styles.get(primary_style_id)
        secondary_style = styles.get(secondary_style_id)
        if primary_style:
            primary_entries.append(primary_style)
            for slot_index in range(4):
                slot_candidates = [
                    entry for entry in rune_entries.values()
                    if int(entry.get("style_id", 0)) == primary_style_id
                    and not entry.get("is_style")
                    and int(entry.get("slot_index", -1)) == slot_index
                ]
                best_entry = max(
                    slot_candidates,
                    key=lambda entry: row_tuple(stats.get(str(entry["id"])), 0),
                    default=None,
                )
                if best_entry and row_tuple(stats.get(str(best_entry["id"])), 0)[0] > 0:
                    primary_entries.append(best_entry)

        if secondary_style:
            secondary_entries.append(secondary_style)
            best_secondary_by_slot: list[dict] = []
            for slot_index in range(1, 4):
                slot_candidates = [
                    entry for entry in rune_entries.values()
                    if int(entry.get("style_id", 0)) == secondary_style_id
                    and not entry.get("is_style")
                    and int(entry.get("slot_index", -1)) == slot_index
                ]
                best_entry = max(
                    slot_candidates,
                    key=lambda entry: row_tuple(stats.get(str(entry["id"])), 1),
                    default=None,
                )
                if best_entry and row_tuple(stats.get(str(best_entry["id"])), 1)[0] > 0:
                    best_secondary_by_slot.append(best_entry)
            best_secondary_by_slot.sort(key=lambda entry: row_tuple(stats.get(str(entry["id"])), 1), reverse=True)
            secondary_entries.extend(best_secondary_by_slot[:2])

        primary_name = primary_style.get("name", "-") if primary_style else "-"
        secondary_name = secondary_style.get("name", "-") if secondary_style else "-"
        shards = [str(rune_entries[int(rune_id)].get("name", "")) for rune_id in rune_payload.get("stat_shards", []) if int(rune_id) in rune_entries]
        summary = f"Arbol primario: {primary_name} | Arbol secundario: {secondary_name}"
        if shards:
            summary += f" | Shards: {', '.join(shards[:3])}"
        return primary_entries[:5], secondary_entries[:3], summary

    def set_runes(self, rune_payload: dict, rune_entries: dict[int, dict], version: str) -> None:
        primary_entries, secondary_entries, summary = self._infer_page(rune_payload, rune_entries)
        self.primary_row.set_entries(primary_entries, self.rune_loader, version)
        self.secondary_row.set_entries(secondary_entries, self.rune_loader, version)
        self.summary.setText(summary)


class ItemizarMode(QWidget):
    analysis_ready = pyqtSignal(dict, object, bool, str, bool)
    analysis_failed = pyqtSignal(str)
    model_scan_ready = pyqtSignal(object, str)
    chat_reply_ready = pyqtSignal(str, object, object, str)
    chat_stream_ready = pyqtSignal(str)
    optimizer_progress_ready = pyqtSignal(int, float, bool)
    knowledge_base_ready = pyqtSignal(object, bool)

    def __init__(self, champion_pool: dict[str, dict], data_loader, data_meta: dict | None = None, parent=None):
        super().__init__(parent)
        self.champion_pool = champion_pool
        self.data_loader = data_loader
        self.data_meta = data_meta or {}
        preferred_patch = self.data_meta.get("current_patch") or self.data_meta.get("patch")
        self.item_loader = ItemDataLoader(data_loader.base_dir, preferred_patch=preferred_patch)
        self.rune_loader = RuneDataLoader(data_loader.base_dir, preferred_patch=preferred_patch)
        self.ollama_client = OllamaClient()
        self.patch_context_store = PatchContextStore(data_loader.base_dir, champion_pool, self.item_loader, self.rune_loader)
        self.selected_model = ""
        self.selected_champ = ""
        self.selected_role = "middle"
        self.current_constraints: dict = {}
        self.current_patch = ""
        self.current_items: dict[int, dict] = {}
        self.current_result = None
        self.current_meta: dict = {}
        self.current_runes: dict = {}
        self.current_rune_entries: dict[int, dict] = {}
        self.chat_history: list[dict] = []
        self.chat_entries: list[dict] = []
        self.chat_system_prompt = ""
        self.knowledge_base: KnowledgeBase | None = None
        self._meta_reference_visible = False
        self._analysis_request_id = 0
        self._pending_chat_index: int | None = None

        self.analysis_ready.connect(self._on_meta_analysis_done)
        self.analysis_failed.connect(self._show_analysis_error)
        self.model_scan_ready.connect(self._apply_model_scan)
        self.chat_reply_ready.connect(self._apply_chat_reply)
        self.chat_stream_ready.connect(self._apply_chat_stream)
        self.optimizer_progress_ready.connect(self._apply_optimizer_progress)
        self.knowledge_base_ready.connect(self._apply_knowledge_base_ready)

        self._build_ui()
        self._populate_controls()
        self._detect_models()
        self._ensure_knowledge_base()

    def _emit_model_scan_ready(self, models, message: str) -> None:
        try:
            self.model_scan_ready.emit(models, message)
        except RuntimeError:
            return

    def _emit_analysis_ready(self, meta: dict, ga_result, is_similar: bool, target: str, from_chat: bool) -> None:
        try:
            self.analysis_ready.emit(meta, ga_result, is_similar, target, from_chat)
        except RuntimeError:
            return

    def _emit_analysis_failed(self, message: str) -> None:
        try:
            self.analysis_failed.emit(message)
        except RuntimeError:
            return

    def _emit_chat_reply_ready(self, message: str, constraints, icon_requests, raw_response: str) -> None:
        try:
            self.chat_reply_ready.emit(message, constraints, icon_requests, raw_response)
        except RuntimeError:
            return

    def _emit_chat_stream_ready(self, message: str) -> None:
        try:
            self.chat_stream_ready.emit(message)
        except RuntimeError:
            return

    def _emit_optimizer_progress(self, generation: int, best_fitness: float, from_chat: bool) -> None:
        try:
            self.optimizer_progress_ready.emit(generation, best_fitness, from_chat)
        except RuntimeError:
            return

    def _prewarm_selected_model(self, model_id: str) -> None:
        model_name = str(model_id or "").strip()
        if not model_name:
            return

        def worker() -> None:
            ok, message = self.ollama_client.prewarm(model_name)
            if ok and self.selected_model == model_name:
                self._emit_model_scan_ready([model_name], f"Modelo activo: {model_name} · listo para responder")
            elif not ok and self.selected_model == model_name and self.current_patch:
                self._emit_model_scan_ready([model_name], f"Modelo activo: {model_name} · prewarm fallido")

        threading.Thread(target=worker, daemon=True).start()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(14)

        left_panel = QFrame()
        left_panel.setStyleSheet("QFrame { background-color: #050912; border: 1px solid #0A1E2A; }")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(10)

        title = QLabel("// ITEMIZAR")
        title.setStyleSheet(
            "color: #C9A84C; font-family: 'Barlow Condensed', 'Arial Narrow', Arial; "
            "font-size: 14px; font-weight: 800; letter-spacing: 3px;"
        )
        left_layout.addWidget(title)

        helper = QLabel("Selecciona campeon y rol. La app analiza el meta actual y verifica si la build popular ya es optima.")
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #5A7A9A;")
        left_layout.addWidget(helper)

        selectors = QHBoxLayout()
        self.champion_combo = QComboBox()
        self.role_combo = QComboBox()
        for combo in (self.champion_combo, self.role_combo):
            combo.setStyleSheet(
                """
                QComboBox {
                    background-color: #0C1420;
                    border: 1px solid #0A2535;
                    border-radius: 3px;
                    color: #E8EEF4;
                    padding: 7px 12px;
                    min-height: 18px;
                }
                """
            )
        selectors.addWidget(self._mini_label("Campeon"))
        selectors.addWidget(self.champion_combo, 1)
        selectors.addSpacing(8)
        selectors.addWidget(self._mini_label("Rol"))
        selectors.addWidget(self.role_combo)
        left_layout.addLayout(selectors)

        actions = QHBoxLayout()
        self.clear_constraints_button = QPushButton("RESET CHAT")
        self.clear_constraints_button.clicked.connect(self._reset_constraints)
        actions.addStretch()
        actions.addWidget(self.clear_constraints_button)
        left_layout.addLayout(actions)

        self.progress_label = QLabel("Listo para analizar.")
        self.progress_label.setStyleSheet("color: #5A7A9A; font-family: 'JetBrains Mono', 'Courier New', monospace;")
        left_layout.addWidget(self.progress_label)

        self.progress_bar = OptimizerProgressBar()
        left_layout.addWidget(self.progress_bar)

        self.build_display = BuildDisplay(self.item_loader)
        left_layout.addWidget(self.build_display)

        self.rune_display = RuneDisplay(self.rune_loader)
        left_layout.addWidget(self.rune_display)
        left_layout.addStretch()

        right_panel = QFrame()
        right_panel.setStyleSheet("QFrame { background-color: #04070D; border: 1px solid #0A1E2A; }")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(10)

        chat_header = QHBoxLayout()
        chat_title = QLabel("// COMP AI")
        chat_title.setStyleSheet("color: #C9A84C; font-size: 14px; font-weight: 800; letter-spacing: 3px;")
        chat_header.addWidget(chat_title)
        chat_header.addStretch()
        self.model_button = QPushButton("MODELOS")
        self.model_button.setEnabled(False)
        self.model_button.clicked.connect(self._open_model_manager)
        chat_header.addWidget(self.model_button)
        right_layout.addLayout(chat_header)

        self.model_status_label = QLabel("Buscando modelos locales...")
        self.model_status_label.setStyleSheet("color: #5A7A9A;")
        right_layout.addWidget(self.model_status_label)

        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setStyleSheet(
            """
            QTextEdit {
                background-color: #080D14;
                border: 1px solid #0A2535;
                border-radius: 3px;
                color: #E8EEF4;
                padding: 10px;
            }
            """
        )
        right_layout.addWidget(self.chat_log, 1)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText(
            "Pide un objetivo distinto: 'hazme una build AD', 'algo para tankear magia'..."
        )
        self.chat_input.returnPressed.connect(self._send_chat)
        right_layout.addWidget(self.chat_input)

        chat_actions = QHBoxLayout()
        chat_actions.addStretch()
        self.send_button = QPushButton("ENVIAR")
        self.send_button.clicked.connect(self._send_chat)
        chat_actions.addWidget(self.send_button)
        right_layout.addLayout(chat_actions)

        root.addWidget(left_panel, 7)
        root.addWidget(right_panel, 5)

    def _mini_label(self, text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setStyleSheet("color: #2A89A8; font-size: 10px; font-weight: 700; letter-spacing: 2px;")
        return label

    def _populate_controls(self) -> None:
        self.champion_combo.addItems(sorted(self.champion_pool))
        for role_key, role_label in ROLE_OPTIONS:
            self.role_combo.addItem(role_label, role_key)
        self.champion_combo.currentTextChanged.connect(self._on_champion_selected)
        self.role_combo.currentIndexChanged.connect(self._on_role_changed)
        if self.champion_combo.count():
            self.selected_champ = self.champion_combo.currentText().strip()
        self.selected_role = str(self.role_combo.currentData())
        self._analyze_meta_build()

    def _detect_models(self) -> None:
        def worker() -> None:
            running, connection_message = self.ollama_client.connection_status()
            models = self.ollama_client.list_models()
            if models:
                self._emit_model_scan_ready(models, f"Modelo activo: {models[0]}")
            else:
                self._emit_model_scan_ready([], connection_message if not running else "Sin modelos detectados en Ollama.")

        threading.Thread(target=worker, daemon=True).start()

    def _ensure_knowledge_base(self, force_refresh: bool = False) -> None:
        def worker() -> None:
            try:
                if self.knowledge_base is None:
                    kb = KnowledgeBase(self.champion_pool)
                    self.knowledge_base_ready.emit(kb, False)
                    return
                if force_refresh and self.knowledge_base.refresh_if_stale():
                    self.knowledge_base_ready.emit(self.knowledge_base, True)
            except Exception:
                return

        threading.Thread(target=worker, daemon=True).start()

    def _apply_knowledge_base_ready(self, kb: object, refreshed: bool) -> None:
        if isinstance(kb, KnowledgeBase):
            self.knowledge_base = kb
        if not self.knowledge_base:
            return
        if self.knowledge_base.version:
            threading.Thread(
                target=lambda: self.patch_context_store.ensure_patch_snapshot(
                    self.knowledge_base.version,
                    force_refresh=refreshed,
                ),
                daemon=True,
            ).start()
        if refreshed:
            self.model_status_label.setText(f"Parche actualizado a {self.knowledge_base.version} · base de conocimiento refrescada")
        elif not self.selected_model:
            self.model_status_label.setText(
                f"Sin modelo local activo. Base de conocimiento: {len(self.knowledge_base.runes)} runas · "
                f"{len(self.knowledge_base.items)} items · parche {self.knowledge_base.version}"
            )

    def on_mode_entered(self) -> None:
        if self.knowledge_base is None:
            self._ensure_knowledge_base()
        else:
            self._ensure_knowledge_base(force_refresh=True)

    def _apply_model_scan(self, models, message: str) -> None:
        self.model_status_label.setText(message)
        self.model_button.setEnabled(True)
        if models and not self.selected_model:
            self.selected_model = models[0]
            self._prewarm_selected_model(self.selected_model)

    def _open_model_manager(self) -> None:
        dialog = ModelManagerDialog(selected_model=self.selected_model, parent=self)
        if dialog.exec():
            self.selected_model = dialog.selected_model
            self.model_status_label.setText(
                f"Modelo activo: {self.selected_model}" if self.selected_model else "Sin modelo local activo."
            )
            self._prewarm_selected_model(self.selected_model)

    def _on_champion_selected(self, name: str) -> None:
        self.selected_champ = name.strip()
        self._analyze_meta_build()

    def _on_role_changed(self) -> None:
        self.selected_role = str(self.role_combo.currentData())
        self._analyze_meta_build()

    def _resolve_optimizer_target(self, meta: dict, items: dict[int, dict]) -> str:
        if meta.get("found"):
            return infer_target_from_meta(meta, items)
        return OptimizationTarget.GOLD_EFFICIENCY

    def _analyze_meta_build(self) -> None:
        if not self.selected_champ:
            return
        self._analysis_request_id += 1
        request_id = self._analysis_request_id
        self.progress_label.setText("Analizando build meta del parche actual...")
        self.progress_bar.set_ratio(0.0)

        champion_name = self.selected_champ
        role = self.selected_role
        record = self.champion_pool.get(champion_name, {})

        def worker() -> None:
            try:
                version = self.item_loader.get_latest_version()
                items = self.item_loader.load_items(version)
                runes = self.rune_loader.load_runes(version)
                champion_stats = self.item_loader.load_champion_stats(
                    version,
                    champion_name,
                    image_key=record.get("image_key"),
                    champion_record=record,
                )
                meta = fetch_meta_build(champion_name, role)
                target = self._resolve_optimizer_target(meta, items)
                optimizer = GeneticBuildOptimizer(
                    items=items,
                    champion_stats=champion_stats,
                    target=target,
                    champion_level=18,
                    progress_callback=lambda generation, fitness: self._emit_optimizer_progress(generation, fitness, False),
                    role=role,
                    champion_name=champion_name,
                )
                ga_result = optimizer.optimize()
                similar = builds_are_similar(meta.get("full_build", []), ga_result.item_ids)
                meta["version"] = version
                meta["items"] = items
                meta["rune_entries"] = runes
                meta["_request_id"] = request_id
                meta["_champion"] = champion_name
                meta["_role"] = role
                self._emit_analysis_ready(meta, ga_result, similar, target, False)
            except Exception as exc:
                self._emit_analysis_failed(str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_optimizer_progress(self, generation: int, best_fitness: float, from_chat: bool) -> None:
        ratio = generation / float(GA_GENERATIONS)
        self.progress_bar.set_ratio(ratio)
        prefix = "CHAT" if from_chat else "META"
        self.progress_label.setText(f"{prefix} gen {generation:02d}/{GA_GENERATIONS}  fitness {best_fitness:.1f}")

    def _on_meta_analysis_done(self, meta: dict, ga_result, is_similar: bool, target: str, from_chat: bool) -> None:
        if (
            not from_chat
            and (
                int(meta.get("_request_id", 0) or 0) != self._analysis_request_id
                or str(meta.get("_champion", "")) != self.selected_champ
                or str(meta.get("_role", "")) != self.selected_role
            )
        ):
            return
        self.current_patch = meta["version"]
        self.current_items = meta["items"]
        self.current_rune_entries = meta.get("rune_entries", self.current_rune_entries)
        self.current_result = ga_result
        if not from_chat:
            self.current_meta = meta
            self.current_runes = meta.get("runes", self.current_runes)

        active_meta = self.current_meta if self.current_meta else meta
        active_runes = self.current_runes if self.current_runes else meta.get("runes", {})

        if active_meta.get("found"):
            self._meta_reference_visible = True
            meta_items = [self.current_items[item_id] for item_id in active_meta.get("full_build", []) if item_id in self.current_items]
            self.build_display.set_label("BUILD POPULAR  ·  META ACTUAL")
            self.build_display.set_build(
                meta_items,
                {},
                (
                    f"WR META {active_meta.get('winrate', 0):.1f}%  ·  "
                    f"PR {active_meta.get('pickrate', 0):.1f}%  ·  "
                    f"Lane {active_meta.get('resolved_lane', '-')}"
                ),
                self.current_patch,
            )
            status = (
                "Runas y build meta actualizadas desde Lolalytics"
                if not from_chat else
                "La UI mantiene visible la build meta; el calculo matematico queda oculto"
            )
        else:
            self._meta_reference_visible = False
            self.build_display.set_label("BUILD META  ·  SIN DATOS")
            self.build_display.set_build([], {}, "No hay build meta disponible para esta combinacion.", self.current_patch)
            status = "No hubo datos de meta para esta combinacion"

        self.rune_display.set_runes(active_runes, self.current_rune_entries, self.current_patch)

        self.progress_bar.set_ratio(1.0)
        if from_chat and ga_result is not None:
            self.progress_label.setText(
                f"{status}  ·  Fitness {ga_result.fitness:.0f}  ·  Gen {ga_result.generation}/{ga_result.generations_run}"
            )
        else:
            self.progress_label.setText(status)
        try:
            self.patch_context_store.write_champion_context(
                version=self.current_patch,
                champion=self.selected_champ,
                role=self.selected_role,
                current_meta=active_meta,
                current_runes=active_runes,
                current_items=self.current_items,
                rune_entries=self.current_rune_entries,
                champion_record=self.champion_pool.get(self.selected_champ, {}),
            )
        except Exception:
            pass
        self._update_chat_system()

    def _show_analysis_error(self, message: str) -> None:
        self.progress_bar.set_ratio(0.0)
        self.progress_label.setText("Fallo al analizar la build meta.")
        QMessageBox.warning(self, "Comp AI", message)

    def _build_meta_reply(self) -> tuple[str, list[tuple[str, int]]] | None:
        build_ids = [int(item_id) for item_id in self.current_meta.get("full_build", []) if int(item_id) in self.current_items]
        if not build_ids:
            return None
        names = [str(self.current_items[item_id].get("name", f"Item {item_id}")) for item_id in build_ids]
        lane = str(self.current_meta.get("resolved_lane", self.selected_role)).upper()
        reply = (
            f"La build meta actual de {self.selected_champ} {lane} es: "
            f"{' > '.join(names)}. WR {float(self.current_meta.get('winrate', 0.0)):.1f}% "
            f"y PR {float(self.current_meta.get('pickrate', 0.0)):.1f}%."
        )
        return reply, [("ITEM", item_id) for item_id in build_ids[:6]]

    def _current_meta_items(self) -> list[dict]:
        return [
            self.current_items[int(item_id)]
            for item_id in self.current_meta.get("full_build", [])
            if int(item_id) in self.current_items
        ]

    def _build_runes_reply(self) -> tuple[str, list[tuple[str, int]]] | None:
        if not self.current_runes or not self.current_rune_entries:
            return None
        primary_entries, secondary_entries, _ = self.rune_display._infer_page(self.current_runes, self.current_rune_entries)
        if not primary_entries:
            return None
        primary_name = str(primary_entries[0].get("name", "Sin arbol primario"))
        secondary_name = str(secondary_entries[0].get("name", "Sin arbol secundario")) if secondary_entries else "Sin arbol secundario"
        primary_names = ", ".join(str(entry.get("name", "-")) for entry in primary_entries[1:]) or "sin runas primarias"
        secondary_names = ", ".join(str(entry.get("name", "-")) for entry in secondary_entries[1:]) or "sin runas secundarias"
        reply = (
            f"Las runas mas usadas para {self.selected_champ} {self.selected_role.upper()} son "
            f"primaria {primary_name} con {primary_names}; secundaria {secondary_name} con {secondary_names}."
        )
        icon_requests: list[tuple[str, int]] = []
        for rune_id in [int(entry.get("id", 0)) for entry in [*primary_entries, *secondary_entries]]:
            if rune_id > 0:
                key = ("RUNE", rune_id)
                if key not in icon_requests:
                    icon_requests.append(key)
        return reply, icon_requests[:6]

    def _build_literal_reply(self, prompt: str) -> str | None:
        text = str(prompt or "").strip()
        literal_patterns = [
            r"(?is)^responde\s+solo\s+con\s+(.+?)[\.\!\?]?$",
            r"(?is)^responde\s+exactamente[:\s]+(.+?)[\.\!\?]?$",
            r"(?is)^di\s+exactamente[:\s]+(.+?)[\.\!\?]?$",
        ]
        for pattern in literal_patterns:
            match = re.match(pattern, text)
            if not match:
                continue
            literal = match.group(1).strip().strip("\"' ")
            return literal[:240] if literal else None
        return None

    def _build_greeting_reply(self, prompt: str) -> str | None:
        prompt_lower = str(prompt or "").strip().lower()
        compact = re.sub(r"[^a-z0-9áéíóúüñ]+", " ", prompt_lower).strip()
        if compact in {"hola", "hey", "buenas", "me recibes", "estas ahi", "estás ahí", "sigues ahi", "sigues ahí"}:
            return "Si, te recibo bien. Preguntame lo que quieras sobre la build, runas o el modo 9."
        return None

    def _build_viability_reply(self) -> str | None:
        record = self.champion_pool.get(self.selected_champ, {})
        if not record:
            return None
        tag_map = {
            "HARD_ENGAGE": "iniciacion fuerte",
            "AOE_KNOCKUP": "control en area",
            "AOE_STUN": "stun en area",
            "PEEL": "peel",
            "AOE_FOLLOW_UP": "follow-up de teamfight",
            "DAMAGE_REDUCTION": "frontline util",
            "SHORT_RANGE_DPS": "peleas cortas",
            "IMMOBILE_CARRY": "proteger carries inmoviles",
        }
        counter_map = {
            "DISENGAGE": "disengage",
            "LONG_RANGE_POKE": "poke de largo alcance",
            "SPLIT_PUSH_THREAT": "split push",
        }
        strengths = [
            label for tag, label in tag_map.items()
            if tag in record.get("ability_tags", [])
        ][:3]
        counters = [
            label for tag, label in counter_map.items()
            if tag in record.get("synergy_keys", {}).get("countered_by_tags", [])
        ][:3]
        archetypes = record.get("archetype_fit", {})
        best_styles = [
            name for name, _ in sorted(archetypes.items(), key=lambda entry: entry[1], reverse=True)[:2]
            if isinstance(name, str)
        ]
        strengths_text = ", ".join(strengths) if strengths else "iniciacion y presencia en peleas"
        styles_text = " y ".join(best_styles) if best_styles else "teamfights"
        counters_text = ", ".join(counters) if counters else "composiciones que te kitean o te sacan del engage"
        return (
            f"{self.selected_champ} {self.selected_role.upper()} suele ser buena cuando tu equipo necesita "
            f"{strengths_text} y quiere jugar {styles_text}; baja bastante contra {counters_text}."
        )

    def _build_kit_fact_reply(self) -> str | None:
        if self.knowledge_base is None or not self.selected_champ:
            return None
        summary = self.knowledge_base.get_champion_kit_summary(self.selected_champ)
        if not summary:
            return None
        lines = [line.strip("- ").strip() for line in str(summary).splitlines() if line.strip()]
        trimmed = " ".join(lines[:3]).strip()
        if not trimmed:
            return None
        return f"Dato real del kit de {self.selected_champ}: {trimmed}"

    def _build_meta_explanation_reply(self) -> str | None:
        items = self._current_meta_items()
        if not items:
            return None
        record = self.champion_pool.get(self.selected_champ, {})
        tag_map = {
            "HARD_ENGAGE": "iniciar fuerte",
            "AOE_KNOCKUP": "encadenar CC en area",
            "AOE_STUN": "pelear en teamfight",
            "PEEL": "proteger carries",
            "DAMAGE_REDUCTION": "aguantar la entrada",
        }
        strengths = [
            label for tag, label in tag_map.items()
            if tag in record.get("ability_tags", [])
        ][:3]
        first_items = ", ".join(str(item.get("name", "-")) for item in items[:3])
        strengths_text = ", ".join(strengths) if strengths else "entrar y aguantar"
        return (
            f"Tiene sentido porque {first_items} refuerzan el plan natural de {self.selected_champ}: "
            f"{strengths_text}, con una build orientada a frontline y utilidad para peleas largas."
        )

    def _detect_other_champion_in_prompt(self, prompt: str) -> str | None:
        prompt_lower = str(prompt or "").lower()
        alias_map = {
            "nafiri": "Naafiri",
        }
        for alias, canonical in alias_map.items():
            if alias in prompt_lower and canonical != self.selected_champ:
                return canonical
        for champion_name in self.champion_pool.keys():
            if champion_name == self.selected_champ:
                continue
            if champion_name.lower() in prompt_lower:
                return champion_name
        return None

    def _build_other_champion_scope_reply(self, prompt: str) -> str | None:
        prompt_lower = str(prompt or "").lower()
        mentioned = self._detect_other_champion_in_prompt(prompt)
        if not mentioned:
            return None
        if f"contra {mentioned.lower()}" in prompt_lower:
            return None
        return (
            f"Ahora mismo el modo 9 esta analizando {self.selected_champ} {self.selected_role.upper()}. "
            f"Si quieres una respuesta correcta sobre {mentioned}, cambia el campeon activo a {mentioned} y te digo su build o sus runas para esa compo."
        )

    def _extract_champion_mentions(self, prompt: str) -> list[str]:
        prompt_lower = str(prompt or "").lower()
        alias_map = {"nafiri": "Naafiri"}
        found: list[str] = []
        for alias, canonical in alias_map.items():
            if alias in prompt_lower and canonical not in found:
                found.append(canonical)
        for champion_name in self.champion_pool.keys():
            if champion_name.lower() in prompt_lower and champion_name not in found:
                found.append(champion_name)
        return found

    def _infer_shared_role(self, champion_a: str, champion_b: str) -> str:
        roles_a = {role.lower() for role in self.champion_pool.get(champion_a, {}).get("roles", [])}
        roles_b = {role.lower() for role in self.champion_pool.get(champion_b, {}).get("roles", [])}
        shared = roles_a & roles_b
        for preferred in ("middle", "top", "jungle", "support", "bottom", "adc", "mid"):
            normalized = {"mid": "middle", "adc": "bottom"}.get(preferred, preferred)
            if normalized in shared:
                return normalized
        return "middle"

    def _build_matchup_advantage_reply(self, prompt: str) -> str | None:
        prompt_lower = str(prompt or "").lower()
        if " vs " not in prompt_lower and " contra " not in prompt_lower:
            return None
        mentions = self._extract_champion_mentions(prompt)
        if len(mentions) < 2:
            return None
        champ_a, champ_b = mentions[0], mentions[1]
        lane = self._infer_shared_role(champ_a, champ_b)
        data_b = fetch_matchup_data(champ_b, lane)
        data_a = fetch_matchup_data(champ_a, lane)
        counters_b = {str(entry.get("id", "")): entry for entry in data_b.get("counters", [])}
        counters_a = {str(entry.get("id", "")): entry for entry in data_a.get("counters", [])}
        if champ_a in counters_b:
            entry = counters_b[champ_a]
            return (
                f"En meta para {lane.upper()}, {champ_a} parece tener la ventaja contra {champ_b}: "
                f"sale como counter en los datos y ronda {float(entry.get('winrate', 0.0)):.1f}% de win rate en ese matchup."
            )
        if champ_b in counters_a:
            entry = counters_a[champ_b]
            return (
                f"En meta para {lane.upper()}, {champ_b} parece tener la ventaja contra {champ_a}: "
                f"sale como counter en los datos y ronda {float(entry.get('winrate', 0.0)):.1f}% de win rate en ese matchup."
            )
        return (
            f"No tengo una ventaja directa verificada para {champ_a} vs {champ_b} en {lane.upper()} con los datos de matchup disponibles ahora mismo."
        )

    def _build_best_pick_against_reply(self, prompt: str) -> str | None:
        prompt_lower = str(prompt or "").lower()
        if "mejor pick contra" not in prompt_lower and "best pick contra" not in prompt_lower and "cual es el mejor pick contra" not in prompt_lower:
            return None
        mentions = self._extract_champion_mentions(prompt)
        if not mentions:
            return None
        enemy = mentions[0]
        enemy_roles = [role.lower() for role in self.champion_pool.get(enemy, {}).get("roles", [])]
        ordered_roles = [role for role in ("top", "middle", "jungle", "support", "bottom") if role in enemy_roles] or ["top"]
        best_entry = None
        best_lane = ""
        for lane in ordered_roles:
            data = fetch_matchup_data(enemy, lane)
            counters = data.get("counters", [])
            if counters:
                entry = counters[0]
                if best_entry is None or float(entry.get("winrate", 0.0)) > float(best_entry.get("winrate", 0.0)):
                    best_entry = entry
                    best_lane = lane
        if best_entry is None:
            return f"No tengo un counter de meta verificado ahora mismo contra {enemy}."
        return (
            f"Segun los datos de meta para {enemy} {best_lane.upper()}, el mejor pick que tengo verificado ahora mismo es "
            f"{best_entry.get('id', '-')}, con alrededor de {float(best_entry.get('winrate', 0.0)):.1f}% de win rate en ese matchup."
        )

    def _build_ap_damage_opinion_reply(self) -> str | None:
        items = self._current_meta_items()
        if not items:
            return None
        names = ", ".join(str(item.get("name", "-")) for item in items[:3])
        return (
            f"Si te refieres a la build meta actual, no parece pensada para dano AP. Va mas hacia frontline y utilidad con {names}. "
            "Si quieres mas dano magico, ya seria cambiar el enfoque de la build, no solo retocar un item."
        )

    def _build_how_would_you_build_reply(self) -> tuple[str, list[tuple[str, int]]] | None:
        overview = self._build_overview_reply()
        if overview is None:
            return None
        return f"Yo la buildearia muy parecido a esto: {overview[0]}", overview[1]

    def _build_next_item_reply(self, prompt: str) -> tuple[str, list[tuple[str, int]]] | None:
        items = self._current_meta_items()
        if len(items) < 3:
            return None
        prompt_lower = str(prompt or "").lower()
        owned_names = ", ".join(str(item.get("name", "-")) for item in items[:2])
        next_item = items[2]
        reason = "porque es el siguiente paso natural de la build meta"
        if "por delante" in prompt_lower or "ahead" in prompt_lower:
            reason = "porque si vas por delante conviene acelerar el tercer pico de utilidad y tempo"
        return (
            f"Si ya tienes {owned_names}, mi tercer item seria {next_item.get('name', '-')}, {reason}.",
            [("ITEM", int(next_item.get("id", 0)))] if int(next_item.get("id", 0)) > 0 else [],
        )

    def _build_rune_comparison_reply(self) -> str | None:
        rune_reply = self._build_runes_reply()
        if rune_reply is None:
            return None
        return (
            f"Puedo opinar, pero para comparar bien necesito que me digas cuales son 'estas runas' y cuales son 'las otras'. "
            f"Ahora mismo la referencia real del modo 9 es esta: {rune_reply[0]}"
        )

    def _build_overview_reply(self) -> tuple[str, list[tuple[str, int]]] | None:
        meta_reply = self._build_meta_reply()
        explanation = self._build_meta_explanation_reply()
        if meta_reply is None or explanation is None:
            return None
        return f"{meta_reply[0]} {explanation}", meta_reply[1]

    def _build_boots_reply(self) -> str | None:
        items = self._current_meta_items()
        boots = next((item for item in items if "Boots" in str(item.get("name", "")) or "Steelcaps" in str(item.get("name", ""))), None)
        if boots is None:
            return None
        name = str(boots.get("name", "las botas de la build meta"))
        return f"Aqui las botas mas seguras son {name}, porque encajan con la build meta actual de {self.selected_champ} {self.selected_role.upper()}."

    def _build_damage_reply(self, kind: str) -> str | None:
        items = self._current_meta_items()
        if not items:
            return None
        if kind == "ad":
            preferred = [item.get("name", "-") for item in items if any(token in str(item.get("name", "")) for token in ("Steelcaps", "Thornmail", "Sunfire"))][:3]
            preferred_text = ", ".join(preferred) if preferred else "armadura y frontline"
            return f"Si el rival tiene mucho AD, prioriza {preferred_text}; la idea es entrar, aguantar el burst fisico y seguir dando utilidad."
        preferred = [item.get("name", "-") for item in items if any(token in str(item.get("name", "")) for token in ("Abyssal", "Kaenic", "Force of Nature", "Jak'Sho"))][:3]
        preferred_text = ", ".join(preferred) if preferred else "resistencia magica y vida"
        return f"Si el rival tiene mucho AP, prioriza {preferred_text}; necesitas sobrevivir a la entrada magica antes de poder forzar engage."

    def _build_poke_reply(self) -> str | None:
        return (
            f"Contra mucho poke, {self.selected_champ} {self.selected_role.upper()} sufre mas: busca flancos, ventanas cortas de engage "
            "y no fuerces front-to-back largo si te desgastan antes de entrar."
        )

    def _build_game_state_reply(self, state: str) -> str | None:
        items = self._current_meta_items()
        if not items:
            return None
        core = ", ".join(str(item.get("name", "-")) for item in items[:2])
        if state == "ahead":
            return f"Si vas por delante, acelera el core de {core} y busca mas peleas para convertir tu engage en objetivos y tempo."
        return f"Si vas por detras, prioriza completar {core}, vision y peleas faciles a tu rango de engage; evita forzar sin apoyo."

    def _build_clear_reply(self) -> str | None:
        if not self.selected_champ:
            return None
        return (
            f"No tengo un tiempo de clear estructurado y verificable para {self.selected_champ} {self.selected_role.upper()} dentro del modo 9. "
            "Lo fiable es tratarla como una jungla de engage y utilidad, no como una pick orientada a acelerar campamentos como un carry de clear rapido."
        )

    def _build_matchup_reply(self, prompt: str) -> str | None:
        record = self.champion_pool.get(self.selected_champ, {})
        prompt_lower = str(prompt or "").lower()
        mentioned = None
        for champion_name in self.champion_pool.keys():
            if champion_name.lower() in prompt_lower and champion_name != self.selected_champ:
                mentioned = champion_name
                break
        if not mentioned:
            return None
        if mentioned in record.get("countered_by", []):
            return (
                f"Contra {mentioned}, juega mas paciente: evita entrar gratis, busca engage con apoyo y prioriza sobrevivir al primer burst antes de comprometerte."
            )
        return (
            f"Contra {mentioned}, intenta pelear cuando tengas apoyo y angulo de engage claro; si te zonifica o te kitea, juega mas por vision y contraataque."
        )

    def _build_constraints_from_prompt(self, prompt: str) -> dict | None:
        prompt_lower = str(prompt or "").lower()
        tokens = {token for token in re.split(r"[^a-z0-9áéíóúüñ\+]+", prompt_lower) if token}

        def has_term(*terms: str) -> bool:
            return any(term in tokens for term in terms)

        target = ""
        if "utilit" in prompt_lower:
            target = "UTILITY"
        elif "mas tanque" in prompt_lower or "más tanque" in prompt_lower or "mucha vida" in prompt_lower:
            target = "TANK_HP"
        elif "armadura" in prompt_lower or "contra ad" in prompt_lower or "mucho ad" in prompt_lower:
            target = "TANK_ARMOR"
        elif "mr" in prompt_lower or "resistencia magica" in prompt_lower or "resistencia mágica" in prompt_lower or "contra ap" in prompt_lower or "mucho ap" in prompt_lower:
            target = "TANK_MR"
        elif has_term("ap") or "magico" in prompt_lower or "mágico" in prompt_lower:
            target = "MAGIC_DPS"
        elif has_term("ad") or "fisic" in prompt_lower:
            target = "PHYSICAL_DPS"
        elif "letal" in prompt_lower:
            target = "LETHALITY"
        if not target:
            return None
        return {"target": target}

    def _prompt_requests_build_change(self, prompt: str) -> bool:
        prompt_lower = str(prompt or "").lower()
        change_markers = (
            "hazme una build",
            "quiero una build",
            "buildearias tu",
            "buildearías tu",
            "recalcula",
            "recalcul",
            "cambia la build",
            "cambiar la build",
            "otra build",
            "build mas ",
            "build más ",
            "optimiza",
            "optimiz",
            "enfoque",
            "version mas ",
            "versión más ",
        )
        return any(marker in prompt_lower for marker in change_markers)

    def _grounded_fallback_reply(self) -> str:
        return (
            "No he podido construir una respuesta util con suficiente contexto. "
            "Prueba a concretar un poco mas la pregunta o pide la build, las runas, el matchup o el enfoque que quieres comparar."
        )

    def _local_chat_reply(self, prompt: str) -> tuple[str, list[tuple[str, int]]] | None:
        prompt_lower = str(prompt or "").strip().lower()
        greeting = self._build_greeting_reply(prompt)
        if greeting is not None:
            return greeting, []
        matchup_advantage = self._build_matchup_advantage_reply(prompt)
        if matchup_advantage is not None:
            return matchup_advantage, []
        best_pick = self._build_best_pick_against_reply(prompt)
        if best_pick is not None:
            return best_pick, []
        other_scope = self._build_other_champion_scope_reply(prompt)
        if other_scope is not None:
            return other_scope, []
        literal = self._build_literal_reply(prompt)
        if literal is not None:
            return literal, []
        if "como ves la build" in prompt_lower or "cómo ves la build" in prompt_lower or "que tal la build" in prompt_lower or "qué tal la build" in prompt_lower:
            overview = self._build_overview_reply()
            if overview:
                return overview
        if ("falta" in prompt_lower and (" daño ap" in prompt_lower or " dano ap" in prompt_lower or " ap" in prompt_lower)):
            ap_reply = self._build_ap_damage_opinion_reply()
            if ap_reply:
                return ap_reply, []
        if "como buildearias tu" in prompt_lower or "cómo buildearías tu" in prompt_lower or "como buildearias tú" in prompt_lower or "cómo buildearías tú" in prompt_lower:
            build_reply = self._build_how_would_you_build_reply()
            if build_reply:
                return build_reply
        if "tercer item" in prompt_lower or "3er item" in prompt_lower or "third item" in prompt_lower:
            next_item = self._build_next_item_reply(prompt)
            if next_item:
                return next_item
        if "build meta" in prompt_lower or ("meta" in prompt_lower and ("build" in prompt_lower or "items" in prompt_lower)):
            return self._build_meta_reply()
        if "runa" in prompt_lower:
            if "menos eficientes" in prompt_lower or "mas eficientes" in prompt_lower or "más eficientes" in prompt_lower:
                comparison = self._build_rune_comparison_reply()
                if comparison:
                    return comparison, []
            return self._build_runes_reply()
        if "explic" in prompt_lower and "meta" in prompt_lower:
            explanation = self._build_meta_explanation_reply()
            if explanation:
                return explanation, []
        if any(chunk in prompt_lower for chunk in ("curiosidad", "dato", "kit", "habilidad", "habilidades", "como funciona", "cómo funciona")):
            kit_reply = self._build_kit_fact_reply()
            if kit_reply:
                return kit_reply, []
        if "clear" in prompt_lower or "limpia" in prompt_lower or "campamentos" in prompt_lower:
            clear_reply = self._build_clear_reply()
            if clear_reply:
                return clear_reply, []
        if any(chunk in prompt_lower for chunk in ("cuando es buena", "cuándo es buena", "cuando es viable", "cuándo es viable", "cuando elegir", "cuándo elegir")):
            viability = self._build_viability_reply()
            if viability:
                return viability, []
        if "mucho poke" in prompt_lower or "mucho rango" in prompt_lower:
            poke = self._build_poke_reply()
            if poke:
                return poke, []
        if "mucho ad" in prompt_lower or "mucho daño fisico" in prompt_lower or "mucho dano fisico" in prompt_lower:
            reply = self._build_damage_reply("ad")
            if reply:
                return reply, []
        if "mucho ap" in prompt_lower or "mucho daño magico" in prompt_lower or "mucho dano magico" in prompt_lower:
            reply = self._build_damage_reply("ap")
            if reply:
                return reply, []
        if "botas" in prompt_lower:
            boots = self._build_boots_reply()
            if boots:
                return boots, []
        if "voy por delante" in prompt_lower:
            ahead = self._build_game_state_reply("ahead")
            if ahead:
                return ahead, []
        if "voy por detras" in prompt_lower or "voy por detrás" in prompt_lower:
            behind = self._build_game_state_reply("behind")
            if behind:
                return behind, []
        if "contra " in prompt_lower:
            matchup = self._build_matchup_reply(prompt)
            if matchup:
                return matchup, []
        return None

    def _sanitize_chat_reply(
        self,
        prompt: str,
        cleaned_reply: str,
        icon_requests: list[tuple[str, int]],
    ) -> tuple[str, list[tuple[str, int]]]:
        del prompt
        reply = (
            str(cleaned_reply or "")
            .replace("```json", "")
            .replace("```", "")
            .replace("[TOKEN_BUILD_REQUEST]", "")
            .strip()
        )
        if reply.startswith("[") and not icon_requests:
            reply = ""
        return reply, icon_requests

    def _preview_stream_reply(self, partial_text: str) -> str:
        preview = str(partial_text or "")
        preview = re.sub(r"\[(?:BUILD_REQUEST|TARGET_BUILD|ICONS):.*$", "", preview, flags=re.DOTALL)
        preview = preview.replace("```json", "").replace("```", "").strip()
        return preview

    def _build_live_meta_context(self, prompt: str) -> str:
        prompt_lower = str(prompt or "").lower()
        lines: list[str] = []
        mentions = self._extract_champion_mentions(prompt)

        if self.current_meta.get("found"):
            build_names = [
                str(self.current_items[item_id].get("name", f"Item {item_id}"))
                for item_id in self.current_meta.get("full_build", [])
                if item_id in self.current_items
            ]
            if build_names:
                lines.append(
                    "=== BUILD META ACTIVA ===\n"
                    f"{self.selected_champ} {str(self.current_meta.get('resolved_lane', self.selected_role)).upper()}: "
                    f"{' > '.join(build_names[:6])}"
                )

        if self.current_runes and self.current_rune_entries:
            primary_entries, secondary_entries, _ = self.rune_display._infer_page(self.current_runes, self.current_rune_entries)
            primary_names = ", ".join(str(entry.get("name", "-")) for entry in primary_entries[:5])
            secondary_names = ", ".join(str(entry.get("name", "-")) for entry in secondary_entries[:3])
            if primary_names:
                lines.append(
                    "=== RUNAS META ACTIVAS ===\n"
                    f"Primaria: {primary_names}\nSecundaria: {secondary_names or 'sin secundaria verificada'}"
                )

        if len(mentions) >= 2 and (" vs " in prompt_lower or " contra " in prompt_lower):
            champ_a, champ_b = mentions[0], mentions[1]
            lane = self._infer_shared_role(champ_a, champ_b)
            data_a = fetch_matchup_data(champ_a, lane)
            data_b = fetch_matchup_data(champ_b, lane)
            counters_a = ", ".join(
                f"{entry.get('id', '-')} ({float(entry.get('winrate', 0.0)):.1f}%)"
                for entry in data_a.get("counters", [])[:3]
            )
            counters_b = ", ".join(
                f"{entry.get('id', '-')} ({float(entry.get('winrate', 0.0)):.1f}%)"
                for entry in data_b.get("counters", [])[:3]
            )
            lines.append(
                "=== MATCHUP META ===\n"
                f"{champ_a} {lane.upper()} counters verificados: {counters_a or 'sin datos'}\n"
                f"{champ_b} {lane.upper()} counters verificados: {counters_b or 'sin datos'}"
            )
        elif "mejor pick contra" in prompt_lower and mentions:
            enemy = mentions[0]
            enemy_roles = [role.lower() for role in self.champion_pool.get(enemy, {}).get("roles", [])]
            ordered_roles = [role for role in ("top", "middle", "jungle", "support", "bottom") if role in enemy_roles] or ["top"]
            for lane in ordered_roles[:2]:
                data = fetch_matchup_data(enemy, lane)
                counters = ", ".join(
                    f"{entry.get('id', '-')} ({float(entry.get('winrate', 0.0)):.1f}%)"
                    for entry in data.get("counters", [])[:3]
                )
                if counters:
                    lines.append(
                        "=== COUNTERS META ===\n"
                        f"{enemy} {lane.upper()} esta siendo castigado por: {counters}"
                    )
                    break

        return "\n\n".join(lines).strip()

    def _build_compact_local_context(self) -> str:
        blocks: list[str] = []
        patch_prompt = self.patch_context_store.get_patch_prompt(self.current_patch or "unknown")
        if patch_prompt:
            blocks.append(patch_prompt)
        champion_prompt = self.patch_context_store.get_champion_prompt(self.selected_champ, self.selected_role)
        if champion_prompt:
            blocks.append(champion_prompt)
        if self.current_constraints:
            blocks.append(f"Restricciones activas del usuario: {self.current_constraints}")
        return "\n\n".join(blocks).strip()

    def _send_chat(self) -> None:
        prompt = self.chat_input.text().strip()
        if not prompt:
            return
        if not self.selected_model:
            QMessageBox.information(
                self,
                "IA local no disponible",
                "Instala un modelo desde el menu MODELOS para usar el chat.",
            )
            return
        self.chat_input.clear()
        self.send_button.setEnabled(False)
        self._pending_chat_index = None
        self.chat_history.append({"role": "user", "content": prompt})
        self._append_chat("Usuario", prompt)
        self._pending_chat_index = self._append_chat("Comp AI", "...")
        context = self._chat_context()
        self._update_chat_system()
        dynamic_context = self._build_compact_local_context()
        if self.knowledge_base is not None:
            detected = self.knowledge_base.detect_entities(prompt)
            kb_context = self.knowledge_base.build_context_block(detected, current_champion="")
            live_meta_context = self._build_live_meta_context(prompt)
            dynamic_context = "\n\n".join(
                block for block in (dynamic_context, kb_context, live_meta_context) if block
            ).strip()

        def worker() -> None:
            try:
                reply = self.ollama_client.stream_generate(
                    self.selected_model,
                    prompt,
                    context=context,
                    system_prompt=self.chat_system_prompt,
                    history=self.chat_history[:-1],
                    dynamic_context=dynamic_context,
                    callback=lambda partial: self._emit_chat_stream_ready(self._preview_stream_reply(partial)),
                )
                cleaned_reply, constraints = self.ollama_client.extract_build_request(reply)
                icon_requests = parse_icon_requests(reply)
                cleaned_preview = strip_all_tokens((cleaned_reply or "").strip())
                should_apply_constraints = bool(constraints) and self._prompt_requests_build_change(prompt)
                if not cleaned_preview and isinstance(constraints, dict) and constraints and should_apply_constraints:
                    cleaned_reply = "He aplicado tu peticion al optimizador y voy a recalcular la build."
                else:
                    cleaned_reply = cleaned_preview
                if constraints and not should_apply_constraints:
                    constraints = None
                final_message, final_icons = self._sanitize_chat_reply(prompt, cleaned_reply, icon_requests)
                if not str(final_message or "").strip():
                    final_message = self._grounded_fallback_reply()
                    final_icons = []
                self._emit_chat_reply_ready(final_message or "Sin respuesta del modelo.", constraints, final_icons, reply)
            except Exception as exc:
                self._emit_chat_reply_ready(f"Error conectando con Ollama: {exc}", None, [], "")

        threading.Thread(target=worker, daemon=True).start()
        return

    def _apply_chat_stream(self, message: str) -> None:
        if self._pending_chat_index is None:
            return
        preview = str(message or "").strip() or "..."
        self._update_chat_entry(self._pending_chat_index, message=preview)

    def _apply_chat_reply(self, message: str, constraints, icon_requests, raw_response: str) -> None:
        if raw_response:
            self.chat_history.append({"role": "assistant", "content": raw_response})
        if self._pending_chat_index is not None:
            self._update_chat_entry(self._pending_chat_index, message=message, icon_requests=icon_requests)
            self._pending_chat_index = None
        else:
            self._append_chat("Comp AI", message, icon_requests=icon_requests)
        self.send_button.setEnabled(True)
        if isinstance(constraints, dict) and constraints:
            sanitized = self._sanitize_constraints(constraints)
            self.current_constraints = sanitized
            self._append_chat("Sistema", f"Restricciones detectadas: {sanitized}")
            self._start_optimization_with_constraints(sanitized)

    def _start_optimization_with_constraints(self, constraints: dict) -> None:
        if not self.selected_champ:
            return
        self.progress_label.setText("Calculando build personalizada...")
        self.progress_bar.set_ratio(0.0)
        champion_name = self.selected_champ
        role = self.selected_role
        record = self.champion_pool.get(champion_name, {})
        target = str(constraints.get("target") or self._resolve_optimizer_target(self.current_meta, self.current_items or {}))

        def worker() -> None:
            try:
                version = self.current_patch or self.item_loader.get_latest_version()
                items = self.current_items or self.item_loader.load_items(version)
                champion_stats = self.item_loader.load_champion_stats(
                    version,
                    champion_name,
                    image_key=record.get("image_key"),
                    champion_record=record,
                )
                optimizer = GeneticBuildOptimizer(
                    items=items,
                    champion_stats=champion_stats,
                    target=target,
                    champion_level=18,
                    progress_callback=lambda generation, fitness: self._emit_optimizer_progress(generation, fitness, True),
                    constraints=constraints,
                    role=role,
                    champion_name=champion_name,
                )
                ga_result = optimizer.optimize()
                meta = {
                    "version": version,
                    "items": items,
                    "rune_entries": self.current_rune_entries,
                    "runes": self.current_runes,
                    "found": self.current_meta.get("found", False),
                    "full_build": list(self.current_meta.get("full_build", [])),
                    "winrate": float(self.current_meta.get("winrate", 0.0)),
                    "pickrate": float(self.current_meta.get("pickrate", 0.0)),
                    "resolved_lane": self.current_meta.get("resolved_lane", role),
                    "_champion": champion_name,
                    "_role": role,
                }
                self._emit_analysis_ready(meta, ga_result, True, target, True)
            except Exception as exc:
                self._emit_analysis_failed(str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _sanitize_constraints(self, constraints: dict) -> dict:
        sanitized: dict = {}
        if "target" in constraints:
            sanitized["target"] = str(constraints["target"])
        if "force_items" in constraints:
            sanitized["force_items"] = [int(item) for item in constraints["force_items"] if str(item).isdigit()]
        if "exclude_items" in constraints:
            sanitized["exclude_items"] = [int(item) for item in constraints["exclude_items"] if str(item).isdigit()]
        if "min_hp" in constraints:
            try:
                sanitized["min_hp"] = float(constraints["min_hp"])
            except Exception:
                pass
        if "prefer_tags" in constraints and isinstance(constraints["prefer_tags"], list):
            sanitized["prefer_tags"] = [str(tag).strip() for tag in constraints["prefer_tags"] if str(tag).strip()]
        return sanitized

    def _append_chat(self, speaker: str, message: str, icon_requests: list[tuple[str, int]] | None = None) -> int:
        self.chat_entries.append(
            {
                "speaker": str(speaker),
                "message": str(message),
                "icon_requests": list(icon_requests or []),
            }
        )
        self._render_chat_log()
        return len(self.chat_entries) - 1

    def _update_chat_entry(
        self,
        index: int,
        *,
        message: str | None = None,
        icon_requests: list[tuple[str, int]] | None = None,
    ) -> None:
        if index < 0 or index >= len(self.chat_entries):
            return
        if message is not None:
            self.chat_entries[index]["message"] = str(message)
        if icon_requests is not None:
            self.chat_entries[index]["icon_requests"] = list(icon_requests)
        self._render_chat_log()

    def _render_chat_log(self) -> None:
        blocks = [
            self._build_chat_entry_html(
                entry.get("speaker", ""),
                entry.get("message", ""),
                entry.get("icon_requests", []),
            )
            for entry in self.chat_entries
        ]
        self.chat_log.setHtml("".join(blocks))
        self.chat_log.verticalScrollBar().setValue(self.chat_log.verticalScrollBar().maximum())

    def _build_chat_entry_html(self, speaker: str, message: str, icon_requests: list[tuple[str, int]]) -> str:
        safe_message = html.escape(str(message or "")).replace("\n", "<br>")
        icon_block = self._build_icon_block_html(icon_requests or [])
        return (
            "<div style='margin-bottom:12px;'>"
            f"<span style='color:#C9A84C;font-weight:700'>{html.escape(speaker)}</span>"
            f"<span style='color:#7C96B0'> :: </span>"
            f"<span style='color:#E8EEF4'>{safe_message}</span>"
            f"{icon_block}</div>"
        )

    def _build_icon_block_html(self, icon_requests: list[tuple[str, int]]) -> str:
        if not icon_requests:
            return ""
        version = self.current_patch or self.item_loader.get_latest_version()
        fragments: list[str] = ["<div style='margin-top:10px;text-align:center;'>"]
        for kind, entity_id in icon_requests[:6]:
            if kind == "ITEM":
                item = self.current_items.get(int(entity_id))
                if not item:
                    continue
                path = self.item_loader.get_item_icon_path(int(entity_id), version)
                if not path or not path.exists():
                    continue
                label = html.escape(str(item.get("name", f"Item {entity_id}")))
                fragments.append(
                    f"<span style='display:inline-block;width:74px;text-align:center;vertical-align:top;margin:0 6px 6px 6px;'>"
                    f"<img src='file:///{path.as_posix()}' width='36' height='36'>"
                    f"<br><span style='color:#00D4FF;font-size:9px;line-height:1.2;'>{label[:14]}</span></span>"
                )
            elif kind == "RUNE" and self.knowledge_base is not None:
                rune = self.knowledge_base.runes.get(int(entity_id))
                if not rune:
                    continue
                path = self.rune_loader.get_rune_icon_path(int(entity_id), version)
                if not path or not path.exists():
                    continue
                label = html.escape(str(rune.get("name", f"Rune {entity_id}")))
                ring_color = "#C9A84C" if int(rune.get("slot", 1)) == 0 else "#00D4FF"
                fragments.append(
                    f"<span style='display:inline-block;width:74px;text-align:center;vertical-align:top;margin:0 6px 6px 6px;'>"
                    f"<img src='file:///{path.as_posix()}' width='36' height='36' "
                    f"style='border:1px solid {ring_color};border-radius:18px;background:#0C1420;'>"
                    f"<br><span style='color:{ring_color};font-size:9px;line-height:1.2;'>{label[:14]}</span></span>"
                )
        fragments.append("</div>")
        return "".join(fragments)

    def _chat_context(self) -> dict:
        return {
            "champion": self.selected_champ,
            "role": self.selected_role,
            "patch": self.current_patch or "unknown",
            "constraints": self.current_constraints,
        }

    def _update_chat_system(self) -> None:
        if self.selected_champ:
            optimization_target = (
                getattr(self.current_result, "target", None)
                or self._resolve_optimizer_target(self.current_meta, self.current_items or {})
            )
            self.chat_system_prompt = make_system_prompt(
                champion_name=self.selected_champ,
                role=self.selected_role,
                current_build=[],
                all_items=self.current_items,
                optimization_target=str(optimization_target),
                patch_version=self.current_patch,
            )
        if self.current_patch:
            self.model_status_label.setText(
                f"Modelo activo: {self.selected_model}  ·  Parche {self.current_patch}"
                if self.selected_model else f"Parche {self.current_patch}  ·  Sin modelo local activo."
            )

    def _reset_constraints(self) -> None:
        self.current_constraints = {}
        self.chat_history = []
        self.chat_system_prompt = ""
        self.chat_entries = []
        self._pending_chat_index = None
        self._render_chat_log()
        self._analyze_meta_build()
