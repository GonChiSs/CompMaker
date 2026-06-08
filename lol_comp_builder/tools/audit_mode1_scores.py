from __future__ import annotations

import itertools
import random
import statistics
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.data_loader import load_all_champions
from logic.synergy_engine import ICONIC_COMBOS
from logic.synergy_engine import PASSIVE_INTERACTIONS
from logic.synergy_engine import compute_pairwise_synergy_pure
from logic.synergy_engine import compute_team_synergy_mode1


def percentile(sorted_values: list[float], pct: int) -> float:
    if not sorted_values:
        return 0.0
    index = max(0, min(len(sorted_values) - 1, int((pct / 100) * len(sorted_values)) - 1))
    return sorted_values[index]


def format_pair(score: float, name_a: str, name_b: str) -> str:
    return f"{score:5.1f} | {name_a} | {name_b}"


def main() -> int:
    champions = load_all_champions(PROJECT_ROOT)
    champion_names = sorted(champions)

    pair_rows: list[tuple[float, str, str]] = []
    for name_a, name_b in itertools.combinations(champion_names, 2):
        score = compute_pairwise_synergy_pure(champions[name_a], champions[name_b])
        pair_rows.append((score, name_a, name_b))

    pair_scores = [score for score, _, _ in pair_rows]
    sorted_pair_scores = sorted(pair_scores)
    pair_rows.sort(reverse=True)

    missing_special_refs: list[tuple[str, list[str], float]] = []
    for label, mapping in (("PASSIVE", PASSIVE_INTERACTIONS), ("ICONIC", ICONIC_COMBOS)):
        for duo, value in mapping.items():
            names = sorted(duo)
            if any(name not in champions for name in names):
                missing_special_refs.append((label, names, float(value)))

    random.seed(7)
    team_scores: list[float] = []
    for _ in range(20_000):
        team = random.sample(champion_names, 5)
        result = compute_team_synergy_mode1([champions[name] for name in team])
        team_scores.append(result["total_score"])

    print("MODE1 AUDIT")
    print()
    print(f"champions: {len(champion_names)}")
    print(f"pairs: {len(pair_rows)}")
    print(f"pair avg: {statistics.mean(pair_scores):.2f}")
    print(f"pair median: {statistics.median(pair_scores):.2f}")
    print(
        "pair percentiles:"
        f" p50={percentile(sorted_pair_scores, 50):.1f}"
        f" p75={percentile(sorted_pair_scores, 75):.1f}"
        f" p90={percentile(sorted_pair_scores, 90):.1f}"
        f" p95={percentile(sorted_pair_scores, 95):.1f}"
        f" p99={percentile(sorted_pair_scores, 99):.1f}"
    )
    for threshold in (50, 60, 70, 80, 90, 95, 100):
        count = sum(1 for score in pair_scores if score >= threshold)
        print(f"pairs >= {threshold:>3}: {count:>4} ({count / len(pair_scores) * 100:.2f}%)")

    print()
    print("top 15 pairs:")
    for score, name_a, name_b in pair_rows[:15]:
        print(format_pair(score, name_a, name_b))

    print()
    print("bottom 15 non-zero pairs:")
    non_zero_pairs = [row for row in sorted(pair_rows, key=lambda row: row[0]) if row[0] > 0]
    for score, name_a, name_b in non_zero_pairs[:15]:
        print(format_pair(score, name_a, name_b))

    print()
    print(f"missing special refs: {len(missing_special_refs)}")
    for label, names, value in missing_special_refs:
        print(f"{label:7} | {value:4.1f} | {' | '.join(names)}")

    print()
    print("20k random 5-man sample:")
    print(
        f"team avg={statistics.mean(team_scores):.2f}"
        f" min={min(team_scores):.1f}"
        f" max={max(team_scores):.1f}"
    )
    for threshold in (20, 30, 40, 50, 60, 70, 80, 90, 95, 100):
        count = sum(1 for score in team_scores if score >= threshold)
        print(f"teams >= {threshold:>3}: {count:>5} ({count / len(team_scores) * 100:.2f}%)")

    return 0 if not missing_special_refs else 1


if __name__ == "__main__":
    raise SystemExit(main())
