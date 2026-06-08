from __future__ import annotations

from functools import partial

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.image_utils import build_rounded_cover_pixmap


class ChampionCard(QPushButton):
    def __init__(
        self,
        champion_name: str,
        pixmap,
        is_recommended: bool,
        is_disabled: bool,
        tooltip_text: str,
        rank: int | None = None,
        rec_score: float | None = None,
        is_secondary_recommendation: bool = False,
    ) -> None:
        super().__init__()
        self.champion_name = champion_name
        self.setFixedSize(104, 132)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setEnabled(not is_disabled)
        self.setObjectName("champCard")

        if is_recommended and is_secondary_recommendation:
            border = "#005A70"
            text_color = "#00A0B8"
            background = "#040E14"
        else:
            border = "#00D4FF" if is_recommended else ("#0A1018" if is_disabled else "#0A1E2A")
            text_color = "#2A4A6A" if is_disabled else ("#00D4FF" if is_recommended else "#5A7A9A")
            background = "#080C12" if is_disabled else ("#06141E" if is_recommended else "#0C1420")
        hover = "#0E1A28"
        self.setStyleSheet(
            f"""
            QPushButton {{
                text-align: center;
                background-color: {background};
                border: 2px solid {border};
                border-radius: 3px;
                color: {text_color};
            }}
            QPushButton:hover {{
                border-color: {"#00D4FF" if is_recommended else "#0A4A6A"};
                background-color: {hover};
            }}
            """
        )
        if is_recommended:
            glow = QGraphicsDropShadowEffect(self)
            glow.setBlurRadius(6 if is_secondary_recommendation else 14)
            glow.setOffset(0, 0)
            glow.setColor(QColor("#005A70" if is_secondary_recommendation else "#00D4FF"))
            self.setGraphicsEffect(glow)
        self.setToolTip(tooltip_text)

        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(8, 8, 8, 8)
        wrapper.setSpacing(6)

        image_wrapper = QFrame()
        image_wrapper.setStyleSheet(
            """
            QFrame {
                background-color: transparent;
                border: none;
            }
            """
        )
        image_layout = QVBoxLayout(image_wrapper)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(0)

        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)
        badge_row.addStretch()
        if is_recommended and rank is not None and rec_score is not None:
            badge = QLabel(f"{rank:02d}")
            badge_bg = "#005A70" if is_secondary_recommendation else "#00D4FF"
            badge_text = "#00A0B8" if is_secondary_recommendation else "#03050A"
            badge.setStyleSheet(
                f"""
                QLabel {{
                    background-color: {badge_bg};
                    color: {badge_text};
                    min-width: 24px;
                    min-height: 16px;
                    max-width: 24px;
                    max-height: 16px;
                    border-radius: 2px;
                    padding: 1px 3px;
                    font-weight: 800;
                    font-size: 9px;
                    font-family: 'JetBrains Mono', 'Courier New', monospace;
                }}
                """
            )
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_row.addWidget(badge)
        image_layout.addLayout(badge_row)

        image_label = QLabel()
        image_label.setPixmap(build_rounded_cover_pixmap(pixmap, 58, 16))
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_layout.addWidget(image_label, alignment=Qt.AlignmentFlag.AlignCenter)

        text_label = QLabel(champion_name)
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setStyleSheet(
            f"""
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: {text_color};
            border: none;
            """
        )

        wrapper.addWidget(image_wrapper)
        wrapper.addWidget(text_label)


class ChampionPicker(QDialog):
    champion_selected = pyqtSignal(str)

    def __init__(self, data_loader, champion_pool: dict[str, dict]) -> None:
        super().__init__()
        self.data_loader = data_loader
        self.champion_pool = champion_pool
        self.current_role = "TOP"
        self.selected_names: set[str] = set()
        self.recommendations: list[dict] = []

        self.setWindowTitle("Seleccionar campeon")
        self.setModal(True)
        self.setFixedSize(960, 660)
        self.setStyleSheet("QDialog { background-color: #03050A; border: 1px solid #0A1E2A; }")

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar campeon...")
        self.search_box.textChanged.connect(self.refresh_cards)

        header = QLabel("// SELECCION DE CAMPEON")
        header.setObjectName("SectionTitle")
        header.setStyleSheet(
            """
            color: #C9A84C;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 3px;
            """
        )

        helper = QLabel("Los recomendados para este rol aparecen destacados en azul.")
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #1A3A55; font-size: 10px; letter-spacing: 1px;")

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.grid_widget)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QVBoxLayout(self)
        content.addWidget(header)
        content.addWidget(helper)
        content.addWidget(self.search_box)
        content.addWidget(self.scroll)

    def open_for_role(
        self,
        role: str,
        selected_names: set[str],
        recommendations: list[dict],
        current_pick: str | None = None,
    ) -> None:
        self.current_role = role
        self.selected_names = set(selected_names)
        if current_pick is not None:
            self.selected_names.discard(current_pick)
        self.recommendations = list(recommendations)
        self.search_box.setPlaceholderText(f"Buscar campeon para {role}...")
        self.search_box.clear()
        self.refresh_cards()
        self.scroll.verticalScrollBar().setValue(0)
        self.exec()

    def refresh_cards(self) -> None:
        self._clear_grid()

        query = self.search_box.text().strip().lower()
        top10_names = [item["champion"].get("name", "") for item in self.recommendations]
        top10_lookup = {item["champion"].get("name", ""): item for item in self.recommendations}

        candidates = []
        for champion_name in sorted(self.champion_pool):
            if query and query not in champion_name.lower():
                continue
            candidates.append(champion_name)

        candidates.sort(key=lambda name: (top10_names.index(name) if name in top10_names else 999, name))

        for index, champion_name in enumerate(candidates):
            info = self.champion_pool[champion_name]
            top10_item = top10_lookup.get(champion_name)
            is_recommended = top10_item is not None
            disabled = champion_name in self.selected_names
            rank = top10_names.index(champion_name) + 1 if is_recommended else None
            rec_score = top10_item["total_score"] if is_recommended else None
            tags = ", ".join(info.get("ability_tags", [])[:4])
            tooltip_lines = [f"Roles: {', '.join(info.get('roles', []))}"]
            if tags:
                tooltip_lines.append(f"Claves: {tags}")
            if top10_item:
                tooltip_lines.append(f"Rank: #{rank}")
                tooltip_lines.append(f"Score: {top10_item['total_score']:.1f}")
                tooltip_lines.append(f"Delta: +{top10_item['delta']:.1f} sinergia")
                tooltip_lines.append(top10_item.get("reason", ""))
            tooltip = "\n".join(tooltip_lines)

            card = ChampionCard(
                champion_name=champion_name,
                pixmap=self.data_loader.get_champion_pixmap(champion_name, 58),
                is_recommended=is_recommended,
                is_disabled=disabled,
                tooltip_text=tooltip,
                rank=rank,
                rec_score=rec_score,
                is_secondary_recommendation=bool(rank and rank > 5),
            )
            card.clicked.connect(partial(self._select_champion, champion_name))
            row = index // 7
            col = index % 7
            self.grid_layout.addWidget(card, row, col)

        if not candidates:
            empty = QLabel("No hay campeones que coincidan con la busqueda.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #CBD5E1; padding: 30px;")
            self.grid_layout.addWidget(empty, 0, 0, 1, 7)

    def _select_champion(self, champion_name: str) -> None:
        self.champion_selected.emit(champion_name)
        self.accept()

    def _clear_grid(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
