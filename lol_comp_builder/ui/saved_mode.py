from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from logic.saved_compositions import (
    delete_composition,
    export_to_text,
    import_from_text,
    load_saved,
    rename_composition,
)
from logic.synergy_engine import compute_team_synergy_mode1
from ui.image_utils import build_rounded_cover_pixmap


class SavedMode(QWidget):
    load_requested = pyqtSignal(dict)

    def __init__(self, all_champions: dict, parent=None):
        super().__init__(parent)
        self.all_champions = all_champions
        self.current_sort_key = "date"
        self.sort_buttons: dict[str, QPushButton] = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()

        title = QLabel("// COMPOSICIONES GUARDADAS")
        title.setStyleSheet(
            """
            color: #C9A84C;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 3px;
            """
        )
        header_layout.addWidget(title)
        header_layout.addStretch()

        export_btn = QPushButton("// EXPORTAR")
        export_btn.setFixedHeight(26)
        export_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #C9A84C44;
                border-radius: 2px;
                color: #C9A84C88;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 0 12px;
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
        export_btn.clicked.connect(self._export_comps)
        header_layout.addWidget(export_btn)

        import_btn = QPushButton("// IMPORTAR")
        import_btn.setFixedHeight(26)
        import_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #00D4FF33;
                border-radius: 2px;
                color: #00D4FF66;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 9px;
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
        import_btn.clicked.connect(self._import_comps)
        header_layout.addWidget(import_btn)

        self.count_label = QLabel("00  GUARDADAS")
        self.count_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            font-size: 10px;
            letter-spacing: 1px;
            """
        )
        header_layout.addWidget(self.count_label)
        layout.addLayout(header_layout)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(
            """
            background: qlineargradient(x1:0, x2:1,
                stop:0 #C9A84C44, stop:0.4 #C9A84C22, stop:1 transparent);
            """
        )
        layout.addWidget(div)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(6)

        sort_label = QLabel("ORDENAR:")
        sort_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 2px;
            """
        )
        filter_layout.addWidget(sort_label)

        button_style = """
            QPushButton {
                background-color: transparent;
                border: 1px solid #0A1E2A;
                border-radius: 2px;
                color: #2A4A6A;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1.5px;
                padding: 3px 10px;
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
        for label, key in [("RECIENTES", "date"), ("SINERGIA", "score"), ("NOMBRE", "name")]:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setFixedHeight(24)
            button.setStyleSheet(button_style)
            button.clicked.connect(lambda checked=False, sort_key=key: self.sort_by(sort_key))
            self.sort_buttons[key] = button
            filter_layout.addWidget(button)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(
            """
            QScrollArea { border: none; background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            """
        )

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(6)
        self.cards_layout.setContentsMargins(0, 0, 4, 0)
        self.cards_layout.addStretch()
        self.scroll.setWidget(self.cards_container)
        layout.addWidget(self.scroll)

        self.empty_label = QLabel(
            "NINGUNA COMPOSICION GUARDADA\n\n"
            "USA EL BOTON // GUARDAR COMPO EN EL MODO 01\n"
            "PARA GUARDAR TUS COMPOSICIONES FAVORITAS."
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(
            """
            color: #1A3A55;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1px;
            line-height: 2;
            """
        )
        layout.addWidget(self.empty_label)

    def refresh(self) -> None:
        self._set_sort_button_state()
        self._rebuild_cards(self._sorted_saved_entries())

    def sort_by(self, key: str) -> None:
        self.current_sort_key = key
        self._set_sort_button_state()
        self._rebuild_cards(self._sorted_saved_entries())

    def on_delete(self, comp_id: str) -> None:
        delete_composition(comp_id)
        self.refresh()

    def on_rename(self, comp_id: str, new_name: str) -> None:
        rename_composition(comp_id, new_name)
        self.refresh()

    def on_load_requested(self, entry: dict) -> None:
        self.load_requested.emit(entry)

    def _export_comps(self) -> None:
        text = export_to_text()
        if not text:
            self._show_toast("No hay composiciones para exportar.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar composiciones",
            "compmaker_export.txt",
            "Texto CompMaker (*.txt);;Todos los archivos (*)",
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as file:
                    file.write(text)
                QApplication.clipboard().setText(text)
                self._show_toast("✓ EXPORTADAS  ·  archivo guardado + copiado al portapapeles")
            except Exception as exc:
                self._show_toast(f"Error al guardar: {exc}")
            return

        QApplication.clipboard().setText(text)
        self._show_toast("✓ COPIADO AL PORTAPAPELES")

    def _import_comps(self) -> None:
        dialog = ImportDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = dialog.import_text
            if not text.strip():
                return
            imported, skipped, errors = import_from_text(text)

            message_parts = []
            if imported > 0:
                message_parts.append(f"✓ {imported} IMPORTADAS")
            if skipped > 0:
                message_parts.append(f"{skipped} OMITIDAS (duplicadas)")
            if errors:
                message_parts.append(f"{len(errors)} ERRORES")

            self._show_toast("  ·  ".join(message_parts) if message_parts else "NADA IMPORTADO")
            self.refresh()

    def _show_toast(self, message: str) -> None:
        if not hasattr(self, "_toast_label"):
            self._toast_label = QLabel(self)
            self._toast_label.setStyleSheet(
                """
                background-color: #080D14;
                border: 1px solid #0A2535;
                border-radius: 2px;
                color: #C9A84C;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 5px 12px;
                """
            )
            self._toast_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._toast_label.setText(message)
        self._toast_label.adjustSize()
        x = (self.width() - self._toast_label.width()) // 2
        y = self.height() - self._toast_label.height() - 16
        self._toast_label.move(x, y)
        self._toast_label.show()
        self._toast_label.raise_()
        QTimer.singleShot(3000, self._toast_label.hide)

    def _sorted_saved_entries(self) -> list[dict]:
        saved = load_saved()
        if self.current_sort_key == "score":
            saved.sort(key=lambda entry: entry.get("synergy_score", 0), reverse=True)
        elif self.current_sort_key == "name":
            saved.sort(key=lambda entry: entry.get("name", ""))
        else:
            saved.sort(key=lambda entry: entry.get("id", ""), reverse=True)
        return saved

    def _set_sort_button_state(self) -> None:
        for key, button in self.sort_buttons.items():
            button.setChecked(key == self.current_sort_key)

    def _rebuild_cards(self, saved: list[dict]) -> None:
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.count_label.setText(f"{len(saved):02d}  GUARDADAS")

        if not saved:
            self.scroll.hide()
            self.empty_label.show()
            return

        self.empty_label.hide()
        self.scroll.show()
        for entry in saved:
            card = SavedCompoCard(entry, self.all_champions, parent=self)
            card.load_requested.connect(self.on_load_requested)
            card.delete_requested.connect(self.on_delete)
            card.rename_requested.connect(self.on_rename)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)


class SavedCompoCard(QWidget):
    load_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal(str)
    rename_requested = pyqtSignal(str, str)

    def __init__(self, entry: dict, all_champions: dict, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.all_champions = all_champions
        self.expanded = False
        self.setFixedHeight(114)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("savedCard")
        self.setStyleSheet(
            """
            QWidget#savedCard {
                background-color: #0C1420;
                border: 1px solid #0A1E2A;
                border-radius: 3px;
            }
            QWidget#savedCard:hover {
                border-color: #0A2A3A;
                background-color: #0D1828;
            }
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        score_value = float(self.entry.get("synergy_score", 0))
        score_color = self._score_color(score_value)
        score_badge = QLabel(f"{score_value:.0f}")
        score_badge.setFixedSize(36, 36)
        score_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_badge.setStyleSheet(
            f"""
            background-color: {score_color}1A;
            border: 1px solid {score_color}44;
            border-radius: 2px;
            color: {score_color};
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            font-size: 13px;
            font-weight: 700;
            """
        )
        top_row.addWidget(score_badge)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        name_label = QLabel(self.entry.get("name", "SIN NOMBRE"))
        name_label.setStyleSheet(
            """
            color: #E8EEF4;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 1px;
            """
        )
        info_col.addWidget(name_label)

        portraits_row = QHBoxLayout()
        portraits_row.setSpacing(6)
        for champion in self.entry.get("champions", []):
            portrait = QLabel()
            portrait.setFixedSize(34, 34)
            portrait.setAlignment(Qt.AlignmentFlag.AlignCenter)
            champion_name = champion.get("name", "")
            champion_info = self.all_champions.get(champion_name, {})
            image_path = champion_info.get("image_path", "")
            if image_path:
                from PyQt6.QtGui import QPixmap

                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    portrait.setPixmap(build_rounded_cover_pixmap(pixmap, 34, 8))
            portrait.setStyleSheet(
                """
                background-color: #080D14;
                border: 1px solid #0A1E2A;
                border-radius: 2px;
                """
            )
            portraits_row.addWidget(portrait)
        portraits_row.addStretch()
        info_col.addLayout(portraits_row)

        pills_row = QHBoxLayout()
        pills_row.setSpacing(4)
        for champion in self.entry.get("champions", []):
            pill = QLabel(champion.get("name", "")[:7].upper())
            pill.setStyleSheet(
                """
                background-color: #080D14;
                border: 1px solid #0A1E2A;
                border-radius: 2px;
                color: #3A5A7A;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 8px;
                font-weight: 700;
                letter-spacing: 0.5px;
                padding: 1px 5px;
                """
            )
            pills_row.addWidget(pill)
        pills_row.addStretch()
        info_col.addLayout(pills_row)
        top_row.addLayout(info_col, 1)

        right_col = QVBoxLayout()
        right_col.setSpacing(4)

        date_label = QLabel(self.entry.get("date", ""))
        date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        date_label.setStyleSheet(
            """
            color: #1A3A55;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            font-size: 9px;
            letter-spacing: 0.5px;
            """
        )
        right_col.addWidget(date_label)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(4)
        for text, color, handler in [
            ("CARGAR", "#00D4FF", lambda: self.load_requested.emit(self.entry)),
            ("RENOMBR", "#C9A84C", self._open_rename),
            ("X", "#FF3B3B", lambda: self.delete_requested.emit(self.entry["id"])),
        ]:
            button = QPushButton(text)
            button.setFixedHeight(20)
            button.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1px solid {color}33;
                    border-radius: 2px;
                    color: {color}88;
                    font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                    font-size: 8px;
                    font-weight: 700;
                    letter-spacing: 1px;
                    padding: 0 6px;
                }}
                QPushButton:hover {{
                    border-color: {color};
                    color: {color};
                    background-color: {color}0D;
                }}
                """
            )
            button.clicked.connect(handler)
            actions_row.addWidget(button)
        right_col.addLayout(actions_row)
        top_row.addLayout(right_col)
        outer.addLayout(top_row)

        self.expanded_widget = QWidget()
        self.expanded_widget.hide()
        expanded_layout = QVBoxLayout(self.expanded_widget)
        expanded_layout.setContentsMargins(0, 6, 0, 0)
        expanded_layout.setSpacing(4)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #0A1E2A;")
        expanded_layout.addWidget(divider)

        team = [
            self.all_champions.get(champion.get("name"))
            for champion in self.entry.get("champions", [])
            if champion.get("name") in self.all_champions
        ]
        if len(team) >= 2:
            result = compute_team_synergy_mode1(team)

            pairs_label = QLabel("SINERGIA POR DUOS")
            pairs_label.setStyleSheet(
                """
                color: #2A4A6A;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 2px;
                """
            )
            expanded_layout.addWidget(pairs_label)

            for pair_name, pair_score in result.get("best_pairs", [])[:3]:
                pair_row = QHBoxLayout()
                pair_name_label = QLabel(pair_name)
                pair_name_label.setStyleSheet(
                    """
                    color: #3A5A7A;
                    font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                    font-size: 10px;
                    """
                )
                pair_score_label = QLabel(f"{pair_score:.0f}")
                pair_score_label.setStyleSheet(
                    """
                    color: #00D4FF;
                    font-family: 'JetBrains Mono', 'Courier New', monospace;
                    font-size: 10px;
                    font-weight: 700;
                    """
                )
                pair_row.addWidget(pair_name_label)
                pair_row.addStretch()
                pair_row.addWidget(pair_score_label)
                expanded_layout.addLayout(pair_row)

            for highlight in result.get("synergy_highlights", [])[:2]:
                highlight_label = QLabel(highlight)
                highlight_label.setWordWrap(True)
                highlight_label.setStyleSheet(
                    """
                    color: #1A3A55;
                    font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                    font-size: 10px;
                    """
                )
                expanded_layout.addWidget(highlight_label)

        outer.addWidget(self.expanded_widget)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_expand()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(QPen(QColor("#0A2535"), 1))
        rect = self.rect().adjusted(1, 1, -2, -2)
        bracket = 10
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        painter.drawLine(x, y, x + bracket, y)
        painter.drawLine(x, y, x, y + bracket)
        painter.drawLine(x + w - bracket, y, x + w, y)
        painter.drawLine(x + w, y, x + w, y + bracket)
        painter.drawLine(x, y + h - bracket, x, y + h)
        painter.drawLine(x, y + h, x + bracket, y + h)
        painter.drawLine(x + w - bracket, y + h, x + w, y + h)
        painter.drawLine(x + w, y + h - bracket, x + w, y + h)

        scan_pen = QPen(QColor(255, 255, 255, 4), 1)
        painter.setPen(scan_pen)
        for line_y in range(6, self.height(), 4):
            painter.drawLine(12, line_y, self.width() - 12, line_y)
        painter.end()

    def toggle_expand(self) -> None:
        self.expanded = not self.expanded
        if self.expanded:
            self.expanded_widget.show()
            self.setFixedHeight(self.sizeHint().height())
        else:
            self.expanded_widget.hide()
            self.setFixedHeight(114)

    def _open_rename(self) -> None:
        dialog = RenameDialog(self.entry.get("name", ""), parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.rename_requested.emit(self.entry["id"], dialog.new_name)

    @staticmethod
    def _score_color(score: float) -> str:
        if score >= 70:
            return "#00FF88"
        if score >= 50:
            return "#C9A84C"
        return "#FF3B3B"


class RenameDialog(QDialog):
    def __init__(self, current_name: str, parent=None):
        super().__init__(parent)
        self.new_name = current_name
        self.setFixedSize(360, 140)
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
        layout.setSpacing(10)

        label = QLabel("// RENOMBRAR COMPOSICION")
        label.setStyleSheet(
            """
            color: #C9A84C;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 3px;
            """
        )
        layout.addWidget(label)

        self.input = QLineEdit(current_name)
        self.input.setFixedHeight(32)
        self.input.setMaxLength(40)
        self.input.setStyleSheet(
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
                padding: 0 10px;
            }
            QLineEdit:focus {
                border-color: #00D4FF;
            }
            """
        )
        layout.addWidget(self.input)

        button_row = QHBoxLayout()
        for text, color, handler in [
            ("CANCELAR", "#2A4A6A", self.reject),
            ("CONFIRMAR", "#C9A84C", self.confirm),
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
                    padding: 0 12px;
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

    def confirm(self) -> None:
        self.new_name = self.input.text().strip().upper() or "SIN NOMBRE"
        self.accept()


class ImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.import_text = ""
        self.setFixedSize(540, 380)
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel("// IMPORTAR COMPOSICIONES")
        title.setStyleSheet(
            """
            color: #00D4FF;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 3px;
            """
        )
        layout.addWidget(title)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(
            "background: qlineargradient(x1:0,x2:1,stop:0 #00D4FF44,stop:0.5 #00D4FF22,stop:1 transparent);"
        )
        layout.addWidget(divider)

        hint = QLabel("Pega el texto exportado de CompMaker o abre un archivo .txt")
        hint.setWordWrap(True)
        hint.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 10px;
            letter-spacing: 0.5px;
            """
        )
        layout.addWidget(hint)

        self.text_area = QPlainTextEdit()
        self.text_area.setPlaceholderText("=== COMPMAKER EXPORT v1 ===\n\n[COMPO] Nombre de la compo\n...")
        self.text_area.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #0C1420;
                border: 1px solid #0A1E2A;
                border-radius: 2px;
                color: #E8EEF4;
                font-family: 'JetBrains Mono', 'Courier New', monospace;
                font-size: 10px;
                padding: 8px;
            }
            QPlainTextEdit:focus {
                border-color: #00D4FF;
            }
            """
        )
        layout.addWidget(self.text_area, 1)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        open_file_btn = QPushButton("ABRIR ARCHIVO")
        open_file_btn.setFixedHeight(28)
        open_file_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: 1px solid #0A2535;
                border-radius: 2px;
                color: #2A4A6A;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 0 12px;
            }
            QPushButton:hover {
                border-color: #00D4FF;
                color: #00D4FF;
                background: #06141E;
            }
            """
        )
        open_file_btn.clicked.connect(self._open_file)
        button_row.addWidget(open_file_btn)

        button_row.addStretch()

        cancel_btn = QPushButton("CANCELAR")
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: 1px solid #0A1E2A22;
                border-radius: 2px;
                color: #2A4A6A;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 0 12px;
            }
            QPushButton:hover {
                border-color: #FF3B3B;
                color: #FF3B3B;
            }
            """
        )
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        confirm_btn = QPushButton("// IMPORTAR")
        confirm_btn.setFixedHeight(28)
        confirm_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: 1px solid #00D4FF44;
                border-radius: 2px;
                color: #00D4FF;
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 0 12px;
            }
            QPushButton:hover {
                border-color: #00D4FF;
                background: #06141E;
            }
            """
        )
        confirm_btn.clicked.connect(self._confirm)
        button_row.addWidget(confirm_btn)

        layout.addLayout(button_row)

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir exportación CompMaker",
            "",
            "Texto CompMaker (*.txt);;Todos los archivos (*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as file:
                self.text_area.setPlainText(file.read())
        except Exception as exc:
            self.text_area.setPlainText(f"Error al leer el archivo: {exc}")

    def _confirm(self) -> None:
        self.import_text = self.text_area.toPlainText()
        self.accept()
