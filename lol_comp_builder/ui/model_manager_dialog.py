from __future__ import annotations

import threading

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget, QDialog

from logic.ollama_client import OllamaClient


class ModelRow(QWidget):
    install_requested = pyqtSignal(str)
    uninstall_requested = pyqtSignal(str)
    selected_requested = pyqtSignal(str)

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._installed = bool(cfg.get("installed"))
        self.setFixedHeight(88)
        self.setStyleSheet("background: #0C1420; border: 1px solid #0A1E2A; border-radius: 3px;")
        self._build_ui()
        self.set_installed(self._installed)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 6, 10, 6)
        outer.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(10)

        name_lbl = QLabel(f"{self.cfg['label']}  ·  {self.cfg['params']}")
        name_lbl.setStyleSheet(
            """
            color: #E8EEF4;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 12px; font-weight: 700; letter-spacing: 0.5px;
            """
        )
        top.addWidget(name_lbl)
        top.addStretch()

        self.status_badge = QLabel("NO INSTALADO")
        self.status_badge.setFixedWidth(95)
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_badge.setStyleSheet(self._badge_style(False))
        top.addWidget(self.status_badge)

        self.use_btn = QPushButton("USAR")
        self.use_btn.setFixedSize(64, 24)
        self.use_btn.setStyleSheet(self._btn_style("#C9A84C"))
        self.use_btn.clicked.connect(lambda: self.selected_requested.emit(self.cfg["id"]))
        top.addWidget(self.use_btn)

        self.action_btn = QPushButton("INSTALAR")
        self.action_btn.setFixedSize(88, 24)
        self.action_btn.setStyleSheet(self._btn_style("#00D4FF"))
        top.addWidget(self.action_btn)
        outer.addLayout(top)

        spec = QLabel(
            f"{self.cfg['size']}  ·  {self.cfg['ram']}  ·  "
            f"VELOCIDAD: {self.cfg['speed']}  ·  CALIDAD: {self.cfg['quality']}"
        )
        spec.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            font-size: 9px; letter-spacing: 0.5px;
            """
        )
        outer.addWidget(spec)

        desc = QLabel(self.cfg["desc"])
        desc.setWordWrap(True)
        desc.setStyleSheet(
            """
            color: #7C96B0;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 10px; letter-spacing: 0.3px;
            """
        )
        outer.addWidget(desc)

    @staticmethod
    def _badge_style(installed: bool) -> str:
        if installed:
            return """
                background: #001A0A; border: 1px solid #00FF8844;
                color: #00FF88; border-radius: 2px;
                font-family: 'JetBrains Mono', monospace; font-size: 8px; font-weight: 700;
                padding: 2px 4px;
            """
        return """
            background: #0C1420; border: 1px solid #1A3A55;
            color: #1A3A55; border-radius: 2px;
            font-family: 'JetBrains Mono', monospace; font-size: 8px; font-weight: 700;
            padding: 2px 4px;
        """

    @staticmethod
    def _btn_style(color: str) -> str:
        return f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {color};
                border-radius: 2px;
                color: {color};
                font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 0 6px;
            }}
            QPushButton:hover {{
                background-color: #06141E;
            }}
            QPushButton:disabled {{
                border-color: #1A3A55;
                color: #1A3A55;
            }}
        """

    def set_installed(self, installed: bool) -> None:
        self._installed = installed
        self.status_badge.setText("INSTALADO" if installed else "NO INSTALADO")
        self.status_badge.setStyleSheet(self._badge_style(installed))
        self.use_btn.setEnabled(installed)
        try:
            self.action_btn.clicked.disconnect()
        except Exception:
            pass
        if installed:
            self.action_btn.setText("DESINSTALAR")
            self.action_btn.setStyleSheet(self._btn_style("#FF3B3B"))
            self.action_btn.clicked.connect(lambda: self.uninstall_requested.emit(self.cfg["id"]))
        else:
            self.action_btn.setText("INSTALAR")
            self.action_btn.setStyleSheet(self._btn_style("#00D4FF"))
            self.action_btn.clicked.connect(lambda: self.install_requested.emit(self.cfg["id"]))

    def set_downloading(self, downloading: bool) -> None:
        self.action_btn.setEnabled(not downloading)
        self.use_btn.setEnabled(self._installed and not downloading)
        self.action_btn.setText("DESCARGANDO..." if downloading else ("DESINSTALAR" if self._installed else "INSTALAR"))


class ModelManagerDialog(QDialog):
    install_progress = pyqtSignal(str, str, int)
    install_finished = pyqtSignal(str, bool, str)

    def __init__(self, selected_model: str | None = None, parent=None):
        super().__init__(parent)
        self.client = OllamaClient()
        self._selected_model = selected_model or ""
        self._rows: dict[str, ModelRow] = {}
        self._busy_model_id = ""

        self.install_progress.connect(self._apply_install_progress)
        self.install_finished.connect(self._apply_install_finished)

        self.setWindowTitle("Modelos Ollama")
        self.setModal(True)
        self.setFixedSize(580, 560)

        layout = QVBoxLayout(self)
        title = QLabel("// MODELOS LOCALES")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        helper = QLabel(
            "Descarga, activa o desinstala modelos desde aqui. Cuando instales uno quedara listo para usar en el chat."
        )
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #7C96B0;")
        layout.addWidget(helper)

        self.status_label = QLabel("Cargando catalogo...")
        self.status_label.setStyleSheet("color: #2A4A6A;")
        layout.addWidget(self.status_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; }")
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

        self._reload_rows()

    @property
    def selected_model(self) -> str:
        return self._selected_model

    def _reload_rows(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._rows.clear()

        rows = self.client.recommended_models()
        installed_names = set(self.client.list_models())
        running, connection_message = self.client.connection_status()
        if not self._selected_model and installed_names:
            self._selected_model = sorted(installed_names)[0]
        for config in rows:
            row = ModelRow({**config, "installed": config["id"] in installed_names}, parent=self.content)
            row.install_requested.connect(self._install_model)
            row.uninstall_requested.connect(self._uninstall_model)
            row.selected_requested.connect(self._use_model)
            self._rows[config["id"]] = row
            self.content_layout.addWidget(row)
        self.content_layout.addStretch()
        if self._selected_model:
            self.status_label.setText(f"Modelo activo: {self._selected_model}")
        elif running:
            self.status_label.setText("No hay ningun modelo activo.")
        else:
            self.status_label.setText(connection_message)

    def _use_model(self, model_id: str) -> None:
        self._selected_model = model_id
        self.status_label.setText(f"Modelo activo: {self._selected_model}")
        self.accept()

    def _install_model(self, model_id: str) -> None:
        row = self._rows.get(model_id)
        if row is None:
            return
        self._busy_model_id = model_id
        row.set_downloading(True)
        self.status_label.setText(f"Preparando descarga de {model_id}...")

        def worker() -> None:
            try:
                def on_progress(status: str, completed: int | None, total: int | None) -> None:
                    progress = -1
                    if completed is not None and total:
                        progress = int(max(0, min(100, round((completed / total) * 100))))
                    self.install_progress.emit(model_id, status, progress)

                for _ in self.client.iter_pull_model_progress(model_id, callback=on_progress):
                    pass
                self._selected_model = model_id
                self.install_finished.emit(model_id, True, f"Modelo instalado y listo: {model_id}")
            except Exception as exc:
                self.install_finished.emit(model_id, False, f"No se pudo descargar {model_id}: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _uninstall_model(self, model_id: str) -> None:
        row = self._rows.get(model_id)
        if row is None:
            return
        row.set_downloading(True)
        self.status_label.setText(f"Desinstalando {model_id}...")

        def worker() -> None:
            try:
                self.client.delete_model(model_id)
                if self._selected_model == model_id:
                    installed = self.client.list_models()
                    self._selected_model = installed[0] if installed else ""
                self._invoke_reload(f"Modelo desinstalado: {model_id}")
            except Exception as exc:
                self._invoke_error(f"No se pudo desinstalar {model_id}: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _invoke_reload(self, status: str) -> None:
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(0, lambda: self._finish_reload(status))

    def _finish_reload(self, status: str) -> None:
        self._reload_rows()
        self.status_label.setText(status)

    def _invoke_error(self, message: str) -> None:
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(0, lambda: self._show_error(message))

    def _show_error(self, message: str) -> None:
        self._reload_rows()
        QMessageBox.warning(self, "Modelos", message)

    def _apply_install_progress(self, model_id: str, status: str, progress: int) -> None:
        if self._busy_model_id != model_id:
            self._busy_model_id = model_id
        prefix = f"Descargando {model_id}"
        if progress >= 0:
            self.status_label.setText(f"{prefix}... {progress}%  ·  {status}")
        else:
            self.status_label.setText(f"{prefix}...  ·  {status}")

    def _apply_install_finished(self, model_id: str, success: bool, message: str) -> None:
        self._busy_model_id = ""
        if success:
            self._finish_reload(message)
            return
        self._show_error(message)
