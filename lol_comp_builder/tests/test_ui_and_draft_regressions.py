from __future__ import annotations

import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from logic.draft_recommender import get_draft_recommendations
from logic.draft_state import DraftState
from ui.draft_mode.draft_screen import RECOMMENDATION_MODE_BOTH
from ui.draft_mode.draft_screen import RECOMMENDATION_MODE_NONE
from ui.draft_mode.draft_screen import RECOMMENDATION_MODE_STANDARD
from ui.draft_mode.draft_screen import resolve_recommendation_state_for_turn


def _load_champions() -> dict[str, dict]:
    data_path = PROJECT_ROOT / "data" / "champions_synergy.json"
    champions = json.loads(data_path.read_text(encoding="utf-8"))
    for name, payload in champions.items():
        payload.setdefault("name", name)
    return champions


def test_advanced_draft_recommendations_do_not_crash() -> None:
    champions = _load_champions()
    state = DraftState(user_side="BLUE")
    state.assign_phase()

    for champion_name in ["Aatrox", "Ahri", "Akali", "Akshan", "Alistar", "Amumu"]:
        team, action, _ = state.current_action()
        assert action == "BAN"
        state.add_ban(team, champions[champion_name])

    state.add_pick("BLUE", champions["Ashe"], "ADC")
    state.add_pick("RED", champions["Blitzcrank"], "SUPPORT")
    state.add_pick("RED", champions["Caitlyn"], "ADC")
    state.add_pick("BLUE", champions["Darius"], "TOP")
    state.add_pick("BLUE", champions["Elise"], "JUNGLE")

    recommendations = get_draft_recommendations(state, champions)

    assert recommendations
    assert all("total_score" in item for item in recommendations)


def test_recommendation_modes_switch_behavior() -> None:
    champions = _load_champions()
    state = DraftState(user_side="BLUE")
    state.assign_phase()

    assert resolve_recommendation_state_for_turn(state, RECOMMENDATION_MODE_NONE) is None

    standard_state = resolve_recommendation_state_for_turn(state, RECOMMENDATION_MODE_STANDARD)
    assert standard_state is state

    state.add_ban("BLUE", champions["Aatrox"])
    assert resolve_recommendation_state_for_turn(state, RECOMMENDATION_MODE_STANDARD) is None

    both_state = resolve_recommendation_state_for_turn(state, RECOMMENDATION_MODE_BOTH)
    assert both_state is not None
    assert both_state is not state
    assert both_state.user_side == "RED"
