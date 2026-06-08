from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.data_loader import DEFAULT_ROLE_MAP

ARCHETYPES = [
    "Wombo Combo",
    "Engage Teamfight",
    "Poke Siege",
    "Split Push",
    "Pick Comp",
    "Hypercarry Protect",
    "Disengage",
    "Skirmish",
]

DEFAULT_ARCHETYPE_FIT = {name: 20 for name in ARCHETYPES}


def fit(**kwargs: int) -> dict[str, int]:
    data = dict(DEFAULT_ARCHETYPE_FIT)
    data.update(kwargs)
    return data


PROFILES = {
    "engage_tank": {
        "damage_type": ["AP"],
        "mobility": 3,
        "range_type": "MELEE",
        "ability_tags": [
            "HARD_ENGAGE", "AOE_STUN", "PEEL", "DAMAGE_REDUCTION", "WAVECLEAR",
            "OBJECTIVE_CONTROL", "LOW_MOBILITY"
        ],
        "synergy_keys": {
            "enables": ["AOE_FOLLOW_UP", "RESET_MECHANIC", "SHORT_RANGE_DPS"],
            "requires": [],
            "amplifies": ["IMMOBILE_CARRY", "KNOCKUP_BENEFICIARY"],
            "countered_by_tags": ["DISENGAGE", "LONG_RANGE_POKE", "SPLIT_PUSH_THREAT"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 75, "Engage Teamfight": 92, "Poke Siege": 25,
               "Split Push": 15, "Pick Comp": 55, "Hypercarry Protect": 50,
               "Disengage": 35, "Skirmish": 40}
        ),
        "pro_tier": 7,
        "self_sufficiency": 5,
    },
    "diver_ad": {
        "damage_type": ["AD"],
        "mobility": 4,
        "range_type": "MELEE",
        "ability_tags": [
            "DIVE_ENGAGE", "AD_BURST", "SINGLE_TARGET_DPS", "DASH",
            "EARLY_GAME_POWER", "ROAM_THREAT", "OBJECTIVE_CONTROL"
        ],
        "synergy_keys": {
            "enables": ["AOE_FOLLOW_UP", "CHAIN_CC", "RESET_MECHANIC"],
            "requires": [],
            "amplifies": ["SHORT_RANGE_DPS", "MOBILE_CARRY"],
            "countered_by_tags": ["HARD_PEEL", "DISENGAGE", "LONG_RANGE_POKE"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 55, "Engage Teamfight": 78, "Poke Siege": 20,
               "Split Push": 35, "Pick Comp": 72, "Hypercarry Protect": 20,
               "Disengage": 15, "Skirmish": 82}
        ),
        "pro_tier": 7,
        "self_sufficiency": 7,
    },
    "assassin": {
        "damage_type": ["AD"],
        "mobility": 5,
        "range_type": "MELEE",
        "ability_tags": [
            "AD_BURST", "EXECUTE", "HIGH_MOBILITY", "DASH", "STEALTH",
            "ROAM_THREAT", "EARLY_GAME_POWER"
        ],
        "synergy_keys": {
            "enables": ["RESET_MECHANIC", "CHAIN_CC"],
            "requires": ["POINT_AND_CLICK_CC", "SINGLE_STUN"],
            "amplifies": ["ROAM_THREAT", "DAMAGE_AMPLIFY_DEBUFF"],
            "countered_by_tags": ["PEEL", "ANTI_ASSASSIN", "POINT_AND_CLICK_CC"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 18, "Engage Teamfight": 30, "Poke Siege": 15,
               "Split Push": 55, "Pick Comp": 92, "Hypercarry Protect": 5,
               "Disengage": 10, "Skirmish": 86}
        ),
        "pro_tier": 7,
        "self_sufficiency": 8,
    },
    "ap_mage": {
        "damage_type": ["AP"],
        "mobility": 2,
        "range_type": "RANGED",
        "ability_tags": [
            "AP_BURST", "WAVECLEAR", "POKE_DAMAGE", "LONG_RANGE_POKE",
            "LOW_MOBILITY", "SKILLSHOT_CC", "OBJECTIVE_CONTROL"
        ],
        "synergy_keys": {
            "enables": ["CHAIN_CC", "AOE_FOLLOW_UP"],
            "requires": ["HARD_ENGAGE"],
            "amplifies": ["IMMOBILE_CARRY", "SHORT_RANGE_DPS"],
            "countered_by_tags": ["DIVE_ENGAGE", "HIGH_MOBILITY", "SPELL_SHIELD"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 45, "Engage Teamfight": 55, "Poke Siege": 82,
               "Split Push": 18, "Pick Comp": 58, "Hypercarry Protect": 28,
               "Disengage": 34, "Skirmish": 42}
        ),
        "pro_tier": 7,
        "self_sufficiency": 5,
    },
    "aoe_mage": {
        "damage_type": ["AP"],
        "mobility": 2,
        "range_type": "RANGED",
        "ability_tags": [
            "AP_BURST", "AOE_DPS", "AOE_FOLLOW_UP", "WAVECLEAR",
            "AOE_STUN", "LOW_MOBILITY", "OBJECTIVE_CONTROL"
        ],
        "synergy_keys": {
            "enables": ["RESET_MECHANIC", "CHAIN_CC"],
            "requires": ["HARD_ENGAGE", "AOE_KNOCKUP"],
            "amplifies": ["IMMOBILE_CARRY", "SHORT_RANGE_DPS"],
            "countered_by_tags": ["DISENGAGE", "LONG_RANGE_POKE", "SPLIT_PUSH_THREAT"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 88, "Engage Teamfight": 80, "Poke Siege": 45,
               "Split Push": 10, "Pick Comp": 35, "Hypercarry Protect": 25,
               "Disengage": 20, "Skirmish": 30}
        ),
        "pro_tier": 8,
        "self_sufficiency": 4,
    },
    "marksman_hyper": {
        "damage_type": ["AD"],
        "mobility": 2,
        "range_type": "RANGED",
        "ability_tags": [
            "HYPERCARRY", "LATE_GAME_SCALE", "SINGLE_TARGET_DPS",
            "IMMOBILE_CARRY", "OBJECTIVE_DAMAGE", "LOW_MOBILITY"
        ],
        "synergy_keys": {
            "enables": [],
            "requires": ["PEEL", "SHIELD", "HEAL"],
            "amplifies": ["ATTACK_SPEED_BUFF", "BUFF_AMPLIFIER", "SPEED_BOOST_ALLY"],
            "countered_by_tags": ["DIVE_ENGAGE", "POINT_AND_CLICK_CC", "STEALTH"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 30, "Engage Teamfight": 48, "Poke Siege": 45,
               "Split Push": 20, "Pick Comp": 15, "Hypercarry Protect": 95,
               "Disengage": 58, "Skirmish": 35}
        ),
        "pro_tier": 8,
        "self_sufficiency": 4,
    },
    "marksman_poke": {
        "damage_type": ["AD"],
        "mobility": 3,
        "range_type": "RANGED",
        "ability_tags": [
            "POKE_DAMAGE", "LONG_RANGE_POKE", "SIEGE_DAMAGE",
            "SINGLE_TARGET_DPS", "OBJECTIVE_DAMAGE", "SELF_PEEL_CARRY"
        ],
        "synergy_keys": {
            "enables": ["POINT_AND_CLICK_CC"],
            "requires": ["PEEL"],
            "amplifies": ["DISENGAGE", "VISION_CONTROL"],
            "countered_by_tags": ["DIVE_ENGAGE", "HARD_ENGAGE", "HIGH_MOBILITY"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 20, "Engage Teamfight": 35, "Poke Siege": 92,
               "Split Push": 15, "Pick Comp": 52, "Hypercarry Protect": 55,
               "Disengage": 50, "Skirmish": 38}
        ),
        "pro_tier": 7,
        "self_sufficiency": 6,
    },
    "enchanter": {
        "damage_type": ["AP"],
        "mobility": 2,
        "range_type": "RANGED",
        "ability_tags": [
            "PEEL", "SOFT_PEEL", "SHIELD", "HEAL", "ANTI_ASSASSIN",
            "EMPOWERED_ALLY", "BUFF_AMPLIFIER"
        ],
        "synergy_keys": {
            "enables": ["HYPERCARRY", "ON_HIT_SYNERGY", "CRIT_SYNERGY"],
            "requires": ["IMMOBILE_CARRY"],
            "amplifies": ["MOBILE_CARRY", "LATE_GAME_SCALE", "ATTACK_SPEED_BUFF"],
            "countered_by_tags": ["HARD_ENGAGE", "AOE_DPS", "SUPPRESSION"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 25, "Engage Teamfight": 32, "Poke Siege": 38,
               "Split Push": 20, "Pick Comp": 10, "Hypercarry Protect": 96,
               "Disengage": 84, "Skirmish": 42}
        ),
        "pro_tier": 8,
        "self_sufficiency": 3,
    },
    "catcher": {
        "damage_type": ["AP"],
        "mobility": 3,
        "range_type": "RANGED",
        "ability_tags": [
            "POINT_AND_CLICK_CC", "SKILLSHOT_CC", "PULL", "ROAM_THREAT",
            "VISION_CONTROL", "SINGLE_STUN", "SOFT_ENGAGE"
        ],
        "synergy_keys": {
            "enables": ["EXECUTE", "AD_BURST", "AP_BURST"],
            "requires": [],
            "amplifies": ["STEALTH", "ROAM_THREAT"],
            "countered_by_tags": ["DISENGAGE", "SPELL_SHIELD", "MOBILE_CARRY"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 28, "Engage Teamfight": 48, "Poke Siege": 35,
               "Split Push": 10, "Pick Comp": 94, "Hypercarry Protect": 26,
               "Disengage": 30, "Skirmish": 55}
        ),
        "pro_tier": 7,
        "self_sufficiency": 5,
    },
    "split_duelist": {
        "damage_type": ["AD"],
        "mobility": 4,
        "range_type": "MELEE",
        "ability_tags": [
            "SPLIT_PUSH_THREAT", "SINGLE_TARGET_DPS", "SHORT_RANGE_DPS",
            "DASH", "EARLY_GAME_POWER", "TOWER_SHRED"
        ],
        "synergy_keys": {
            "enables": ["GLOBAL_PRESENCE"],
            "requires": ["TELEPORT_SYNERGY"],
            "amplifies": ["GLOBAL_PRESENCE", "WAVECLEAR"],
            "countered_by_tags": ["HARD_ENGAGE", "AOE_KNOCKUP", "POINT_AND_CLICK_CC"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 12, "Engage Teamfight": 20, "Poke Siege": 18,
               "Split Push": 95, "Pick Comp": 45, "Hypercarry Protect": 10,
               "Disengage": 12, "Skirmish": 80}
        ),
        "pro_tier": 7,
        "self_sufficiency": 9,
    },
    "bruiser_skirmish": {
        "damage_type": ["AD"],
        "mobility": 3,
        "range_type": "MELEE",
        "ability_tags": [
            "SINGLE_TARGET_DPS", "EARLY_GAME_POWER", "MID_GAME_SPIKE",
            "DIVE_ENGAGE", "SUSTAIN", "OBJECTIVE_CONTROL"
        ],
        "synergy_keys": {
            "enables": ["CHAIN_CC", "AOE_FOLLOW_UP"],
            "requires": [],
            "amplifies": ["SPEED_BOOST_ALLY", "HEAL"],
            "countered_by_tags": ["LONG_RANGE_POKE", "KNOCKBACK_PEEL", "DISENGAGE"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 35, "Engage Teamfight": 62, "Poke Siege": 12,
               "Split Push": 58, "Pick Comp": 48, "Hypercarry Protect": 20,
               "Disengage": 15, "Skirmish": 88}
        ),
        "pro_tier": 6,
        "self_sufficiency": 8,
    },
}


OVERRIDES = {
    "Malphite": {
        "roles": ["TOP", "SUPPORT"],
        "damage_type": ["AP"],
        "mobility": 2,
        "range_type": "MELEE",
        "ability_tags": [
            "AOE_KNOCKUP", "HARD_ENGAGE", "PEEL", "POINT_AND_CLICK_CC",
            "AOE_STUN", "IMMOBILE", "DAMAGE_REDUCTION"
        ],
        "synergy_keys": {
            "enables": ["KNOCKUP_BENEFICIARY", "AOE_FOLLOW_UP", "RESET_MECHANIC"],
            "requires": [],
            "amplifies": ["IMMOBILE_CARRY", "SHORT_RANGE_DPS"],
            "countered_by_tags": ["SPLIT_PUSH_THREAT", "DISENGAGE", "LONG_RANGE_POKE"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 95, "Engage Teamfight": 90, "Poke Siege": 20,
               "Split Push": 10, "Pick Comp": 35, "Hypercarry Protect": 60,
               "Disengage": 30, "Skirmish": 15}
        ),
        "pro_tier": 8,
        "self_sufficiency": 4,
    },
    "Yasuo": {
        "profile": "split_duelist",
        "damage_type": ["AD"],
        "ability_tags": [
            "KNOCKUP_BENEFICIARY", "SINGLE_TARGET_DPS", "DASH", "WIND_WALL",
            "CRIT_SYNERGY", "MOBILE_CARRY", "MID_GAME_SPIKE"
        ],
        "synergy_keys": {
            "enables": ["CHAIN_CC"],
            "requires": ["AOE_KNOCKUP", "SINGLE_KNOCKUP"],
            "amplifies": ["HARD_ENGAGE", "SPEED_BOOST_ALLY"],
            "countered_by_tags": ["POINT_AND_CLICK_CC", "ANTI_ASSASSIN", "DISENGAGE"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 97, "Engage Teamfight": 74, "Poke Siege": 10,
               "Split Push": 70, "Pick Comp": 38, "Hypercarry Protect": 18,
               "Disengage": 8, "Skirmish": 80}
        ),
        "pro_tier": 8,
        "self_sufficiency": 7,
    },
    "Orianna": {
        "profile": "aoe_mage",
        "ability_tags": [
            "AP_BURST", "AOE_FOLLOW_UP", "WAVECLEAR", "SHIELD",
            "AOE_STUN", "LOW_MOBILITY", "COMBO_EXTENDER"
        ],
        "synergy_keys": {
            "enables": ["AOE_FOLLOW_UP", "CHAIN_CC"],
            "requires": ["HARD_ENGAGE", "DIVE_ENGAGE"],
            "amplifies": ["IMMOBILE_CARRY", "SHORT_RANGE_DPS"],
            "countered_by_tags": ["DISENGAGE", "HIGH_MOBILITY", "LONG_RANGE_POKE"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 94, "Engage Teamfight": 86, "Poke Siege": 58,
               "Split Push": 12, "Pick Comp": 40, "Hypercarry Protect": 62,
               "Disengage": 28, "Skirmish": 38}
        ),
        "pro_tier": 9,
        "self_sufficiency": 5,
    },
    "Kog'Maw": {
        "profile": "marksman_hyper",
        "ability_tags": [
            "HYPERCARRY", "ON_HIT_SYNERGY", "LATE_GAME_SCALE",
            "IMMOBILE_CARRY", "LONG_RANGE_POKE", "OBJECTIVE_DAMAGE"
        ],
        "synergy_keys": {
            "enables": [],
            "requires": ["PEEL", "SHIELD", "HEAL", "ATTACK_SPEED_BUFF"],
            "amplifies": ["BUFF_AMPLIFIER", "SPEED_BOOST_ALLY", "ANTI_ASSASSIN"],
            "countered_by_tags": ["DIVE_ENGAGE", "STEALTH", "POINT_AND_CLICK_CC"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 24, "Engage Teamfight": 45, "Poke Siege": 60,
               "Split Push": 8, "Pick Comp": 10, "Hypercarry Protect": 99,
               "Disengage": 78, "Skirmish": 30}
        ),
        "pro_tier": 8,
        "self_sufficiency": 3,
    },
    "Lulu": {
        "profile": "enchanter",
        "ability_tags": [
            "PEEL", "HARD_PEEL", "SHIELD", "EMPOWERED_ALLY",
            "ATTACK_SPEED_BUFF", "ANTI_ASSASSIN", "BUFF_AMPLIFIER"
        ],
        "synergy_keys": {
            "enables": ["HYPERCARRY", "ON_HIT_SYNERGY", "CRIT_SYNERGY"],
            "requires": ["IMMOBILE_CARRY"],
            "amplifies": ["MOBILE_CARRY", "LATE_GAME_SCALE", "SHORT_RANGE_DPS"],
            "countered_by_tags": ["AOE_DPS", "SUPPRESSION", "LONG_RANGE_POKE"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 18, "Engage Teamfight": 25, "Poke Siege": 35,
               "Split Push": 12, "Pick Comp": 8, "Hypercarry Protect": 99,
               "Disengage": 85, "Skirmish": 35}
        ),
        "pro_tier": 9,
        "self_sufficiency": 3,
    },
    "Taric": {
        "profile": "enchanter",
        "range_type": "MELEE",
        "mobility": 1,
        "ability_tags": [
            "PEEL", "HARD_PEEL", "HEAL", "SHIELD", "INVULNERABILITY",
            "ANTI_ASSASSIN", "POINT_AND_CLICK_CC"
        ],
        "synergy_keys": {
            "enables": ["HYPERCARRY", "SHORT_RANGE_DPS"],
            "requires": [],
            "amplifies": ["IMMOBILE_CARRY", "LATE_GAME_SCALE", "DIVE_ENGAGE"],
            "countered_by_tags": ["LONG_RANGE_POKE", "DISENGAGE", "SPELL_SHIELD"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 35, "Engage Teamfight": 56, "Poke Siege": 18,
               "Split Push": 8, "Pick Comp": 15, "Hypercarry Protect": 98,
               "Disengage": 72, "Skirmish": 48}
        ),
        "pro_tier": 8,
        "self_sufficiency": 4,
    },
    "Jarvan IV": {
        "profile": "diver_ad",
        "ability_tags": [
            "AOE_KNOCKUP", "HARD_ENGAGE", "DIVE_ENGAGE", "TERRAIN_CREATION",
            "EARLY_GAME_POWER", "OBJECTIVE_CONTROL", "CHAIN_CC"
        ],
        "synergy_keys": {
            "enables": ["AOE_FOLLOW_UP", "KNOCKUP_BENEFICIARY", "RESET_MECHANIC"],
            "requires": [],
            "amplifies": ["SHORT_RANGE_DPS", "DIVE_ENGAGE"],
            "countered_by_tags": ["DISENGAGE", "WIND_WALL", "LONG_RANGE_POKE"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 88, "Engage Teamfight": 90, "Poke Siege": 18,
               "Split Push": 20, "Pick Comp": 72, "Hypercarry Protect": 18,
               "Disengage": 10, "Skirmish": 75}
        ),
        "pro_tier": 8,
        "self_sufficiency": 6,
    },
    "Blitzcrank": {
        "profile": "catcher",
        "range_type": "MELEE",
        "ability_tags": [
            "PULL", "POINT_AND_CLICK_CC", "SINGLE_KNOCKUP", "ROAM_THREAT",
            "VISION_CONTROL", "HARD_ENGAGE", "SINGLE_KNOCKUP"
        ],
    },
    "Twisted Fate": {
        "profile": "ap_mage",
        "ability_tags": [
            "POINT_AND_CLICK_CC", "GLOBAL_PRESENCE", "ROAM_THREAT",
            "SINGLE_STUN", "WAVECLEAR", "AP_BURST", "GLOBAL_MOBILITY"
        ],
        "synergy_keys": {
            "enables": ["EXECUTE", "AD_BURST", "AP_BURST"],
            "requires": [],
            "amplifies": ["STEALTH", "DIVE_ENGAGE", "SPLIT_PUSH_THREAT"],
            "countered_by_tags": ["DISENGAGE", "SPELL_SHIELD", "HIGH_MOBILITY"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 18, "Engage Teamfight": 30, "Poke Siege": 48,
               "Split Push": 62, "Pick Comp": 95, "Hypercarry Protect": 15,
               "Disengage": 18, "Skirmish": 64}
        ),
        "pro_tier": 8,
        "self_sufficiency": 7,
    },
    "Shen": {
        "profile": "engage_tank",
        "damage_type": ["AD"],
        "ability_tags": [
            "PEEL", "POINT_AND_CLICK_CC", "GLOBAL_PRESENCE", "SHIELD",
            "ANTI_ASSASSIN", "TELEPORT_SYNERGY", "POINT_AND_CLICK_ULT"
        ],
        "synergy_keys": {
            "enables": ["SPLIT_PUSH_THREAT", "DIVE_ENGAGE"],
            "requires": [],
            "amplifies": ["IMMOBILE_CARRY", "SHORT_RANGE_DPS"],
            "countered_by_tags": ["LONG_RANGE_POKE", "SPLIT_PUSH_THREAT", "AOE_DPS"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 28, "Engage Teamfight": 58, "Poke Siege": 16,
               "Split Push": 84, "Pick Comp": 42, "Hypercarry Protect": 88,
               "Disengage": 52, "Skirmish": 70}
        ),
        "pro_tier": 8,
        "self_sufficiency": 7,
    },
    "Gangplank": {
        "profile": "split_duelist",
        "range_type": "MELEE",
        "damage_type": ["AD"],
        "ability_tags": [
            "GLOBAL_PRESENCE", "AOE_FOLLOW_UP", "TRUE_DAMAGE", "PUSH_POWER",
            "LATE_GAME_SCALE", "OBJECTIVE_DAMAGE", "SPLIT_PUSH_THREAT"
        ],
        "synergy_keys": {
            "enables": ["CHAIN_CC", "EXECUTE"],
            "requires": [],
            "amplifies": ["GLOBAL_PRESENCE", "POINT_AND_CLICK_CC"],
            "countered_by_tags": ["HARD_ENGAGE", "POINT_AND_CLICK_CC", "DIVE_ENGAGE"],
        },
        "archetype_fit": fit(
            **{"Wombo Combo": 64, "Engage Teamfight": 55, "Poke Siege": 58,
               "Split Push": 82, "Pick Comp": 32, "Hypercarry Protect": 20,
               "Disengage": 18, "Skirmish": 55}
        ),
        "pro_tier": 8,
        "self_sufficiency": 8,
    },
}


CHAMPION_PROFILE_MAP = {
    # Tanks / engage
    "Alistar": "engage_tank", "Amumu": "engage_tank", "Braum": "enchanter",
    "Leona": "engage_tank", "Nautilus": "engage_tank", "Ornn": "engage_tank",
    "Poppy": "engage_tank", "Rakan": "engage_tank", "Rammus": "engage_tank",
    "Rell": "engage_tank", "Sejuani": "engage_tank", "Sion": "engage_tank",
    "Skarner": "engage_tank", "Tahm Kench": "engage_tank", "Thresh": "catcher",
    "Vi": "diver_ad", "Wukong": "diver_ad", "Zac": "engage_tank", "Maokai": "engage_tank",
    # bruisers / duelists
    "Aatrox": "bruiser_skirmish", "Camille": "split_duelist", "Darius": "bruiser_skirmish",
    "Dr. Mundo": "bruiser_skirmish", "Fiora": "split_duelist", "Garen": "split_duelist",
    "Gnar": "engage_tank", "Illaoi": "split_duelist", "Irelia": "bruiser_skirmish",
    "Jax": "split_duelist", "K'Sante": "engage_tank", "Kled": "diver_ad", "Mordekaiser": "bruiser_skirmish",
    "Nasus": "split_duelist", "Olaf": "bruiser_skirmish", "Renekton": "bruiser_skirmish",
    "Riven": "bruiser_skirmish", "Sett": "bruiser_skirmish", "Tryndamere": "split_duelist",
    "Urgot": "split_duelist", "Volibear": "diver_ad", "Warwick": "bruiser_skirmish",
    "Yorick": "split_duelist", "Gwen": "split_duelist", "Trundle": "split_duelist",
    "Udyr": "bruiser_skirmish", "Shyvana": "bruiser_skirmish",
    # assassins
    "Ahri": "assassin", "Akali": "assassin", "Diana": "diver_ad", "Ekko": "assassin",
    "Evelynn": "assassin", "Fizz": "assassin", "Katarina": "assassin", "Kha'Zix": "assassin",
    "LeBlanc": "assassin", "Naafiri": "assassin", "Nocturne": "assassin", "Pyke": "catcher",
    "Qiyana": "assassin", "Rek'Sai": "diver_ad", "Rengar": "assassin", "Shaco": "assassin",
    "Sylas": "diver_ad", "Talon": "assassin", "Viego": "bruiser_skirmish", "Yone": "bruiser_skirmish",
    "Zed": "assassin", "Kayn": "assassin", "Bel'Veth": "split_duelist", "Briar": "diver_ad",
    # mages
    "Anivia": "ap_mage", "Annie": "ap_mage", "Aurelion Sol": "aoe_mage", "Azir": "marksman_poke",
    "Brand": "aoe_mage", "Cassiopeia": "marksman_hyper", "Corki": "marksman_poke",
    "Galio": "engage_tank", "Heimerdinger": "ap_mage", "Hwei": "aoe_mage", "Karthus": "aoe_mage",
    "Kassadin": "assassin", "Lissandra": "aoe_mage", "Lux": "ap_mage", "Malzahar": "ap_mage",
    "Neeko": "aoe_mage", "Ryze": "ap_mage", "Syndra": "ap_mage", "Taliyah": "ap_mage",
    "Veigar": "ap_mage", "Vel'Koz": "ap_mage", "Vex": "ap_mage", "Viktor": "ap_mage",
    "Vladimir": "aoe_mage", "Xerath": "ap_mage", "Ziggs": "ap_mage", "Zoe": "ap_mage",
    "Orianna": "aoe_mage", "Rumble": "aoe_mage", "Swain": "aoe_mage", "Seraphine": "enchanter",
    # marksmen
    "Akshan": "marksman_poke", "Aphelios": "marksman_hyper", "Ashe": "marksman_poke",
    "Caitlyn": "marksman_poke", "Draven": "marksman_poke", "Ezreal": "marksman_poke",
    "Jhin": "marksman_poke", "Jinx": "marksman_hyper", "Kai'Sa": "marksman_hyper",
    "Kalista": "marksman_hyper", "Kog'Maw": "marksman_hyper", "Lucian": "marksman_poke",
    "Miss Fortune": "marksman_poke", "Nilah": "marksman_hyper", "Samira": "marksman_hyper",
    "Senna": "marksman_poke", "Sivir": "marksman_hyper", "Smolder": "marksman_hyper",
    "Tristana": "marksman_hyper", "Twitch": "marksman_hyper", "Varus": "marksman_poke",
    "Vayne": "marksman_hyper", "Xayah": "marksman_hyper", "Zeri": "marksman_hyper",
    # supports / enchanters / catchers
    "Bard": "catcher", "Blitzcrank": "catcher", "Janna": "enchanter", "Karma": "enchanter",
    "Lulu": "enchanter", "Milio": "enchanter", "Morgana": "catcher", "Nami": "enchanter",
    "Renata Glasc": "enchanter", "Sona": "enchanter", "Soraka": "enchanter", "Taric": "enchanter",
    "Yuumi": "enchanter", "Zilean": "enchanter", "Zyra": "ap_mage",
    # misc ranged tops/junglers
    "Graves": "marksman_poke", "Jayce": "marksman_poke", "Kennen": "aoe_mage", "Kindred": "marksman_hyper",
    "Lee Sin": "diver_ad", "Nidalee": "ap_mage", "Pantheon": "diver_ad", "Quinn": "marksman_poke",
    "Singed": "engage_tank", "Teemo": "marksman_poke", "Xin Zhao": "diver_ad", "Master Yi": "marksman_hyper",
    "Ivern": "enchanter", "Nunu & Willump": "engage_tank", "Elise": "ap_mage",
    "Fiddlesticks": "aoe_mage", "Hecarim": "diver_ad", "Lillia": "ap_mage", "Lucian": "marksman_poke",
    "Kayle": "marksman_hyper", "Shen": "engage_tank", "Gangplank": "split_duelist", "Malphite": "engage_tank",
}


def make_record(name: str) -> dict:
    profile_name = CHAMPION_PROFILE_MAP.get(name, "bruiser_skirmish")
    base = dict(PROFILES[profile_name])
    override = OVERRIDES.get(name, {})
    if "profile" in override:
        base = dict(PROFILES[override["profile"]])
    roles = DEFAULT_ROLE_MAP[name]
    record = {
        "name": name,
        "roles": roles,
        **base,
    }
    record.update({k: v for k, v in override.items() if k != "profile"})
    return record


def main() -> None:
    target = PROJECT_ROOT / "data" / "champions_synergy.json"
    payload = {name: make_record(name) for name in sorted(DEFAULT_ROLE_MAP)}
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(payload)} champions to {target}")


if __name__ == "__main__":
    main()
