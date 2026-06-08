from __future__ import annotations

import random

from logic.composition import ROLES
from logic.draft_recommender import get_draft_recommendations
from logic.draft_state import DraftState


def draft_state_from_enemy_perspective(draft_state: DraftState) -> DraftState:
    enemy_side = "RED" if draft_state.user_side == "BLUE" else "BLUE"
    return draft_state.clone_for_side(enemy_side)


class DraftBot:
    def __init__(self, all_champions: dict[str, dict]):
        self.all_champions = all_champions

    def choose_action(self, draft_state: DraftState) -> dict:
        enemy_state = draft_state_from_enemy_perspective(draft_state)
        _, action, _ = enemy_state.current_action()

        if action == "BAN":
            recs = get_draft_recommendations(enemy_state, self.all_champions)
            top = recs[:3] or recs[:1]
            choice = random.choices(top, weights=[0.60, 0.25, 0.15][: len(top)])[0]
            return choice["champion"]

        enemy_side = enemy_state.user_side
        enemy_picks = enemy_state.team_for_side(enemy_side)
        filled_roles = [champ.get("assigned_role") for champ in enemy_picks if champ.get("assigned_role")]
        needed_roles = [role for role in ROLES if role not in filled_roles]
        target_role = needed_roles[0] if needed_roles else None
        recs = get_draft_recommendations(enemy_state, self.all_champions, target_role=target_role)
        top = recs[:5] or recs[:1]
        choice = random.choices(top, weights=[0.55, 0.25, 0.12, 0.05, 0.03][: len(top)])[0]
        return choice["champion"]
