from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.synergy_engine import compute_team_synergy
from logic.synergy_engine import compute_team_synergy_mode1
from logic.synergy_engine import SynergyEngine


class SynergyEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        data_path = PROJECT_ROOT / "data" / "champions_synergy.json"
        cls.champions = json.loads(data_path.read_text(encoding="utf-8"))

    def team_score(self, names: list[str]) -> float:
        team = [self.champions[name] for name in names]
        return compute_team_synergy(team)["total_score"]

    def setUp(self) -> None:
        self.engine = SynergyEngine(self.champions)

    def test_wombo_core_scores_high(self) -> None:
        score = self.team_score(["Malphite", "Yasuo", "Orianna"])
        self.assertGreaterEqual(score, 80.0)

    def test_hypercarry_protect_scores_high(self) -> None:
        score = self.team_score(["Kog'Maw", "Lulu", "Taric"])
        self.assertGreaterEqual(score, 85.0)

    def test_unrelated_comp_scores_low(self) -> None:
        score = self.team_score(["Tryndamere", "Teemo", "Shaco", "Zed", "Draven"])
        self.assertLessEqual(score, 40.0)

    def test_generator_builds_large_unique_pool(self) -> None:
        pool = self.engine.generate_composition_pool("Wombo Combo", limit=25)
        signatures = {tuple(entry["picks"][role] for role in ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]) for entry in pool}
        self.assertGreaterEqual(len(pool), 25)
        self.assertEqual(len(pool), len(signatures))

    def test_generator_supports_ui_archetype_alias(self) -> None:
        pool = self.engine.generate_composition_pool("Poke / Siege", limit=5)
        self.assertEqual(len(pool), 5)
        self.assertTrue(all(entry["archetype_score"] >= 0 for entry in pool))

    def test_default_team_analysis_uses_mode1_total_score(self) -> None:
        team = [self.champions[name] for name in ["Vi", "Ahri", "Rell"]]
        analysis = compute_team_synergy(team)
        pure = compute_team_synergy_mode1(team)
        self.assertEqual(analysis["total_score"], pure["total_score"])

    def test_generator_entries_expose_unified_scores(self) -> None:
        pool = self.engine.generate_composition_pool("Wombo Combo", limit=3)
        self.assertTrue(all(entry["team_score"] == entry["synergy_score"] for entry in pool))


if __name__ == "__main__":
    unittest.main()
