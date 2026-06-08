from __future__ import annotations

import math
from pathlib import Path

from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, QTime, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygon
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from logic.board_persistence import load_all_boards, save_all_boards


class PizarraMode(QWidget):
    def __init__(self, all_champions: dict, champion_images: dict, parent=None):
        super().__init__(parent)
        self.all_champions = all_champions
        self.champion_images = champion_images
        self.current_board_idx = 1
        self.board_states: dict[int, dict] = {}
        self.blue_team: list[str] = []
        self.red_team: list[str] = []
        self._build_ui()
        self._load_all_boards()
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.save_before_close)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        header = self._build_header()
        main_layout.addLayout(header)

        self.map_area = MapCanvas(self.all_champions, self.champion_images, parent=self)
        self.map_area.setMinimumHeight(500)
        main_layout.addWidget(self.map_area, 1)

    def _build_header(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(10)

        title = QLabel("// PIZARRA TACTICA")
        title.setStyleSheet(
            """
            color: #C9A84C;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 3px;
            """
        )
        layout.addWidget(title)

        div = QLabel("—")
        div.setStyleSheet("color: #0A2535; font-size: 12px;")
        layout.addWidget(div)

        self.blue_btn = QPushButton("⬡  EQUIPO AZUL  —  SIN PICKS")
        self.blue_btn.setFixedHeight(26)
        self.blue_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #1E90FF44;
                border-radius: 2px;
                color: #1A4A7A;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.5px;
                padding: 0 12px;
            }
            QPushButton:hover {
                border-color: #1E90FF;
                color: #1E90FF;
                background-color: #06101E;
            }
            """
        )
        self.blue_btn.clicked.connect(lambda: self._open_team_picker("BLUE"))
        layout.addWidget(self.blue_btn)

        vs_label = QLabel("VS")
        vs_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 3px;
            """
        )
        layout.addWidget(vs_label)

        self.red_btn = QPushButton("⬡  EQUIPO ROJO  —  SIN PICKS")
        self.red_btn.setFixedHeight(26)
        self.red_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #FF3B3B44;
                border-radius: 2px;
                color: #7A1A1A;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.5px;
                padding: 0 12px;
            }
            QPushButton:hover {
                border-color: #FF3B3B;
                color: #FF3B3B;
                background-color: #160606;
            }
            """
        )
        self.red_btn.clicked.connect(lambda: self._open_team_picker("RED"))
        layout.addWidget(self.red_btn)

        layout.addStretch()

        board_sep = QLabel("//")
        board_sep.setStyleSheet("color: #2A4A6A; font-size: 10px; font-weight: 700;")
        layout.addWidget(board_sep)

        board_label = QLabel("PIZARRA")
        board_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 2px;
            """
        )
        layout.addWidget(board_label)

        self.board_btns: list[QPushButton] = []
        for idx in range(1, 6):
            button = QPushButton(str(idx))
            button.setFixedSize(26, 26)
            button.setCheckable(True)
            button.setChecked(idx == 1)
            button.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            button.setStyleSheet(self._board_btn_style(idx == 1))
            button.clicked.connect(lambda checked=False, board_idx=idx: self._switch_board(board_idx))
            self.board_btns.append(button)
            layout.addWidget(button)

        clear_btn = QPushButton("// LIMPIAR TODO")
        clear_btn.setFixedHeight(26)
        clear_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #FF3B3B33;
                border-radius: 2px;
                color: #FF3B3B66;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 0 12px;
            }
            QPushButton:hover {
                border-color: #FF3B3B;
                color: #FF3B3B;
                background-color: #0D0404;
            }
            """
        )
        clear_btn.clicked.connect(self._clear_all)
        layout.addWidget(clear_btn)

        return layout

    @staticmethod
    def _board_btn_style(active: bool) -> str:
        if active:
            return """
                QPushButton {
                    background-color: #06141E;
                    border: 1px solid #00D4FF;
                    border-radius: 2px;
                    color: #00D4FF;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 0px;
                    text-align: center;
                }
            """
        return """
            QPushButton {
                background-color: transparent;
                border: 1px solid #1A3242;
                border-radius: 2px;
                color: #6C8EAE;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11px;
                font-weight: 700;
                padding: 0px;
                text-align: center;
            }
            QPushButton:hover {
                border-color: #0A7A9A;
                color: #A5D8FF;
            }
        """

    def _open_team_picker(self, side: str) -> None:
        current = self.blue_team if side == "BLUE" else self.red_team
        dialog = TeamPickerDialog(
            side=side,
            all_champions=self.all_champions,
            champion_images=self.champion_images,
            current_team=current,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if side == "BLUE":
                self.blue_team = dialog.selected_team
                names = " · ".join(c[:5].upper() for c in self.blue_team) or "SIN PICKS"
                self.blue_btn.setText(f"AZUL  -  {names}")
            else:
                self.red_team = dialog.selected_team
                names = " · ".join(c[:5].upper() for c in self.red_team) or "SIN PICKS"
                self.red_btn.setText(f"ROJO  -  {names}")
            self.map_area.set_teams(self.blue_team, self.red_team)

    def _clear_all(self) -> None:
        self.map_area.clear_all()

    def keyPressEvent(self, event) -> None:
        shortcuts = {
            Qt.Key.Key_V: "cursor",
            Qt.Key.Key_P: "pen",
            Qt.Key.Key_A: "arrow",
            Qt.Key.Key_C: "circle",
            Qt.Key.Key_R: "rect",
            Qt.Key.Key_E: "eraser",
            Qt.Key.Key_W: "ward",
            Qt.Key.Key_G: "ping",
        }
        tool = shortcuts.get(event.key())
        if tool:
            self.map_area.left_toolbar._select_tool(tool)
            event.accept()
            return
        if event.key() == Qt.Key.Key_Z and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.map_area.undo_last()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Delete:
            self.map_area.clear_drawings_only()
            event.accept()
            return
        super().keyPressEvent(event)

    def _open_team_picker(self, side: str) -> None:
        current = self.blue_team if side == "BLUE" else self.red_team
        dialog = TeamPickerDialog(
            side=side,
            all_champions=self.all_champions,
            champion_images=self.champion_images,
            current_team=current,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if side == "BLUE":
                self.blue_team = dialog.selected_team
            else:
                self.red_team = dialog.selected_team
            self._update_team_buttons()
            self.map_area.set_teams(self.blue_team, self.red_team)

    def _clear_all(self) -> None:
        confirm = ConfirmDialog("¿LIMPIAR ESTA PIZARRA?", parent=self)
        if confirm.exec() == QDialog.DialogCode.Accepted:
            self.map_area.clear_all()
            self.board_states[self.current_board_idx] = {}
            save_all_boards(self.board_states)

    def _switch_board(self, idx: int) -> None:
        if idx == self.current_board_idx:
            return

        self._save_current_board()
        for button_idx, button in enumerate(self.board_btns, start=1):
            active = button_idx == idx
            button.setChecked(active)
            button.setStyleSheet(self._board_btn_style(active))

        self.current_board_idx = idx
        self._load_board(idx)

    def _save_current_board(self) -> None:
        canvas = self.map_area
        state = {
            "blue_team": list(self.blue_team),
            "red_team": list(self.red_team),
            "strokes": [
                {
                    "points": [[point.x(), point.y()] for point in stroke["points"]],
                    "color": stroke["color"].name(),
                    "width": stroke["width"],
                }
                for stroke in canvas.strokes
            ],
            "arrows": [
                {
                    "start": [arrow["start"].x(), arrow["start"].y()],
                    "end": [arrow["end"].x(), arrow["end"].y()],
                    "color": arrow["color"].name(),
                    "width": arrow["width"],
                }
                for arrow in canvas.arrows
            ],
            "shapes": [
                {
                    "type": shape["type"],
                    "rect": [
                        shape["rect"].x(),
                        shape["rect"].y(),
                        shape["rect"].width(),
                        shape["rect"].height(),
                    ],
                    "color": shape["color"].name(),
                    "width": shape["width"],
                }
                for shape in canvas.shapes
            ],
            "wards": [
                {"pos": [ward["pos"].x(), ward["pos"].y()], "team": ward["team"]}
                for ward in canvas.wards
            ],
            "tokens": [
                {
                    "name": token.champ_name,
                    "side": token.side,
                    "x": token.pos().x(),
                    "y": token.pos().y(),
                }
                for token in canvas.tokens
            ],
        }
        self.board_states[self.current_board_idx] = state
        save_all_boards(self.board_states)

    def _load_board(self, idx: int) -> None:
        canvas = self.map_area

        for token in canvas.tokens:
            token.deleteLater()
        canvas.tokens.clear()
        canvas.strokes.clear()
        canvas.arrows.clear()
        canvas.shapes.clear()
        canvas.wards.clear()
        canvas.pings.clear()
        canvas.current_stroke = None

        state = self.board_states.get(idx, {})
        if not state:
            self.blue_team = []
            self.red_team = []
            self._update_team_buttons()
            canvas.set_teams([], [])
            canvas.update()
            return

        self.blue_team = list(state.get("blue_team", []))
        self.red_team = list(state.get("red_team", []))
        self._update_team_buttons()
        canvas.set_teams(self.blue_team, self.red_team)

        for stroke in state.get("strokes", []):
            canvas.strokes.append(
                {
                    "points": [QPoint(point[0], point[1]) for point in stroke.get("points", [])],
                    "color": QColor(stroke.get("color", "#00D4FF")),
                    "width": int(stroke.get("width", 2)),
                }
            )

        for arrow in state.get("arrows", []):
            start = arrow.get("start", [0, 0])
            end = arrow.get("end", [0, 0])
            canvas.arrows.append(
                {
                    "start": QPoint(start[0], start[1]),
                    "end": QPoint(end[0], end[1]),
                    "color": QColor(arrow.get("color", "#00D4FF")),
                    "width": int(arrow.get("width", 2)),
                }
            )

        for shape in state.get("shapes", []):
            rect = shape.get("rect", [0, 0, 0, 0])
            canvas.shapes.append(
                {
                    "type": shape.get("type", MapCanvas.TOOL_RECT),
                    "rect": QRect(rect[0], rect[1], rect[2], rect[3]),
                    "color": QColor(shape.get("color", "#00D4FF")),
                    "width": int(shape.get("width", 2)),
                }
            )

        for ward in state.get("wards", []):
            pos = ward.get("pos", [0, 0])
            canvas.wards.append(
                {
                    "pos": QPoint(pos[0], pos[1]),
                    "team": ward.get("team", "BLUE"),
                }
            )

        for token in state.get("tokens", []):
            canvas.spawn_champion_token(
                name=token.get("name", ""),
                side=token.get("side", "BLUE"),
                spawn_pos=QPoint(int(token.get("x", 0)) + 22, int(token.get("y", 0)) + 22),
            )

        canvas.update()

    def _load_all_boards(self) -> None:
        self.board_states = load_all_boards()
        self._load_board(1)

    def _update_team_buttons(self) -> None:
        blue_names = " · ".join(champion[:5].upper() for champion in self.blue_team) or "SIN PICKS"
        red_names = " · ".join(champion[:5].upper() for champion in self.red_team) or "SIN PICKS"
        self.blue_btn.setText(f"⬡  AZUL  —  {blue_names}")
        self.red_btn.setText(f"⬡  ROJO  —  {red_names}")

    def save_before_close(self) -> None:
        self._save_current_board()


class MapCanvas(QWidget):
    TOOL_CURSOR = "cursor"
    TOOL_PEN = "pen"
    TOOL_ARROW = "arrow"
    TOOL_CIRCLE = "circle"
    TOOL_RECT = "rect"
    TOOL_ERASER = "eraser"
    TOOL_WARD = "ward"
    TOOL_PING = "ping"

    def __init__(self, all_champions, champion_images, parent=None):
        super().__init__(parent)
        self.all_champions = all_champions
        self.champion_images = champion_images
        self.current_tool = self.TOOL_CURSOR
        self.current_color = QColor("#00D4FF")
        self.stroke_width = 2
        self.show_grid = False
        self.blue_team: list[str] = []
        self.red_team: list[str] = []
        self.strokes: list[dict] = []
        self.arrows: list[dict] = []
        self.shapes: list[dict] = []
        self.wards: list[dict] = []
        self.pings: list[dict] = []
        self.current_stroke = None
        self.tokens: list[ChampionToken] = []
        self.map_pixmap: QPixmap | None = None
        self._load_map()
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._build_left_toolbar()
        self._build_right_toolbar()

    def _load_map(self) -> None:
        base_dir = Path(__file__).resolve().parents[1]
        candidate_paths = [
            base_dir / "assets" / "mapa 2.jpg",
            base_dir / "assets" / "map" / "summoners_rift.png",
            base_dir / "assets" / "Summoner-Rift-Map.png",
            Path.cwd() / "assets" / "mapa 2.jpg",
            Path.cwd() / "assets" / "map" / "summoners_rift.png",
            Path.cwd() / "assets" / "Summoner-Rift-Map.png",
        ]
        for path in candidate_paths:
            if path.exists():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    self.map_pixmap = pixmap
                    return

    def set_teams(self, blue: list[str], red: list[str]) -> None:
        self.blue_team = blue
        self.red_team = red
        self.right_toolbar.refresh_tokens(blue, red)

    def clear_all(self) -> None:
        self.strokes.clear()
        self.arrows.clear()
        self.shapes.clear()
        self.wards.clear()
        self.pings.clear()
        self.current_stroke = None
        self.blue_team = []
        self.red_team = []
        self.right_toolbar.refresh_tokens([], [])
        for token in self.tokens:
            token.deleteLater()
        self.tokens.clear()
        parent = self.parent()
        if isinstance(parent, PizarraMode):
            parent.blue_team = []
            parent.red_team = []
            parent._update_team_buttons()
        self.update()

    def clear_drawings_only(self) -> None:
        self.strokes.clear()
        self.arrows.clear()
        self.shapes.clear()
        self.wards.clear()
        self.pings.clear()
        self.current_stroke = None
        self.update()

    def _build_left_toolbar(self) -> None:
        self.left_toolbar = DrawingToolbar(parent=self)
        self.left_toolbar.tool_changed.connect(self.set_tool)
        self.left_toolbar.color_changed.connect(self.set_color)
        self.left_toolbar.width_changed.connect(self.set_stroke_width)
        self.left_toolbar.undo_requested.connect(self.undo_last)
        self.left_toolbar.clear_requested.connect(self.clear_drawings_only)
        self.left_toolbar.grid_toggled.connect(self.toggle_grid)
        self.left_toolbar.raise_()

    def _build_right_toolbar(self) -> None:
        self.right_toolbar = TokenPanel(champion_images=self.champion_images, parent=self)
        self.right_toolbar.spawn_token.connect(self.spawn_champion_token)
        self.right_toolbar.raise_()

    def resizeEvent(self, event) -> None:
        if event:
            super().resizeEvent(event)

        if not hasattr(self, "left_toolbar") or not hasattr(self, "right_toolbar"):
            return

        h = self.height()
        w = self.width()

        tb_ideal = self.left_toolbar.sizeHint().height()
        tb_h = min(tb_ideal, h - 20)
        self.left_toolbar.setFixedHeight(tb_h)
        self.left_toolbar.move(10, (h - tb_h) // 2)

        rp_w = self.right_toolbar.width()
        rp_ideal = self.right_toolbar.ideal_height()
        rp_h = max(min(rp_ideal, h - 20), min(h - 20, 680))
        self.right_toolbar.setFixedHeight(rp_h)
        self.right_toolbar.move(w - rp_w - 10, (h - rp_h) // 2)

        self.left_toolbar.raise_()
        self.right_toolbar.raise_()

    def set_tool(self, tool: str) -> None:
        self.current_tool = tool
        cursor = Qt.CursorShape.ArrowCursor if tool == self.TOOL_CURSOR else Qt.CursorShape.CrossCursor
        self.setCursor(cursor)
        for token in self.tokens:
            token.setDraggable(tool == self.TOOL_CURSOR)

    def set_color(self, color: QColor) -> None:
        self.current_color = color

    def set_stroke_width(self, width: int) -> None:
        self.stroke_width = width

    def toggle_grid(self, visible: bool) -> None:
        self.show_grid = visible
        self.update()

    def mousePressEvent(self, event) -> None:
        if self.current_tool == self.TOOL_CURSOR:
            return
        pos = event.position().toPoint()

        if self.current_tool == self.TOOL_PEN:
            self.current_stroke = {
                "points": [pos],
                "color": QColor(self.current_color),
                "width": self.stroke_width,
                "tool": "pen",
            }
        elif self.current_tool == self.TOOL_ARROW:
            self.arrow_start = pos
            self.arrow_preview = pos
        elif self.current_tool in (self.TOOL_CIRCLE, self.TOOL_RECT):
            self.shape_start = pos
            self.shape_preview = pos
        elif self.current_tool == self.TOOL_ERASER:
            self._erase_near(pos)
        elif self.current_tool == self.TOOL_WARD:
            team = "BLUE" if event.button() == Qt.MouseButton.LeftButton else "RED"
            self.wards.append({"pos": pos, "team": team})
            self.update()
        elif self.current_tool == self.TOOL_PING:
            self.pings.append({"pos": pos, "color": QColor(self.current_color), "born": QTime.currentTime()})
            self.update()
            QTimer.singleShot(2000, self.update)

    def mouseMoveEvent(self, event) -> None:
        pos = event.position().toPoint()
        if self.current_tool == self.TOOL_PEN and self.current_stroke:
            self.current_stroke["points"].append(pos)
            self.update()
        elif self.current_tool == self.TOOL_ARROW and hasattr(self, "arrow_start"):
            self.arrow_preview = pos
            self.update()
        elif self.current_tool in (self.TOOL_CIRCLE, self.TOOL_RECT) and hasattr(self, "shape_start"):
            self.shape_preview = pos
            self.update()
        elif self.current_tool == self.TOOL_ERASER and event.buttons() & Qt.MouseButton.LeftButton:
            self._erase_near(pos)

    def mouseReleaseEvent(self, event) -> None:
        pos = event.position().toPoint()
        if self.current_tool == self.TOOL_PEN and self.current_stroke:
            if len(self.current_stroke["points"]) > 1:
                self.strokes.append(self.current_stroke)
            self.current_stroke = None
            self.update()
        elif self.current_tool == self.TOOL_ARROW and hasattr(self, "arrow_start"):
            if (pos - self.arrow_start).manhattanLength() > 10:
                self.arrows.append(
                    {
                        "start": self.arrow_start,
                        "end": pos,
                        "color": QColor(self.current_color),
                        "width": self.stroke_width,
                    }
                )
            del self.arrow_start
            if hasattr(self, "arrow_preview"):
                del self.arrow_preview
            self.update()
        elif self.current_tool in (self.TOOL_CIRCLE, self.TOOL_RECT) and hasattr(self, "shape_start"):
            rect = QRect(self.shape_start, pos).normalized()
            if rect.width() > 5 and rect.height() > 5:
                self.shapes.append(
                    {
                        "type": self.current_tool,
                        "rect": rect,
                        "color": QColor(self.current_color),
                        "width": self.stroke_width,
                    }
                )
            del self.shape_start
            if hasattr(self, "shape_preview"):
                del self.shape_preview
            self.update()

    def _erase_near(self, pos: QPoint, radius: int = 20) -> None:
        self.strokes = [
            s for s in self.strokes if not any((p - pos).manhattanLength() < radius for p in s["points"])
        ]
        self.arrows = [
            a
            for a in self.arrows
            if (a["start"] - pos).manhattanLength() > radius and (a["end"] - pos).manhattanLength() > radius
        ]
        self.shapes = [s for s in self.shapes if not s["rect"].adjusted(-radius, -radius, radius, radius).contains(pos)]
        self.wards = [w for w in self.wards if (w["pos"] - pos).manhattanLength() > radius]
        self.pings = [p for p in self.pings if (p["pos"] - pos).manhattanLength() > radius]
        self.update()

    def undo_last(self) -> None:
        if self.strokes:
            self.strokes.pop()
        elif self.arrows:
            self.arrows.pop()
        elif self.shapes:
            self.shapes.pop()
        elif self.wards:
            self.wards.pop()
        elif self.pings:
            self.pings.pop()
        self.update()

    def spawn_champion_token(self, name: str, side: str, spawn_pos: QPoint | None = None) -> None:
        spawned_from_panel = spawn_pos is None or spawn_pos == QPoint(0, 0)
        if spawned_from_panel:
            spawn_pos = QPoint(self.width() // 2, self.height() // 2)
            self.left_toolbar._select_tool(self.TOOL_CURSOR)
        token = ChampionToken(name=name, side=side, pixmap=self.champion_images.get(name), parent=self)
        token.move(spawn_pos - QPoint(22, 22))
        token.setDraggable(self.current_tool == self.TOOL_CURSOR)
        token.show()
        token.raise_()
        token.remove_requested.connect(lambda n, s: self._remove_token_widget(token, n, s))
        self.tokens.append(token)
        self.right_toolbar.mark_token_state(name, side, True)
        self.setFocus()
        self.left_toolbar.raise_()
        self.right_toolbar.raise_()

    def _remove_token_widget(self, token: "ChampionToken", name: str, side: str) -> None:
        if token in self.tokens:
            self.tokens.remove(token)
        self.right_toolbar.mark_token_state(name, side, False)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect()

        if self.map_pixmap:
            fitted = self.map_pixmap.scaled(
                rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            zoom_factor = 1.14
            scaled = fitted.scaled(
                int(fitted.width() * zoom_factor),
                int(fitted.height() * zoom_factor),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (rect.width() - scaled.width()) // 2
            y = (rect.height() - scaled.height()) // 2
            painter.fillRect(rect, QColor("#03050A"))
            painter.drawPixmap(x, y, scaled)
        else:
            painter.fillRect(rect, QColor("#1A2E1A"))
            painter.setPen(QPen(QColor("#1E3A1E"), 1))
            for x in range(0, rect.width(), 40):
                painter.drawLine(x, 0, x, rect.height())
            for y in range(0, rect.height(), 40):
                painter.drawLine(0, y, rect.width(), y)

        if self.show_grid:
            painter.setPen(QPen(QColor(255, 255, 255, 18), 1, Qt.PenStyle.DotLine))
            for x in range(0, rect.width(), 60):
                painter.drawLine(x, 0, x, rect.height())
            for y in range(0, rect.height(), 60):
                painter.drawLine(0, y, rect.width(), y)

        for ward in self.wards:
            pos = ward["pos"]
            color = QColor("#00D4FF") if ward["team"] == "BLUE" else QColor("#FF3B3B")
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 40)))
            painter.drawEllipse(pos.x() - 10, pos.y() - 10, 20, 20)
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor("#FFFFFF88"), 1))
            pts = QPolygon(
                [
                    QPoint(pos.x(), pos.y() - 8),
                    QPoint(pos.x() + 6, pos.y()),
                    QPoint(pos.x(), pos.y() + 8),
                    QPoint(pos.x() - 6, pos.y()),
                ]
            )
            painter.drawPolygon(pts)

        for stroke in self.strokes:
            if len(stroke["points"]) < 2:
                continue
            pen = QPen(
                stroke["color"],
                stroke["width"],
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            path = QPainterPath()
            path.moveTo(QPointF(stroke["points"][0]))
            for pt in stroke["points"][1:]:
                path.lineTo(QPointF(pt))
            painter.drawPath(path)

        if self.current_stroke and len(self.current_stroke["points"]) > 1:
            pen = QPen(
                self.current_stroke["color"],
                self.current_stroke["width"],
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
            painter.setPen(pen)
            path = QPainterPath()
            path.moveTo(QPointF(self.current_stroke["points"][0]))
            for pt in self.current_stroke["points"][1:]:
                path.lineTo(QPointF(pt))
            painter.drawPath(path)

        for shape in self.shapes:
            pen = QPen(shape["color"], shape["width"])
            painter.setPen(pen)
            fill_color = QColor(shape["color"].red(), shape["color"].green(), shape["color"].blue(), 30)
            painter.setBrush(QBrush(fill_color))
            if shape["type"] == self.TOOL_CIRCLE:
                painter.drawEllipse(shape["rect"])
            else:
                painter.drawRect(shape["rect"])

        if hasattr(self, "shape_start") and hasattr(self, "shape_preview"):
            rect_prev = QRect(self.shape_start, self.shape_preview).normalized()
            pen = QPen(self.current_color, self.stroke_width, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            fill_prev = QColor(self.current_color.red(), self.current_color.green(), self.current_color.blue(), 20)
            painter.setBrush(QBrush(fill_prev))
            if self.current_tool == self.TOOL_CIRCLE:
                painter.drawEllipse(rect_prev)
            else:
                painter.drawRect(rect_prev)

        for arrow in self.arrows:
            self._draw_arrow(painter, arrow["start"], arrow["end"], arrow["color"], arrow["width"])

        if hasattr(self, "arrow_start") and hasattr(self, "arrow_preview"):
            self._draw_arrow(
                painter,
                self.arrow_start,
                self.arrow_preview,
                self.current_color,
                self.stroke_width,
                dashed=True,
            )

        now = QTime.currentTime()
        for ping in self.pings[:]:
            elapsed = ping["born"].msecsTo(now)
            if elapsed > 2000:
                continue
            alpha = max(0, 255 - int(elapsed / 2000 * 255))
            pos = ping["pos"]
            c = ping["color"]
            radius = 10 + int(elapsed / 200)
            ring_color = QColor(c.red(), c.green(), c.blue(), alpha)
            painter.setPen(QPen(ring_color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(pos.x() - radius, pos.y() - radius, radius * 2, radius * 2)
            dot_color = QColor(c.red(), c.green(), c.blue(), alpha)
            painter.setBrush(QBrush(dot_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(pos.x() - 4, pos.y() - 4, 8, 8)

    @staticmethod
    def _draw_arrow(painter, start: QPoint, end: QPoint, color: QColor, width: int, dashed: bool = False) -> None:
        pen = QPen(
            color,
            width,
            Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(start, end)

        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.sqrt(dx * dx + dy * dy)
        if length < 10:
            return
        ux, uy = dx / length, dy / length
        arrow_size = max(8, width * 4)
        perp_x, perp_y = -uy, ux

        tip = end
        base1 = QPoint(
            int(end.x() - ux * arrow_size + perp_x * arrow_size * 0.4),
            int(end.y() - uy * arrow_size + perp_y * arrow_size * 0.4),
        )
        base2 = QPoint(
            int(end.x() - ux * arrow_size - perp_x * arrow_size * 0.4),
            int(end.y() - uy * arrow_size - perp_y * arrow_size * 0.4),
        )

        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygon([tip, base1, base2]))


class DrawingToolbar(QWidget):
    tool_changed = pyqtSignal(str)
    color_changed = pyqtSignal(QColor)
    width_changed = pyqtSignal(int)
    undo_requested = pyqtSignal()
    clear_requested = pyqtSignal()
    grid_toggled = pyqtSignal(bool)

    EXPANDED_WIDTH = 130
    COLLAPSED_WIDTH = 18

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = True
        self.current_tool = "cursor"
        self.current_color = QColor("#00D4FF")
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.content = QWidget()
        self.content.setFixedWidth(self.EXPANDED_WIDTH - self.COLLAPSED_WIDTH)
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(6, 8, 4, 8)
        content_layout.setSpacing(2)

        tools_labeled = [
            ("cursor", "↖", "CURSOR"),
            ("pen", "✏", "DIBUJO"),
            ("arrow", "→", "FLECHA"),
            ("circle", "○", "ZONA"),
            ("rect", "□", "RECT"),
            ("eraser", "⌫", "BORRAR"),
            ("ward", "◆", "WARD"),
            ("ping", "◉", "PING"),
        ]

        self.tool_btns: dict[str, QPushButton] = {}
        for tool_key, icon, label in tools_labeled:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setFixedHeight(30)
            btn.setCheckable(True)
            btn.setChecked(tool_key == "cursor")
            btn.setToolTip(self._full_tooltip(tool_key))
            btn.setStyleSheet(self._tool_btn_style(tool_key == "cursor"))
            btn.clicked.connect(lambda checked=False, k=tool_key: self._select_tool(k))
            self.tool_btns[tool_key] = btn
            content_layout.addWidget(btn)

        content_layout.addSpacing(4)
        content_layout.addWidget(self._make_separator())
        content_layout.addSpacing(4)

        colors_label = QLabel("COLOR")
        colors_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 8px; font-weight: 700; letter-spacing: 2px;
            """
        )
        content_layout.addWidget(colors_label)

        colors = [
            ("#00D4FF", "Azul"),
            ("#FF3B3B", "Rojo"),
            ("#00FF88", "Verde"),
            ("#FFD700", "Amarillo"),
            ("#FF8C00", "Naranja"),
            ("#FFFFFF", "Blanco"),
        ]
        for row_idx in range(0, len(colors), 3):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(3)
            for hex_color, name in colors[row_idx : row_idx + 3]:
                swatch = ColorSwatch(hex_color, name)
                swatch.setFixedSize(30, 16)
                swatch.clicked.connect(lambda c=QColor(hex_color): self._select_color(c))
                row_layout.addWidget(swatch)
            content_layout.addWidget(row_widget)

        content_layout.addSpacing(4)
        content_layout.addWidget(self._make_separator())
        content_layout.addSpacing(4)

        width_label = QLabel("GROSOR")
        width_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 8px; font-weight: 700; letter-spacing: 2px;
            """
        )
        content_layout.addWidget(width_label)

        widths_row = QWidget()
        widths_layout = QHBoxLayout(widths_row)
        widths_layout.setContentsMargins(0, 0, 0, 0)
        widths_layout.setSpacing(3)
        self.width_btns: list[tuple[int, QPushButton]] = []
        for w, icon in [(1, "·"), (2, "—"), (4, "━")]:
            btn = QPushButton(icon)
            btn.setFixedSize(30, 22)
            btn.setToolTip(f"{w}px")
            btn.setCheckable(True)
            btn.setChecked(w == 2)
            btn.setStyleSheet(
                """
                QPushButton {
                    background: transparent;
                    border: 1px solid #0A1E2A;
                    border-radius: 2px;
                    color: #2A4A6A;
                    font-size: 13px;
                }
                QPushButton:checked {
                    border-color: #00D4FF;
                    color: #00D4FF;
                    background-color: #06141E;
                }
                QPushButton:hover:!checked {
                    border-color: #0A7A9A;
                    color: #5A9ABF;
                }
                """
            )
            btn.clicked.connect(lambda checked=False, ww=w: self._on_width(ww))
            widths_layout.addWidget(btn)
            self.width_btns.append((w, btn))
        content_layout.addWidget(widths_row)

        content_layout.addSpacing(4)
        content_layout.addWidget(self._make_separator())
        content_layout.addSpacing(4)

        for label, signal, color_dim, color_hover in [
            ("↩  DESHACER", self.undo_requested, "#2A4A6A", "#00D4FF"),
            ("⊘  LIMPIAR", self.clear_requested, "#2A4A6A", "#FF3B3B"),
        ]:
            btn = QPushButton(label)
            btn.setFixedHeight(26)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent;
                    border: 1px solid #0A1E2A;
                    border-radius: 2px;
                    color: {color_dim};
                    font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                    font-size: 9px; font-weight: 700; letter-spacing: 1.5px;
                    text-align: left; padding-left: 8px;
                }}
                QPushButton:hover {{
                    border-color: {color_hover};
                    color: {color_hover};
                    background-color: {color_hover}0D;
                }}
                """
            )
            btn.clicked.connect(signal.emit)
            content_layout.addWidget(btn)

        grid_btn = QPushButton("⊞  CUADRICULA")
        grid_btn.setFixedHeight(26)
        grid_btn.setCheckable(True)
        grid_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: 1px solid #0A1E2A;
                border-radius: 2px;
                color: #2A4A6A;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 9px; font-weight: 700; letter-spacing: 1.5px;
                text-align: left; padding-left: 8px;
            }
            QPushButton:checked {
                border-color: #C9A84C;
                color: #C9A84C;
                background-color: #0E0C04;
            }
            QPushButton:hover:!checked {
                border-color: #C9A84C44;
                color: #C9A84C88;
            }
            """
        )
        grid_btn.toggled.connect(self.grid_toggled.emit)
        content_layout.addWidget(grid_btn)
        content_layout.addStretch()

        outer.addWidget(self.content)

        self.toggle_strip = QWidget()
        self.toggle_strip.setFixedWidth(self.COLLAPSED_WIDTH)
        toggle_layout = QVBoxLayout(self.toggle_strip)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setSpacing(0)
        toggle_layout.addStretch()

        self.toggle_btn = QPushButton("\u2190")
        self.toggle_btn.setFixedSize(18, 48)
        self.toggle_btn.setToolTip("OCULTAR HERRAMIENTAS")
        self.toggle_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.toggle_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #0A1E2A;
                border: none;
                border-radius: 0px;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
                color: #9CCFE5;
                font-size: 13px;
                font-weight: 700;
                padding: 0px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #0C2A3A;
                color: #00D4FF;
            }
            """
        )
        self.toggle_btn.clicked.connect(self.toggle_collapse)
        toggle_layout.addWidget(self.toggle_btn)
        toggle_layout.addStretch()
        outer.addWidget(self.toggle_strip)

    def toggle_collapse(self) -> None:
        self._expanded = not self._expanded
        self.content.setVisible(self._expanded)
        if self._expanded:
            self.setFixedWidth(self.EXPANDED_WIDTH)
            self.toggle_btn.setText("\u2190")
            self.toggle_btn.setToolTip("OCULTAR HERRAMIENTAS")
        else:
            self.setFixedWidth(self.COLLAPSED_WIDTH)
            self.toggle_btn.setText("\u2192")
            self.toggle_btn.setToolTip("MOSTRAR HERRAMIENTAS")
        if self.parent():
            self.parent().resizeEvent(None)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._expanded:
            rect = self.rect().adjusted(0, 0, -self.COLLAPSED_WIDTH, 0)
            painter.setBrush(QBrush(QColor(8, 13, 20, 215)))
            painter.setPen(QPen(QColor("#0A1E2A"), 1))
            painter.drawRoundedRect(rect, 3, 3)

    @staticmethod
    def _tool_btn_style(active: bool) -> str:
        if active:
            return """
                QPushButton {
                    background-color: #06141E;
                    border: 1px solid #00D4FF;
                    border-radius: 3px;
                    color: #00D4FF;
                    font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 1px;
                    text-align: left;
                    padding-left: 8px;
                }
            """
        return """
            QPushButton {
                background-color: transparent;
                border: 1px solid #0A1E2A;
                border-radius: 3px;
                color: #2A4A6A;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                text-align: left;
                padding-left: 8px;
            }
            QPushButton:hover {
                border-color: #0A7A9A;
                color: #5A9ABF;
                background-color: #060E18;
            }
        """

    @staticmethod
    def _full_tooltip(tool_key: str) -> str:
        tooltips = {
            "cursor": "CURSOR  -  Seleccionar y mover tokens  [V]",
            "pen": "DIBUJO LIBRE  -  Trazar lineas libres  [P]",
            "arrow": "FLECHA  -  Indicar rutas y rotaciones  [A]",
            "circle": "ZONA CIRCULAR  -  Marcar areas de control  [C]",
            "rect": "ZONA RECT  -  Marcar areas rectangulares  [R]",
            "eraser": "BORRADOR  -  Eliminar trazos cercanos  [E]",
            "ward": "WARD  -  Clic izq = azul  ·  Clic der = rojo  [W]",
            "ping": "PING  -  Senal de atencion en el mapa  [G]",
        }
        return tooltips.get(tool_key, tool_key)

    @staticmethod
    def _make_separator() -> QFrame:
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(
            """
            background: qlineargradient(x1:0, x2:1,
                stop:0 transparent,
                stop:0.2 #0A2535,
                stop:0.8 #0A2535,
                stop:1 transparent);
            """
        )
        return sep

    def _on_width(self, chosen_w: int) -> None:
        for w, btn in self.width_btns:
            btn.setChecked(w == chosen_w)
        self.width_changed.emit(chosen_w)

    def _select_tool(self, key: str) -> None:
        self.current_tool = key
        for k, btn in self.tool_btns.items():
            active = k == key
            btn.setChecked(active)
            btn.setStyleSheet(self._tool_btn_style(active))
        self.tool_changed.emit(key)

    def _select_color(self, color: QColor) -> None:
        self.current_color = color
        self.color_changed.emit(color)


class ColorSwatch(QWidget):
    clicked = pyqtSignal()

    def __init__(self, hex_color: str, name: str, parent=None):
        super().__init__(parent)
        self.color = QColor(hex_color)
        self.setToolTip(name)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(self.color))
        painter.setPen(QPen(QColor("#0A1E2A"), 1))
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 2, 2)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()


class TokenPanel(QWidget):
    spawn_token = pyqtSignal(str, str, QPoint)
    PANEL_WIDTH = 68
    TOKEN_SIZE = 44
    TOKEN_SPACING = 2

    def __init__(self, champion_images: dict, parent=None):
        super().__init__(parent)
        self.champion_images = champion_images
        self.token_buttons: dict[tuple[str, str], TokenButton] = {}
        self.setFixedWidth(self.PANEL_WIDTH)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 6, 0, 6)
        outer.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(
            """
            QScrollArea { border: none; background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            """
        )

        self.inner = QWidget()
        self.inner.setStyleSheet("background: transparent;")
        self.inner_layout = QVBoxLayout(self.inner)
        self.inner_layout.setContentsMargins(6, 4, 6, 4)
        self.inner_layout.setSpacing(0)

        self.blue_header = self._make_team_header("BLU", "#1E90FF")
        self.inner_layout.addWidget(self.blue_header)
        self.inner_layout.addSpacing(4)

        self.blue_vbox = QVBoxLayout()
        self.blue_vbox.setSpacing(self.TOKEN_SPACING)
        self.blue_vbox.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.addLayout(self.blue_vbox)

        self.inner_layout.addSpacing(4)
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(
            """
            background: qlineargradient(x1:0, x2:1,
                stop:0 transparent,
                stop:0.3 #0A2535,
                stop:0.7 #0A2535,
                stop:1 transparent);
            """
        )
        self.inner_layout.addWidget(sep)
        self.inner_layout.addSpacing(4)

        self.red_header = self._make_team_header("RED", "#FF3B3B")
        self.inner_layout.addWidget(self.red_header)
        self.inner_layout.addSpacing(4)

        self.red_vbox = QVBoxLayout()
        self.red_vbox.setSpacing(self.TOKEN_SPACING)
        self.red_vbox.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.addLayout(self.red_vbox)
        self.empty_hint = QLabel("SIN\nEQUIPO")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.setStyleSheet(
            """
            color: #1A3A55;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 8px; font-weight: 700; letter-spacing: 1px;
            """
        )
        self.inner_layout.addWidget(self.empty_hint)

        self.scroll.setWidget(self.inner)
        outer.addWidget(self.scroll)
        self._update_ideal_height()

    @staticmethod
    def _make_team_header(text: str, color: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFixedHeight(16)
        lbl.setStyleSheet(
            f"""
            color: {color};
            background-color: {color}1A;
            border: 1px solid {color}33;
            border-radius: 2px;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 8px; font-weight: 700; letter-spacing: 2px;
            """
        )
        return lbl

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(8, 13, 20, 210)))
        painter.setPen(QPen(QColor("#0A1E2A"), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 4, 4)

    def refresh_tokens(self, blue_team: list[str], red_team: list[str]) -> None:
        self.token_buttons.clear()
        for vbox in (self.blue_vbox, self.red_vbox):
            while vbox.count():
                item = vbox.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        has_any = bool(blue_team or red_team)
        self.empty_hint.setVisible(not has_any)
        self.blue_header.setVisible(bool(blue_team))
        self.red_header.setVisible(bool(red_team))

        for name in blue_team:
            btn = TokenButton(
                name=name,
                side="BLUE",
                pixmap=self.champion_images.get(name),
                border_color="#1E90FF",
                panel_width=self.PANEL_WIDTH - 12,
            )
            btn.clicked_token.connect(lambda n, s: self.spawn_token.emit(n, s, QPoint(0, 0)))
            self.token_buttons[(name, "BLUE")] = btn
            self.blue_vbox.addWidget(btn)

        for name in red_team:
            btn = TokenButton(
                name=name,
                side="RED",
                pixmap=self.champion_images.get(name),
                border_color="#FF3B3B",
                panel_width=self.PANEL_WIDTH - 12,
            )
            btn.clicked_token.connect(lambda n, s: self.spawn_token.emit(n, s, QPoint(0, 0)))
            self.token_buttons[(name, "RED")] = btn
            self.red_vbox.addWidget(btn)

        self._update_ideal_height()

    def _update_ideal_height(self) -> None:
        blue_count = self.blue_vbox.count()
        red_count = self.red_vbox.count()
        token_h = self.TOKEN_SIZE + 16 + self.TOKEN_SPACING
        header_h = 16
        sep_h = 9
        padding = 12

        ideal = (
            padding
            + (header_h + 4 + blue_count * token_h if blue_count else 0)
            + (sep_h if blue_count and red_count else 0)
            + (header_h + 4 + red_count * token_h if red_count else 0)
        )
        self._ideal_height = max(60, ideal)

    def ideal_height(self) -> int:
        return getattr(self, "_ideal_height", 200)

    def mark_token_state(self, name: str, side: str, spawned: bool) -> None:
        button = self.token_buttons.get((name, side))
        if button is not None:
            button.spawned = spawned
            button.update()


class TokenButton(QWidget):
    clicked_token = pyqtSignal(str, str)

    def __init__(
        self,
        name: str,
        side: str,
        pixmap=None,
        border_color: str = "#00D4FF",
        panel_width: int = 56,
        parent=None,
    ):
        super().__init__(parent)
        self.champ_name = name
        self.side = side
        self.pixmap = pixmap
        self.border_color = border_color
        self.spawned = False
        self._token_size = 44
        self.setFixedSize(panel_width, self._token_size + 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"COLOCAR {name.upper()} EN EL MAPA\nClic de nuevo para quitar del mapa")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        ts = self._token_size
        cx = (self.width() - ts) // 2
        portrait_rect = QRect(cx, 0, ts, ts)
        inner = portrait_rect.adjusted(3, 3, -3, -3)

        ring_color = QColor(self.border_color)
        ring_alpha = 140 if self.spawned else 60
        glow_pen = QPen(QColor(ring_color.red(), ring_color.green(), ring_color.blue(), ring_alpha), 3)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(portrait_rect.adjusted(1, 1, -1, -1))

        if self.pixmap:
            clip = QPainterPath()
            clip.addEllipse(QRectF(inner))
            painter.setClipPath(clip)
            scaled = self.pixmap.scaled(
                inner.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            source_rect = QRect(
                max(0, (scaled.width() - inner.width()) // 2),
                max(0, (scaled.height() - inner.height()) // 2),
                inner.width(),
                inner.height(),
            )
            painter.drawPixmap(inner, scaled, source_rect)
            painter.setClipping(False)
        else:
            painter.setBrush(QBrush(QColor("#0C1420")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(inner)

        border_alpha = 220 if self.spawned else 80
        painter.setPen(QPen(QColor(ring_color.red(), ring_color.green(), ring_color.blue(), border_alpha), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(portrait_rect.adjusted(2, 2, -2, -2))

        if self.spawned:
            painter.setBrush(QBrush(QColor(0, 0, 0, 120)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(inner)
            painter.setPen(QPen(QColor("#00FF88"), 2))
            painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            painter.drawText(inner, int(Qt.AlignmentFlag.AlignCenter), "✓")

        name_rect = QRect(0, ts + 1, self.width(), 14)
        painter.setPen(QColor(0, 0, 0, 160))
        painter.setFont(QFont("Barlow Condensed", 7, QFont.Weight.Bold))
        painter.drawText(name_rect.adjusted(1, 1, 1, 1), int(Qt.AlignmentFlag.AlignCenter), self.champ_name[:7].upper())
        text_color = QColor(self.border_color) if self.spawned else QColor("#2A4A6A")
        painter.setPen(text_color)
        painter.drawText(name_rect, int(Qt.AlignmentFlag.AlignCenter), self.champ_name[:7].upper())

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.spawned = not self.spawned
            self.update()
            self.clicked_token.emit(self.champ_name, self.side)


class ChampionToken(QWidget):
    remove_requested = pyqtSignal(str, str)
    TOKEN_SIZE = 44

    def __init__(self, name: str, side: str, pixmap=None, parent=None):
        super().__init__(parent)
        self.champ_name = name
        self.side = side
        self.pixmap = pixmap
        self.draggable = True
        self.show_label = True
        self._drag_offset = QPoint()
        self._dragging = False
        self.setFixedSize(self.TOKEN_SIZE, self.TOKEN_SIZE + 14)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip(f"{name}\nCLIC DERECHO -> QUITAR")

    def setDraggable(self, val: bool) -> None:
        self.draggable = val
        self.setCursor(Qt.CursorShape.OpenHandCursor if val else Qt.CursorShape.ArrowCursor)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ring_color = QColor("#1E90FF") if self.side == "BLUE" else QColor("#FF3B3B")
        size = self.TOKEN_SIZE
        token_rect = QRect(0, 0, size, size)

        glow_pen = QPen(QColor(ring_color.red(), ring_color.green(), ring_color.blue(), 80), 4)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(token_rect.adjusted(2, 2, -2, -2))

        inner = token_rect.adjusted(4, 4, -4, -4)
        if self.pixmap:
            clip = QPainterPath()
            clip.addEllipse(QRectF(inner))
            painter.setClipPath(clip)
            scaled = self.pixmap.scaled(
                inner.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            source_rect = QRect(
                max(0, (scaled.width() - inner.width()) // 2),
                max(0, (scaled.height() - inner.height()) // 2),
                inner.width(),
                inner.height(),
            )
            painter.drawPixmap(inner, scaled, source_rect)
            painter.setClipping(False)
        else:
            painter.setBrush(QBrush(QColor("#0C1420")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(inner)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(ring_color, 2))
        painter.drawEllipse(token_rect.adjusted(3, 3, -3, -3))

        if self.show_label:
            painter.setFont(QFont("Barlow Condensed", 7, QFont.Weight.Bold))
            label_rect = QRect(0, size, self.TOKEN_SIZE, 14)
            painter.setPen(QColor(0, 0, 0, 180))
            painter.drawText(label_rect.adjusted(1, 1, 1, 1), int(Qt.AlignmentFlag.AlignCenter), self.champ_name[:7].upper())
            painter.setPen(QColor("#E8EEF4"))
            painter.drawText(label_rect, int(Qt.AlignmentFlag.AlignCenter), self.champ_name[:7].upper())

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.draggable:
            self._dragging = True
            self._drag_offset = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.raise_()

    def mouseMoveEvent(self, event) -> None:
        if self._dragging and self.draggable:
            new_pos = self.mapToParent(event.position().toPoint() - self._drag_offset)
            parent_rect = self.parent().rect()
            x = max(0, min(new_pos.x(), parent_rect.width() - self.width()))
            y = max(0, min(new_pos.y(), parent_rect.height() - self.height()))
            self.move(x, y)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor if self.draggable else Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event) -> None:
        self.show_label = not self.show_label
        self.update()

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #080D14;
                border: 1px solid #0A2535;
                border-radius: 3px;
                padding: 3px 0;
            }
            QMenu::item {
                padding: 5px 16px;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
                color: #5A7A9A;
            }
            QMenu::item:selected {
                background-color: #0C1E2F;
                color: #FF3B3B;
            }
            """
        )
        remove = menu.addAction(f"QUITAR  {self.champ_name.upper()}")
        toggle = menu.addAction("OCULTAR NOMBRE" if self.show_label else "MOSTRAR NOMBRE")
        action = menu.exec(event.globalPos())
        if action == remove:
            self.remove_requested.emit(self.champ_name, self.side)
            self.deleteLater()
        elif action == toggle:
            self.show_label = not self.show_label
            self.update()


class TeamPickerDialog(QDialog):
    def __init__(self, side: str, all_champions: dict, champion_images: dict, current_team: list, parent=None):
        super().__init__(parent)
        self.side = side
        self.all_champions = all_champions
        self.champion_images = champion_images
        self.selected_team = list(current_team)
        self.setFixedSize(640, 480)
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
        self._build_ui()

    def _build_ui(self) -> None:
        color = "#1E90FF" if self.side == "BLUE" else "#FF3B3B"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel(f"// EQUIPO {'AZUL' if self.side == 'BLUE' else 'ROJO'}  -  SELECCIONA HASTA 5")
        title.setStyleSheet(
            f"""
            color: {color};
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 12px; font-weight: 800; letter-spacing: 3px;
            """
        )
        layout.addWidget(title)

        self.search = QLineEdit()
        self.search.setPlaceholderText("BUSCAR CAMPEON...")
        self.search.setFixedHeight(28)
        self.search.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: #0C1420; border: 1px solid #0A1E2A;
                border-radius: 2px; color: #E8EEF4;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 11px; font-weight: 700; letter-spacing: 1px;
                padding: 0 10px;
            }}
            QLineEdit:focus {{ border-color: {color}; }}
            """
        )
        layout.addWidget(self.search)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(4)
        grid.setContentsMargins(2, 2, 2, 2)

        self.champ_btns: dict[str, QToolButton] = {}
        cols = 10
        for i, name in enumerate(sorted(self.all_champions.keys())):
            btn = QToolButton()
            btn.setFixedSize(52, 60)
            btn.setCheckable(True)
            btn.setChecked(name in self.selected_team)
            btn.setToolTip(name)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            pm = self.champion_images.get(name)
            if pm:
                btn.setIcon(QIcon(pm))
                btn.setIconSize(QSize(36, 36))
            btn.setText(name[:6].upper())
            btn.setStyleSheet(
                f"""
                QToolButton {{
                    background-color: #0C1420;
                    border: 1px solid #0A1E2A;
                    border-radius: 3px;
                    color: #1A3A55;
                    font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                    font-size: 7px; font-weight: 700; letter-spacing: 0.5px;
                    padding: 2px 0 0 0;
                }}
                QToolButton:checked {{
                    border: 2px solid {color};
                    background-color: {color}11;
                    color: {color};
                }}
                QToolButton:hover:!checked {{
                    border-color: {color}66;
                    background-color: {color}08;
                }}
                """
            )
            btn.clicked.connect(lambda checked=False, n=name: self._toggle(n, checked))
            self.champ_btns[name] = btn
            grid.addWidget(btn, i // cols, i % cols)

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        self.search.textChanged.connect(self._filter)

        bottom = QHBoxLayout()
        self.count_label = QLabel(f"{len(self.selected_team)} / 5  SELECCIONADOS")
        self.count_label.setStyleSheet(
            f"""
            color: {color}88;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            font-size: 10px;
            """
        )
        bottom.addWidget(self.count_label)
        bottom.addStretch()

        cancel = QPushButton("CANCELAR")
        cancel.setFixedHeight(26)
        cancel.setStyleSheet(
            """
            QPushButton {
                background: transparent; border: 1px solid #0A1E2A22;
                border-radius: 2px; color: #2A4A6A;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 9px; font-weight: 700; letter-spacing: 2px; padding: 0 12px;
            }
            QPushButton:hover { border-color: #FF3B3B; color: #FF3B3B; }
            """
        )
        cancel.clicked.connect(self.reject)
        bottom.addWidget(cancel)

        confirm = QPushButton("// CONFIRMAR")
        confirm.setFixedHeight(26)
        confirm.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent; border: 1px solid {color}44;
                border-radius: 2px; color: {color};
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 9px; font-weight: 700; letter-spacing: 2px; padding: 0 12px;
            }}
            QPushButton:hover {{ border-color: {color}; background: {color}0D; }}
            """
        )
        confirm.clicked.connect(self.accept)
        bottom.addWidget(confirm)
        layout.addLayout(bottom)

    def _toggle(self, name: str, checked: bool) -> None:
        if checked:
            if name not in self.selected_team:
                if len(self.selected_team) >= 5:
                    self.champ_btns[name].setChecked(False)
                    return
                self.selected_team.append(name)
                self.search.clear()
                self.search.setFocus()
        else:
            if name in self.selected_team:
                self.selected_team.remove(name)
        self.count_label.setText(f"{len(self.selected_team)} / 5  SELECCIONADOS")

    def _filter(self, query: str) -> None:
        q = query.upper()
        for name, btn in self.champ_btns.items():
            btn.setVisible(not q or q in name.upper())


class ConfirmDialog(QDialog):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(340, 140)
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
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            """
            color: #E8EEF4;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 13px;
            font-weight: 800;
            letter-spacing: 2px;
            """
        )
        layout.addWidget(label)
        layout.addStretch()

        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton("CANCELAR")
        cancel.setFixedHeight(26)
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        confirm = QPushButton("// LIMPIAR")
        confirm.setFixedHeight(26)
        confirm.clicked.connect(self.accept)
        row.addWidget(confirm)
        layout.addLayout(row)
