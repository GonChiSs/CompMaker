from __future__ import annotations

import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QFontDatabase, QIcon
from PyQt6.QtWidgets import QApplication, QDialog, QLabel, QMessageBox, QProgressBar, QVBoxLayout

from logic.data_loader import DataLoader
from logic.ollama_client import OllamaClient
from ui.main_window import MainWindow


def setup_fonts(app: QApplication) -> None:
    """Carga fuentes locales tacticas si existen y aplica la fuente base global."""
    assets_dir = Path(__file__).resolve().parent / "assets" / "fonts"
    if assets_dir.exists():
        for font_path in assets_dir.glob("*.ttf"):
            QFontDatabase.addApplicationFont(str(font_path))

    app_font = QFont("Barlow Condensed", 13)
    app_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.3)
    app.setFont(app_font)


def build_stylesheet() -> str:
    return """
    QMainWindow, QWidget#centralWidget {
        background-color: #03050A;
    }

    QWidget {
        font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
        font-size: 13px;
        color: #E8EEF4;
        background-color: transparent;
    }

    QScrollBar:vertical {
        background: #03050A;
        width: 4px;
        margin: 0;
        border: none;
    }
    QScrollBar::handle:vertical {
        background: #0A7A9A;
        border-radius: 2px;
        min-height: 30px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar:horizontal {
        background: #03050A;
        height: 4px;
        border: none;
    }
    QScrollBar::handle:horizontal {
        background: #0A7A9A;
        border-radius: 2px;
    }

    QDialog {
        background-color: #03050A;
        border: 1px solid #0A2535;
    }

    QToolTip {
        background-color: #080D14;
        color: #E8EEF4;
        border: 1px solid #00D4FF;
        border-radius: 4px;
        padding: 6px 10px;
        font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
        font-size: 12px;
        letter-spacing: 0.3px;
    }

    QLabel {
        background: transparent;
        color: #E8EEF4;
    }
    QLabel#TitleLabel {
        color: #C9A84C;
        font-size: 22px;
        font-weight: 800;
        font-family: 'Cinzel', 'Trajan Pro', 'Georgia';
        letter-spacing: 1.2px;
        padding-left: 4px;
    }
    QLabel#SectionTitle {
        color: #C9A84C;
        font-size: 16px;
        font-weight: 800;
        letter-spacing: 3px;
    }

    QLineEdit {
        background-color: #0C1420;
        border: 1px solid #0A2535;
        border-radius: 3px;
        color: #E8EEF4;
        padding: 7px 12px;
        font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
        font-size: 13px;
        letter-spacing: 0.5px;
        selection-background-color: rgba(0, 212, 255, 0.25);
    }
    QLineEdit:focus {
        border: 1px solid #00D4FF;
        background-color: #0D1E2F;
    }

    QPushButton {
        background-color: transparent;
        border: 1px solid #0A1E2A;
        border-radius: 2px;
        color: #2A4A6A;
        font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 2px;
        padding: 9px 16px;
    }
    QPushButton:hover {
        border-color: #00D4FF;
        color: #00D4FF;
        background-color: #06141E;
    }
    QPushButton[active="true"] {
        border-color: #C9A84C;
        color: #C9A84C;
        background-color: rgba(201, 168, 76, 0.06);
    }

    QMenu {
        background-color: #080D14;
        border: 1px solid #0A2535;
        border-radius: 4px;
        padding: 4px 0;
    }
    QMenu::item {
        padding: 7px 18px;
        font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
        font-size: 12px;
        letter-spacing: 0.5px;
        color: #E8EEF4;
    }
    QMenu::item:selected {
        background-color: #0C1E2F;
        color: #00D4FF;
    }

    QProgressBar {
        background-color: #0C1420;
        border: none;
        border-radius: 2px;
        height: 6px;
        text-align: right;
    }
    QProgressBar::chunk {
        border-radius: 2px;
    }

    QScrollArea, QListWidget {
        border: none;
        background: transparent;
    }
    """


def start_ollama_background() -> None:
    """Inicia Ollama en segundo plano al abrir CompMaker si está instalado."""
    def worker() -> None:
        try:
            OllamaClient().ensure_server_ready(autostart=True)
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()


class DataLoadWorker(QObject):
    progress_changed = pyqtSignal(str, int)
    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, loader: DataLoader) -> None:
        super().__init__()
        self.loader = loader

    def run(self) -> None:
        try:
            bundle = self.loader.prepare_runtime_data(self.progress_changed.emit)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(bundle)


class LoadingDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.result_bundle: dict | None = None
        self.error_message: str | None = None
        self.setWindowTitle("CompMaker")
        self.setModal(True)
        self.setFixedSize(520, 200)
        self.status_label = QLabel("Preparando datos iniciales...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addStretch()

    def update_progress(self, message: str, value: int) -> None:
        self.status_label.setText(message)
        self.progress_bar.setValue(value)

    def set_success(self, bundle: dict) -> None:
        self.result_bundle = bundle
        self.accept()

    def set_failure(self, message: str) -> None:
        self.error_message = message
        self.reject()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("CompMaker")
    setup_fonts(app)
    app.setStyleSheet(build_stylesheet())

    loader = DataLoader(Path(__file__).resolve().parent)
    icon_path = loader.ensure_app_icon()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    loading_dialog = LoadingDialog()
    worker = DataLoadWorker(loader)
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.progress_changed.connect(loading_dialog.update_progress)
    worker.finished.connect(loading_dialog.set_success)
    worker.finished.connect(thread.quit)
    worker.failed.connect(loading_dialog.set_failure)
    worker.failed.connect(thread.quit)
    thread.start()
    loading_dialog.exec()
    thread.wait()

    if loading_dialog.result_bundle is None:
        QMessageBox.critical(
            None,
            "Error de inicio",
            "No se pudo iniciar CompMaker.\n\nDetalle: "
            + (loading_dialog.error_message or "Error desconocido."),
        )
        return 1

    start_ollama_background()
    window = MainWindow(loading_dialog.result_bundle, loader)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
