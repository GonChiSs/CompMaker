from __future__ import annotations

from collections.abc import Iterable


DEFAULT_CURVE = {
    "early": 5.0,
    "mid": 5.0,
    "late": 5.0,
    "peak": "mid",
}

CURVE_HINTS = {
    "EARLY_GAME": {"early": 9.0, "mid": 6.0, "late": 3.0, "peak": "early"},
    "MID_GAME_SPIKE": {"early": 6.0, "mid": 9.0, "late": 5.0, "peak": "mid"},
    "LATE_GAME": {"early": 3.0, "mid": 6.0, "late": 9.0, "peak": "late"},
    "HYPERCARRY": {"early": 2.0, "mid": 5.0, "late": 10.0, "peak": "late"},
    "SCALING": {"early": 3.0, "mid": 6.0, "late": 8.0, "peak": "late"},
    "LANE_BULLY": {"early": 8.0, "mid": 6.0, "late": 4.0, "peak": "early"},
    "ROAM_THREAT": {"early": 7.0, "mid": 7.0, "late": 4.0, "peak": "early"},
    "PICK_POTENTIAL": {"early": 6.0, "mid": 8.0, "late": 5.0, "peak": "mid"},
    "TEAMFIGHT_SCALING": {"early": 4.0, "mid": 7.0, "late": 8.0, "peak": "late"},
}


def _average(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def get_curve(champion_name: str, ability_tags: list[str] | None = None) -> dict[str, float | str]:
    tags = set(ability_tags or [])
    matches = [CURVE_HINTS[tag] for tag in tags if tag in CURVE_HINTS]
    if not matches:
        return dict(DEFAULT_CURVE)

    early = _average(match["early"] for match in matches)
    mid = _average(match["mid"] for match in matches)
    late = _average(match["late"] for match in matches)
    phase_scores = {"early": early, "mid": mid, "late": late}
    peak = max(phase_scores, key=phase_scores.get)
    return {
        "early": round(early, 1),
        "mid": round(mid, 1),
        "late": round(late, 1),
        "peak": peak,
    }


def evaluate_team_curve(team: list[dict]) -> dict:
    if not team:
        return {
            "dominant_phase": "unknown",
            "early_score": 5.0,
            "mid_score": 5.0,
            "late_score": 5.0,
            "coherence": 50.0,
            "timing_label": "CURVA MIXTA",
            "timing_warning": None,
        }

    curves = [get_curve(champ.get("name", ""), champ.get("ability_tags", [])) for champ in team]
    early = _average(curve["early"] for curve in curves)
    mid = _average(curve["mid"] for curve in curves)
    late = _average(curve["late"] for curve in curves)

    phase_scores = {"early": early, "mid": mid, "late": late}
    dominant_phase = max(phase_scores, key=phase_scores.get)
    peak_count = sum(1 for curve in curves if curve["peak"] == dominant_phase)
    coherence = round((peak_count / len(curves)) * 100, 1)

    labels = {
        "early": "DOMINIO TEMPRANO (0-15 min)",
        "mid": "SPIKE DE MID GAME (15-25 min)",
        "late": "ESCALA AL LATE (25+ min)",
    }
    warning = None
    early_heavy = sum(1 for curve in curves if curve["peak"] == "early")
    late_heavy = sum(1 for curve in curves if curve["peak"] == "late")
    if early_heavy >= 2 and late_heavy >= 2:
        warning = "Conflicto de curva: la compo mezcla picos de early y late sin ventana clara."
    elif dominant_phase == "early" and late >= 7.5:
        warning = "Hay carries de escala en una compo de early; si no snowballea, pierde timing."
    elif dominant_phase == "late" and early <= 4.5:
        warning = "La compo escala bien, pero cede demasiada presion en los primeros minutos."

    return {
        "dominant_phase": dominant_phase,
        "early_score": round(early, 1),
        "mid_score": round(mid, 1),
        "late_score": round(late, 1),
        "coherence": coherence,
        "timing_label": labels.get(dominant_phase, "CURVA MIXTA"),
        "timing_warning": warning,
    }
