from __future__ import annotations

import random

from logic.composition import ROLES
from logic.synergy_engine import (
    compute_pairwise_synergy_pure,
    compute_team_synergy,
)

ARCHETYPE_NAME_ALIASES = {
    "Poke / Siege": "Poke Siege",
}

ROLE_ORDER_VARIANTS = [
    ROLES,
    ["JUNGLE", "MID", "SUPPORT", "ADC", "TOP"],
    ["MID", "JUNGLE", "TOP", "SUPPORT", "ADC"],
    ["SUPPORT", "ADC", "MID", "JUNGLE", "TOP"],
    ["ADC", "SUPPORT", "TOP", "MID", "JUNGLE"],
]


def normalize_archetype_name(archetype: str) -> str:
    return ARCHETYPE_NAME_ALIASES.get(archetype, archetype)


def _score_candidate_for_role(candidate: dict, team: list[dict], archetype: str) -> float:
    archetype = normalize_archetype_name(archetype)
    arch_score = candidate["archetype_fit"].get(archetype, 0)
    if team:
        pure_pair_scores = [compute_pairwise_synergy_pure(candidate, teammate) for teammate in team]
        pure_pair_avg = sum(pure_pair_scores) / len(pure_pair_scores)
        hypothetical_synergy = compute_team_synergy(team + [candidate])["total_score"]
    else:
        pure_pair_avg = 55.0
        hypothetical_synergy = 50.0
    pro_score = candidate["pro_tier"] * 10
    flexibility_bonus = candidate["self_sufficiency"] * 10
    return (
        (arch_score * 0.55)
        + (pure_pair_avg * 0.25)
        + (hypothetical_synergy * 0.15)
        + (pro_score * 0.03)
        + (flexibility_bonus * 0.02)
    )


def _build_team_once(
    archetype: str,
    all_champions: dict,
    randomize: bool,
    role_order: list[str] | None = None,
    candidate_pool_size: int | None = None,
) -> list[dict]:
    archetype = normalize_archetype_name(archetype)
    role_order = role_order or ROLES
    team: list[dict] = []
    used_names: list[str] = []
    picks_by_role: dict[str, dict] = {}

    for role in role_order:
        candidates = [
            champ for name, champ in all_champions.items()
            if role in champ["roles"] and name not in used_names
        ]
        scored = []
        for candidate in candidates:
            total = _score_candidate_for_role(candidate, team, archetype)
            scored.append((candidate, total))

        scored.sort(key=lambda item: item[1], reverse=True)
        default_pool_size = 12 if randomize else 4
        pool_size = min(candidate_pool_size or default_pool_size, len(scored))
        candidate_pool = scored[:pool_size]
        if randomize and candidate_pool:
            weights = [max(pool_size - index, 1) for index in range(pool_size)]
            chosen = random.choices([item[0] for item in candidate_pool], weights=weights)[0]
        else:
            chosen = candidate_pool[0][0]
        team.append(chosen)
        used_names.append(chosen["name"])
        picks_by_role[role] = chosen
    return [picks_by_role[role] for role in ROLES]


def _evaluate_team(team: list[dict], archetype: str) -> dict:
    archetype = normalize_archetype_name(archetype)
    synergy = compute_team_synergy(team)
    total_score = synergy["total_score"]
    archetype_score = synergy["archetype_scores"].get(archetype, 0.0)
    combined = (archetype_score * 0.60) + (total_score * 0.40)
    return {
        "team": team,
        "combined_score": round(combined, 3),
        "live_synergy": synergy,
        "pure_synergy": synergy,
        "archetype_score": round(archetype_score, 1),
    }


def generate_composition_catalog(
    archetype: str,
    all_champions: dict,
    limit: int = 250,
) -> list[dict]:
    archetype = normalize_archetype_name(archetype)
    target_limit = max(1, limit)
    collection_goal = target_limit + max(20, target_limit // 4)
    attempt_budget = max(target_limit * 2, 240)
    min_pool_size = 10
    max_pool_size = 20
    seen_signatures: set[tuple[str, ...]] = set()
    catalog: list[dict] = []

    best_team = _build_team_once(archetype, all_champions, randomize=False)
    best_entry = _evaluate_team(best_team, archetype)
    best_signature = tuple(champion["name"] for champion in best_team)
    seen_signatures.add(best_signature)
    catalog.append(best_entry)

    for attempt in range(attempt_budget):
        role_order = random.choice(ROLE_ORDER_VARIANTS)
        candidate_pool_size = min(max_pool_size, min_pool_size + (attempt % (max_pool_size - min_pool_size + 1)))
        team = _build_team_once(
            archetype,
            all_champions,
            randomize=True,
            role_order=role_order,
            candidate_pool_size=candidate_pool_size,
        )
        signature = tuple(champion["name"] for champion in team)
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        catalog.append(_evaluate_team(team, archetype))
        if len(catalog) >= collection_goal:
            break

    catalog.sort(key=lambda item: item["combined_score"], reverse=True)
    return catalog[:target_limit]


def generate_best_composition(archetype: str, all_champions: dict, randomize: bool = False) -> list[dict]:
    catalog_size = 64 if randomize else 1
    catalog = generate_composition_catalog(archetype, all_champions, limit=catalog_size)
    if not catalog:
        return _build_team_once(archetype, all_champions, randomize=False)
    if randomize and len(catalog) > 1:
        weighted_pool = catalog[: min(24, len(catalog))]
        weights = [max(len(weighted_pool) - index, 1) for index in range(len(weighted_pool))]
        return random.choices(weighted_pool, weights=weights)[0]["team"]
    return catalog[0]["team"]
