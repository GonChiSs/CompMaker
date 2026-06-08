from __future__ import annotations

import threading
from typing import Optional

from PyQt6.QtCore import QMimeData, QRect, Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QDrag, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from logic.lol_data_fetcher import fetch_tier_list
from ui.flow_layout import FlowLayout
from ui.image_utils import build_rounded_cover_pixmap

TIER_CONFIG = [
    {"key": "S", "label": "S", "color": "#FF4444", "bg": "#1A0808"},
    {"key": "A", "label": "A", "color": "#FF8C00", "bg": "#1A0E00"},
    {"key": "B", "label": "B", "color": "#FFD700", "bg": "#1A1600"},
    {"key": "C", "label": "C", "color": "#00CC66", "bg": "#001A0E"},
    {"key": "D", "label": "D", "color": "#00AAFF", "bg": "#00101A"},
    {"key": "F", "label": "F", "color": "#6644CC", "bg": "#0A0814"},
]

ROLE_CONFIG = [
    {
        "key": "top",
        "label": "TOP",
        "icon_url": (
            "https://raw.communitydragon.org/latest/plugins/"
            "rcp-fe-lol-champ-select/global/default/svg/position-top.svg"
        ),
        "color": "#C9A84C",
    },
    {
        "key": "jungle",
        "label": "JG",
        "icon_url": (
            "https://raw.communitydragon.org/latest/plugins/"
            "rcp-fe-lol-champ-select/global/default/svg/position-jungle.svg"
        ),
        "color": "#00FF88",
    },
    {
        "key": "middle",
        "label": "MID",
        "icon_url": (
            "https://raw.communitydragon.org/latest/plugins/"
            "rcp-fe-lol-champ-select/global/default/svg/position-middle.svg"
        ),
        "color": "#00D4FF",
    },
    {
        "key": "bottom",
        "label": "ADC",
        "icon_url": (
            "https://raw.communitydragon.org/latest/plugins/"
            "rcp-fe-lol-champ-select/global/default/svg/position-bottom.svg"
        ),
        "color": "#FF8C00",
    },
    {
        "key": "support",
        "label": "SUP",
        "icon_url": (
            "https://raw.communitydragon.org/latest/plugins/"
            "rcp-fe-lol-champ-select/global/default/svg/position-utility.svg"
        ),
        "color": "#BF5FFF",
    },
]


def _normalize_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


class RoleIconButton(QWidget):
    clicked_role = pyqtSignal(str)
    icon_ready = pyqtSignal()

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.active = False
        self.loading = False
        self._icon_pixmap: Optional[QPixmap] = None
        self.setFixedSize(40, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(cfg["label"])
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
            pixmap = QPixmap(28, 28)
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

    def set_loading(self, loading: bool) -> None:
        self.loading = loading
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self.cfg["color"])

        background = QColor(color.red(), color.green(), color.blue(), 30) if self.active else QColor("#0C1420")
        painter.fillRect(self.rect(), background)

        border_color = color if self.active else QColor("#0A1E2A")
        painter.setPen(QPen(border_color, 1.5 if self.active else 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))

        if self._icon_pixmap and not self.loading:
            painter.setOpacity(1.0 if self.active else 0.45)
            x = (self.width() - 26) // 2
            y = (self.height() - 26) // 2
            painter.drawPixmap(x, y, 26, 26, self._icon_pixmap)
            painter.setOpacity(1.0)
        else:
            painter.setPen(color if self.active else QColor("#2A4A6A"))
            painter.setFont(QFont("Barlow Condensed", 8, QFont.Weight.Bold))
            painter.drawText(self.rect(), int(Qt.AlignmentFlag.AlignCenter), "..." if self.loading else self.cfg["label"])
        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked_role.emit(self.cfg["key"])
        super().mousePressEvent(event)


class TierlistMode(QWidget):
    role_fetch_ready = pyqtSignal(int, str, object)

    def __init__(self, all_champions: dict, champion_images: dict, parent=None):
        super().__init__(parent)
        self.all_champions = all_champions
        self.champion_images = champion_images
        self.tier_data: dict[str, list[str]] = {config["key"]: [] for config in TIER_CONFIG}
        self.pool: list[str] = list(all_champions.keys())
        self.drag_champ: str | None = None
        self.drag_source = None
        self.export_button: QPushButton | None = None
        self.role_buttons: list[RoleIconButton] = []
        self._loading_label: QLabel | None = None
        self._active_role: Optional[str] = None
        self._fetch_thread: Optional[threading.Thread] = None
        self._fetch_nonce = 0
        self._auto_populated_names: set[str] = set()
        self._champion_name_map = {_normalize_name(name): name for name in all_champions}
        self.role_fetch_ready.connect(self._apply_role_fetch)
        self._build_ui()
        self._populate_pool()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()

        title = QLabel("// TIER LIST")
        title.setStyleSheet(
            """
            color: #C9A84C;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 3px;
            """
        )
        header.addWidget(title)
        header.addStretch()

        self.export_button = self._build_action_button("EXPORTAR", "#00D4FF")
        self.export_button.clicked.connect(self.export_tierlist)
        header.addWidget(self.export_button)

        layout.addLayout(header)

        role_bar = QHBoxLayout()
        role_bar.setSpacing(4)

        auto_label = QLabel("AUTO-RANK")
        auto_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 2px;
            """
        )
        role_bar.addWidget(auto_label)

        for cfg in ROLE_CONFIG:
            button = RoleIconButton(cfg)
            button.clicked_role.connect(self._on_role_clicked)
            self.role_buttons.append(button)
            role_bar.addWidget(button)

        self._loading_label = QLabel("")
        self._loading_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            font-size: 9px;
            letter-spacing: 1px;
            """
        )
        role_bar.addWidget(self._loading_label)
        role_bar.addStretch()

        reset_button = self._build_action_button("// RESET", "#FF3B3B")
        reset_button.clicked.connect(self.reset_tierlist)
        role_bar.addWidget(reset_button)
        layout.addLayout(role_bar)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(
            """
            background: qlineargradient(x1:0, x2:1,
                stop:0 #C9A84C44, stop:0.4 #C9A84C22, stop:1 transparent);
            """
        )
        layout.addWidget(div)

        tiers_scroll = QScrollArea()
        tiers_scroll.setWidgetResizable(True)
        tiers_scroll.setFixedHeight(420)
        tiers_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tiers_scroll.setStyleSheet(
            """
            QScrollArea { border: none; background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            """
        )

        tiers_container = QWidget()
        tiers_layout = QVBoxLayout(tiers_container)
        tiers_layout.setSpacing(2)
        tiers_layout.setContentsMargins(0, 0, 0, 0)

        self.tier_rows: dict[str, TierRow] = {}
        for config in TIER_CONFIG:
            row = TierRow(config, self)
            row.champ_dropped.connect(self.on_champ_dropped_to_tier)
            row.champ_removed.connect(self.on_champ_removed_from_tier)
            self.tier_rows[config["key"]] = row
            tiers_layout.addWidget(row)

        tiers_layout.addStretch()
        tiers_scroll.setWidget(tiers_container)
        layout.addWidget(tiers_scroll)

        pool_controls = QHBoxLayout()
        pool_controls.setSpacing(8)

        search_label = QLabel("//")
        search_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 2px;
            """
        )
        pool_controls.addWidget(search_label)

        self.pool_search = QLineEdit()
        self.pool_search.setPlaceholderText("BUSCAR CAMPEON...")
        self.pool_search.setFixedHeight(28)
        self.pool_search.setFixedWidth(200)
        self.pool_search.setStyleSheet(
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
                border-color: #00D4FF;
            }
            """
        )
        self.pool_search.textChanged.connect(self.filter_pool)
        pool_controls.addWidget(self.pool_search)

        pool_count_label = QLabel("POOL")
        pool_count_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 2px;
            """
        )
        pool_controls.addWidget(pool_count_label)

        self.pool_count = QLabel("0")
        self.pool_count.setStyleSheet(
            """
            color: #1A3A55;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            font-size: 10px;
            """
        )
        pool_controls.addWidget(self.pool_count)
        pool_controls.addStretch()
        layout.addLayout(pool_controls)

        pool_scroll = QScrollArea()
        pool_scroll.setWidgetResizable(True)
        pool_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        pool_scroll.setStyleSheet(
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

        self.pool_container = QWidget()
        self.pool_container.setStyleSheet("background: #080D14;")
        self.pool_flow = FlowLayout(self.pool_container, spacing=3)
        self.pool_flow.setContentsMargins(6, 6, 6, 6)
        pool_scroll.setWidget(self.pool_container)
        layout.addWidget(pool_scroll, 1)

    def _populate_pool(self) -> None:
        for name in sorted(self.pool):
            card = TierChampCard(name=name, pixmap=self.champion_images.get(name), parent=self)
            card.drag_started.connect(self.on_drag_started)
            self.pool_flow.addWidget(card)
        self._update_pool_count()

    def filter_pool(self, query: str) -> None:
        upper_query = query.upper()
        for index in range(self.pool_flow.count()):
            item = self.pool_flow.itemAt(index)
            if item and item.widget():
                widget = item.widget()
                widget.setVisible(upper_query in widget.champ_name.upper() if upper_query else True)
        self.pool_container.updateGeometry()

    def on_drag_started(self, champ_name: str, source_widget) -> None:
        self.drag_champ = champ_name
        self.drag_source = source_widget

    def on_champ_dropped_to_tier(self, tier_key: str, champ_name: str) -> None:
        if champ_name in self.pool:
            self.pool.remove(champ_name)
            self._remove_from_pool_ui(champ_name)
        else:
            for key, champions in self.tier_data.items():
                if champ_name in champions and key != tier_key:
                    champions.remove(champ_name)
                    self.tier_rows[key].remove_champion(champ_name)

        if champ_name not in self.tier_data[tier_key]:
            self.tier_data[tier_key].append(champ_name)
            self.tier_rows[tier_key].add_champion(champ_name, self.champion_images.get(champ_name))
        self._update_pool_count()

    def on_champ_removed_from_tier(self, champ_name: str) -> None:
        for key, champions in self.tier_data.items():
            if champ_name in champions:
                champions.remove(champ_name)
                self.tier_rows[key].remove_champion(champ_name)
                break
        if champ_name not in self.pool:
            self.pool.append(champ_name)
            card = TierChampCard(name=champ_name, pixmap=self.champion_images.get(champ_name), parent=self)
            card.drag_started.connect(self.on_drag_started)
            self.pool_flow.addWidget(card)
        self.filter_pool(self.pool_search.text())
        self._update_pool_count()

    def reset_tierlist(self) -> None:
        confirm = ConfirmDialog("RESETEAR LA TIER LIST?", parent=self)
        if confirm.exec() != QDialog.DialogCode.Accepted:
            return

        self._active_role = None
        self._auto_populated_names.clear()
        self._fetch_nonce += 1
        self._set_role_loading(None, "")

        for key in self.tier_data:
            self.tier_data[key] = []
            self.tier_rows[key].clear_champions()

        self.pool = list(self.all_champions.keys())
        while self.pool_flow.count():
            item = self.pool_flow.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._populate_pool()
        self.filter_pool("")
        self.pool_search.clear()

    def export_tierlist(self) -> None:
        clean_lines = ["// TIER LIST - COMPMAKER", ""]
        for config in TIER_CONFIG:
            key = config["key"]
            label = self.tier_rows[key].current_label
            champions = self.tier_data[key]
            if champions:
                clean_lines.append(f"[ {label} ]  " + " | ".join(champions))
        QApplication.clipboard().setText("\n".join(clean_lines))
        if self.export_button is not None:
            self.export_button.setText("COPIADO")
            QTimer.singleShot(1600, lambda: self.export_button.setText("EXPORTAR"))

    def _on_role_clicked(self, role_key: str) -> None:
        toggling_off = self._active_role == role_key
        for button in self.role_buttons:
            button.set_active(button.cfg["key"] == role_key and not toggling_off)

        if toggling_off:
            self._active_role = None
            self._clear_auto_populated()
            self._set_role_loading(None, "")
            return

        self._active_role = role_key
        self._fetch_nonce += 1
        current_nonce = self._fetch_nonce
        self._set_role_loading(role_key, "CARGANDO...")
        self._fetch_thread = threading.Thread(
            target=self._fetch_role_tier_data,
            args=(role_key, current_nonce),
            daemon=True,
        )
        self._fetch_thread.start()

    def _fetch_role_tier_data(self, role_key: str, nonce: int) -> None:
        data = fetch_tier_list(role_key, self._role_candidates(role_key))
        self.role_fetch_ready.emit(nonce, role_key, data)

    def _role_candidates(self, role_key: str) -> list[str]:
        role_map = {
            "top": {"TOP"},
            "jungle": {"JUNGLE", "JGL", "JG"},
            "middle": {"MID", "MIDDLE"},
            "bottom": {"ADC", "BOT", "BOTTOM"},
            "support": {"SUPPORT", "SUP"},
        }
        accepted_roles = role_map.get(role_key, set())
        candidates = []
        for name, payload in self.all_champions.items():
            roles = {str(role).upper() for role in payload.get("roles", [])} if isinstance(payload, dict) else set()
            if not accepted_roles or roles.intersection(accepted_roles):
                candidates.append(name)
        return candidates or list(self.all_champions.keys())

    @pyqtSlot(int, str, object)
    def _apply_role_fetch(self, nonce: int, role_key: str, data: object) -> None:
        if nonce != self._fetch_nonce or self._active_role != role_key:
            return

        items = data if isinstance(data, list) else []
        if not items:
            self._clear_auto_populated()
            self._set_role_loading(role_key, "SIN DATOS")
            return

        self._clear_auto_populated()
        applied_count = 0
        for entry in items:
            tier_key = str(entry.get("tier") or "C").upper()
            champion_name = self._champion_name_map.get(entry.get("norm_id") or _normalize_name(entry.get("id", "")))
            if not champion_name or tier_key not in self.tier_rows:
                continue
            self._place_champion_in_tier(champion_name, tier_key)
            self._auto_populated_names.add(champion_name)
            applied_count += 1

        self.filter_pool(self.pool_search.text())
        self._update_pool_count()
        self._set_role_loading(role_key, f"{applied_count} PICKS" if applied_count else "SIN DATOS")

    def _place_champion_in_tier(self, champ_name: str, tier_key: str) -> None:
        if champ_name in self.pool:
            self.pool.remove(champ_name)
            self._remove_from_pool_ui(champ_name)
        for key, champions in self.tier_data.items():
            if champ_name in champions:
                champions.remove(champ_name)
                self.tier_rows[key].remove_champion(champ_name)
        if champ_name not in self.tier_data[tier_key]:
            self.tier_data[tier_key].append(champ_name)
            self.tier_rows[tier_key].add_champion(champ_name, self.champion_images.get(champ_name))

    def _clear_auto_populated(self) -> None:
        names_to_restore = list(self._auto_populated_names)
        self._auto_populated_names.clear()
        for champ_name in names_to_restore:
            for key, champions in self.tier_data.items():
                if champ_name in champions:
                    champions.remove(champ_name)
                    self.tier_rows[key].remove_champion(champ_name)
            if champ_name not in self.pool and champ_name in self.all_champions:
                self.pool.append(champ_name)
                card = TierChampCard(name=champ_name, pixmap=self.champion_images.get(champ_name), parent=self)
                card.drag_started.connect(self.on_drag_started)
                self.pool_flow.addWidget(card)
        self.filter_pool(self.pool_search.text())
        self._update_pool_count()

    def _set_role_loading(self, active_role: str | None, text: str) -> None:
        if self._loading_label is not None:
            self._loading_label.setText(text)
        for button in self.role_buttons:
            button.set_loading(button.cfg["key"] == active_role and bool(text) and text != "SIN DATOS" and text != "0 PICKS")
            button.set_active(button.cfg["key"] == active_role)

    def _remove_from_pool_ui(self, champ_name: str) -> None:
        for index in range(self.pool_flow.count()):
            item = self.pool_flow.itemAt(index)
            if item and item.widget() and item.widget().champ_name == champ_name:
                widget = item.widget()
                self.pool_flow.takeAt(index)
                widget.deleteLater()
                break

    def _update_pool_count(self) -> None:
        self.pool_count.setText(str(len(self.pool)))

    @staticmethod
    def _build_action_button(text: str, color: str) -> QPushButton:
        button = QPushButton(text)
        button.setFixedHeight(26)
        button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {color}44;
                border-radius: 2px;
                color: {color}88;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                border-color: {color};
                color: {color};
                background-color: {color}0D;
            }}
            """
        )
        return button


class TierRow(QWidget):
    champ_dropped = pyqtSignal(str, str)
    champ_removed = pyqtSignal(str)

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.current_label = cfg["label"]
        self.setAcceptDrops(True)
        self.setFixedHeight(58)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("tierRow")
        self._apply_border_style(active=False)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 8, 0)
        row.setSpacing(8)

        self.label_block = EditableTierLabel(self.cfg, self.current_label, self)
        self.label_block.label_changed.connect(self._update_label)
        row.addWidget(self.label_block)

        self.chips_widget = QWidget()
        self.chips_widget.setStyleSheet("background: transparent;")
        self.chips_layout = FlowLayout(self.chips_widget, spacing=3)
        self.chips_layout.setContentsMargins(4, 4, 4, 4)
        row.addWidget(self.chips_widget, 1)

    def add_champion(self, name: str, pixmap=None) -> None:
        chip = TierChampChip(name, pixmap, self.cfg["color"], parent=self.chips_widget)
        chip.remove_clicked.connect(lambda champ=name: self.champ_removed.emit(champ))
        self.chips_layout.addWidget(chip)
        self._schedule_chip_layout_refresh()

    def remove_champion(self, name: str) -> None:
        for index in range(self.chips_layout.count()):
            item = self.chips_layout.itemAt(index)
            if item and item.widget() and getattr(item.widget(), "champ_name", "") == name:
                widget = item.widget()
                self.chips_layout.takeAt(index)
                widget.deleteLater()
                break
        self._schedule_chip_layout_refresh()

    def clear_champions(self) -> None:
        while self.chips_layout.count():
            item = self.chips_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._schedule_chip_layout_refresh()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasText():
            self._apply_border_style(active=True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self._apply_border_style(active=False)
        if event is not None:
            event.accept()

    def dropEvent(self, event) -> None:
        champ_name = event.mimeData().text()
        self._apply_border_style(active=False)
        self.champ_dropped.emit(self.cfg["key"], champ_name)
        event.acceptProposedAction()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._schedule_chip_layout_refresh()

    def _schedule_chip_layout_refresh(self) -> None:
        QTimer.singleShot(0, self._refresh_chip_layout)

    def _refresh_chip_layout(self) -> None:
        chip_count = self.chips_layout.count()
        if chip_count <= 0:
            self.chips_widget.setMinimumHeight(50)
            self.setFixedHeight(58)
            return

        self.layout().activate()
        available_width = max(self.chips_widget.contentsRect().width(), 52)
        flow_height = self.chips_layout.heightForWidth(available_width)
        content_height = max(50, flow_height)
        self.chips_widget.setMinimumHeight(content_height)
        self.chips_layout.invalidate()
        self.layout().activate()
        self.chips_layout.setGeometry(self.chips_widget.contentsRect())
        self.chips_widget.updateGeometry()
        self.layout().activate()
        self.setFixedHeight(max(58, content_height + 10))
        self.chips_widget.update()

    def _apply_border_style(self, active: bool) -> None:
        border_color = f"{self.cfg['color']}AA" if active else "#0A1E2A"
        accent_color = f"{self.cfg['color']}33" if active else f"{self.cfg['color']}18"
        self.setStyleSheet(
            f"""
            QWidget#tierRow {{
                background-color: #0C1420;
                border: 1px solid {border_color};
                border-radius: 3px;
                border-left: 3px solid {accent_color};
            }}
            """
        )

    def _update_label(self, label: str) -> None:
        self.current_label = label


class EditableTierLabel(QWidget):
    label_changed = pyqtSignal(str)

    def __init__(self, cfg: dict, initial_label: str, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.current_label = initial_label
        self.setFixedWidth(64)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.label = QLabel(initial_label)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(
            f"""
            color: {self.cfg['color']};
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 24px;
            font-weight: 800;
            letter-spacing: 1.5px;
            """
        )
        layout.addWidget(self.label)

        self.editor = QLineEdit(initial_label)
        self.editor.hide()
        self.editor.setMaxLength(3)
        self.editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.editor.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: #080D14;
                border: none;
                color: {self.cfg['color']};
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 16px;
                font-weight: 800;
                letter-spacing: 1px;
            }}
            """
        )
        self.editor.editingFinished.connect(self.finish_edit)
        layout.addWidget(self.editor)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.label.hide()
            self.editor.show()
            self.editor.setText(self.current_label)
            self.editor.selectAll()
            self.editor.setFocus()
        super().mouseDoubleClickEvent(event)

    def finish_edit(self) -> None:
        text = self.editor.text().strip().upper() or self.current_label
        self.current_label = text[:3]
        self.label.setText(self.current_label)
        self.editor.hide()
        self.label.show()
        self.label_changed.emit(self.current_label)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -2, -2)

        painter.fillRect(rect, QColor("#080D14"))
        painter.setPen(QPen(QColor(self.cfg["color"]), 1))
        painter.drawRect(rect)

        badge_rect = QRect(rect.x() + 6, rect.y() + 6, 18, 12)
        painter.fillRect(badge_rect, QColor(self.cfg["color"]))
        painter.setPen(QColor("#03050A"))
        badge_font = QFont("JetBrains Mono", 7, QFont.Weight.Bold)
        painter.setFont(badge_font)
        painter.drawText(badge_rect, int(Qt.AlignmentFlag.AlignCenter), self.cfg["key"])

        painter.setPen(QPen(QColor("#0A2535"), 1))
        bracket = 8
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        painter.drawLine(x, y, x + bracket, y)
        painter.drawLine(x, y, x, y + bracket)
        painter.drawLine(x + w - bracket, y, x + w, y)
        painter.drawLine(x + w, y, x + w, y + bracket)
        painter.drawLine(x, y + h - bracket, x, y + h)
        painter.drawLine(x, y + h, x + bracket, y + h)
        painter.drawLine(x + w - bracket, y + h, x + w, y + h)
        painter.drawLine(x + w, y + h - bracket, x + w, y + h)

        painter.setPen(QPen(QColor(255, 255, 255, 4), 1))
        for line_y in range(rect.y() + 4, rect.y() + rect.height(), 4):
            painter.drawLine(rect.x() + 2, line_y, rect.x() + rect.width() - 2, line_y)
        painter.end()


class TierChampCard(QWidget):
    drag_started = pyqtSignal(str, object)

    def __init__(self, name: str, pixmap=None, parent=None):
        super().__init__(parent)
        self.champ_name = name
        self.cover = build_rounded_cover_pixmap(pixmap, 36, 8) if pixmap else None
        self.setFixedSize(44, 52)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip(name)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.fillRect(rect, QColor("#0C1420"))
        painter.setPen(QPen(QColor("#0A1E2A"), 1))
        painter.drawRect(rect)

        if self.cover:
            x = (self.width() - 36) // 2
            painter.drawPixmap(x, 4, self.cover)

        painter.setPen(QColor("#2A4A6A"))
        painter.setFont(QFont("Barlow Condensed", 6, QFont.Weight.Bold))
        painter.drawText(QRect(0, 38, self.width(), 12), int(Qt.AlignmentFlag.AlignCenter), self.champ_name[:6].upper())

        painter.setPen(QPen(QColor("#0A2535"), 1))
        painter.drawLine(1, 1, 9, 1)
        painter.drawLine(1, 1, 1, 9)
        painter.drawLine(self.width() - 10, 1, self.width() - 2, 1)
        painter.drawLine(self.width() - 2, 1, self.width() - 2, 9)
        painter.end()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.champ_name)
            drag.setMimeData(mime)
            if self.cover:
                drag.setPixmap(self.cover)
            self.drag_started.emit(self.champ_name, self)
            drag.exec(Qt.DropAction.MoveAction)
        super().mouseMoveEvent(event)


class TierChampChip(QWidget):
    remove_clicked = pyqtSignal(str)

    def __init__(self, name: str, pixmap=None, tier_color: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self.champ_name = name
        self.tier_color = tier_color
        self.cover = build_rounded_cover_pixmap(pixmap, 36, 8) if pixmap else None
        self.setFixedSize(54, 58)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{name}\nCLIC DERECHO -> QUITAR")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.fillRect(rect, QColor("#080D14"))
        painter.setPen(QPen(QColor("#0A1E2A"), 1))
        painter.drawRect(rect)

        if self.cover:
            x = (self.width() - 36) // 2
            painter.drawPixmap(x, 6, self.cover)

        painter.setPen(QPen(QColor(f"{self.tier_color}66"), 1))
        inner = rect.adjusted(3, 3, -3, -14)
        painter.drawRect(inner)

        painter.fillRect(QRect(8, 42, self.width() - 16, 1), QColor(self.tier_color))
        painter.setPen(QColor("#E8EEF4"))
        painter.setFont(QFont("Barlow Condensed", 7, QFont.Weight.Bold))
        painter.drawText(QRect(0, 44, self.width(), 11), int(Qt.AlignmentFlag.AlignCenter), self.champ_name[:7].upper())

        painter.setPen(QPen(QColor("#0A2535"), 1))
        bracket = 7
        x0, y0, w0, h0 = rect.x(), rect.y(), rect.width(), rect.height()
        painter.drawLine(x0, y0, x0 + bracket, y0)
        painter.drawLine(x0, y0, x0, y0 + bracket)
        painter.drawLine(x0 + w0 - bracket, y0, x0 + w0, y0)
        painter.drawLine(x0 + w0, y0, x0 + w0, y0 + bracket)
        painter.end()

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        remove_action = menu.addAction("QUITAR DEL TIER")
        action = menu.exec(self.mapToGlobal(event.pos()))
        if action == remove_action:
            self.remove_clicked.emit(self.champ_name)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.champ_name)
            drag.setMimeData(mime)
            if self.cover:
                drag.setPixmap(self.cover)
            drag.exec(Qt.DropAction.MoveAction)
        super().mouseMoveEvent(event)


class ConfirmDialog(QDialog):
    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(320, 120)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #080D14;
                border: 1px solid #0A2535;
                border-radius: 3px;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setStyleSheet(
            """
            color: #E8EEF4;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1.5px;
            """
        )
        layout.addWidget(message_label)

        button_row = QHBoxLayout()
        for text, color, handler in [
            ("CANCELAR", "#2A4A6A", self.reject),
            ("CONFIRMAR", "#FF3B3B", self.accept),
        ]:
            button = QPushButton(text)
            button.setFixedHeight(26)
            button.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent;
                    border: 1px solid {color}55;
                    border-radius: 2px;
                    color: {color};
                    font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                    font-size: 9px;
                    font-weight: 700;
                    letter-spacing: 2px;
                    padding: 0 14px;
                }}
                QPushButton:hover {{
                    border-color: {color};
                    background: {color}0D;
                }}
                """
            )
            button.clicked.connect(handler)
            button_row.addWidget(button)
        layout.addLayout(button_row)
