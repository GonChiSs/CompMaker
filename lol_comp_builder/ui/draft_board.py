from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QCursor, QPainter, QPen, QPixmap, QPolygon
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from logic.composition import ROLES
from ui.image_utils import build_rounded_cover_pixmap


class ChampionSlot(QFrame):
    clicked = pyqtSignal(str)
    cleared = pyqtSignal(str)

    def __init__(self, role: str) -> None:
        super().__init__()
        self.role = role
        self.champion_name: str | None = None
        self.setFixedSize(190, 220)
        self.setObjectName("ChampionSlot")
        self.setStyleSheet(
            """
            QFrame#ChampionSlot {
                background-color: #0C1420;
                border: 1px solid #0F1E2D;
                border-radius: 4px;
            }
            QFrame#ChampionSlot:hover {
                border-color: #00D4FF;
                background-color: #0E1A28;
            }
            """
        )

        self.image_label = QLabel()
        self.image_label.setFixedSize(110, 110)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.role_label = QLabel(role)
        self.role_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.role_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 2.5px;
            """
        )
        self.name_label = QLabel("Seleccionar")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet(
            """
            color: #1A3A55;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 2px;
            """
        )

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.role_label)
        layout.addWidget(self.name_label)
        layout.addStretch()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.role)
        elif event.button() == Qt.MouseButton.RightButton and self.champion_name:
            menu = QMenu(self)
            clear_action = QAction("Quitar campeon", self)
            clear_action.triggered.connect(lambda: self.cleared.emit(self.role))
            menu.addAction(clear_action)
            menu.exec(QCursor.pos())
        super().mousePressEvent(event)

    def set_champion(self, champion_name: str | None, pixmap: QPixmap | None = None) -> None:
        self.champion_name = champion_name
        self.name_label.setText(champion_name or "Seleccionar")
        if pixmap is None or champion_name is None:
            self.image_label.clear()
            self.name_label.setStyleSheet(
                """
                color: #1A3A55;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2px;
                """
            )
            self.update()
            return
        self.name_label.setStyleSheet(
            """
            color: #E8EEF4;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.8px;
            """
        )
        self.image_label.setPixmap(build_rounded_cover_pixmap(pixmap, 110, 22))
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#0A2535")
        pen = QPen(color, 1)
        painter.setPen(pen)

        rect = self.rect().adjusted(1, 1, -2, -2)
        size = 10
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        painter.drawLine(x, y, x + size, y)
        painter.drawLine(x, y, x, y + size)
        painter.drawLine(x + w - size, y, x + w, y)
        painter.drawLine(x + w, y, x + w, y + size)
        painter.drawLine(x, y + h - size, x, y + h)
        painter.drawLine(x, y + h, x + size, y + h)
        painter.drawLine(x + w - size, y + h, x + w, y + h)
        painter.drawLine(x + w, y + h - size, x + w, y + h)

        if self.champion_name is None:
            portrait_rect = self.image_label.geometry()
            cx = portrait_rect.center().x()
            cy = portrait_rect.center().y()
            diamond = QPolygon(
                [
                    QPoint(cx, cy - 18),
                    QPoint(cx + 18, cy),
                    QPoint(cx, cy + 18),
                    QPoint(cx - 18, cy),
                ]
            )
            painter.drawPolygon(diamond)
            painter.setBrush(color)
            painter.drawEllipse(cx - 2, cy - 2, 4, 4)
        else:
            portrait_rect = self.image_label.geometry().adjusted(0, 0, -1, -1)
            painter.setPen(QPen(QColor("#00D4FF26"), 1))
            painter.drawRoundedRect(portrait_rect, 18, 18)
        painter.end()


class DraftBoard(QWidget):
    role_clicked = pyqtSignal(str)
    role_cleared = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.slots: dict[str, ChampionSlot] = {}
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        outer_layout.addStretch(1)

        slots_layout = QHBoxLayout()
        slots_layout.setContentsMargins(0, 0, 0, 0)
        slots_layout.setSpacing(18)

        for index, role in enumerate(ROLES):
            slot = ChampionSlot(role)
            slot.clicked.connect(self.role_clicked.emit)
            slot.cleared.connect(self.role_cleared.emit)
            slots_layout.addWidget(slot)
            self.slots[role] = slot

        outer_layout.addLayout(slots_layout)
        outer_layout.addStretch(2)

    def update_slot(self, role: str, champion_name: str | None, pixmap: QPixmap | None = None) -> None:
        self.slots[role].set_champion(champion_name, pixmap)


class SaveCompoDialog(QDialog):
    """Modal tactico para nombrar y guardar una composicion."""

    def __init__(self, current_team: list, synergy_score: float, parent=None):
        super().__init__(parent)
        self.saved_name = ""
        self.current_team = current_team
        self.synergy_score = synergy_score
        self.setWindowTitle("Guardar composicion")
        self.setFixedSize(420, 220)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background-color: #080D14;
                border: 1px solid #0A2535;
                border-radius: 3px;
            }
            """
        )

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        frame = QFrame()
        frame.setObjectName("SaveCompoFrame")
        frame.setStyleSheet(
            """
            QFrame#SaveCompoFrame {
                background-color: #080D14;
                border: 1px solid #0A2535;
                border-radius: 3px;
            }
            """
        )
        outer_layout.addWidget(frame)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("// GUARDAR COMPOSICION")
        title.setStyleSheet(
            """
            color: #C9A84C;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 3px;
            """
        )
        layout.addWidget(title)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(
            """
            background: qlineargradient(x1:0, x2:1,
                stop:0 #C9A84C44, stop:0.5 #C9A84C22, stop:1 transparent);
            """
        )
        layout.addWidget(divider)

        preview_layout = QHBoxLayout()
        preview_layout.setSpacing(6)
        for champion in self.current_team:
            name = champion.get("name", "-") if champion else "-"
            tag = QLabel(name.upper()[:8])
            tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tag.setStyleSheet(
                """
                background-color: #0C1420;
                border: 1px solid #0A1E2A;
                border-radius: 2px;
                color: #5A7A9A;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 3px 6px;
                """
            )
            preview_layout.addWidget(tag)
        layout.addLayout(preview_layout)

        score_label = QLabel(f"SINERGIA  {self.synergy_score:.1f} / 100")
        score_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            font-size: 10px;
            letter-spacing: 1px;
            """
        )
        layout.addWidget(score_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("NOMBRE DE LA COMPOSICION...")
        self.name_input.setFixedHeight(34)
        self.name_input.setMaxLength(40)
        self.name_input.setStyleSheet(
            """
            QLineEdit {
                background-color: #0C1420;
                border: 1px solid #0A2535;
                border-radius: 2px;
                color: #E8EEF4;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 0 12px;
            }
            QLineEdit:focus {
                border-color: #00D4FF;
                background-color: #0A1820;
            }
            """
        )
        layout.addWidget(self.name_input)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        cancel_button = QPushButton("CANCELAR")
        cancel_button.setFixedHeight(30)
        cancel_button.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #0A1E2A;
                border-radius: 2px;
                color: #2A4A6A;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 0 14px;
            }
            QPushButton:hover {
                border-color: #FF3B3B;
                color: #FF3B3B;
                background-color: #0D0404;
            }
            """
        )
        cancel_button.clicked.connect(self.reject)

        confirm_button = QPushButton("// GUARDAR")
        confirm_button.setFixedHeight(30)
        confirm_button.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #7A6030;
                border-radius: 2px;
                color: #C9A84C;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 0 14px;
            }
            QPushButton:hover {
                border-color: #C9A84C;
                background-color: #0E0C04;
            }
            """
        )
        confirm_button.clicked.connect(self.save)

        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(confirm_button)
        layout.addLayout(button_layout)

    def save(self) -> None:
        name = self.name_input.text().strip()
        if not name:
            name = f"COMPO_{datetime.now().strftime('%d%m_%H%M')}"
        self.saved_name = name
        self.accept()
