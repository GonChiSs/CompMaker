from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from logic.composition import ROLES
from ui.image_utils import build_rounded_cover_pixmap

ARCHETYPE_BUTTONS = [
    ("Wombo Combo", "Wombo Combo"),
    ("Poke / Siege", "Poke / Siege"),
    ("Split Push", "Split Push"),
    ("Pick Comp", "Pick Comp"),
    ("Hypercarry Protect", "Hypercarry Protect"),
]

ARCHETYPE_CONFIG = {
    "Wombo Combo": {"code": "WC", "color": "#00D4FF", "desc": "PROT. COLECTIVA"},
    "Poke / Siege": {"code": "PS", "color": "#C9A84C", "desc": "CONTROL DE ZONA"},
    "Split Push": {"code": "SP", "color": "#00FF88", "desc": "PRESION DE MAPA"},
    "Pick Comp": {"code": "PC", "color": "#FF6B35", "desc": "CAZA DE OBJETIVOS"},
    "Hypercarry Protect": {"code": "HP", "color": "#BF5FFF", "desc": "ESCALA MAXIMA"},
}


class GeneratedCompCard(QWidget):
    def __init__(self, role: str) -> None:
        super().__init__()
        self.setObjectName("compCard")
        self.setStyleSheet(
            """
            QWidget#compCard {
                background-color: #0C1420;
                border: 1px solid #0A1E2A;
                border-radius: 3px;
            }
            """
        )
        self.image_label = QLabel()
        self.image_label.setFixedSize(82, 82)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.role_label = QLabel(role)
        self.role_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.role_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 2.5px;
            """
        )
        self.name_label = QLabel("Sin asignar")
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet(
            """
            color: #E8EEF4;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.5px;
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.role_label)
        layout.addWidget(self.name_label)

    def set_champion(self, champion_name: str, pixmap) -> None:
        self.name_label.setText(champion_name)
        self.image_label.setPixmap(build_rounded_cover_pixmap(pixmap, 82, 18))


class ArchetypeCards(QWidget):
    archetype_selected = pyqtSignal(str)

    def __init__(self, data_loader) -> None:
        super().__init__()
        self.data_loader = data_loader
        self.current_archetype: str | None = None
        title = QLabel("// GENERADOR DE COMPOSICION")
        title.setObjectName("SectionTitle")
        title.setStyleSheet(
            """
            color: #C9A84C;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 16px;
            font-weight: 800;
            letter-spacing: 3px;
            """
        )
        subtitle = QLabel("Elige un arquetipo y CompMaker montara una compo automaticamente.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #5A7A9A; font-size: 11px;")

        self.regenerate_button = QPushButton("Generar nueva compo")
        self.regenerate_button.setEnabled(False)

        self.score_label = QLabel("Score del arquetipo: --")
        self.score_label.setStyleSheet(
            "color: #C9A84C; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 13px; font-weight: 700;"
        )

        self.explanation_label = QLabel("Selecciona un arquetipo para autogenerar la composicion.")
        self.explanation_label.setWordWrap(True)
        self.explanation_label.setStyleSheet("color: #5A7A9A; font-size: 11px;")

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        self.buttons = {}
        for index, (archetype_key, label) in enumerate(ARCHETYPE_BUTTONS):
            config = ARCHETYPE_CONFIG[archetype_key]
            button = QPushButton(f"{config['code']}  {label.upper()}\n{config['desc']}")
            button.setMinimumHeight(72)
            button.setStyleSheet(self._button_style(config["color"], False))
            button.clicked.connect(lambda _, key=archetype_key: self._select_archetype(key))
            self.buttons[archetype_key] = button
            grid.addWidget(button, index // 2, index % 2)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        self.generated_cards: dict[str, GeneratedCompCard] = {}
        for role in ROLES:
            card = GeneratedCompCard(role)
            cards_row.addWidget(card)
            self.generated_cards[role] = card

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(grid)
        layout.addLayout(cards_row)
        layout.addWidget(self.regenerate_button)
        layout.addWidget(self.score_label)
        layout.addWidget(self.explanation_label)
        layout.addStretch()

    def _select_archetype(self, archetype_key: str) -> None:
        self.current_archetype = archetype_key
        self.regenerate_button.setEnabled(True)
        for key, button in self.buttons.items():
            button.setProperty("active", "true" if key == archetype_key else "false")
            button.setStyleSheet(self._button_style(ARCHETYPE_CONFIG[key]["color"], key == archetype_key))
            button.style().unpolish(button)
            button.style().polish(button)
        self.archetype_selected.emit(archetype_key)

    def show_generated_comp(self, picks: dict[str, str], text: str, archetype_score: float) -> None:
        for role in ROLES:
            champion_name = picks[role]
            pixmap = self.data_loader.get_champion_pixmap(champion_name, 82)
            self.generated_cards[role].set_champion(champion_name, pixmap)
        self.score_label.setText(f"Score del arquetipo: {archetype_score:.1f} / 100")
        self.explanation_label.setText(text)

    @staticmethod
    def _button_style(color: str, active: bool) -> str:
        if active:
            return f"""
            QPushButton {{
                background-color: {color}0D;
                border: 1px solid {color}44;
                border-left: 3px solid {color};
                border-radius: 3px;
                color: {color};
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.5px;
                padding: 12px 14px;
                text-align: left;
            }}
            """
        return f"""
        QPushButton {{
            background-color: #0C1420;
            border: 1px solid #0A1E2A;
            border-left: 3px solid {color}22;
            border-radius: 3px;
            color: #3A5A7A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            padding: 12px 14px;
            text-align: left;
        }}
        QPushButton:hover {{
            background-color: #0E1A28;
            border-left: 3px solid {color}88;
            color: #8AAABF;
        }}
        """
