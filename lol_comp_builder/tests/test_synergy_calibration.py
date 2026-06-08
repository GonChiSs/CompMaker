from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.data_loader import load_all_champions
from logic.synergy_engine import compute_team_synergy_mode1


CHAMPS = load_all_champions(PROJECT_ROOT)


def team(*names: str) -> list[dict]:
    return [CHAMPS[name] for name in names if name in CHAMPS]


class TestPairwiseScores:
    def test_malphite_yasuo_high(self) -> None:
        result = compute_team_synergy_mode1(team("Malphite", "Yasuo"))
        assert result["total_score"] >= 75, f"Got {result['total_score']}"

    def test_kogmaw_lulu_high(self) -> None:
        result = compute_team_synergy_mode1(team("Kog'Maw", "Lulu"))
        assert result["total_score"] >= 75

    def test_rakan_xayah_high(self) -> None:
        result = compute_team_synergy_mode1(team("Rakan", "Xayah"))
        assert result["total_score"] >= 80

    def test_amumu_misfortune_high(self) -> None:
        result = compute_team_synergy_mode1(team("Amumu", "Miss Fortune"))
        assert result["total_score"] >= 75

    def test_neutral_pair_low(self) -> None:
        result = compute_team_synergy_mode1(team("Garen", "Caitlyn"))
        assert result["total_score"] <= 35

    def test_random_pair_low(self) -> None:
        result = compute_team_synergy_mode1(team("Singed", "Tristana"))
        assert result["total_score"] <= 30


class TestFullTeamScores:
    def test_wombo_combo_high(self) -> None:
        result = compute_team_synergy_mode1(
            team("Malphite", "Yasuo", "Orianna", "Amumu", "Miss Fortune")
        )
        assert result["total_score"] >= 80

    def test_protect_carry_high(self) -> None:
        result = compute_team_synergy_mode1(
            team("Kog'Maw", "Lulu", "Taric", "Ivern", "Shen")
        )
        assert result["total_score"] >= 78

    def test_samira_cc_chain_high(self) -> None:
        result = compute_team_synergy_mode1(
            team("Samira", "Nautilus", "Leona", "Malphite", "Orianna")
        )
        assert result["total_score"] >= 72

    def test_kalista_support_high(self) -> None:
        result = compute_team_synergy_mode1(
            team("Kalista", "Thresh", "Malphite", "Orianna", "Jarvan IV")
        )
        assert result["total_score"] >= 70

    def test_random_5_low(self) -> None:
        result = compute_team_synergy_mode1(
            team("Singed", "Tristana", "Veigar", "Xin Zhao", "Soraka")
        )
        assert result["total_score"] <= 40

    def test_score_rises_with_synergy(self) -> None:
        r1 = compute_team_synergy_mode1(team("Malphite", "Yasuo"))
        r2 = compute_team_synergy_mode1(team("Malphite", "Yasuo", "Orianna"))
        r3 = compute_team_synergy_mode1(team("Malphite", "Yasuo", "Orianna", "Amumu"))
        assert r2["total_score"] >= r1["total_score"] - 8, (
            f"Score dropped too much: {r1['total_score']} -> {r2['total_score']}"
        )
        assert r3["total_score"] >= r1["total_score"] - 8, (
            f"Score dropped too much: {r1['total_score']} -> {r3['total_score']}"
        )

    def test_score_does_not_drop_sharply(self) -> None:
        r1 = compute_team_synergy_mode1(team("Kog'Maw", "Lulu"))
        r5 = compute_team_synergy_mode1(team("Kog'Maw", "Lulu", "Taric", "Ivern", "Shen"))
        assert r5["total_score"] >= r1["total_score"] - 10, (
            f"Score dropped too much: {r1['total_score']} -> {r5['total_score']}"
        )


class TestNewMechanics:
    def test_ashe_seraphine(self) -> None:
        r = compute_team_synergy_mode1(team("Ashe", "Seraphine"))
        assert r["total_score"] >= 75, f"Got {r['total_score']}"

    def test_braum_caitlyn(self) -> None:
        r = compute_team_synergy_mode1(team("Braum", "Caitlyn"))
        assert r["total_score"] >= 65

    def test_braum_kog(self) -> None:
        r = compute_team_synergy_mode1(team("Braum", "Kog'Maw"))
        assert r["total_score"] >= 60

    def test_kindred_karthus(self) -> None:
        r = compute_team_synergy_mode1(team("Kindred", "Karthus"))
        assert r["total_score"] >= 75

    def test_zyra_leona(self) -> None:
        r = compute_team_synergy_mode1(team("Zyra", "Leona"))
        assert r["total_score"] >= 62

    def test_brand_alistar(self) -> None:
        r = compute_team_synergy_mode1(team("Brand", "Alistar"))
        assert r["total_score"] >= 62

    def test_yuumi_zeri(self) -> None:
        r = compute_team_synergy_mode1(team("Yuumi", "Zeri"))
        assert r["total_score"] >= 70

    def test_senna_lucian(self) -> None:
        r = compute_team_synergy_mode1(team("Senna", "Lucian"))
        assert r["total_score"] >= 70

    def test_twitch_amumu(self) -> None:
        r = compute_team_synergy_mode1(team("Twitch", "Amumu"))
        assert r["total_score"] >= 62

    def test_viktor_ashe(self) -> None:
        r = compute_team_synergy_mode1(team("Viktor", "Ashe"))
        assert r["total_score"] >= 60

    def test_bard_misfortune_anti_synergy(self) -> None:
        r = compute_team_synergy_mode1(team("Bard", "Miss Fortune"))
        assert r["total_score"] <= 35

    def test_sleep_into_burst_zoe_syndra(self) -> None:
        r = compute_team_synergy_mode1(team("Zoe", "Syndra"))
        assert r["total_score"] >= 58

    def test_kindred_karthus_orianna_5man(self) -> None:
        r = compute_team_synergy_mode1(
            team("Kindred", "Karthus", "Orianna", "Amumu", "Miss Fortune")
        )
        assert r["total_score"] >= 78

    def test_vi_ahri_pro_pick_not_treated_as_dead_pair(self) -> None:
        r = compute_team_synergy_mode1(team("Vi", "Ahri"))
        assert r["total_score"] >= 40

    def test_lucian_nami_scores_as_real_pro_duo(self) -> None:
        r = compute_team_synergy_mode1(team("Lucian", "Nami"))
        assert r["total_score"] >= 45

    def test_xin_orianna_has_meaningful_dive_value(self) -> None:
        r = compute_team_synergy_mode1(team("Xin Zhao", "Orianna"))
        assert r["total_score"] >= 38

    def test_nocturne_orianna_has_meaningful_dive_value(self) -> None:
        r = compute_team_synergy_mode1(team("Nocturne", "Orianna"))
        assert r["total_score"] >= 39

    def test_kalista_renata_is_not_scored_like_random_lane(self) -> None:
        r = compute_team_synergy_mode1(team("Kalista", "Renata Glasc"))
        assert r["total_score"] >= 40
