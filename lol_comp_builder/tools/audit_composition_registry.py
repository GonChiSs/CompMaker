from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.composition import ROLES
from logic.composition_registry import build_pair_score_lookup
from logic.composition_registry import build_registry_meta
from logic.composition_registry import build_role_pools
from logic.composition_registry import compute_mode1_score_from_pair_scores
from logic.composition_registry import sample_registered_compositions
from logic.data_loader import load_all_champions


DEFAULT_AUDIT_DIR = PROJECT_ROOT / "audit"
DEFAULT_MANIFEST = DEFAULT_AUDIT_DIR / "composition_registry_manifest.json"


def _ensure_audit_dir() -> Path:
    DEFAULT_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_AUDIT_DIR


def command_manifest(args: argparse.Namespace) -> int:
    champions = load_all_champions(PROJECT_ROOT)
    meta = build_registry_meta(champions, base_dir=PROJECT_ROOT)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(PROJECT_ROOT),
        **asdict(meta),
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def command_sample(args: argparse.Namespace) -> int:
    champions = load_all_champions(PROJECT_ROOT)
    pair_lookup = build_pair_score_lookup(champions)
    samples = sample_registered_compositions(champions, sample_size=args.samples, seed=args.seed)
    scores: list[float] = []
    for picks in samples:
        team = [champions[picks[role]] for role in ROLES]
        raw_values = []
        for index, role_a in enumerate(ROLES):
            for role_b in ROLES[index + 1:]:
                raw_values.append(pair_lookup[picks[role_a]].get(picks[role_b], 0.0))
        scores.append(compute_mode1_score_from_pair_scores(team, raw_values))

    sorted_scores = sorted(scores)

    def percentile(pct: float) -> float:
        index = min(len(sorted_scores) - 1, max(0, int((pct / 100) * (len(sorted_scores) - 1))))
        return sorted_scores[index]

    payload = {
        "sample_size": len(scores),
        "mean": round(statistics.mean(scores), 2),
        "median": round(statistics.median(scores), 2),
        "min": round(sorted_scores[0], 2),
        "p10": round(percentile(10), 2),
        "p25": round(percentile(25), 2),
        "p75": round(percentile(75), 2),
        "p90": round(percentile(90), 2),
        "max": round(sorted_scores[-1], 2),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def command_recommendation_sample(args: argparse.Namespace) -> int:
    champions = load_all_champions(PROJECT_ROOT)
    pair_lookup = build_pair_score_lookup(champions)
    role_pools = build_role_pools(champions)
    full_comps = sample_registered_compositions(champions, sample_size=args.samples, seed=args.seed)

    role_top1: dict[str, Counter[str]] = {role: Counter() for role in ROLES}
    role_top5: dict[str, Counter[str]] = {role: Counter() for role in ROLES}
    role_contexts: dict[str, int] = {role: 0 for role in ROLES}

    for picks in full_comps:
        for target_role in ROLES:
            current_names = [picks[role] for role in ROLES if role != target_role]
            current_team = [champions[name] for name in current_names]
            fixed_pair_scores: list[float] = []
            for index, name_a in enumerate(current_names):
                for name_b in current_names[index + 1:]:
                    fixed_pair_scores.append(pair_lookup[name_a].get(name_b, 0.0))

            scored: list[tuple[float, str]] = []
            for candidate in role_pools[target_role]:
                candidate_name = candidate["name"]
                if candidate_name in current_names:
                    continue
                raw_values = list(fixed_pair_scores)
                for teammate_name in current_names:
                    raw_values.append(pair_lookup[candidate_name].get(teammate_name, 0.0))
                team = current_team + [candidate]
                score = compute_mode1_score_from_pair_scores(team, raw_values)
                scored.append((score, candidate_name))

            scored.sort(key=lambda item: (-item[0], item[1]))
            if not scored:
                continue

            role_contexts[target_role] += 1
            top5 = scored[:5]
            role_top1[target_role][top5[0][1]] += 1
            for _score, champion_name in top5:
                role_top5[target_role][champion_name] += 1

    summary: dict[str, dict] = {}
    for role in ROLES:
        top1_total = sum(role_top1[role].values()) or 1
        top5_total = sum(role_top5[role].values()) or 1
        top1_ranked = role_top1[role].most_common()
        top5_ranked = role_top5[role].most_common()
        top1_top10_share = sum(count for _, count in top1_ranked[:10]) / top1_total
        top5_top10_share = sum(count for _, count in top5_ranked[:10]) / top5_total
        summary[role] = {
            "contexts": role_contexts[role],
            "unique_top1_champions": len(role_top1[role]),
            "unique_top5_champions": len(role_top5[role]),
            "top1_top10_share": round(top1_top10_share * 100, 2),
            "top5_top10_share": round(top5_top10_share * 100, 2),
            "top1_leaders": [
                {
                    "champion": champion,
                    "count": count,
                    "share": round((count / top1_total) * 100, 2),
                }
                for champion, count in top1_ranked[:10]
            ],
            "top5_leaders": [
                {
                    "champion": champion,
                    "count": count,
                    "share": round((count / top5_total) * 100, 2),
                }
                for champion, count in top5_ranked[:10]
            ],
        }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sampled_full_compositions": len(full_comps),
        "sampled_recommendation_contexts": sum(role_contexts.values()),
        "mode": "mode1_pure_recommendations",
        "summary_by_role": summary,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _build_threshold_auditor(champions: dict[str, dict]) -> dict:
    role_order = ("ADC", "SUPPORT", "JUNGLE", "TOP", "MID")
    pools = build_role_pools(champions, role_order=role_order)
    pair_lookup = build_pair_score_lookup(champions)
    role_index = {role: index for index, role in enumerate(role_order)}
    name_to_tags = {name: set(champ.get("ability_tags", [])) for name, champ in champions.items()}

    role_tag_union: dict[str, set[str]] = {}
    for role, pool in pools.items():
        merged: set[str] = set()
        for champion in pool:
            merged |= name_to_tags[champion["name"]]
        role_tag_union[role] = merged

    role_pair_global_max: dict[tuple[str, str], float] = {}
    champ_to_role_max: dict[str, dict[str, dict[str, float]]] = {}
    for role in role_order:
        champ_to_role_max[role] = {}
        for champion in pools[role]:
            name = champion["name"]
            champ_to_role_max[role][name] = {}
            for other_role in role_order:
                if other_role == role:
                    continue
                max_score = 0.0
                for other in pools[other_role]:
                    if other["name"] == name:
                        continue
                    max_score = max(max_score, pair_lookup[name].get(other["name"], 0.0))
                champ_to_role_max[role][name][other_role] = max_score

    for index, role_a in enumerate(role_order):
        for role_b in role_order[index + 1:]:
            max_score = 0.0
            for champion_a in pools[role_a]:
                for champion_b in pools[role_b]:
                    if champion_a["name"] == champion_b["name"]:
                        continue
                    max_score = max(
                        max_score,
                        pair_lookup[champion_a["name"]].get(champion_b["name"], 0.0),
                    )
            role_pair_global_max[(role_a, role_b)] = max_score
            role_pair_global_max[(role_b, role_a)] = max_score

    signature_checks = [
        (lambda tags: "AOE_KNOCKUP" in tags and "KNOCKUP_BENEFICIARY" in tags, 8.0),
        (lambda tags: "HARD_ENGAGE" in tags and "AOE_FOLLOW_UP" in tags, 7.0),
        (
            lambda tags: "IMMOBILE_CARRY" in tags and any(
                tag in tags for tag in {"HARD_PEEL", "ANTI_ASSASSIN", "SHIELD"}
            ),
            7.0,
        ),
        (lambda tags: "HYPERCARRY" in tags and "BUFF_AMPLIFIER" in tags, 6.0),
        (lambda tags: "ON_HIT_SYNERGY" in tags and "ATTACK_SPEED_BUFF" in tags, 5.0),
        (
            lambda tags: "PULL" in tags and any(tag in tags for tag in {"AP_BURST", "AD_BURST", "AOE_DPS"}),
            5.0,
        ),
        (
            lambda tags: "RESET_MECHANIC" in tags and any(tag in tags for tag in {"CHAIN_CC", "AOE_STUN"}),
            5.0,
        ),
        (lambda tags: "TERRAIN_CREATION" in tags and "AOE_FOLLOW_UP" in tags, 4.0),
    ]

    def upper_bound(
        known_scores: list[float],
        missing_upper_scores: list[float],
        current_tags: set[str],
        remaining_roles: tuple[str, ...],
    ) -> float:
        possible_scores = known_scores + missing_upper_scores
        values = sorted(possible_scores, reverse=True)
        base = (
            (sum(values[:3]) / 3.0) * 0.55
            + (sum(values[3:6]) / 3.0) * 0.30
            + (sum(values[6:]) / 4.0) * 0.15
        )
        count50 = sum(1 for value in values if value >= 50)
        count65 = sum(1 for value in values if value >= 65)
        depth = min((count50 * 2.5) + (count65 * 4.0), 20.0)

        min_upper = min(values)
        consistency = min((min_upper - 40) * 0.3, 6.0) if min_upper >= 40 else 0.0

        possible_tags = set(current_tags)
        for role in remaining_roles:
            possible_tags |= role_tag_union[role]
        signature = 0.0
        for check_fn, bonus in signature_checks:
            if check_fn(possible_tags):
                signature += bonus
        standout_pairs = sum(1 for value in values if value >= 70)
        if standout_pairs >= 2:
            signature += min((standout_pairs - 1) * 2.5, 7.5)
        signature = min(signature, 24.0)
        return min(100.0, base + depth + consistency + signature)

    return {
        "role_order": role_order,
        "pools": pools,
        "pair_lookup": pair_lookup,
        "name_to_tags": name_to_tags,
        "champ_to_role_max": champ_to_role_max,
        "role_pair_global_max": role_pair_global_max,
        "upper_bound": upper_bound,
    }


def command_thresholds(args: argparse.Namespace) -> int:
    champions = load_all_champions(PROJECT_ROOT)
    auditor = _build_threshold_auditor(champions)
    role_order = auditor["role_order"]
    pools = auditor["pools"]
    pair_lookup = auditor["pair_lookup"]
    name_to_tags = auditor["name_to_tags"]
    champ_to_role_max = auditor["champ_to_role_max"]
    role_pair_global_max = auditor["role_pair_global_max"]
    upper_bound = auditor["upper_bound"]

    thresholds = sorted(set(float(value) for value in args.threshold))
    threshold_key = {value: str(int(value)) if value.is_integer() else str(value) for value in thresholds}
    counts_above = {threshold_key[value]: 0 for value in thresholds}
    counts_equal = {threshold_key[value]: 0 for value in thresholds if value == 100.0}
    leaves_visited = 0
    pruned_nodes = 0
    started = time.time()

    def dfs(
        index: int,
        selected_names: list[str],
        selected_roles: list[str],
        selected_team: list[dict],
        known_scores: list[float],
        current_tags: set[str],
    ) -> None:
        nonlocal leaves_visited, pruned_nodes
        if index >= len(role_order):
            leaves_visited += 1
            score = compute_mode1_score_from_pair_scores(selected_team, known_scores)
            for threshold in thresholds:
                key = threshold_key[threshold]
                if score > threshold:
                    counts_above[key] += 1
                if threshold == 100.0 and score >= 100.0:
                    counts_equal[key] += 1
            return

        role = role_order[index]
        remaining_roles = role_order[index + 1:]
        min_threshold = thresholds[0]
        for champion in pools[role]:
            name = champion["name"]
            if name in selected_names:
                continue

            candidate_scores = list(known_scores)
            for prev_name in selected_names:
                candidate_scores.append(pair_lookup[prev_name].get(name, 0.0))

            optimistic_missing: list[float] = []
            combined_roles = selected_roles + [role]
            combined_names = selected_names + [name]
            for prev_role, prev_name in zip(combined_roles, combined_names):
                for pending_role in remaining_roles:
                    optimistic_missing.append(champ_to_role_max[prev_role][prev_name][pending_role])
            for pending_index, role_a in enumerate(remaining_roles):
                for role_b in remaining_roles[pending_index + 1:]:
                    optimistic_missing.append(role_pair_global_max[(role_a, role_b)])

            optimistic = upper_bound(
                candidate_scores,
                optimistic_missing,
                current_tags | name_to_tags[name],
                remaining_roles,
            )
            if optimistic <= min_threshold:
                pruned_nodes += 1
                continue

            dfs(
                index + 1,
                selected_names + [name],
                combined_roles,
                selected_team + [champion],
                candidate_scores,
                current_tags | name_to_tags[name],
            )

    dfs(0, [], [], [], [], set())
    meta = build_registry_meta(champions, base_dir=PROJECT_ROOT, role_order=tuple(ROLES))
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registry_checksum": meta.registry_checksum,
        "exact_composition_count": meta.exact_composition_count,
        "thresholds": thresholds,
        "counts_strictly_above": counts_above,
        "counts_equal": counts_equal,
        "leaves_visited_exactly": leaves_visited,
        "pruned_nodes": pruned_nodes,
        "elapsed_seconds": round(time.time() - started, 2),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Registro y auditoria interna de todas las composiciones validas por rol."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest_parser = subparsers.add_parser(
        "manifest",
        help="Genera el manifiesto exacto del universo de composiciones validas.",
    )
    manifest_parser.add_argument("--out", default=str(DEFAULT_MANIFEST))
    manifest_parser.set_defaults(func=command_manifest)

    sample_parser = subparsers.add_parser(
        "sample",
        help="Saca una estimacion rapida de distribucion con muestreo reproducible.",
    )
    sample_parser.add_argument("--samples", type=int, default=20000)
    sample_parser.add_argument("--seed", type=int, default=7)
    sample_parser.set_defaults(func=command_sample)

    threshold_parser = subparsers.add_parser(
        "thresholds",
        help="Cuenta exactamente cuantas composiciones superan umbrales altos usando poda.",
    )
    threshold_parser.add_argument(
        "--threshold",
        type=float,
        action="append",
        required=True,
        help="Umbral estricto para el conteo. Repite la opcion para varios cortes.",
    )
    threshold_parser.set_defaults(func=command_thresholds)

    recommendation_parser = subparsers.add_parser(
        "recommendation-sample",
        help="Audita la concentracion de recomendaciones del Modo 1 por rol sobre una muestra reproducible.",
    )
    recommendation_parser.add_argument("--samples", type=int, default=10000)
    recommendation_parser.add_argument("--seed", type=int, default=7)
    recommendation_parser.set_defaults(func=command_recommendation_sample)

    return parser


def main() -> int:
    _ensure_audit_dir()
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
