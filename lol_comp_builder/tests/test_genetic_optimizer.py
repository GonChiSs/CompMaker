from __future__ import annotations

import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.genetic_build_optimizer import GeneticBuildOptimizer
from logic.genetic_build_optimizer import ITEM_IDS
from logic.genetic_build_optimizer import OptimizationTarget
from logic.item_data_loader import ItemDataLoader


def _champion_stats() -> dict:
    return {
        "hp": 620.0,
        "hp_per_level": 100.0,
        "armor": 30.0,
        "armor_per_level": 4.0,
        "mr": 30.0,
        "mr_per_level": 1.3,
        "ad": 60.0,
        "ad_per_level": 3.0,
        "as_base": 0.625,
        "as_ratio": 3.0,
        "range": 550.0,
        "ms": 330.0,
        "ap_ratio": 0.7,
    }


def _optimizer_items() -> dict[int, dict]:
    return {
        3006: {"id": 3006, "name": "Berserker's Greaves", "gold": 1100, "stats": {"ms": 45, "as_bonus": 0.35}, "tags": ["Boots"], "is_mythic": False, "is_boots": True, "boots_tier": "tier2", "description": "Unique - Rage: move faster"},
        3047: {"id": 3047, "name": "Plated Steelcaps", "gold": 1200, "stats": {"ms": 45, "armor": 25}, "tags": ["Boots"], "is_mythic": False, "is_boots": True, "boots_tier": "tier2", "description": "Unique - Plating: block attacks"},
        ITEM_IDS["InfinityEdge"]: {"id": ITEM_IDS["InfinityEdge"], "name": "Infinity Edge", "gold": 3400, "stats": {"ad": 80, "crit": 0.25}, "tags": ["Damage", "CriticalStrike"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": "Unique - Perfection: crit damage"},
        ITEM_IDS["Rageblade"]: {"id": ITEM_IDS["Rageblade"], "name": "Guinsoo's Rageblade", "gold": 3000, "stats": {"ad": 30, "ap": 30, "as_bonus": 0.25}, "tags": ["Damage", "AttackSpeed"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": "Unique - Wrath: on-hit ramp"},
        ITEM_IDS["Kraken"]: {"id": ITEM_IDS["Kraken"], "name": "Kraken Slayer", "gold": 3100, "stats": {"ad": 45, "as_bonus": 0.35}, "tags": ["Damage", "AttackSpeed"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": "Unique - Bring It Down: third hit"},
        ITEM_IDS["Navori"]: {"id": ITEM_IDS["Navori"], "name": "Navori", "gold": 3200, "stats": {"ad": 60, "crit": 0.25, "ah": 15}, "tags": ["Damage", "CriticalStrike"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": "Unique - Transcendence: crit haste"},
        6333: {"id": 6333, "name": "Death's Dance", "gold": 3300, "stats": {"ad": 60, "armor": 45, "ah": 15}, "tags": ["Damage"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": "Unique - Ignore Pain: delay damage"},
        3071: {"id": 3071, "name": "Black Cleaver", "gold": 3000, "stats": {"ad": 40, "hp": 400, "ah": 20}, "tags": ["Damage"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": "Unique - Carve: shred armor"},
        3115: {"id": 3115, "name": "Nashor's Tooth", "gold": 3000, "stats": {"ap": 90, "as_bonus": 0.50}, "tags": ["SpellDamage", "AttackSpeed"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": "Unique - Icathian Bite: on-hit magic"},
        3157: {"id": 3157, "name": "Zhonya's Hourglass", "gold": 3250, "stats": {"ap": 105, "armor": 50, "ah": 15}, "tags": ["SpellDamage"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": "Unique - Stasis: untargetable"},
    }


def test_non_mid_boots_only_contribute_move_speed() -> None:
    opt = GeneticBuildOptimizer(
        items=_optimizer_items(),
        champion_stats=_champion_stats(),
        target=OptimizationTarget.PHYSICAL_DPS,
        role="bottom",
        champion_name="Ashe",
    )
    stats = opt._aggregate_stats([3047])
    base_stats = opt._champion_stats_at_level()
    assert opt.role_gets_boots_passive is False
    assert stats["ms"] > base_stats["ms"]
    assert stats["armor"] == base_stats["armor"]


def test_mid_boots_keep_full_passive_stats() -> None:
    opt = GeneticBuildOptimizer(
        items=_optimizer_items(),
        champion_stats=_champion_stats(),
        target=OptimizationTarget.MAGIC_DPS,
        role="middle",
        champion_name="Ahri",
    )
    stats = opt._aggregate_stats([3047])
    assert opt.role_gets_boots_passive is True
    assert stats["armor"] > _champion_stats()["armor"]


def test_optimizer_does_not_recommend_boots_in_math_build() -> None:
    random.seed(3)
    items = _optimizer_items()
    opt = GeneticBuildOptimizer(
        items=items,
        champion_stats=_champion_stats(),
        target=OptimizationTarget.PHYSICAL_DPS,
        role="bottom",
        champion_name="Ashe",
    )
    result = opt.run()
    assert all(not items[item_id]["is_boots"] for item_id in result.item_ids)


def test_item_loader_filters_tier1_boots_components_and_required_ally() -> None:
    loader = ItemDataLoader(PROJECT_ROOT)
    raw = {
        "data": {
            "1001": {"name": "Boots", "gold": {"total": 300, "purchasable": True}, "maps": {"11": True}, "tags": ["Boots"], "stats": {}, "depth": 1},
            "3006": {"name": "Greaves", "gold": {"total": 1100, "purchasable": True}, "maps": {"11": True}, "tags": ["Boots"], "stats": {"FlatMovementSpeedMod": 45}, "from": ["1001"], "depth": 2},
            "1036": {"name": "Long Sword", "gold": {"total": 350, "purchasable": True}, "maps": {"11": True}, "tags": ["Damage"], "stats": {"FlatPhysicalDamageMod": 10}, "depth": 1, "into": ["6672"]},
            "6665": {"name": "Ornn Item", "gold": {"total": 3000, "purchasable": True}, "maps": {"11": True}, "tags": ["Damage"], "stats": {"FlatPhysicalDamageMod": 50}, "requiredAlly": "Ornn", "depth": 3},
            "663058": {"name": "Shield of Molten Stone", "gold": {"total": 2500, "purchasable": True}, "maps": {"11": True}, "tags": ["Health", "Armor"], "stats": {"FlatHPPoolMod": 250, "FlatArmorMod": 80}},
            "6672": {"name": "Kraken", "gold": {"total": 3100, "purchasable": True}, "maps": {"11": True}, "tags": ["Damage", "AttackSpeed"], "stats": {"FlatPhysicalDamageMod": 45, "PercentAttackSpeedMod": 0.35}, "depth": 3},
        }
    }
    loader._load_json_cached = lambda *args, **kwargs: raw
    items = loader.load_items("99.1.1", force_refresh=True)

    assert 1001 not in items
    assert 1036 not in items
    assert 6665 not in items
    assert 663058 not in items
    assert 3006 in items
    assert items[3006]["boots_tier"] == "tier2"


def test_kogmaw_prefers_onhit_build_over_crit_build() -> None:
    items = _optimizer_items()
    opt = GeneticBuildOptimizer(
        items=items,
        champion_stats=_champion_stats(),
        target=OptimizationTarget.PHYSICAL_DPS,
        role="bottom",
        champion_name="Kog'Maw",
    )
    on_hit = [3006, ITEM_IDS["Rageblade"], ITEM_IDS["Kraken"], 3115, 6333, 3071]
    crit = [3006, ITEM_IDS["InfinityEdge"], ITEM_IDS["Navori"], 6333, 3071, 3157]
    assert opt._fitness(on_hit) > opt._fitness(crit)


def test_yasuo_prefers_crit_build_over_onhit_build() -> None:
    items = _optimizer_items()
    opt = GeneticBuildOptimizer(
        items=items,
        champion_stats=_champion_stats(),
        target=OptimizationTarget.PHYSICAL_DPS,
        role="middle",
        champion_name="Yasuo",
    )
    crit = [3006, ITEM_IDS["InfinityEdge"], ITEM_IDS["Navori"], 6333, 3071, 3157]
    on_hit = [3006, ITEM_IDS["Rageblade"], ITEM_IDS["Kraken"], 3115, 6333, 3071]
    assert opt._fitness(crit) > opt._fitness(on_hit)


def test_different_profiles_produce_different_optimized_builds() -> None:
    random.seed(7)
    items = _optimizer_items()
    kog = GeneticBuildOptimizer(items, _champion_stats(), OptimizationTarget.PHYSICAL_DPS, role="bottom", champion_name="Kog'Maw").run()
    random.seed(7)
    jhin = GeneticBuildOptimizer(items, _champion_stats(), OptimizationTarget.PHYSICAL_DPS, role="bottom", champion_name="Jhin").run()
    assert ITEM_IDS["Rageblade"] in kog.item_ids
    assert ITEM_IDS["InfinityEdge"] in jhin.item_ids
    assert set(kog.item_ids) != set(jhin.item_ids)


def test_redundant_unique_passives_are_rejected() -> None:
    items = _optimizer_items()
    items[4001] = {"id": 4001, "name": "Clone A", "gold": 2500, "stats": {"hp": 300}, "tags": ["Health"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": "Unique - Echo: pulse"}
    items[4002] = {"id": 4002, "name": "Clone B", "gold": 2500, "stats": {"hp": 300}, "tags": ["Health"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": "Unique - Echo: burst"}
    opt = GeneticBuildOptimizer(
        items=items,
        champion_stats=_champion_stats(),
        target=OptimizationTarget.TANK_HP,
        role="top",
        champion_name="Darius",
    )
    assert opt._has_redundant_uniques([3006, 4001, 4002, 3071, 6333, 3157]) is True
