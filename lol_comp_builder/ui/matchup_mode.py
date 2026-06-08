from __future__ import annotations

import threading
from typing import Optional

from PyQt6.QtCore import QRect, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from logic.lol_data_fetcher import fetch_item_pixmap, fetch_matchup_data
from ui.image_utils import build_rounded_cover_pixmap
from ui.tierlist_mode import ROLE_CONFIG


def _normalize_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


class MatchupMode(QWidget):
    matchup_ready = pyqtSignal(object, str, str)

    def __init__(self, all_champions: dict, champion_images: dict, parent=None):
        super().__init__(parent)
        self.all_champions = all_champions
        self.champion_images = champion_images
        self.selected_role = ""
        self.selected_enemy = ""
        self._champion_name_map = {_normalize_name(name): name for name in all_champions}
        self.matchup_ready.connect(self._on_matchup_ready)
        self._build_ui()
        self._build_enemy_grid()

    def _build_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(18, 16, 18, 16)
        main.setSpacing(12)

        title = QLabel("// MATCHUP")
        title.setStyleSheet(
            """
            color: #FF3B3B;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 3px;
            """
        )
        main.addWidget(title)

        role_label = QLabel("PASO 1  ·  ELIGE ROL")
        role_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 2px;
            """
        )
        main.addWidget(role_label)

        role_row = QHBoxLayout()
        role_row.setSpacing(10)
        self.role_btns: list[LargeRoleButton] = []
        for cfg in ROLE_CONFIG:
            button = LargeRoleButton(cfg)
            button.clicked_role.connect(self._on_role_selected)
            self.role_btns.append(button)
            role_row.addWidget(button)
        role_row.addStretch()
        main.addLayout(role_row)

        self.step2_widget = QWidget()
        step2 = QVBoxLayout(self.step2_widget)
        step2.setContentsMargins(0, 0, 0, 0)
        step2.setSpacing(10)

        enemy_label = QLabel("PASO 2  ·  ELIGE ENEMIGO")
        enemy_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 2px;
            """
        )
        step2.addWidget(enemy_label)

        self.enemy_search = QLineEdit()
        self.enemy_search.setPlaceholderText("BUSCAR CAMPEON ENEMIGO...")
        self.enemy_search.setFixedHeight(30)
        self.enemy_search.setStyleSheet(
            """
            QLineEdit {
                background-color: #0C1420;
                border: 1px solid #0A1E2A;
                border-radius: 2px;
                color: #E8EEF4;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 0 10px;
            }
            QLineEdit:focus {
                border-color: #FF3B3B;
            }
            """
        )
        self.enemy_search.textChanged.connect(self._filter_enemy_grid)
        step2.addWidget(self.enemy_search)

        enemy_scroll = QScrollArea()
        enemy_scroll.setWidgetResizable(True)
        enemy_scroll.setStyleSheet(
            """
            QScrollArea {
                border: 1px solid #0A1420;
                border-radius: 3px;
                background: #080D14;
            }
            QScrollArea > QWidget > QWidget {
                background: #080D14;
            }
            """
        )

        self.enemy_widget = QWidget()
        self.enemy_grid = QGridLayout(self.enemy_widget)
        self.enemy_grid.setContentsMargins(8, 8, 8, 8)
        self.enemy_grid.setHorizontalSpacing(6)
        self.enemy_grid.setVerticalSpacing(6)
        enemy_scroll.setWidget(self.enemy_widget)
        step2.addWidget(enemy_scroll, 1)
        self.step2_widget.hide()
        main.addWidget(self.step2_widget, 1)

        self.results_widget = QWidget()
        results_layout = QVBoxLayout(self.results_widget)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(10)

        self.matchup_header = QLabel("VS")
        self.matchup_header.setStyleSheet(
            """
            color: #E8EEF4;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 2px;
            """
        )
        results_layout.addWidget(self.matchup_header)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        for text, width, color in [
            ("COUNTERS", 270, "#C9A84C"),
            ("BUILD", 320, "#C9A84C"),
            ("INICIO", 130, "#2A4A6A"),
        ]:
            label = QLabel(text)
            label.setMinimumWidth(width)
            label.setStyleSheet(
                f"""
                color: {color};
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2px;
                """
            )
            header_row.addWidget(label)
        header_row.addStretch()
        results_layout.addLayout(header_row)

        self.counter_rows_layout = QVBoxLayout()
        self.counter_rows_layout.setSpacing(8)
        results_layout.addLayout(self.counter_rows_layout)

        self.results_loading = QLabel("CARGANDO DATOS...")
        self.results_loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_loading.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 2px;
            """
        )
        self.results_loading.hide()
        results_layout.addWidget(self.results_loading)
        self.results_widget.hide()
        main.addWidget(self.results_widget)

    def _build_enemy_grid(self) -> None:
        cols = 12
        self._enemy_btns: dict[str, EnemyChampButton] = {}
        for index, name in enumerate(sorted(self.all_champions.keys())):
            button = EnemyChampButton(name, self.champion_images.get(name))
            button.clicked_name.connect(self._on_enemy_selected)
            self._enemy_btns[name] = button
            self.enemy_grid.addWidget(button, index // cols, index % cols)

    def _filter_enemy_grid(self, query: str) -> None:
        upper_query = query.upper()
        for name, button in self._enemy_btns.items():
            button.setVisible(not upper_query or upper_query in name.upper())

    def _on_role_selected(self, role_key: str) -> None:
        self.selected_role = role_key
        self.selected_enemy = ""
        for button in self.role_btns:
            button.set_active(button.cfg["key"] == role_key)
        for button in self._enemy_btns.values():
            button.set_active(False)
        self.step2_widget.show()
        self.results_widget.hide()
        self.results_loading.hide()
        self.enemy_search.clear()
        self.enemy_search.setFocus()

    def _on_enemy_selected(self, name: str) -> None:
        self.selected_enemy = name
        for enemy_name, button in self._enemy_btns.items():
            button.set_active(enemy_name == name)
        if not self.selected_role:
            return

        self.matchup_header.setText(f"VS  {name.upper()}  ·  {self._role_label()}")
        self._clear_results()
        self.results_loading.show()
        self.results_widget.show()

        threading.Thread(
            target=self._fetch_matchup,
            args=(name, self.selected_role),
            daemon=True,
        ).start()

    def _role_label(self) -> str:
        for role in ROLE_CONFIG:
            if role["key"] == self.selected_role:
                return role["label"]
        return ""

    def _fetch_matchup(self, enemy: str, lane: str) -> None:
        enemy_data = fetch_matchup_data(enemy, lane)
        rows = []
        for index, counter in enumerate(enemy_data.get("counters", [])[:3]):
            champ_name = self._champion_name_map.get(
                counter.get("norm_id") or _normalize_name(counter.get("id", "")),
                counter.get("id", ""),
            )
            build_data = fetch_matchup_data(champ_name, lane)
            rows.append(
                {
                    "rank": index + 1,
                    "champ_name": champ_name,
                    "winrate": float(counter.get("winrate", 50.0)),
                    "games": int(counter.get("games", 0)),
                    "build": build_data.get("best_build", []),
                    "start_items": build_data.get("start_items", []),
                }
            )
        self.matchup_ready.emit(rows, enemy, lane)

    def _on_matchup_ready(self, rows: list, enemy: str, lane: str) -> None:
        if enemy != self.selected_enemy or lane != self.selected_role:
            return

        self.results_loading.hide()
        self._clear_results()

        if not rows:
            empty = QLabel("SIN DATOS DE COUNTERS")
            empty.setStyleSheet("color: #1A3A55; font-size: 10px;")
            self.counter_rows_layout.addWidget(empty)
            return

        for row in rows:
            widget = CounterBuildRow(
                rank=row["rank"],
                champ_name=row["champ_name"],
                winrate=row["winrate"],
                games=row["games"],
                pixmap=self.champion_images.get(row["champ_name"]),
                build=row["build"],
                start_items=row["start_items"],
            )
            self.counter_rows_layout.addWidget(widget)

    def _clear_results(self) -> None:
        while self.counter_rows_layout.count():
            item = self.counter_rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class EnemyChampButton(QWidget):
    clicked_name = pyqtSignal(str)

    def __init__(self, champ_name: str, pixmap: Optional[QPixmap], parent=None):
        super().__init__(parent)
        self.champ_name = champ_name
        self.active = False
        self.cover = build_rounded_cover_pixmap(pixmap, 34, 6) if pixmap else None
        self.setFixedSize(48, 56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(champ_name)

    def set_active(self, active: bool) -> None:
        self.active = active
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)

        painter.fillRect(rect, QColor("#0C1420"))
        painter.setPen(QPen(QColor("#FF3B3B") if self.active else QColor("#0A1E2A"), 2 if self.active else 1))
        painter.drawRect(rect)

        if self.cover:
            x = (self.width() - 34) // 2
            painter.drawPixmap(x, 4, self.cover)

        painter.setPen(QColor("#FF3B3B") if self.active else QColor("#1A3A55"))
        painter.setFont(QFont("Barlow Condensed", 7, QFont.Weight.Bold))
        painter.drawText(QRect(2, 40, self.width() - 4, 12), int(Qt.AlignmentFlag.AlignCenter), self.champ_name[:7].upper())
        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked_name.emit(self.champ_name)
        super().mousePressEvent(event)


class LargeRoleButton(QWidget):
    clicked_role = pyqtSignal(str)
    icon_ready = pyqtSignal()

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.active = False
        self._icon_pixmap: Optional[QPixmap] = None
        self.setFixedSize(80, 90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon_ready.connect(self.update)
        threading.Thread(target=self._download_icon, daemon=True).start()

    def _download_icon(self) -> None:
        try:
            import requests as req
            from PyQt6.QtSvg import QSvgRenderer

            response = req.get(self.cfg["icon_url"], timeout=8)
            if response.status_code != 200:
                return
            renderer = QSvgRenderer(response.content)
            pixmap = QPixmap(48, 48)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            self._icon_pixmap = pixmap
            self.icon_ready.emit()
        except Exception:
            return

    def set_active(self, active: bool) -> None:
        self.active = active
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self.cfg["color"])
        rect = self.rect()

        if self.active:
            painter.fillRect(rect, QColor(color.red(), color.green(), color.blue(), 25))

        border_alpha = 200 if self.active else 40
        pen_color = QColor(color.red(), color.green(), color.blue(), border_alpha)
        painter.setPen(QPen(pen_color, 2 if self.active else 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect.adjusted(0, 0, -1, -1))

        if self.active:
            painter.setPen(QPen(color, 2))
            painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())

        icon_rect = QRect((rect.width() - 48) // 2, 12, 48, 48)
        if self._icon_pixmap:
            painter.setOpacity(1.0 if self.active else 0.4)
            painter.drawPixmap(icon_rect, self._icon_pixmap)
            painter.setOpacity(1.0)
        else:
            painter.setPen(pen_color)
            painter.setFont(QFont("Barlow Condensed", 18, QFont.Weight.Bold))
            painter.drawText(icon_rect, int(Qt.AlignmentFlag.AlignCenter), self.cfg["label"][:1])

        label_rect = QRect(0, rect.height() - 20, rect.width(), 18)
        painter.setPen(color if self.active else QColor("#1A3A55"))
        painter.setFont(QFont("Barlow Condensed", 9, QFont.Weight.Bold))
        painter.setOpacity(1.0 if self.active else 0.6)
        painter.drawText(label_rect, int(Qt.AlignmentFlag.AlignCenter), self.cfg["label"])
        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked_role.emit(self.cfg["key"])
        super().mousePressEvent(event)


class CounterBuildRow(QWidget):
    def __init__(
        self,
        rank: int,
        champ_name: str,
        winrate: float,
        games: int,
        pixmap: Optional[QPixmap],
        build: list[int],
        start_items: list[int],
        parent=None,
    ):
        super().__init__(parent)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #0C1420;
                border: 1px solid #0A1E2A;
                border-radius: 3px;
            }
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 12, 8)
        layout.setSpacing(10)

        rank_lbl = QLabel(f"0{rank}")
        rank_lbl.setFixedSize(20, 20)
        rank_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rank_lbl.setStyleSheet(
            """
            background-color: #00D4FF;
            color: #03050A;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            font-size: 9px;
            font-weight: 700;
            border-radius: 2px;
            """
        )
        layout.addWidget(rank_lbl)

        portrait = QLabel()
        portrait.setFixedSize(42, 42)
        if pixmap:
            portrait.setPixmap(
                pixmap.scaled(
                    42,
                    42,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            portrait.setStyleSheet("border: 1px solid #0A1E2A; border-radius: 2px;")
        else:
            portrait.setStyleSheet("background: #080D14; border: 1px solid #0A1E2A; border-radius: 2px;")
        layout.addWidget(portrait)

        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(champ_name.upper())
        name_lbl.setStyleSheet(
            """
            color: #E8EEF4;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.5px;
            """
        )
        info.addWidget(name_lbl)
        detail = f"{winrate:.1f}% WR  ·  {games:,} PARTIDAS" if games > 0 else "COUNTER LIVE  ·  LOLALYTICS"
        detail_lbl = QLabel(detail)
        detail_lbl.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            font-size: 9px;
            """
        )
        info.addWidget(detail_lbl)
        info_wrap = QWidget()
        info_wrap.setLayout(info)
        info_wrap.setFixedWidth(180)
        layout.addWidget(info_wrap)

        build_wrap = QWidget()
        build_wrap.setFixedWidth(320)
        build_layout = QHBoxLayout(build_wrap)
        build_layout.setContentsMargins(0, 0, 0, 0)
        build_layout.setSpacing(6)
        for item_id in build[:6]:
            build_layout.addWidget(ItemIconWidget(item_id))
        if not build:
            empty = QLabel("SIN BUILD")
            empty.setStyleSheet("color: #1A3A55; font-size: 10px;")
            build_layout.addWidget(empty)
        layout.addWidget(build_wrap)

        start_wrap = QWidget()
        start_wrap.setFixedWidth(130)
        start_layout = QHBoxLayout(start_wrap)
        start_layout.setContentsMargins(0, 0, 0, 0)
        start_layout.setSpacing(6)
        for item_id in start_items[:2]:
            start_layout.addWidget(ItemIconWidget(item_id, small=True))
        if not start_items:
            empty = QLabel("SIN INICIO")
            empty.setStyleSheet("color: #1A3A55; font-size: 10px;")
            start_layout.addWidget(empty)
        layout.addWidget(start_wrap)
        layout.addStretch()


class ItemIconWidget(QWidget):
    _pixmap_cache: dict[int, QPixmap] = {}
    pixmap_ready = pyqtSignal()

    def __init__(self, item_id: int, small: bool = False, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self._size = 32 if small else 40
        self._pixmap: Optional[QPixmap] = None
        self.setFixedSize(self._size, self._size)
        self.pixmap_ready.connect(self.update)

        if item_id in self._pixmap_cache:
            self._pixmap = self._pixmap_cache[item_id]
        else:
            threading.Thread(target=self._download, daemon=True).start()

    def _download(self) -> None:
        data = fetch_item_pixmap(self.item_id)
        if not data:
            return
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        if pixmap.isNull():
            return
        ItemIconWidget._pixmap_cache[self.item_id] = pixmap
        self._pixmap = pixmap
        self.pixmap_ready.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        icon_rect = QRect(0, 0, self._size, self._size)

        if self._pixmap and not self._pixmap.isNull():
            path = QPainterPath()
            path.addRoundedRect(QRectF(icon_rect), 3, 3)
            painter.setClipPath(path)
            scaled = self._pixmap.scaled(
                self._size,
                self._size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(icon_rect, scaled)
            painter.setClipping(False)
            painter.setPen(QPen(QColor("#C9A84C44"), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(icon_rect.adjusted(0, 0, -1, -1)), 3, 3)
        else:
            painter.fillRect(icon_rect, QColor("#0C1420"))
            painter.setPen(QPen(QColor("#0A1E2A"), 1))
            painter.drawRect(icon_rect.adjusted(0, 0, -1, -1))
            painter.setPen(QColor("#2A4A6A"))
            painter.setFont(QFont("JetBrains Mono", 7))
            painter.drawText(icon_rect, int(Qt.AlignmentFlag.AlignCenter), str(self.item_id)[-4:])
        painter.end()
