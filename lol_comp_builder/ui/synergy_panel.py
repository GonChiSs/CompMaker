from __future__ import annotations

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget


class SynergyPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.current_score = 0.0
        self.setObjectName("SynergyPanel")
        self.setStyleSheet(
            """
            QFrame#SynergyPanel {
                background-color: #080D14;
                border: 1px solid #0A1E2A;
                border-radius: 3px;
            }
            QLabel#ScoreLabel {
                color: #E8EEF4;
                font-size: 32px;
                font-weight: 700;
            }
            QLabel#MetaLabel {
                color: #5A7A9A;
                font-size: 11px;
            }
            QProgressBar {
                background-color: #0A1420;
                border: none;
                border-radius: 2px;
                min-height: 4px;
            }
            QProgressBar::chunk {
                border-radius: 2px;
            }
            """
        )
        self.title_label = QLabel("// ANALISIS DE SINERGIA")
        self.title_label.setObjectName("SectionTitle")
        self.title_label.setStyleSheet(
            """
            color: #2A4A6A;
            font-family: 'Barlow Condensed', 'Arial Narrow', Arial;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 2.5px;
            """
        )

        self.score_label = QLabel("0.0 / 100")
        self.score_label.setObjectName("ScoreLabel")
        mono_font = QFont("JetBrains Mono", 28, QFont.Weight.Bold)
        self.score_label.setFont(mono_font)
        self.score_label.setStyleSheet(
            """
            color: #E8EEF4;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            font-size: 32px;
            font-weight: 700;
            letter-spacing: -1px;
            """
        )
        self.archetype_label = QLabel("Sin definir")
        self.archetype_label.setStyleSheet(
            "color: #C9A84C; font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 13px; font-weight: 700;"
        )

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)

        self.best_pair_label = QLabel("Mejor duo: aun no disponible")
        self.best_pair_label.setObjectName("MetaLabel")
        self.best_pair_label.setWordWrap(True)
        self.worst_pair_label = QLabel("Peor duo: aun no disponible")
        self.worst_pair_label.setObjectName("MetaLabel")
        self.worst_pair_label.setWordWrap(True)
        self.patch_label = QLabel("Patch de datos: --")
        self.patch_label.setObjectName("MetaLabel")
        self.patch_label.setWordWrap(True)
        self.score_meta_label = QLabel("RAW/AJUSTE | aun no disponible")
        self.score_meta_label.setObjectName("MetaLabel")
        self.score_meta_label.setWordWrap(True)

        self.strength_label = QLabel("Fortalezas: completa picks para empezar el analisis.")
        self.strength_label.setWordWrap(True)
        self.strength_label.setStyleSheet("color: #3A6A8A; font-size: 11px;")
        self.weakness_label = QLabel("Debilidades: aun no hay suficientes datos.")
        self.weakness_label.setWordWrap(True)
        self.weakness_label.setStyleSheet("color: #3A6A8A; font-size: 11px;")
        self.tip_label = QLabel("Consejo: empieza por una condicion de victoria.")
        self.tip_label.setWordWrap(True)
        self.tip_label.setStyleSheet("color: #3A6A8A; font-size: 11px;")
        self.curve_title = QLabel("CURVA | aun no disponible")
        self.curve_title.setStyleSheet("color: #C9A84C; font-size: 11px; font-weight: 700;")
        self.curve_widget = QWidget()
        self.curve_layout = QVBoxLayout(self.curve_widget)
        self.curve_layout.setContentsMargins(0, 0, 0, 0)
        self.curve_layout.setSpacing(4)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addWidget(self.title_label)
        layout.addWidget(self.score_label)
        layout.addWidget(self.archetype_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.best_pair_label)
        layout.addWidget(self.worst_pair_label)
        layout.addWidget(self.patch_label)
        layout.addWidget(self.score_meta_label)
        layout.addWidget(self.curve_title)
        layout.addWidget(self.curve_widget)
        layout.addWidget(self.strength_label)
        layout.addWidget(self.weakness_label)
        layout.addWidget(self.tip_label)
        layout.addStretch()

    def update_mode1(self, analysis: dict) -> None:
        score = float(analysis.get("display_score", analysis.get("total_score", 0.0)))
        self.current_score = score
        color = self.lerp_color_gradient(score)

        self.score_label.setText(f"{score:.1f} / 100")
        self.progress_bar.setValue(int(score))
        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: #0F172A;
                border: 1px solid #223047;
                border-radius: 10px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 10px;
            }}
            """
        )

        self.title_label.setText("// ANALISIS DE SINERGIA")
        self.archetype_label.hide()
        self.weakness_label.hide()
        self.tip_label.hide()
        self.worst_pair_label.hide()
        self.patch_label.show()
        self.score_meta_label.show()
        self.curve_title.show()
        self.curve_widget.show()

        best_pairs = analysis.get("best_pairs", [])
        if best_pairs:
            best_lines = [f"{pair_name} ({pair_score:.0f})" for pair_name, pair_score in best_pairs[:3]]
            self.best_pair_label.setText("TOP DUOS | " + " | ".join(best_lines))
        else:
            self.best_pair_label.setText("TOP DUOS | aun no disponibles")

        highlights = analysis.get("synergy_highlights", [])
        self.strength_label.setText(
            "LECTURA | " + (" | ".join(highlights) if highlights else "Sin sinergias marcadas aun.")
        )
        self.archetype_label.setText("Sin definir")
        self.weakness_label.setText("Debilidades: aun no hay suficientes datos.")
        self.tip_label.setText("Consejo: empieza por una condicion de victoria.")
        self.worst_pair_label.setText("Peor duo: aun no disponible")
        raw_total = float(analysis.get("raw_total_score", analysis.get("total_score", 0.0)))
        adjusted_raw = float(analysis.get("adjusted_raw_score", analysis.get("total_score", 0.0)))
        self.score_meta_label.setText(
            f"RAW {raw_total:.1f} -> AJUSTADO {adjusted_raw:.1f} | modo 1 puro"
        )
        self._render_curve(analysis.get("curve", {}))

    def update_mode2(self, analysis: dict) -> None:
        score = float(analysis.get("display_score", analysis.get("total_score", 0.0)))
        self.current_score = score
        color = self.lerp_color_gradient(score)

        self.score_label.setText(f"{score:.1f} / 100")
        self.progress_bar.setValue(int(score))
        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: #0F172A;
                border: 1px solid #223047;
                border-radius: 10px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 10px;
            }}
            """
        )

        self.title_label.setText("// ANALISIS DE SINERGIA")
        self.archetype_label.show()
        self.weakness_label.show()
        self.tip_label.show()
        self.worst_pair_label.show()
        self.patch_label.show()
        self.score_meta_label.show()
        self.curve_title.show()
        self.curve_widget.show()

        archetype_scores = analysis.get("archetype_scores", {})
        dominant = analysis.get("dominant_archetype", "Sin definir")
        dominant_score = archetype_scores.get(dominant, 0.0)
        self.archetype_label.setText(f"{dominant.upper()}  {dominant_score:.0f}%")

        best_pair = analysis.get("best_pair", "")
        worst_pair = analysis.get("worst_pair", "")
        pairwise = analysis.get("pairwise_scores", {})
        if best_pair:
            self.best_pair_label.setText(
                f"TOP DUO | {best_pair} ({pairwise.get(best_pair, 0):.0f})"
            )
        else:
            self.best_pair_label.setText("TOP DUO | aun no disponible")
        if worst_pair:
            self.worst_pair_label.setText(
                f"RIESGO | {worst_pair} ({pairwise.get(worst_pair, 0):.0f})"
            )
        else:
            self.worst_pair_label.setText("RIESGO | aun no disponible")

        strengths = analysis.get("strengths", [])
        weaknesses = analysis.get("weaknesses", [])
        tips = analysis.get("tips", [])
        self.strength_label.setText(
            "FORTALEZAS | " + (" | ".join(strengths) if strengths else "Sin fortalezas marcadas aun.")
        )
        self.weakness_label.setText(
            "DEBILIDADES | " + (" | ".join(weaknesses) if weaknesses else "Sin debilidades criticas detectadas.")
        )
        self.tip_label.setText(
            "CONSEJO | " + (" | ".join(tips) if tips else "Sigue equilibrando dano, engage y peel.")
        )

        curve = analysis.get("curve", {})
        self._render_curve(curve)
        raw_total = analysis.get("raw_total_score")
        adjusted_raw = analysis.get("adjusted_raw_score")
        role_penalty = analysis.get("role_coherence_penalty", 0.0)
        curve_adjustment = analysis.get("curve_adjustment", 0.0)
        if raw_total is not None and adjusted_raw is not None:
            self.score_meta_label.setText(
                f"RAW {raw_total:.1f} -> AJUSTADO {adjusted_raw:.1f} | penalty {role_penalty:.1f} | curve {curve_adjustment:+.1f}"
            )
        else:
            self.score_meta_label.setText("RAW/AJUSTE | aun no disponible")

    def update_analysis(self, analysis: dict) -> None:
        self.update_mode2(analysis)

    def set_data_meta(self, meta: dict) -> None:
        patch = meta.get("patch", "--")
        current_patch = meta.get("current_patch", "--")
        if meta.get("is_stale"):
            self.patch_label.setText(f"PATCH DATOS | {patch} (actual {current_patch})")
            self.patch_label.setStyleSheet("color: #FF8C66; font-size: 11px;")
        else:
            self.patch_label.setText(f"PATCH DATOS | {patch}")
            self.patch_label.setStyleSheet("color: #5A7A9A; font-size: 11px;")

    def _clear_curve_rows(self) -> None:
        while self.curve_layout.count():
            item = self.curve_layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                while child_layout.count():
                    child_item = child_layout.takeAt(0)
                    child_widget = child_item.widget()
                    if child_widget is not None:
                        child_widget.deleteLater()

    def _render_curve(self, curve: dict) -> None:
        self._clear_curve_rows()
        if not curve:
            self.curve_title.setText("CURVA | aun no disponible")
            return

        self.curve_title.setText(
            f"CURVA | {curve.get('timing_label', 'CURVA MIXTA')} | coherencia {curve.get('coherence', 0):.0f}%"
        )
        for phase, value in (
            ("EARLY", curve.get("early_score", 0)),
            ("MID", curve.get("mid_score", 0)),
            ("LATE", curve.get("late_score", 0)),
        ):
            row = QHBoxLayout()
            label = QLabel(phase)
            label.setStyleSheet(
                "color:#2A4A6A; font-size:8px; font-weight:700; letter-spacing:1px; min-width:40px;"
            )
            bar = QProgressBar()
            bar.setFixedHeight(4)
            bar.setRange(0, 10)
            bar.setValue(int(value))
            bar.setTextVisible(False)
            intensity = int((float(value) / 10) * 255)
            bar.setStyleSheet(
                f"QProgressBar::chunk{{background:rgba({255-intensity},{intensity},100,200);border-radius:2px;}}"
                "QProgressBar{background:#0C1420;border:none;border-radius:2px;}"
            )
            row.addWidget(label)
            row.addWidget(bar, 1)
            self.curve_layout.addLayout(row)

        if curve.get("timing_warning"):
            warning = QLabel(curve["timing_warning"])
            warning.setWordWrap(True)
            warning.setStyleSheet("color:#FF8C00; font-size:9px; letter-spacing:0.3px;")
            self.curve_layout.addWidget(warning)

    @staticmethod
    def lerp_color(hex1: str, hex2: str, t: float) -> str:
        t = max(0.0, min(1.0, t))
        r1, g1, b1 = int(hex1[1:3], 16), int(hex1[3:5], 16), int(hex1[5:7], 16)
        r2, g2, b2 = int(hex2[1:3], 16), int(hex2[3:5], 16), int(hex2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    @classmethod
    def lerp_color_gradient(cls, score: float) -> str:
        stops = [
            (0, "#E84040"),
            (30, "#E87840"),
            (60, "#E8C840"),
            (80, "#A8E840"),
            (100, "#40E87A"),
        ]
        for index in range(len(stops) - 1):
            start_score, start_color = stops[index]
            end_score, end_color = stops[index + 1]
            if start_score <= score <= end_score:
                t = (score - start_score) / (end_score - start_score)
                return cls.lerp_color(start_color, end_color, t)
        return stops[-1][1]
