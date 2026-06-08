from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from logic.composition import ROLES
from logic.data_loader import get_data_meta
from logic.synergy_engine import compute_mode1_signature_bonus
from logic.synergy_engine import compute_pairwise_synergy_pure


@dataclass(frozen=True)
class RegistryMeta:
    role_order: tuple[str, ...]
    role_counts: dict[str, int]
    exact_composition_count: int
    registry_checksum: str
    data_patch: str


def build_role_pools(
    champions: dict[str, dict],
    role_order: tuple[str, ...] = tuple(ROLES),
) -> dict[str, list[dict]]:
    pools: dict[str, list[dict]] = {}
    for role in role_order:
        pools[role] = sorted(
            (
                champ for champ in champions.values()
                if isinstance(champ, dict) and role in champ.get("roles", [])
            ),
            key=lambda champ: champ["name"],
        )
    return pools


def build_registry_meta(
    champions: dict[str, dict],
    base_dir: Path | None = None,
    role_order: tuple[str, ...] = tuple(ROLES),
) -> RegistryMeta:
    pools = build_role_pools(champions, role_order=role_order)
    role_counts = {role: len(pool) for role, pool in pools.items()}
    count = count_valid_compositions(champions, role_order=role_order)
    registry_payload = {
        "role_order": list(role_order),
        "role_pools": {
            role: [champ["name"] for champ in pool]
            for role, pool in pools.items()
        },
    }
    checksum = hashlib.sha256(
        json.dumps(registry_payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    data_meta = get_data_meta(base_dir) if base_dir is not None else {"patch": "unknown"}
    return RegistryMeta(
        role_order=role_order,
        role_counts=role_counts,
        exact_composition_count=count,
        registry_checksum=checksum,
        data_patch=str(data_meta.get("patch", "unknown")),
    )


def count_valid_compositions(
    champions: dict[str, dict],
    role_order: tuple[str, ...] = tuple(ROLES),
) -> int:
    role_index = {role: index for index, role in enumerate(role_order)}
    dp = [0] * (1 << len(role_order))
    dp[0] = 1

    for champion in champions.values():
        if not isinstance(champion, dict):
            continue
        masks = [
            1 << role_index[role]
            for role in champion.get("roles", [])
            if role in role_index
        ]
        if not masks:
            continue
        next_dp = dp[:]
        for state, count in enumerate(dp):
            if count == 0:
                continue
            for mask in masks:
                if state & mask:
                    continue
                next_dp[state | mask] += count
        dp = next_dp

    return dp[-1]


def iter_registered_compositions(
    champions: dict[str, dict],
    role_order: tuple[str, ...] = tuple(ROLES),
) -> Iterator[tuple[int, dict[str, str]]]:
    pools = build_role_pools(champions, role_order=role_order)
    next_id = 0

    def dfs(index: int, picks: dict[str, str], used_names: set[str]) -> Iterator[tuple[int, dict[str, str]]]:
        nonlocal next_id
        if index >= len(role_order):
            next_id += 1
            yield next_id, dict(picks)
            return

        role = role_order[index]
        for champion in pools[role]:
            name = champion["name"]
            if name in used_names:
                continue
            picks[role] = name
            used_names.add(name)
            yield from dfs(index + 1, picks, used_names)
            used_names.remove(name)
            picks.pop(role, None)

    yield from dfs(0, {}, set())


def sample_registered_compositions(
    champions: dict[str, dict],
    sample_size: int,
    seed: int = 7,
    role_order: tuple[str, ...] = tuple(ROLES),
) -> list[dict[str, str]]:
    pools = build_role_pools(champions, role_order=role_order)
    rng = random.Random(seed)
    samples: list[dict[str, str]] = []
    while len(samples) < sample_size:
        picks: dict[str, str] = {}
        used_names: set[str] = set()
        valid = True
        for role in role_order:
            candidates = [champ for champ in pools[role] if champ["name"] not in used_names]
            if not candidates:
                valid = False
                break
            champion = rng.choice(candidates)
            picks[role] = champion["name"]
            used_names.add(champion["name"])
        if valid:
            samples.append(picks)
    return samples


def build_pair_score_lookup(champions: dict[str, dict]) -> dict[str, dict[str, float]]:
    lookup: dict[str, dict[str, float]] = {}
    champion_items = sorted(champions.items())
    for name, _champion in champion_items:
        lookup.setdefault(name, {})
    for index, (name_a, champ_a) in enumerate(champion_items):
        for name_b, champ_b in champion_items[index + 1:]:
            score = compute_pairwise_synergy_pure(champ_a, champ_b)
            lookup[name_a][name_b] = score
            lookup[name_b][name_a] = score
    return lookup


def compute_mode1_score_from_pair_scores(team: list[dict], raw_values: list[float]) -> float:
    if len(raw_values) == 1:
        base = raw_values[0]
    elif len(raw_values) <= 3:
        weights = [0.50, 0.30, 0.20]
        values = sorted(raw_values, reverse=True)
        base = sum(value * weight for value, weight in zip(values, weights[:len(values)]))
    elif len(raw_values) <= 6:
        values = sorted(raw_values, reverse=True)
        tier_1 = values[:2]
        tier_2 = values[2:]
        base = ((sum(tier_1) / len(tier_1)) * 0.60) + ((sum(tier_2) / len(tier_2)) * 0.40)
    else:
        values = sorted(raw_values, reverse=True)
        tier_1 = values[:3]
        tier_2 = values[3:6]
        tier_3 = values[6:]
        base = (
            (sum(tier_1) / len(tier_1)) * 0.55
            + (sum(tier_2) / len(tier_2)) * 0.30
            + (sum(tier_3) / len(tier_3)) * 0.15
        )

    pairs_above_50 = sum(1 for value in raw_values if value >= 50)
    pairs_above_65 = sum(1 for value in raw_values if value >= 65)
    depth_bonus = min((pairs_above_50 * 2.5) + (pairs_above_65 * 4.0), 20.0)

    min_pair = min(raw_values)
    consistency_bonus = min((min_pair - 40) * 0.3, 6.0) if min_pair >= 40 else 0.0
    signature_bonus = compute_mode1_signature_bonus(team, raw_values)

    return max(
        1.0,
        min(100.0, round(base + depth_bonus + consistency_bonus + signature_bonus, 1)),
    )
