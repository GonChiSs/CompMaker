from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class DataToolsHubDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.selected_action: str | None = None
        self.setWindowTitle("Herramientas de datos")
        self.setModal(True)
        self.setFixedSize(420, 240)
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

        title = QLabel("// HERRAMIENTAS DE DATOS")
        title.setStyleSheet("color: #C9A84C; font-size: 12px; font-weight: 800; letter-spacing: 3px;")
        layout.addWidget(title)

        helper = QLabel(
            "Desde aqui puedes consultar todos los tags o editar tags y roles de campeones para que los cambios afecten a toda la app."
        )
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #5A7A9A; font-size: 11px; font-weight: 700;")
        layout.addWidget(helper)

        actions = [
            ("LISTA DE TAGS", "tag_list"),
            ("EDICION DE TAGS", "tag_edit"),
            ("CHAMPION ROLES", "role_edit"),
        ]
        for label, action in actions:
            button = QPushButton(label)
            button.setFixedHeight(42)
            button.setStyleSheet(
                """
                QPushButton {
                    background-color: transparent;
                    border: 1px solid #0A2535;
                    border-radius: 2px;
                    color: #E8EEF4;
                    font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                    font-size: 11px;
                    font-weight: 700;
                    letter-spacing: 2px;
                    text-align: left;
                    padding: 0 12px;
                }
                QPushButton:hover {
                    border-color: #00D4FF;
                    color: #00D4FF;
                    background-color: #06141E;
                }
                """
            )
            button.clicked.connect(lambda checked=False, selected=action: self._select_action(selected))
            layout.addWidget(button)

    def _select_action(self, action: str) -> None:
        self.selected_action = action
        self.accept()

    @classmethod
    def get_action(cls, parent=None) -> str | None:
        dialog = cls(parent=parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_action
        return None


class TagCatalogDialog(QDialog):
    def __init__(self, catalog: dict[str, list[str]], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Lista de tags")
        self.setModal(True)
        self.resize(720, 560)
        self.setStyleSheet("QDialog { background-color: #080D14; border: 1px solid #0A2535; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("// LISTA DE TAGS")
        title.setStyleSheet("color: #C9A84C; font-size: 12px; font-weight: 800; letter-spacing: 3px;")
        layout.addWidget(title)

        helper = QLabel("Todos los tags registrados aparecen en una sola lista visual para que sean faciles de leer.")
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #5A7A9A; font-size: 11px; font-weight: 700;")
        layout.addWidget(helper)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        container = QWidget()
        body = QVBoxLayout(container)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)

        all_tags = []
        for tag in catalog.get("ability_tags", []):
            if tag not in all_tags:
                all_tags.append(tag)
        for tag in catalog.get("tags", []):
            if tag not in all_tags:
                all_tags.append(tag)

        summary = QLabel(f"TAGS DISPONIBLES  |  {len(all_tags)}")
        summary.setStyleSheet("color: #00D4FF; font-size: 10px; font-weight: 700; letter-spacing: 2px;")
        body.addWidget(summary)

        grid_wrap = QWidget()
        grid_wrap.setStyleSheet("background-color: #0C1420; border: 1px solid #0A1E2A; border-radius: 3px;")
        grid = QGridLayout(grid_wrap)
        grid.setContentsMargins(14, 14, 14, 14)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        if not all_tags:
            empty = QLabel("Sin tags registrados.")
            empty.setStyleSheet("color: #E8EEF4; font-size: 12px;")
            grid.addWidget(empty, 0, 0)
        else:
            columns = 3
            for index, tag in enumerate(all_tags):
                chip = QLabel(tag)
                chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
                chip.setMinimumHeight(42)
                chip.setStyleSheet(
                    """
                    QLabel {
                        background-color: #101C2A;
                        border: 1px solid #18435A;
                        border-radius: 4px;
                        color: #F1F7FF;
                        font-family: 'JetBrains Mono', 'Segoe UI', sans-serif;
                        font-size: 13px;
                        font-weight: 700;
                        letter-spacing: 0.6px;
                        padding: 6px 12px;
                    }
                    """
                )
                grid.addWidget(chip, index // columns, index % columns)

        body.addWidget(grid_wrap)

        body.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)


class ChampionTagEditorDialog(QDialog):
    def __init__(self, champion_pool: dict[str, dict], parent=None) -> None:
        super().__init__(parent)
        self.champion_pool = champion_pool
        self.rows: dict[str, tuple[QWidget, QLineEdit, QLineEdit]] = {}
        self.setWindowTitle("Edicion de tags")
        self.setModal(True)
        self.resize(980, 680)
        self.setStyleSheet("QDialog { background-color: #080D14; border: 1px solid #0A2535; }")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("// EDICION DE TAGS")
        title.setStyleSheet("color: #C9A84C; font-size: 12px; font-weight: 800; letter-spacing: 3px;")
        layout.addWidget(title)

        helper = QLabel("Edita los tags separados por comas. Los tags clave se guardan en mayusculas.")
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #5A7A9A; font-size: 11px; font-weight: 700;")
        layout.addWidget(helper)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar campeon...")
        self.search_box.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search_box)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        container = QWidget()
        body = QVBoxLayout(container)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(6)

        for champion_name in sorted(self.champion_pool):
            payload = self.champion_pool[champion_name]
            row = QWidget()
            row.setStyleSheet("background-color: #0C1420; border: 1px solid #0A1E2A; border-radius: 3px;")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(6)

            header = QLabel(champion_name)
            header.setStyleSheet("color: #E8EEF4; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
            row_layout.addWidget(header)

            ability_edit = QLineEdit(", ".join(payload.get("ability_tags", [])))
            ability_edit.setPlaceholderText("Tags clave")
            tags_edit = QLineEdit(", ".join(payload.get("tags", [])))
            tags_edit.setPlaceholderText("Tags generales")
            row_layout.addWidget(ability_edit)
            row_layout.addWidget(tags_edit)

            body.addWidget(row)
            self.rows[champion_name] = (row, ability_edit, tags_edit)

        body.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("CANCELAR")
        cancel.clicked.connect(self.reject)
        save = QPushButton("GUARDAR")
        save.clicked.connect(self.accept)
        actions.addWidget(cancel)
        actions.addWidget(save)
        layout.addLayout(actions)

    def _apply_filter(self, query: str) -> None:
        needle = query.strip().lower()
        for champion_name, (row, _, _) in self.rows.items():
            row.setVisible(not needle or needle in champion_name.lower())

    def get_updates(self) -> list[tuple[str, list[str], list[str]]]:
        updates: list[tuple[str, list[str], list[str]]] = []
        for champion_name, (_, ability_edit, tags_edit) in self.rows.items():
            ability_tags = [item.strip() for item in ability_edit.text().split(",")]
            tags = [item.strip() for item in tags_edit.text().split(",")]
            updates.append((champion_name, ability_tags, tags))
        return updates

    @classmethod
    def edit(cls, champion_pool: dict[str, dict], parent=None) -> list[tuple[str, list[str], list[str]]] | None:
        dialog = cls(champion_pool, parent=parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_updates()
        return None


class ChampionRoleEditorDialog(QDialog):
    def __init__(self, champion_pool: dict[str, dict], parent=None) -> None:
        super().__init__(parent)
        self.champion_pool = champion_pool
        self.rows: dict[str, tuple[QWidget, QLineEdit]] = {}
        self.setWindowTitle("Champion roles")
        self.setModal(True)
        self.resize(860, 680)
        self.setStyleSheet("QDialog { background-color: #080D14; border: 1px solid #0A2535; }")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("// CHAMPION ROLES")
        title.setStyleSheet("color: #C9A84C; font-size: 12px; font-weight: 800; letter-spacing: 3px;")
        layout.addWidget(title)

        helper = QLabel("Edita los roles separados por comas. Ejemplo: TOP, MID.")
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #5A7A9A; font-size: 11px; font-weight: 700;")
        layout.addWidget(helper)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar campeon...")
        self.search_box.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search_box)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        container = QWidget()
        body = QVBoxLayout(container)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(6)

        for champion_name in sorted(self.champion_pool):
            payload = self.champion_pool[champion_name]
            row = QWidget()
            row.setStyleSheet("background-color: #0C1420; border: 1px solid #0A1E2A; border-radius: 3px;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(10)

            header = QLabel(champion_name)
            header.setFixedWidth(180)
            header.setStyleSheet("color: #E8EEF4; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
            row_layout.addWidget(header)

            roles_edit = QLineEdit(", ".join(payload.get("roles", [])))
            roles_edit.setPlaceholderText("TOP, JUNGLE, MID, ADC, SUPPORT")
            row_layout.addWidget(roles_edit, 1)

            body.addWidget(row)
            self.rows[champion_name] = (row, roles_edit)

        body.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel = QPushButton("CANCELAR")
        cancel.clicked.connect(self.reject)
        save = QPushButton("GUARDAR")
        save.clicked.connect(self.accept)
        actions.addWidget(cancel)
        actions.addWidget(save)
        layout.addLayout(actions)

    def _apply_filter(self, query: str) -> None:
        needle = query.strip().lower()
        for champion_name, (row, _) in self.rows.items():
            row.setVisible(not needle or needle in champion_name.lower())

    def get_updates(self) -> list[tuple[str, list[str]]]:
        updates: list[tuple[str, list[str]]] = []
        for champion_name, (_, roles_edit) in self.rows.items():
            roles = [item.strip() for item in roles_edit.text().split(",")]
            updates.append((champion_name, roles))
        return updates

    @classmethod
    def edit(cls, champion_pool: dict[str, dict], parent=None) -> list[tuple[str, list[str]]] | None:
        dialog = cls(champion_pool, parent=parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_updates()
        return None
