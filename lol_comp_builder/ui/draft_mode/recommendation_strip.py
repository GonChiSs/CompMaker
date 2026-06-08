from __future__ import annotations

from functools import partial

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QProgressBar, QVBoxLayout, QWidget

from ui.image_utils import build_rounded_cover_pixmap


class RecommendationCard(QPushButton):
    clicked_champion = pyqtSignal(str)

    def __init__(self, champion: dict, pixmap, total_score: float, synergy_score: float, matchup_score: float, flex_score: float, reason: str, rank: int) -> None:
        super().__init__()
        self.champion_name = champion["name"]
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(148, 170)
        self.setStyleSheet(
            """
            QPushButton {
                background-color: #0A1620;
                border: 1px solid #223047;
                border-radius: 12px;
                color: #E8E0D0;
            }
            QPushButton:hover {
                border: 1px solid #C89B3C;
                background-color: #102036;
            }
            """
        )
        self.clicked.connect(partial(self.clicked_champion.emit, champion["name"]))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        rank_label = QLabel(f"#{rank}  {total_score:.0f}")
        rank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rank_label.setStyleSheet("background:#C89B3C; color:#04111C; border-radius:8px; font-weight:800;")
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setPixmap(build_rounded_cover_pixmap(pixmap, 60, 12))
        name_label = QLabel(champion["name"])
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setStyleSheet("font-weight:700;")
        reason_label = QLabel(reason)
        reason_label.setWordWrap(True)
        reason_label.setStyleSheet("color:#9CA3AF; font-size:10px;")

        layout.addWidget(rank_label)
        layout.addWidget(image_label)
        layout.addWidget(name_label)
        layout.addWidget(self._build_bar("Sin", synergy_score))
        layout.addWidget(self._build_bar("Mat", matchup_score))
        layout.addWidget(self._build_bar("Flex", flex_score))
        layout.addWidget(reason_label)

    def _build_bar(self, label: str, value: float) -> QWidget:
        wrapper = QWidget()
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        text = QLabel(label)
        text.setFixedWidth(24)
        text.setStyleSheet("color:#6B7280; font-size:10px;")
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(value))
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        row.addWidget(text)
        row.addWidget(bar)
        return wrapper


class RecommendationStrip(QFrame):
    champion_clicked = pyqtSignal(str)

    def __init__(self, data_loader) -> None:
        super().__init__()
        self.data_loader = data_loader
        self.setStyleSheet(
            """
            QFrame {
                background-color: #060C15;
                border: 1px solid #1E2A3A;
                border-radius: 14px;
            }
            """
        )
        self.title = QLabel("Picks recomendados")
        self.title.setStyleSheet("color:#C89B3C; font-size:16px; font-weight:700;")
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(10)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addLayout(self.cards_layout)

    def update_recommendations(self, recs: list[dict], is_ban: bool) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        label = "Bans recomendados" if is_ban else "Picks recomendados"
        self.title.setText(label)

        for index, rec in enumerate(recs[:5], start=1):
            champion = rec["champion"]
            card = RecommendationCard(
                champion=champion,
                pixmap=self.data_loader.get_champion_pixmap(champion["name"], 60),
                total_score=rec["total_score"],
                synergy_score=rec["synergy_score"],
                matchup_score=rec["matchup_score"],
                flex_score=rec["flex_score"],
                reason=rec["reason"],
                rank=index,
            )
            card.clicked_champion.connect(self.champion_clicked.emit)
            self.cards_layout.addWidget(card)
