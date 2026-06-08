from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.composition_registry import build_pair_score_lookup
from logic.composition_registry import build_registry_meta
from logic.composition_registry import compute_mode1_score_from_pair_scores
from logic.composition_registry import count_valid_compositions
from logic.composition_registry import iter_registered_compositions
from logic.data_loader import load_all_champions
from logic.synergy_engine import compute_team_synergy_mode1


def test_registry_count_and_iteration_match_small_fixture() -> None:
    champions = {
        "A": {"name": "A", "roles": ["TOP"]},
        "B": {"name": "B", "roles": ["JUNGLE"]},
        "C": {"name": "C", "roles": ["MID"]},
        "D": {"name": "D", "roles": ["ADC"]},
        "E": {"name": "E", "roles": ["SUPPORT"]},
        "FlexTopJg": {"name": "FlexTopJg", "roles": ["TOP", "JUNGLE"]},
    }
    role_order = ("TOP", "JUNGLE", "MID", "ADC", "SUPPORT")

    count = count_valid_compositions(champions, role_order=role_order)
    compositions = list(iter_registered_compositions(champions, role_order=role_order))

    assert count == 3
    assert len(compositions) == 3
    assert compositions[0][1]["TOP"] == "A"
    assert compositions[-1][1]["TOP"] == "FlexTopJg"


def test_registry_meta_has_checksum() -> None:
    champions = load_all_champions(PROJECT_ROOT)
    meta = build_registry_meta(champions, base_dir=PROJECT_ROOT)

    assert meta.exact_composition_count > 0
    assert len(meta.registry_checksum) == 64
    assert meta.role_counts["TOP"] > 0


def test_fast_mode1_score_matches_engine_for_real_team() -> None:
    champions = load_all_champions(PROJECT_ROOT)
    names = ["Malphite", "Jarvan IV", "Orianna", "Miss Fortune", "Leona"]
    team = [champions[name] for name in names]
    pair_lookup = build_pair_score_lookup(champions)
    raw_values = []
    for index, name_a in enumerate(names):
        for name_b in names[index + 1:]:
            raw_values.append(pair_lookup[name_a][name_b])

    fast_score = compute_mode1_score_from_pair_scores(team, raw_values)
    engine_score = compute_team_synergy_mode1(team)["total_score"]

    assert fast_score == engine_score
