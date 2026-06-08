from __future__ import annotations

from logic.draft_state import DraftState
from logic.synergy_engine import compute_gap_filling_bonus
from logic.synergy_engine import compute_team_synergy_mode1


def compute_matchup_score(candidate: dict, enemy_team: list[dict]) -> float:
    score = 50.0
    for enemy in enemy_team:
        if enemy["name"] in candidate.get("counters", []):
            score += 8
        if enemy["name"] in candidate.get("countered_by", []):
            score -= 10

    enemy_tags = [tag for enemy in enemy_team for tag in enemy.get("ability_tags", [])]
    enemy_archetype_map = {
        "BEATS_ENGAGE": ["HARD_ENGAGE", "AOE_KNOCKUP", "DIVE_ENGAGE"],
        "BEATS_POKE": ["POKE_DAMAGE", "LONG_RANGE_POKE", "SIEGE_DAMAGE"],
        "BEATS_ASSASSIN": ["ASSASSIN", "BURST", "HIGH_MOBILITY"],
        "BEATS_TANK": ["TANK", "DAMAGE_REDUCTION", "HIGH_BASE_STATS"],
        "BEATS_SPLIT": ["SPLIT_PUSH_THREAT", "DUELIST"],
        "BEATS_HYPERCARRY": ["HYPERCARRY", "IMMOBILE_CARRY"],
        "BEATS_DISENGAGE": ["DISENGAGE", "KNOCKBACK_PEEL", "ANTI_ASSASSIN"],
    }

    for counter_tag in candidate.get("counter_tags", []):
        relevant_enemy_tags = enemy_archetype_map.get(counter_tag, [])
        hits = sum(1 for tag in enemy_tags if tag in relevant_enemy_tags)
        score += hits * 5

    for enemy in enemy_team:
        blocked_by_enemy = len(
            set(candidate.get("synergy_keys", {}).get("countered_by_tags", []))
            & set(enemy.get("ability_tags", []))
        )
        score -= blocked_by_enemy * 4

    return max(0.0, min(100.0, score))


def compute_flex_value(candidate: dict, draft_state: DraftState) -> float:
    score = 0.0
    picks_so_far = len(draft_state.ally_team())

    if picks_so_far <= 2:
        role_count = len(candidate.get("roles", []))
        score += max(role_count - 1, 0) * 6

        high_arch = sum(1 for value in candidate.get("archetype_fit", {}).values() if value >= 65)
        score += high_arch * 4

        score += candidate.get("pro_tier", 5) * 1.5

        win_condition_hiders = {
            "Orianna", "Azir", "Viktor", "Syndra",
            "Camille", "Kennen", "Jayce", "Gnar",
            "Graves", "Kindred", "Nidalee", "Taliyah",
            "Ashe", "Ezreal", "Lucian", "Varus",
            "Thresh", "Nautilus", "Karma", "Rakan",
        }
        if candidate.get("name") in win_condition_hiders:
            score += 8
    else:
        ally_team = draft_state.ally_team()
        enemy_team = draft_state.enemy_team()
        all_ally_tags = [tag for champ in ally_team for tag in champ.get("ability_tags", [])]

        score += compute_gap_filling_bonus(candidate, ally_team) * 0.25

        waiting_combos = {
            ("AOE_KNOCKUP", "KNOCKUP_BENEFICIARY"): 10,
            ("HARD_ENGAGE", "AOE_FOLLOW_UP"): 8,
            ("IMMOBILE_CARRY", "PEEL"): 7,
            ("HYPERCARRY", "BUFF_AMPLIFIER"): 9,
            ("PULL", "AP_BURST"): 8,
        }
        candidate_tags = set(candidate.get("ability_tags", []))
        for (tag_a, tag_b), bonus in waiting_combos.items():
            ally_has_a = tag_a in all_ally_tags
            ally_has_b = tag_b in all_ally_tags
            if (ally_has_a and tag_b in candidate_tags) or (ally_has_b and tag_a in candidate_tags):
                score += bonus

        for enemy in enemy_team:
            if enemy.get("name", "") in candidate.get("counters", []):
                score += 6

    return min(score, 30.0)


def compute_ban_priority(candidate: dict, ally_team: list[dict], enemy_team: list[dict]) -> float:
    score = candidate.get("pro_tier", 0) * 8
    for ally in ally_team:
        if ally["name"] in candidate.get("counters", []):
            score += 12
        dangerous_vs_us = 0
        for tag in ally.get("ability_tags", []):
            mapped = {
                "HARD_ENGAGE": "BEATS_ENGAGE",
                "AOE_KNOCKUP": "BEATS_ENGAGE",
                "POKE_DAMAGE": "BEATS_POKE",
                "LONG_RANGE_POKE": "BEATS_POKE",
                "SPLIT_PUSH_THREAT": "BEATS_SPLIT",
                "HYPERCARRY": "BEATS_HYPERCARRY",
                "IMMOBILE_CARRY": "BEATS_HYPERCARRY",
                "DISENGAGE": "BEATS_DISENGAGE",
            }.get(tag)
            if mapped and mapped in candidate.get("counter_tags", []):
                dangerous_vs_us += 1
        score += dangerous_vs_us * 5

    if enemy_team:
        hyp_enemy = compute_team_synergy_mode1(enemy_team + [candidate])
        score += (hyp_enemy["total_score"] - 50) * 0.3

    return min(score, 100)


def generate_pick_reason(candidate, allies, enemies, syn_score, match_score) -> str:
    reasons = []
    if syn_score > 70:
        reasons.append(f"Alta sinergia con el equipo ({syn_score:.0f}/100)")
    if match_score > 65:
        reasons.append(f"Buen matchup vs rival ({match_score:.0f}/100)")
    if match_score < 40:
        reasons.append(f"Matchup dificil ({match_score:.0f}/100)")
    for enemy in enemies:
        if enemy["name"] in candidate.get("counters", []):
            reasons.append(f"Contrarresta a {enemy['name']}")
            break
    if len(candidate.get("roles", [])) >= 2:
        reasons.append(f"Flex pick ({'/'.join(candidate['roles'])})")
    return " · ".join(reasons[:2]) if reasons else "Buen pick general"


def generate_ban_reason(candidate, enemy_team) -> str:
    if candidate.get("pro_tier", 0) >= 9:
        return "Campeon de altisima prioridad en el meta"
    for ally in enemy_team:
        if ally["name"] in candidate.get("counters", []):
            return f"Contrarresta a {ally['name']} del rival"
    return "Alta presencia en drafts profesionales"


def get_draft_recommendations(
    draft_state: DraftState,
    all_champions: dict,
    target_role: str | None = None,
) -> list[dict]:
    _, action, _ = draft_state.current_action()
    is_ban_turn = action == "BAN"
    unavailable = draft_state.get_unavailable()
    ally_team = draft_state.ally_team()
    enemy_team = draft_state.enemy_team()
    filled_ally_roles = set(draft_state.filled_roles_for_side(draft_state.user_side))
    enemy_side = "RED" if draft_state.user_side == "BLUE" else "BLUE"
    filled_enemy_roles = set(draft_state.filled_roles_for_side(enemy_side))

    candidates = [
        champion
        for name, champion in all_champions.items()
        if name not in unavailable
        and (target_role is None or target_role in champion.get("roles", []))
        and (
            not is_ban_turn
            or any(role not in filled_enemy_roles for role in champion.get("roles", []))
            or not filled_enemy_roles
        )
        and (
            is_ban_turn
            or any(role not in filled_ally_roles for role in champion.get("roles", []))
            or not filled_ally_roles
        )
    ]

    scored = []
    for candidate in candidates:
        if is_ban_turn:
            ban_score = compute_ban_priority(candidate, ally_team, enemy_team)
            scored.append(
                {
                    "champion": candidate,
                    "total_score": round(ban_score, 1),
                    "synergy_score": 0.0,
                    "matchup_score": round(ban_score, 1),
                    "flex_score": 0.0,
                    "reason": generate_ban_reason(candidate, enemy_team),
                }
            )
            continue

        if ally_team:
            syn_result = compute_team_synergy_mode1(ally_team + [candidate])
            syn_score = syn_result["total_score"]
        else:
            syn_score = candidate.get("pro_tier", 0) * 10

        match_score = compute_matchup_score(candidate, enemy_team)
        flex_score = compute_flex_value(candidate, draft_state)

        picks_so_far = len(ally_team)
        syn_weight = 0.25 + (picks_so_far * 0.10)
        match_weight = 0.45 - (picks_so_far * 0.05)
        flex_weight = 0.30 - (picks_so_far * 0.05)

        total = (
            (syn_score * syn_weight)
            + (match_score * match_weight)
            + (flex_score * flex_weight)
        )
        scored.append(
            {
                "champion": candidate,
                "total_score": round(total, 1),
                "synergy_score": round(syn_score, 1),
                "matchup_score": round(match_score, 1),
                "flex_score": round(flex_score, 1),
                "reason": generate_pick_reason(
                    candidate, ally_team, enemy_team, syn_score, match_score
                ),
            }
        )

    scored.sort(key=lambda item: item["total_score"], reverse=True)
    return scored[:10]
