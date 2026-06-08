from __future__ import annotations

import itertools
import random

from logic.composition import ROLES
from logic.game_curve import evaluate_team_curve

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

ARCHETYPE_NAME_ALIASES = {
    "Poke / Siege": "Poke Siege",
}

CC_TAGS = {
    "AOE_KNOCKUP",
    "SINGLE_KNOCKUP",
    "AOE_STUN",
    "SINGLE_STUN",
    "AOE_ROOT",
    "SINGLE_ROOT",
    "SUPPRESSION",
    "DISPLACEMENT",
    "PULL",
    "POINT_AND_CLICK_CC",
    "SKILLSHOT_CC",
    "GROUNDED",
    "SLEEP_CC",
    "FEAR_CC",
    "CHARM_CC",
    "TAUNT_CC",
    "BLIND_CC",
    "SILENCE_CC",
    "GLOBAL_CC",
}

ENGAGE_TAGS = {
    "HARD_ENGAGE",
    "SOFT_ENGAGE",
    "AOE_KNOCKUP",
    "DIVE_ENGAGE",
    "GLOBAL_ENGAGE",
    "FLANK_ENGAGE",
}

DAMAGE_TAGS = {
    "AP_BURST",
    "AD_BURST",
    "AOE_DPS",
    "SINGLE_TARGET_DPS",
    "POKE_DAMAGE",
    "HYPERCARRY",
    "EXECUTE",
}

COMBO_RELEVANT_TAGS = {
    "AOE_KNOCKUP",
    "SINGLE_KNOCKUP",
    "KNOCKUP_BENEFICIARY",
    "AOE_FOLLOW_UP",
    "AOE_DPS",
    "AOE_STUN",
    "SINGLE_STUN",
    "CHAIN_CC",
    "SUPPRESSION",
    "PEEL",
    "HARD_PEEL",
    "SHIELD",
    "HEAL",
    "ANTI_ASSASSIN",
    "SPEED_BOOST_ALLY",
    "ATTACK_SPEED_BUFF",
    "BUFF_AMPLIFIER",
    "HYPERCARRY",
    "IMMOBILE_CARRY",
    "ON_HIT_SYNERGY",
    "SHRED_ARMOR",
    "SHRED_MR",
    "DAMAGE_AMPLIFY_DEBUFF",
    "PERCENT_HP_DAMAGE",
    "EXECUTE",
    "RESET_MECHANIC",
    "COMBO_EXTENDER",
    "DASH_CANCEL",
    "HARD_ENGAGE",
    "DIVE_ENGAGE",
    "FLANK_ENGAGE",
    "GLOBAL_ENGAGE",
    "PULL",
    "DISPLACEMENT",
    "WIND_WALL",
    "TERRAIN_CREATION",
    "STEALTH",
    "GLOBAL_PRESENCE",
    "OATHSWORN_SYNERGY",
    "ATTACHED_SUPPORT",
    "AURA_BUFF",
    "BLIND_CC",
    "CC_TRIGGERED_DAMAGE",
    "CHARM_CC",
    "CLUSTERED_ENEMIES_BENEFIT",
    "CONCUSSIVE_ENABLER",
    "CONDITIONAL_CC_UPGRADE",
    "ENCHANTER_CARRY",
    "EXECUTE_AFTER_INVULN",
    "FEAR_CC",
    "FROST_APPLICATION",
    "FROST_SHATTER",
    "GLOBAL_CC",
    "GROUNDED",
    "INVULN_WINDOW_ALLY",
    "INVULN_ZONE",
    "KILL_ENABLER",
    "LONG_RANGE_ULT",
    "ON_HIT_POISON",
    "ON_HIT_SLOW",
    "PASSIVE_BURN",
    "RESET_ON_KILL",
    "REVIVE_ALLY",
    "SAVE_MECHANIC_ALLY",
    "SETUP_FOR_EXECUTE",
    "SILENCE_CC",
    "SLEEP_CC",
    "SLOW_CONDITIONAL_ROOT",
    "STACK_SCALING",
    "TAUNT_CC",
    "TERRAIN_TRAP",
    "UTILITY_CARRY",
    "VISION_DENIAL",
    "VISION_PROVIDER",
    "WALL_SLAM_ENABLER",
    "ZONE_DENIAL",
}

TAG_INTERACTION_VALUES = {
    frozenset({"AOE_KNOCKUP", "KNOCKUP_BENEFICIARY"}): 28,
    frozenset({"SINGLE_KNOCKUP", "KNOCKUP_BENEFICIARY"}): 22,
    frozenset({"HARD_ENGAGE", "AOE_FOLLOW_UP"}): 24,
    frozenset({"SUPPRESSION", "KNOCKUP_BENEFICIARY"}): 22,
    frozenset({"AOE_KNOCKUP", "AOE_FOLLOW_UP"}): 16,
    frozenset({"AOE_STUN", "AOE_FOLLOW_UP"}): 14,
    frozenset({"AOE_STUN", "AOE_DPS"}): 16,
    frozenset({"AOE_STUN", "POKE_DAMAGE"}): 10,
    frozenset({"AOE_STUN", "SIEGE_DAMAGE"}): 10,
    frozenset({"PULL", "AOE_DPS"}): 18,
    frozenset({"PULL", "AP_BURST"}): 18,
    frozenset({"PULL", "AD_BURST"}): 18,
    frozenset({"DISPLACEMENT", "KNOCKUP_BENEFICIARY"}): 20,
    frozenset({"OATHSWORN_SYNERGY", "HARD_ENGAGE"}): 20,
    frozenset({"DIVE_ENGAGE", "SPEED_BOOST_ALLY"}): 16,
    frozenset({"RESET_MECHANIC", "CHAIN_CC"}): 18,
    frozenset({"IMMOBILE_CARRY", "HARD_PEEL"}): 10,
    frozenset({"IMMOBILE_CARRY", "PEEL"}): 6,
    frozenset({"IMMOBILE_CARRY", "SHIELD"}): 8,
    frozenset({"IMMOBILE_CARRY", "SPEED_BOOST_ALLY"}): 11,
    frozenset({"HYPERCARRY", "ANTI_ASSASSIN"}): 8,
    frozenset({"HYPERCARRY", "SHIELD"}): 7,
    frozenset({"HYPERCARRY", "BUFF_AMPLIFIER"}): 9,
    frozenset({"HYPERCARRY", "ATTACK_SPEED_BUFF"}): 8,
    frozenset({"HYPERCARRY", "DAMAGE_AMPLIFY_DEBUFF"}): 13,
    frozenset({"ON_HIT_SYNERGY", "ATTACK_SPEED_BUFF"}): 13,
    frozenset({"ON_HIT_SYNERGY", "BUFF_AMPLIFIER"}): 12,
    frozenset({"SHRED_ARMOR", "AD_BURST"}): 12,
    frozenset({"SHRED_ARMOR", "AOE_DPS"}): 11,
    frozenset({"SHRED_MR", "AP_BURST"}): 12,
    frozenset({"SHRED_MR", "AOE_DPS"}): 11,
    frozenset({"DAMAGE_AMPLIFY_DEBUFF", "AP_BURST"}): 12,
    frozenset({"DAMAGE_AMPLIFY_DEBUFF", "AD_BURST"}): 12,
    frozenset({"EXECUTE", "PERCENT_HP_DAMAGE"}): 11,
    frozenset({"GLOBAL_PRESENCE", "SPLIT_PUSH_THREAT"}): 12,
    frozenset({"TERRAIN_CREATION", "HARD_ENGAGE"}): 11,
    frozenset({"TERRAIN_CREATION", "AOE_FOLLOW_UP"}): 12,
    frozenset({"HARD_ENGAGE", "CHAIN_CC"}): 11,
    frozenset({"FLANK_ENGAGE", "AOE_FOLLOW_UP"}): 12,
    frozenset({"STEALTH", "HARD_ENGAGE"}): 10,
    frozenset({"WIND_WALL", "POKE_DAMAGE"}): 10,
    frozenset({"HARD_ENGAGE", "SIEGE_DAMAGE"}): 12,
    frozenset({"POINT_AND_CLICK_CC", "SINGLE_TARGET_DPS"}): 8,
    frozenset({"PEEL", "HYPERCARRY"}): 5,
    frozenset({"HEAL", "HYPERCARRY"}): 4,
    frozenset({"SHIELD", "AD_BURST"}): 7,
    frozenset({"COMBO_EXTENDER", "HARD_ENGAGE"}): 8,
    frozenset({"DASH_CANCEL", "AOE_DPS"}): 7,
    frozenset({"WAVECLEAR", "POKE_DAMAGE"}): 6,
    frozenset({"OBJECTIVE_CONTROL", "GLOBAL_PRESENCE"}): 7,
    frozenset({"SOFT_ENGAGE", "AOE_FOLLOW_UP"}): 6,
    frozenset({"ANTI_ASSASSIN", "IMMOBILE_CARRY"}): 5,
    frozenset({"GRIEVOUS_WOUNDS", "HEAL"}): -5,
    frozenset({"CONCUSSIVE_ENABLER",     "BASIC_ATTACK_RELIANT"}):  18,
    frozenset({"CONCUSSIVE_ENABLER",     "ON_HIT_SYNERGY"}):        16,
    frozenset({"CONCUSSIVE_ENABLER",     "SINGLE_TARGET_DPS"}):     14,
    frozenset({"CONCUSSIVE_ENABLER",     "ON_HIT_SLOW"}):           12,
    frozenset({"FROST_APPLICATION",      "BASIC_ATTACK_RELIANT"}):  15,
    frozenset({"FROST_APPLICATION",      "AOE_DPS"}):               12,
    frozenset({"FROST_APPLICATION",      "SINGLE_TARGET_DPS"}):     11,
    frozenset({"FROST_SHATTER",          "FROST_APPLICATION"}):     18,
    frozenset({"PASSIVE_BURN",           "CHAIN_CC"}):              16,
    frozenset({"PASSIVE_BURN",           "AOE_STUN"}):              15,
    frozenset({"PASSIVE_BURN",           "SINGLE_STUN"}):           14,
    frozenset({"PASSIVE_BURN",           "PULL"}):                  14,
    frozenset({"PASSIVE_BURN",           "HARD_ENGAGE"}):           12,
    frozenset({"CC_TRIGGERED_DAMAGE",    "AOE_STUN"}):              15,
    frozenset({"CC_TRIGGERED_DAMAGE",    "SINGLE_STUN"}):           13,
    frozenset({"CC_TRIGGERED_DAMAGE",    "PULL"}):                  14,
    frozenset({"CC_TRIGGERED_DAMAGE",    "AOE_ROOT"}):              14,
    frozenset({"CC_TRIGGERED_DAMAGE",    "AOE_KNOCKUP"}):           13,
    frozenset({"CC_TRIGGERED_DAMAGE",    "HARD_ENGAGE"}):           12,
    frozenset({"CC_TRIGGERED_DAMAGE",    "CHARM_CC"}):              13,
    frozenset({"CC_TRIGGERED_DAMAGE",    "FEAR_CC"}):               11,
    frozenset({"ON_HIT_SLOW",            "SLOW_CONDITIONAL_ROOT"}): 20,
    frozenset({"ON_HIT_SLOW",            "CONDITIONAL_CC_UPGRADE"}):18,
    frozenset({"SINGLE_SLOW",            "SLOW_CONDITIONAL_ROOT"}): 14,
    frozenset({"AOE_SLOW",               "SLOW_CONDITIONAL_ROOT"}): 13,
    frozenset({"GROUNDED",               "SHORT_RANGE_DPS"}):       13,
    frozenset({"GROUNDED",               "DIVE_ENGAGE"}):           12,
    frozenset({"GROUNDED",               "DUELIST"}):               11,
    frozenset({"SLEEP_CC",               "AP_BURST"}):              18,
    frozenset({"SLEEP_CC",               "AD_BURST"}):              17,
    frozenset({"SLEEP_CC",               "SINGLE_TARGET_DPS"}):     15,
    frozenset({"SLEEP_CC",               "AOE_FOLLOW_UP"}):         13,
    frozenset({"CHARM_CC",               "AP_BURST"}):              14,
    frozenset({"CHARM_CC",               "AOE_DPS"}):               12,
    frozenset({"CHARM_CC",               "ASSASSIN"}):              13,
    frozenset({"CHARM_CC",               "HARD_ENGAGE"}):           11,
    frozenset({"FEAR_CC",                "ZONE_DENIAL"}):           12,
    frozenset({"FEAR_CC",                "AOE_FOLLOW_UP"}):         11,
    frozenset({"FEAR_CC",                "DIVE_ENGAGE"}):           10,
    frozenset({"SILENCE_CC",             "DIVE_ENGAGE"}):           13,
    frozenset({"SILENCE_CC",             "ASSASSIN"}):              12,
    frozenset({"SILENCE_CC",             "HARD_ENGAGE"}):           11,
    frozenset({"TAUNT_CC",               "PEEL"}):                  10,
    frozenset({"TAUNT_CC",               "TANK"}):                  11,
    frozenset({"BLIND_CC",               "HYPERCARRY"}):             9,
    frozenset({"LONG_RANGE_ULT",         "LONG_RANGE_ULT"}):        15,
    frozenset({"GLOBAL_CC",              "LONG_RANGE_ULT"}):        13,
    frozenset({"LONG_RANGE_ULT",         "AOE_FOLLOW_UP"}):         11,
    frozenset({"GLOBAL_CC",              "GLOBAL_CC"}):             14,
    frozenset({"LONG_RANGE_ULT",         "GLOBAL_ENGAGE"}):         12,
    frozenset({"INVULN_WINDOW_ALLY",     "HYPERCARRY"}):            14,
    frozenset({"INVULN_WINDOW_ALLY",     "AOE_FOLLOW_UP"}):         15,
    frozenset({"INVULN_WINDOW_ALLY",     "IMMOBILE_CARRY"}):        13,
    frozenset({"INVULN_ZONE",            "AP_BURST"}):              16,
    frozenset({"INVULN_ZONE",            "AOE_DPS"}):               15,
    frozenset({"INVULN_ZONE",            "LONG_RANGE_ULT"}):        14,
    frozenset({"EXECUTE_AFTER_INVULN",   "AP_BURST"}):              14,
    frozenset({"EXECUTE_AFTER_INVULN",   "AOE_DPS"}):               13,
    frozenset({"SAVE_MECHANIC_ALLY",     "IMMOBILE_CARRY"}):        16,
    frozenset({"SAVE_MECHANIC_ALLY",     "HYPERCARRY"}):            15,
    frozenset({"REVIVE_ALLY",            "HYPERCARRY"}):            14,
    frozenset({"REVIVE_ALLY",            "IMMOBILE_CARRY"}):        15,
    frozenset({"REVIVE_ALLY",            "LONG_RANGE_ULT"}):        10,
    frozenset({"ATTACHED_SUPPORT",       "HIGH_MOBILITY"}):         15,
    frozenset({"ATTACHED_SUPPORT",       "HYPERCARRY"}):            13,
    frozenset({"ATTACHED_SUPPORT",       "MOBILE_CARRY"}):          14,
    frozenset({"ATTACHED_SUPPORT",       "IMMOBILE_CARRY"}):         8,
    frozenset({"CLUSTERED_ENEMIES_BENEFIT","AOE_KNOCKUP"}):         14,
    frozenset({"CLUSTERED_ENEMIES_BENEFIT","HARD_ENGAGE"}):         13,
    frozenset({"CLUSTERED_ENEMIES_BENEFIT","AOE_STUN"}):            13,
    frozenset({"CLUSTERED_ENEMIES_BENEFIT","TERRAIN_CREATION"}):    12,
    frozenset({"CLUSTERED_ENEMIES_BENEFIT","AOE_ROOT"}):            12,
    frozenset({"RESET_ON_KILL",          "CHAIN_CC"}):              14,
    frozenset({"RESET_ON_KILL",          "AOE_STUN"}):              15,
    frozenset({"RESET_ON_KILL",          "SETUP_FOR_EXECUTE"}):     13,
    frozenset({"RESET_ON_KILL",          "HARD_ENGAGE"}):           12,
    frozenset({"VISION_DENIAL",          "PULL"}):                  13,
    frozenset({"VISION_DENIAL",          "HARD_ENGAGE"}):           12,
    frozenset({"VISION_DENIAL",          "ASSASSIN"}):              11,
    frozenset({"ENCHANTER_CARRY",        "IMMOBILE_CARRY"}):        14,
    frozenset({"ENCHANTER_CARRY",        "HYPERCARRY"}):            14,
    frozenset({"ENCHANTER_CARRY",        "UTILITY_CARRY"}):         12,
    frozenset({"UTILITY_CARRY",          "HARD_ENGAGE"}):           11,
    frozenset({"AURA_BUFF",              "HYPERCARRY"}):            11,
    frozenset({"AURA_BUFF",              "AURA_BUFF"}):             12,
    frozenset({"AURA_BUFF",              "IMMOBILE_CARRY"}):        10,
    frozenset({"TERRAIN_TRAP",           "AOE_FOLLOW_UP"}):         13,
    frozenset({"TERRAIN_TRAP",           "CLUSTERED_ENEMIES_BENEFIT"}): 14,
    frozenset({"WALL_SLAM_ENABLER",      "DISPLACEMENT"}):          12,
    frozenset({"WALL_SLAM_ENABLER",      "KNOCK_BACK"}):            13,
}

PASSIVE_INTERACTIONS = {
    frozenset(["Yasuo", "Orianna"]): 12,
    frozenset(["Yasuo", "Gragas"]): 8,
    frozenset(["Yasuo", "Lee Sin"]): 8,
    frozenset(["Yasuo", "Cho'Gath"]): 7,
    frozenset(["Yasuo", "Xin Zhao"]): 7,
    frozenset(["Yone", "Orianna"]): 12,
    frozenset(["Yone", "Gragas"]): 8,
    frozenset(["Yone", "Lee Sin"]): 8,
    frozenset(["Orianna", "Zac"]): 10,
    frozenset(["Orianna", "Hecarim"]): 10,
    frozenset(["Orianna", "Vi"]): 9,
    frozenset(["Orianna", "Jarvan IV"]): 10,
    frozenset(["Kog'Maw", "Lulu"]): 20,
    frozenset(["Kog'Maw", "Taric"]): 18,
    frozenset(["Kog'Maw", "Janna"]): 16,
    frozenset(["Kog'Maw", "Yuumi"]): 15,
    frozenset(["Kog'Maw", "Soraka"]): 13,
    frozenset(["Zeri", "Lulu"]): 18,
    frozenset(["Zeri", "Yuumi"]): 16,
    frozenset(["Aphelios", "Lulu"]): 15,
    frozenset(["Aphelios", "Yuumi"]): 14,
    frozenset(["Jinx", "Lulu"]): 14,
    frozenset(["Vayne", "Lulu"]): 14,
    frozenset(["Kalista", "Thresh"]): 18,
    frozenset(["Kalista", "Alistar"]): 18,
    frozenset(["Kalista", "Nautilus"]): 15,
    frozenset(["Kalista", "Blitzcrank"]): 12,
    frozenset(["Kalista", "Rakan"]): 14,
    frozenset(["Rakan", "Xayah"]): 26,
    frozenset(["Rakan", "Yasuo"]): 14,
    frozenset(["Rakan", "Yone"]): 14,
    frozenset(["Renata Glasc", "Miss Fortune"]): 18,
    frozenset(["Renata Glasc", "Jinx"]): 16,
    frozenset(["Renata Glasc", "Katarina"]): 14,
    frozenset(["Miss Fortune", "Amumu"]): 18,
    frozenset(["Miss Fortune", "Leona"]): 14,
    frozenset(["Miss Fortune", "Jarvan IV"]): 13,
    frozenset(["Miss Fortune", "Malzahar"]): 12,
    frozenset(["Malzahar", "Zed"]): 12,
    frozenset(["Malzahar", "Vayne"]): 13,
    frozenset(["Malzahar", "Kog'Maw"]): 12,
    frozenset(["Twisted Fate", "Zed"]): 12,
    frozenset(["Twisted Fate", "Ahri"]): 12,
    frozenset(["Twisted Fate", "Nocturne"]): 13,
    frozenset(["Twisted Fate", "Fizz"]): 10,
    frozenset(["Twisted Fate", "Qiyana"]): 11,
    frozenset(["Nocturne", "Blitzcrank"]): 12,
    frozenset(["Nocturne", "Caitlyn"]): 10,
    frozenset(["Nocturne", "Zed"]): 9,
    frozenset(["Amumu", "Katarina"]): 16,
    frozenset(["Amumu", "Orianna"]): 14,
    frozenset(["Amumu", "Miss Fortune"]): 18,
    frozenset(["Amumu", "Fiddlesticks"]): 14,
    frozenset(["Shen", "Jinx"]): 12,
    frozenset(["Shen", "Kog'Maw"]): 13,
    frozenset(["Shen", "Vayne"]): 11,
    frozenset(["Shen", "Fiora"]): 11,
    frozenset(["Gangplank", "Jarvan IV"]): 10,
    frozenset(["Gangplank", "Orianna"]): 10,
    frozenset(["Ivern", "Miss Fortune"]): 12,
    frozenset(["Ivern", "Jinx"]): 11,
    frozenset(["Ivern", "Kog'Maw"]): 12,
    frozenset(["Taric", "Ezreal"]): 14,
    frozenset(["Taric", "Pantheon"]): 12,
    frozenset(["Taric", "Jinx"]): 11,
    frozenset(["Jarvan IV", "Syndra"]): 9,
    frozenset(["Jarvan IV", "Katarina"]): 11,
    frozenset(["Jarvan IV", "Orianna"]): 10,
    frozenset(["Fiddlesticks", "Amumu"]): 13,
    frozenset(["Fiddlesticks", "Lissandra"]): 10,
    frozenset(["Lissandra", "Zed"]): 10,
    frozenset(["Lissandra", "Veigar"]): 10,
    frozenset(["Alistar", "Draven"]): 13,
    frozenset(["Alistar", "Jinx"]): 11,
    frozenset(["Alistar", "Kalista"]): 18,
    frozenset(["Blitzcrank", "Zed"]): 12,
    frozenset(["Blitzcrank", "Ahri"]): 11,
    frozenset(["Blitzcrank", "Caitlyn"]): 12,
    frozenset(["Blitzcrank", "Nautilus"]): 9,
    frozenset(["Blitzcrank", "Morgana"]): 10,
    frozenset(["Morgana", "Caitlyn"]): 13,
    frozenset(["Morgana", "Ezreal"]): 8,
    frozenset(["Morgana", "Zoe"]): 9,
    frozenset(["Seraphine", "Sona"]): 10,
    frozenset(["Seraphine", "Lulu"]): 9,
    frozenset(["Seraphine", "Kog'Maw"]): 11,
    frozenset(["Hecarim", "Janna"]): 13,
    frozenset(["Hecarim", "Zilean"]): 11,
    frozenset(["Hecarim", "Orianna"]): 10,
    frozenset(["Vi", "Orianna"]): 10,
    frozenset(["Vi", "Caitlyn"]): 12,
    frozenset(["Vi", "Miss Fortune"]): 10,
    frozenset(["Elise", "Orianna"]): 8,
    frozenset(["Elise", "Miss Fortune"]): 8,
    frozenset(["Volibear", "Caitlyn"]): 9,
    frozenset(["Sylas", "Orianna"]): 10,
    frozenset(["Sylas", "Amumu"]): 9,
    frozenset(["Singed", "Orianna"]): 9,
    frozenset(["Singed", "Jarvan IV"]): 8,
    frozenset(["Zilean", "Zed"]): 11,
    frozenset(["Zilean", "Kog'Maw"]): 12,
    frozenset(["Zilean", "Jinx"]): 11,
    frozenset(["Zilean", "Vayne"]): 11,
    frozenset(["Xayah", "Rakan"]): 26,
    frozenset(["Xayah", "Lulu"]): 13,
    frozenset(["Xayah", "Janna"]): 11,
    frozenset(["Samira", "Nautilus"]): 14,
    frozenset(["Samira", "Leona"]): 14,
    frozenset(["Samira", "Alistar"]): 13,
    frozenset(["Samira", "Thresh"]): 12,
    frozenset(["Draven", "Alistar"]): 13,
    frozenset(["Draven", "Leona"]): 12,
    frozenset(["Draven", "Blitzcrank"]): 9,
    frozenset(["Caitlyn", "Morgana"]): 13,
    frozenset(["Caitlyn", "Lux"]): 10,
    frozenset(["Caitlyn", "Vel'Koz"]): 9,
    frozenset(["Caitlyn", "Xerath"]): 9,
    frozenset(["Caitlyn", "Zyra"]): 10,
    frozenset(["Ashe", "Lucian"]): 10,
    frozenset(["Ashe", "Zed"]): 9,
    frozenset(["Ashe", "Nocturne"]): 9,
    frozenset(["Jhin", "Lux"]): 11,
    frozenset(["Jhin", "Morgana"]): 10,
    frozenset(["Jhin", "Thresh"]): 10,
    frozenset(["Nami", "Yasuo"]): 13,
    frozenset(["Nami", "Yone"]): 13,
    frozenset(["Poppy", "Caitlyn"]): 8,
    frozenset(["Poppy", "Orianna"]): 8,
    frozenset(["Braum", "Caitlyn"]):   18,  # Braum stacks + Caitlyn auto = headshot + stun
    frozenset(["Braum", "Lucian"]):    17,  # Lucian double shot = 2 stacks per ult
    frozenset(["Braum", "Jinx"]):      16,
    frozenset(["Braum", "Draven"]):    16,
    frozenset(["Braum", "Ashe"]):      15,  # on-hit builds stacks
    frozenset(["Braum", "Tristana"]): 15,
    frozenset(["Braum", "Kog'Maw"]):  15,  # W machine gun
    frozenset(["Braum", "Aphelios"]): 14,
    frozenset(["Braum", "Ezreal"]):    13,
    frozenset(["Braum", "Sivir"]):     12,
    frozenset(["Braum", "Xayah"]):    12,
    frozenset(["Sejuani", "Draven"]):   13,
    frozenset(["Sejuani", "Caitlyn"]): 13,
    frozenset(["Sejuani", "Jinx"]):    13,
    frozenset(["Sejuani", "Ashe"]):    12,
    frozenset(["Sejuani", "Orianna"]): 11,
    frozenset(["Sejuani", "Viktor"]):  11,
    frozenset(["Brand", "Leona"]):     16,
    frozenset(["Brand", "Nautilus"]): 16,
    frozenset(["Brand", "Alistar"]):   15,
    frozenset(["Brand", "Blitzcrank"]): 14,
    frozenset(["Brand", "Jarvan IV"]): 13,
    frozenset(["Brand", "Thresh"]):    12,
    frozenset(["Zyra", "Blitzcrank"]): 14,
    frozenset(["Zyra", "Leona"]):      14,
    frozenset(["Zyra", "Nautilus"]):   14,
    frozenset(["Zyra", "Alistar"]):    13,
    frozenset(["Zyra", "Thresh"]):     13,
    frozenset(["Zyra", "Jarvan IV"]): 12,
    frozenset(["Zyra", "Amumu"]):      13,
    frozenset(["Kindred", "Karthus"]): 20,  # THE iconic combo: Karthus ult during invuln = all die after
    frozenset(["Kindred", "Miss Fortune"]): 16,
    frozenset(["Kindred", "Orianna"]):  15,
    frozenset(["Kindred", "Fiddlesticks"]): 14,
    frozenset(["Kindred", "Jinx"]):    13,
    frozenset(["Kindred", "Amumu"]):   13,
    frozenset(["Senna", "Lucian"]):    28,  # Lucian fires extra shots from Senna autos; soul passive
    frozenset(["Senna", "Jinx"]):     11,
    frozenset(["Senna", "Draven"]):   11,
    frozenset(["Senna", "Kai'Sa"]):   11,
    frozenset(["Senna", "Aphelios"]): 10,
    frozenset(["Yuumi", "Zeri"]):      18,  # Zeri moves freely + Yuumi attacks from her
    frozenset(["Yuumi", "Hecarim"]):   16,
    frozenset(["Yuumi", "Jinx"]):     14,
    frozenset(["Yuumi", "Corki"]):    13,
    frozenset(["Yuumi", "Tristana"]): 13,
    frozenset(["Yuumi", "Jayce"]):    12,
    frozenset(["Tahm Kench", "Kog'Maw"]):  16,
    frozenset(["Tahm Kench", "Jinx"]):     14,
    frozenset(["Tahm Kench", "Vayne"]):    14,
    frozenset(["Tahm Kench", "Aphelios"]): 13,
    frozenset(["Tahm Kench", "Kalista"]): 12,
    frozenset(["Tahm Kench", "Tristana"]): 12,
    frozenset(["Viktor", "Ashe"]):     14,
    frozenset(["Viktor", "Nunu & Willump"]): 13,
    frozenset(["Viktor", "Sejuani"]): 12,
    frozenset(["Viktor", "Lissandra"]): 11,
    frozenset(["Viktor", "Orianna"]): 11,
    frozenset(["Swain", "Blitzcrank"]): 16,
    frozenset(["Swain", "Nautilus"]):   15,
    frozenset(["Swain", "Thresh"]):     14,
    frozenset(["Swain", "Leona"]):      13,
    frozenset(["Swain", "Alistar"]):    14,
    frozenset(["Zoe", "Syndra"]):      13,
    frozenset(["Zoe", "Twisted Fate"]): 12,
    frozenset(["Zoe", "Lissandra"]):   11,
    frozenset(["Zoe", "Veigar"]):      12,
    frozenset(["Zoe", "Ahri"]):        10,
    frozenset(["Twitch", "Amumu"]):    14,
    frozenset(["Twitch", "Lulu"]):     14,
    frozenset(["Twitch", "Malzahar"]): 11,
    frozenset(["Twitch", "Zac"]):      12,
    frozenset(["Kennen", "Orianna"]):  14,
    frozenset(["Kennen", "Fiddlesticks"]): 13,
    frozenset(["Kennen", "Taric"]):    13,
    frozenset(["Kennen", "Miss Fortune"]): 12,
    frozenset(["Kennen", "Rumble"]):   11,
    frozenset(["Rumble", "Jarvan IV"]): 12,
    frozenset(["Rumble", "Amumu"]):     12,
    frozenset(["Rumble", "Sejuani"]):   11,
    frozenset(["Rumble", "Orianna"]):   11,
    frozenset(["Rumble", "Miss Fortune"]): 11,
    frozenset(["Ashe", "Seraphine"]): 20,  # THE FIX: slow enables root
    frozenset(["Ashe", "Leona"]):     12,
    frozenset(["Ashe", "Draven"]):    12,
    frozenset(["Ashe", "Jhin"]):      11,
    frozenset(["Ashe", "Caitlyn"]):   11,
    frozenset(["Ashe", "Varus"]):     11,
    frozenset(["Ashe", "Vel'Koz"]):   10,
    frozenset(["Ashe", "Zed"]):       10,
    frozenset(["Seraphine", "Sona"]):       11,
    frozenset(["Seraphine", "Nami"]):       10,
    frozenset(["Seraphine", "Leona"]):      11,
    frozenset(["Seraphine", "Nautilus"]):   12,
    frozenset(["Seraphine", "Cassiopeia"]): 13,  # Miasma grounded + slow → Sera E root
    frozenset(["Nami", "Samira"]):    12,
    frozenset(["Nami", "Draven"]):    11,
    frozenset(["Nami", "Varus"]):     10,
    frozenset(["Nami", "Jhin"]):      10,
    frozenset(["Gangplank", "Amumu"]):      11,
    frozenset(["Gangplank", "Miss Fortune"]): 12,
    frozenset(["Gangplank", "Jarvan IV"]): 10,
    frozenset(["Lissandra", "Fiora"]):  10,
    frozenset(["Lissandra", "Talon"]): 10,
    frozenset(["Lissandra", "Zed"]):    12,  # already have, keep
    frozenset(["Bard", "Miss Fortune"]): -8,
    frozenset(["Bard", "Katarina"]):     -8,
    frozenset(["Bard", "Fiddlesticks"]): -6,
    frozenset(["Bard", "Malzahar"]):     -5,
}

ICONIC_COMBOS = {
    frozenset(["Malphite", "Yasuo"]): 20,
    frozenset(["Malphite", "Yone"]): 20,
    frozenset(["Rakan", "Xayah"]): 20,
    frozenset(["Kog'Maw", "Lulu"]): 20,
    frozenset(["Kalista", "Thresh"]): 18,
    frozenset(["Orianna", "Malphite"]): 18,
    frozenset(["Amumu", "Miss Fortune"]): 18,
    frozenset(["Renata Glasc", "Miss Fortune"]): 16,
    frozenset(["Renata Glasc", "Jinx"]): 16,
    frozenset(["Nautilus", "Samira"]): 15,
    frozenset(["Leona", "Draven"]): 14,
    frozenset(["Jarvan IV", "Yasuo"]): 14,
    frozenset(["Jarvan IV", "Yone"]): 14,
    frozenset(["Orianna", "Jarvan IV"]): 14,
    frozenset(["Orianna", "Zac"]): 13,
    frozenset(["Amumu", "Katarina"]): 13,
    frozenset(["Morgana", "Caitlyn"]): 13,
    frozenset(["Alistar", "Kalista"]): 13,
    frozenset(["Blitzcrank", "Caitlyn"]): 12,
    frozenset(["Taric", "Ezreal"]): 12,
    frozenset(["Hecarim", "Janna"]): 12,
    frozenset(["Miss Fortune", "Jarvan IV"]): 12,
    frozenset(["Twisted Fate", "Nocturne"]): 12,
    frozenset(["Ziggs", "Sivir"]): 11,
    frozenset(["Caitlyn", "Xerath"]): 11,
    frozenset(["Nami", "Yasuo"]): 11,
    frozenset(["Zilean", "Kog'Maw"]): 11,
    frozenset(["Jhin", "Lux"]): 10,
    frozenset(["Wukong", "Yasuo"]): 10,
    frozenset(["Ashe", "Lucian"]): 10,
    frozenset(["Vi", "Caitlyn"]): 10,
    # Competitive pairings repeatedly drafted in LCK/LEC that the pure tag model undershoots.
    frozenset(["Vi", "Ahri"]): 18,
    frozenset(["Lucian", "Nami"]): 22,
    frozenset(["Maokai", "Orianna"]): 8,
    frozenset(["Xin Zhao", "Orianna"]): 18,
    frozenset(["Nocturne", "Orianna"]): 16,
    frozenset(["Kalista", "Renata Glasc"]): 16,
    frozenset(["Sejuani", "Ahri"]): 16,
    frozenset(["Rell", "Ahri"]): 16,
    frozenset(["Azir", "Vi"]): 10,
    frozenset(["Azir", "Maokai"]): 10,
}

SCORE_PERCENTILES = {
    0: 0,
    15: 10,
    25: 20,
    35: 30,
    45: 40,
    55: 50,
    63: 60,
    71: 70,
    79: 80,
    88: 90,
    100: 100,
}


def normalize_archetype_name(archetype: str) -> str:
    return ARCHETYPE_NAME_ALIASES.get(archetype, archetype)


def get_passive_interaction_bonus(name_a: str, name_b: str) -> float:
    return float(PASSIVE_INTERACTIONS.get(frozenset([name_a, name_b]), 0.0))


def get_iconic_combo_bonus(name_a: str, name_b: str) -> float:
    key = frozenset([name_a, name_b])
    if key in PASSIVE_INTERACTIONS:
        return 0.0
    return float(ICONIC_COMBOS.get(key, 0.0))


def compute_pairwise_synergy_pure(champ_a: dict, champ_b: dict) -> float:
    score = 0.0
    tags_a = set(champ_a["ability_tags"])
    tags_b = set(champ_b["ability_tags"])

    interaction_score = 0.0
    for tag_pair, value in TAG_INTERACTION_VALUES.items():
        pair_tags = tuple(tag_pair)
        if len(pair_tags) == 1:
            tag = pair_tags[0]
            if tag in tags_a and tag in tags_b:
                interaction_score += value
            continue

        tag_1, tag_2 = pair_tags
        if (tag_1 in tags_a and tag_2 in tags_b) or (tag_1 in tags_b and tag_2 in tags_a):
            interaction_score += value
    score += min(interaction_score, 55.0)

    enables_a_b = len(set(champ_a["synergy_keys"]["enables"]) & tags_b)
    enables_b_a = len(set(champ_b["synergy_keys"]["enables"]) & tags_a)
    if enables_a_b > 0 and enables_b_a > 0:
        score += min((enables_a_b + enables_b_a) * 8, 24)
    else:
        score += min((enables_a_b + enables_b_a) * 6, 18)

    amp_a_b = len(set(champ_a["synergy_keys"]["amplifies"]) & tags_b)
    amp_b_a = len(set(champ_b["synergy_keys"]["amplifies"]) & tags_a)
    score += min((amp_a_b + amp_b_a) * 6, 18)

    score += get_iconic_combo_bonus(champ_a["name"], champ_b["name"]) * 1.8

    counter_a = len(set(champ_a["synergy_keys"].get("countered_by_tags", [])) & tags_b)
    counter_b = len(set(champ_b["synergy_keys"].get("countered_by_tags", [])) & tags_a)
    score -= min((counter_a + counter_b) * 2, 6)

    score += get_passive_interaction_bonus(champ_a["name"], champ_b["name"]) * 2.5
    return max(0.0, min(100.0, score))


def generate_synergy_highlights_v2(
    team: list[dict],
    pair_scores: dict,
    sorted_pair_values: list[float],
) -> list[str]:
    highlights = []
    all_tags = {tag for champion in team for tag in champion["ability_tags"]}
    names = [champion["name"] for champion in team]
    name_set = set(names)

    trio_checks = [
        ({"Orianna", "Malphite", "Yasuo"}, "Trio clasico: Orianna + Malphite + Yasuo crea un wombo de libro."),
        ({"Orianna", "Malphite", "Yone"}, "Trio wombo: Malphite abre y Orianna/Yone convierten la pelea."),
        ({"Amumu", "Miss Fortune", "Orianna"}, "Trio teamfight: engage AoE y follow-up total en una sola ventana."),
        ({"Jarvan IV", "Yasuo", "Orianna"}, "Trio de encierro: Cataclismo fuerza una Shockwave devastadora."),
        ({"Kog'Maw", "Lulu", "Taric"}, "Protect comp real: triple capa de buffs y supervivencia para el carry."),
        ({"Kindred", "Karthus", "Orianna"}, "Trio execute: sobreviven dentro de la zona y castigan al salir."),
        ({"Twisted Fate", "Nocturne", "Zed"}, "Trio pick: presion global y cazada constante sobre sidelanes."),
        ({"Amumu", "Katarina", "Orianna"}, "Trio reset: el engage inmoviliza y Katarina limpia la pelea."),
        ({"Malphite", "Yasuo", "Yone"}, "Double blade: doble beneficiario de knockup con engage frontal."),
    ]
    for trio_names, message in trio_checks:
        if trio_names.issubset(name_set):
            highlights.append(message)
        if len(highlights) >= 2:
            break

    pair_checks = [
        (lambda tags: "AOE_KNOCKUP" in tags and "KNOCKUP_BENEFICIARY" in tags,
         "Combo knockup: el CC aereo activa habilidades clave de los aliados."),
        (lambda tags: "HARD_ENGAGE" in tags and "AOE_FOLLOW_UP" in tags,
         "Engage + dano masivo: el equipo convierte una iniciacion en teamfight ganada."),
        (lambda tags: "IMMOBILE_CARRY" in tags and ("HARD_PEEL" in tags or "ANTI_ASSASSIN" in tags),
         "Carry protegido: hay peel dedicado para el campeon de escala."),
        (lambda tags: "ON_HIT_SLOW" in tags and "SLOW_CONDITIONAL_ROOT" in tags,
         "Slow permanente: habilita roots fiables durante los intercambios largos."),
        (lambda tags: "INVULN_ZONE" in tags and ("AP_BURST" in tags or "AOE_DPS" in tags),
         "Invulnerabilidad + burst: fuerzan una ventana de daño muy dificil de responder."),
        (lambda tags: "CC_TRIGGERED_DAMAGE" in tags and any(cc in tags for cc in {"AOE_STUN", "SINGLE_STUN", "AOE_ROOT", "PULL"}),
         "CC activa dano extra: cada control potencia la salida de dano del equipo."),
        (lambda tags: "CONCUSSIVE_ENABLER" in tags and "BASIC_ATTACK_RELIANT" in tags,
         "Braum setup: los autos del carry aceleran el aturdimiento."),
        (lambda tags: "LONG_RANGE_ULT" in tags and len([c for c in team if "LONG_RANGE_ULT" in c.get("ability_tags", [])]) >= 2,
         "Doble presion global: dos ultimates de largo alcance condicionan todo el mapa."),
        (lambda tags: "DAMAGE_AMPLIFY_DEBUFF" in tags and "HYPERCARRY" in tags,
         "Amplificacion de dano: el debuff multiplica el valor del hipercarry."),
        (lambda tags: "RESET_ON_KILL" in tags and ("AOE_STUN" in tags or "CHAIN_CC" in tags),
         "Setup para resets: el control masivo abre la cadena de ejecuciones."),
        (lambda tags: "SAVE_MECHANIC_ALLY" in tags and "HYPERCARRY" in tags,
         "Segunda vida para el carry: la compo puede jugar front-to-back con mucha seguridad."),
    ]
    for check_fn, message in pair_checks:
        if len(highlights) >= 4:
            break
        if check_fn(all_tags):
            highlights.append(message)

    if len(highlights) < 3:
        for champ_a, champ_b in itertools.combinations(team, 2):
            key = frozenset([champ_a["name"], champ_b["name"]])
            value = PASSIVE_INTERACTIONS.get(key, 0)
            if value >= 15:
                highlights.append(
                    f"Sinergia iconica: {champ_a['name']} + {champ_b['name']} tienen interaccion directa."
                )
                break

    if len(highlights) < 2:
        sorted_pairs = sorted(pair_scores.items(), key=lambda item: item[1], reverse=True)
        if sorted_pairs and sorted_pairs[0][1] > 30:
            highlights.append(f"Mejor duo del equipo: {sorted_pairs[0][0]} ({sorted_pairs[0][1]:.0f}/100)")
        elif not highlights:
            highlights.append("Los campeones seleccionados tienen poca interaccion mecanica entre si.")

    return highlights[:4]


def generate_synergy_highlights(team: list[dict], pair_scores: dict) -> list[str]:
    sorted_pair_values = sorted(pair_scores.values(), reverse=True)
    return generate_synergy_highlights_v2(team, pair_scores, sorted_pair_values)


def compute_mode1_signature_bonus(team: list[dict], raw_values: list[float]) -> float:
    all_tags = {tag for champion in team for tag in champion["ability_tags"]}
    bonus = 0.0

    signature_checks = [
        ("AOE_KNOCKUP" in all_tags and "KNOCKUP_BENEFICIARY" in all_tags, 8.0),
        ("HARD_ENGAGE" in all_tags and "AOE_FOLLOW_UP" in all_tags, 7.0),
        (
            "IMMOBILE_CARRY" in all_tags
            and any(tag in all_tags for tag in {"HARD_PEEL", "ANTI_ASSASSIN", "SHIELD"}),
            7.0,
        ),
        ("HYPERCARRY" in all_tags and "BUFF_AMPLIFIER" in all_tags, 6.0),
        ("ON_HIT_SYNERGY" in all_tags and "ATTACK_SPEED_BUFF" in all_tags, 5.0),
        ("PULL" in all_tags and any(tag in all_tags for tag in {"AP_BURST", "AD_BURST", "AOE_DPS"}), 5.0),
        ("RESET_MECHANIC" in all_tags and any(tag in all_tags for tag in {"CHAIN_CC", "AOE_STUN"}), 5.0),
        ("TERRAIN_CREATION" in all_tags and "AOE_FOLLOW_UP" in all_tags, 4.0),
    ]
    for condition, value in signature_checks:
        if condition:
            bonus += value

    standout_pairs = sum(1 for value in raw_values if value >= 70)
    if standout_pairs >= 2:
        bonus += min((standout_pairs - 1) * 2.5, 7.5)

    return min(bonus, 24.0)


def compute_team_synergy_mode1(team: list[dict]) -> dict:
    if len(team) < 2:
        return {
            "total_score": 0,
            "pair_scores": {},
            "best_pairs": [],
            "synergy_highlights": [],
        }

    pairs = list(itertools.combinations(team, 2))
    pair_scores = {}
    raw_values = []
    for champ_a, champ_b in pairs:
        score = compute_pairwise_synergy_pure(champ_a, champ_b)
        key = f"{champ_a['name']} + {champ_b['name']}"
        pair_scores[key] = round(score, 1)
        raw_values.append(score)

    pair_count = len(raw_values)
    raw_values_sorted = sorted(raw_values, reverse=True)
    if pair_count == 1:
        base = raw_values[0]
    elif pair_count <= 3:
        weights = [0.50, 0.30, 0.20]
        base = sum(value * weight for value, weight in zip(raw_values_sorted, weights[:pair_count]))
    elif pair_count <= 6:
        tier_1 = raw_values_sorted[:2]
        tier_2 = raw_values_sorted[2:]
        base = ((sum(tier_1) / len(tier_1)) * 0.60) + ((sum(tier_2) / len(tier_2)) * 0.40)
    else:
        tier_1 = raw_values_sorted[:3]
        tier_2 = raw_values_sorted[3:6]
        tier_3 = raw_values_sorted[6:]
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

    total = max(
        1.0,
        min(100.0, round(base + depth_bonus + consistency_bonus + signature_bonus, 1)),
    )
    sorted_pairs = sorted(pair_scores.items(), key=lambda item: item[1], reverse=True)
    highlights = generate_synergy_highlights_v2(team, pair_scores, raw_values_sorted)

    return {
        "total_score": total,
        "pair_scores": pair_scores,
        "best_pairs": sorted_pairs[:3],
        "synergy_highlights": highlights,
        "depth_bonus": round(depth_bonus, 1),
        "consistency_bonus": round(consistency_bonus, 1),
        "signature_bonus": round(signature_bonus, 1),
    }


def compute_pairwise_synergy(champ_a: dict, champ_b: dict) -> float:
    score = 0.0
    enables_hits = len(
        set(champ_a["synergy_keys"]["enables"]).intersection(champ_b["ability_tags"])
    )
    enables_hits += len(
        set(champ_b["synergy_keys"]["enables"]).intersection(champ_a["ability_tags"])
    )
    score += min(enables_hits * 12, 35)

    requires_hits = len(
        set(champ_a["synergy_keys"]["requires"]).intersection(champ_b["ability_tags"])
    )
    requires_hits += len(
        set(champ_b["synergy_keys"]["requires"]).intersection(champ_a["ability_tags"])
    )
    score += min(requires_hits * 10, 20)

    amplifies_hits = len(
        set(champ_a["synergy_keys"]["amplifies"]).intersection(champ_b["ability_tags"])
    )
    amplifies_hits += len(
        set(champ_b["synergy_keys"]["amplifies"]).intersection(champ_a["ability_tags"])
    )
    score += min(amplifies_hits * 8, 25)

    archetype_overlap = 0.0
    for arch, val_a in champ_a["archetype_fit"].items():
        val_b = champ_b["archetype_fit"].get(arch, 0)
        if val_a >= 70 and val_b >= 70:
            archetype_overlap += (val_a + val_b) / 200 * 10
    score += min(archetype_overlap, 20)

    if set(champ_a["damage_type"]) != set(champ_b["damage_type"]):
        score += 5

    counter_hits = len(
        set(champ_a["synergy_keys"]["countered_by_tags"]).intersection(champ_b["ability_tags"])
    )
    counter_hits += len(
        set(champ_b["synergy_keys"]["countered_by_tags"]).intersection(champ_a["ability_tags"])
    )
    score -= min(counter_hits * 5, 15)

    if (
        "IMMOBILE_CARRY" in champ_a["ability_tags"] and "PEEL" in champ_b["ability_tags"]
    ) or (
        "IMMOBILE_CARRY" in champ_b["ability_tags"] and "PEEL" in champ_a["ability_tags"]
    ):
        score += 5

    if (
        "AOE_KNOCKUP" in champ_a["ability_tags"] and "KNOCKUP_BENEFICIARY" in champ_b["ability_tags"]
    ) or (
        "AOE_KNOCKUP" in champ_b["ability_tags"] and "KNOCKUP_BENEFICIARY" in champ_a["ability_tags"]
    ):
        score += 8

    if (
        "HYPERCARRY" in champ_a["ability_tags"] and any(
            tag in champ_b["ability_tags"] for tag in {"PEEL", "SHIELD", "HEAL", "ANTI_ASSASSIN"}
        )
    ) or (
        "HYPERCARRY" in champ_b["ability_tags"] and any(
            tag in champ_a["ability_tags"] for tag in {"PEEL", "SHIELD", "HEAL", "ANTI_ASSASSIN"}
        )
    ):
        score += 10

    return max(0.0, min(100.0, score))


def compute_archetype_scores(team: list[dict]) -> dict[str, float]:
    result = {}
    for arch in ARCHETYPES:
        total_weight = sum(champ["pro_tier"] for champ in team)
        weighted_score = sum(
            champ["archetype_fit"].get(arch, 0) * champ["pro_tier"] for champ in team
        )
        result[arch] = weighted_score / total_weight if total_weight else 0.0
    return result


def compute_role_coherence_penalty(team: list[dict]) -> float:
    penalty = 0.0
    ability_tags_all = [tag for champ in team for tag in champ["ability_tags"]]
    engage_count = sum(1 for tag in ability_tags_all if tag in ENGAGE_TAGS)
    frontline_count = sum(1 for champ in team if champ["range_type"] == "MELEE")
    peel_count = sum(1 for tag in ability_tags_all if tag in {"PEEL", "HARD_PEEL", "ANTI_ASSASSIN", "SHIELD", "HEAL"})
    hypercarry_count = sum(1 for champ in team if "HYPERCARRY" in champ["ability_tags"])
    split_count = sum(1 for champ in team if "SPLIT_PUSH_THREAT" in champ["ability_tags"])
    dive_count = sum(1 for champ in team if any(tag in champ["ability_tags"] for tag in {"DIVE_ENGAGE", "FLANK_ENGAGE"}))
    poke_count = sum(1 for champ in team if any(tag in champ["ability_tags"] for tag in {"POKE_DAMAGE", "LONG_RANGE_POKE", "SIEGE_DAMAGE"}))

    if engage_count == 0:
        penalty += 7
    elif engage_count == 1:
        penalty += 3

    if frontline_count <= 1:
        penalty += 4
    elif all(champ["range_type"] == "MELEE" for champ in team):
        penalty += 2

    if hypercarry_count >= 2 and peel_count == 0:
        penalty += 7
    elif hypercarry_count >= 1 and peel_count == 0:
        penalty += 3

    if not any(tag in DAMAGE_TAGS for tag in ability_tags_all):
        penalty += 6

    if split_count >= 2 and engage_count >= 2:
        penalty += 4
    if dive_count >= 2 and poke_count >= 2:
        penalty += 3

    return round(min(penalty, 22.0), 1)


def normalize_score_percentile(raw_score: float) -> float:
    clamped = max(0.0, min(100.0, raw_score))
    points = sorted(SCORE_PERCENTILES.items())
    for index in range(len(points) - 1):
        low_score, low_percentile = points[index]
        high_score, high_percentile = points[index + 1]
        if low_score <= clamped <= high_score:
            span = high_score - low_score
            if span <= 0:
                return float(high_percentile)
            t = (clamped - low_score) / span
            return round(low_percentile + ((high_percentile - low_percentile) * t), 1)
    return float(points[-1][1])


def generate_team_analysis(team, score, archetype_scores, pairwise) -> dict:
    strengths = []
    weaknesses = []
    tips = []

    all_tags = [tag for champ in team for tag in champ["ability_tags"]]
    all_damage_types = [dt for champ in team for dt in champ["damage_type"]]

    if score >= 75:
        strengths.append("Composicion con alta cohesion tactica")
    cc_count = sum(1 for tag in all_tags if tag in CC_TAGS)
    if cc_count >= 4:
        strengths.append(f"Control de masas abundante ({cc_count} habilidades de CC)")
    if "AP" in all_damage_types and "AD" in all_damage_types:
        strengths.append("Dano equilibrado AP/AD (dificil de itemizar en contra)")
    if any("GLOBAL_PRESENCE" in champ["ability_tags"] for champ in team):
        strengths.append("Presencia global en el mapa")
    if any("PEEL" in champ["ability_tags"] for champ in team) and any(
        "HYPERCARRY" in champ["ability_tags"] for champ in team
    ):
        strengths.append("Carry protegido correctamente")

    if not any(tag in all_tags for tag in {"WAVECLEAR", "PUSH_POWER"}):
        weaknesses.append("Sin waveclear: vulnerable al asedio prolongado")
    if "AP" not in all_damage_types:
        weaknesses.append("Sin dano magico: el rival puede itemizar armadura")
    if "AD" not in all_damage_types:
        weaknesses.append("Sin dano fisico: el rival puede itemizar resistencia magica")
    if sum(1 for champ in team if champ["mobility"] <= 2) >= 3:
        weaknesses.append("Composicion poco movil: vulnerable al kiting")
    if not any(tag in all_tags for tag in ENGAGE_TAGS):
        weaknesses.append("Sin engage real: dificultad para iniciar peleas")
    if not any(tag in all_tags for tag in {"OBJECTIVE_CONTROL", "OBJECTIVE_DAMAGE"}):
        weaknesses.append("Control de objetivos limitado")

    dominant_arch = max(archetype_scores, key=archetype_scores.get)
    arch_score = archetype_scores[dominant_arch]
    if arch_score < 60:
        tips.append("La compo carece de identidad clara. Define mejor el win condition.")
    if dominant_arch == "Wombo Combo" and arch_score > 70:
        tips.append("Espera el engage colectivo. No pelees en escaramuzas aisladas.")
    if dominant_arch == "Poke Siege" and arch_score > 70:
        tips.append("Juega alrededor del rango y fuerza objetivos con vision previa.")
    if dominant_arch == "Hypercarry Protect" and arch_score > 70:
        tips.append("Protege al carry a toda costa: la pelea front-to-back te favorece.")
    if dominant_arch == "Pick Comp" and arch_score > 70:
        tips.append("Gana en vision. El pick solo aparece si controlas el mapa.")

    best_pair = max(pairwise, key=pairwise.get) if pairwise else ""
    worst_pair = min(pairwise, key=pairwise.get) if pairwise else ""
    return {
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
        "tips": tips[:2],
        "best_pair": best_pair,
        "worst_pair": worst_pair,
    }


def compute_team_synergy(team: list[dict]) -> dict:
    if len(team) < 2:
        return {
            "total_score": 0.0,
            "dominant_archetype": "Sin definir",
            "archetype_scores": {arch: 0.0 for arch in ARCHETYPES},
            "pairwise_scores": {},
            "strengths": ["Completa picks para analizar sinergias reales."],
            "weaknesses": ["Aun no hay suficientes campeones seleccionados."],
            "tips": ["Empieza por fijar una condicion de victoria."],
            "breakdown": {},
            "best_pair": "",
            "worst_pair": "",
        }
    pure_result = compute_team_synergy_mode1(team)
    archetype_scores = compute_archetype_scores(team)
    dominant = max(archetype_scores, key=archetype_scores.get)
    pairwise = {
        pair_name.replace(" + ", " - "): pair_score
        for pair_name, pair_score in pure_result.get("pair_scores", {}).items()
    }
    raw_total = float(pure_result["total_score"])
    role_penalty = compute_role_coherence_penalty(team)
    curve_result = evaluate_team_curve(team)
    curve_adjustment = 0.0
    if curve_result["coherence"] >= 80:
        curve_adjustment = 3.0
    elif curve_result["coherence"] < 40:
        curve_adjustment = -4.0

    adjusted_raw = max(1.0, min(100.0, raw_total - role_penalty + curve_adjustment))
    normalized_total = normalize_score_percentile(adjusted_raw)

    analysis = generate_team_analysis(team, raw_total, archetype_scores, pairwise)
    sorted_pairs = sorted(pairwise.items(), key=lambda item: item[1], reverse=True)
    return {
        "total_score": raw_total,
        "display_score": normalized_total,
        "raw_total_score": round(raw_total, 1),
        "adjusted_raw_score": round(adjusted_raw, 1),
        "dominant_archetype": dominant,
        "archetype_scores": archetype_scores,
        "pairwise_scores": pairwise,
        "curve": curve_result,
        "curve_adjustment": round(curve_adjustment, 1),
        "role_coherence_penalty": role_penalty,
        "breakdown": {
            "mode1_depth_bonus": pure_result.get("depth_bonus", 0.0),
            "mode1_consistency_bonus": pure_result.get("consistency_bonus", 0.0),
            "mode1_signature_bonus": pure_result.get("signature_bonus", 0.0),
            "role_coherence_penalty": role_penalty,
            "curve_adjustment": round(curve_adjustment, 1),
            "raw_total_score": round(raw_total, 1),
            "adjusted_raw_score": round(adjusted_raw, 1),
        },
        "best_pairs": sorted_pairs[:3],
        "synergy_highlights": pure_result.get("synergy_highlights", []),
        **analysis,
    }


def compute_gap_filling_bonus(candidate: dict, current_team: list[dict]) -> float:
    bonus = 0.0
    all_tags = [tag for champ in current_team for tag in champ["ability_tags"]]
    all_damage = [dt for champ in current_team for dt in champ["damage_type"]]

    gaps = [
        ("WAVECLEAR", "WAVECLEAR" not in all_tags, 15),
        ("HARD_ENGAGE", not any(tag in all_tags for tag in {"HARD_ENGAGE", "AOE_KNOCKUP", "DIVE_ENGAGE"}), 20),
        ("PEEL", "PEEL" not in all_tags, 15),
        ("OBJECTIVE_CONTROL", "OBJECTIVE_CONTROL" not in all_tags, 10),
    ]
    for gap_tag, has_gap, gap_value in gaps:
        if has_gap and gap_tag in candidate["ability_tags"]:
            bonus += gap_value

    if "AP" not in all_damage and "AP" in candidate["damage_type"]:
        bonus += 20
    if "AD" not in all_damage and "AD" in candidate["damage_type"]:
        bonus += 20
    return min(bonus, 100)


def _reason_no_context(candidate: dict) -> str:
    pro = candidate.get("pro_tier", 5)
    roles = "/".join(candidate.get("roles", []))
    archs = [arch for arch, value in candidate.get("archetype_fit", {}).items() if value >= 70][:2]
    arch_str = ", ".join(archs) if archs else "versatil"
    if pro >= 9:
        return f"Tier S en meta - {arch_str}"
    if pro >= 7:
        return f"Alta prioridad - {arch_str}"
    return f"Pick solido - {roles}"


def _reason_contextual(
    candidate: dict,
    current_team: list[dict],
    delta: float,
    specific_score: float,
    gap_bonus: float,
    arch_fit: float,
    dominant_arch: str,
) -> str:
    reasons = []
    best_ally_name = ""
    best_ally_score = 0.0
    cand_name = candidate.get("name", "")
    cand_tags = set(candidate.get("ability_tags", []))

    for ally in current_team:
        ally_name = ally.get("name", "")
        ally_tags = set(ally.get("ability_tags", []))
        passive_bonus = get_passive_interaction_bonus(cand_name, ally_name)
        iconic_bonus = get_iconic_combo_bonus(cand_name, ally_name)
        enables = len(set(candidate.get("synergy_keys", {}).get("enables", [])) & ally_tags)
        enables += len(set(ally.get("synergy_keys", {}).get("enables", [])) & cand_tags)
        score = passive_bonus + iconic_bonus + (enables * 6)
        if score > best_ally_score:
            best_ally_score = score
            best_ally_name = ally_name

    if best_ally_score >= 15 and best_ally_name:
        reasons.append(f"Combo directo con {best_ally_name}")
    elif delta >= 12:
        reasons.append(f"Mejora esta compo +{delta:.0f} pts de sinergia")
    elif specific_score >= 40:
        reasons.append("Alta sinergia mecanica con el equipo actual")

    if gap_bonus >= 20:
        if "WAVECLEAR" in candidate.get("ability_tags", []):
            reasons.append("Cubre el waveclear que falta")
        elif any(tag in candidate.get("ability_tags", []) for tag in {"HARD_ENGAGE", "AOE_KNOCKUP", "DIVE_ENGAGE"}):
            reasons.append("Anade el engage que necesita la compo")
        elif any(tag in candidate.get("ability_tags", []) for tag in {"PEEL", "HARD_PEEL", "ANTI_ASSASSIN"}):
            reasons.append("Da el peel que necesita el carry")
        elif "AP" in candidate.get("damage_type", []):
            reasons.append("Equilibra el dano magico")
        elif "AD" in candidate.get("damage_type", []):
            reasons.append("Equilibra el dano fisico")

    if arch_fit >= 80:
        reasons.append(f"Fit perfecto para compo {dominant_arch}")
    elif arch_fit >= 60:
        reasons.append(f"Encaja con la identidad {dominant_arch}")

    if not reasons:
        reasons.append(f"Delta contextual: {delta:+.1f}")

    return "  ·  ".join(reasons[:2])


def _apply_diversity_pass(scored: list[dict], max_results: int = 10) -> list[dict]:
    if len(scored) <= 3:
        return scored[:max_results]

    def dominant_archetype(champion: dict) -> str:
        fits = champion.get("archetype_fit", {})
        if not fits:
            return "unknown"
        return max(fits, key=fits.get)

    locked = scored[:3]
    remaining = [dict(item) for item in scored[3:]]
    seen_archs = {dominant_archetype(item["champion"]) for item in locked}
    seen_roles = {item["champion"].get("roles", ["?"])[0] for item in locked}

    for item in remaining:
        arch = dominant_archetype(item["champion"])
        role = item["champion"].get("roles", ["?"])[0]
        arch_bonus = 5.0 if arch not in seen_archs else -3.0
        role_bonus = 2.0 if role not in seen_roles else 0.0
        item["total_score"] = round(min(100.0, item["total_score"] + arch_bonus + role_bonus), 1)
        seen_archs.add(arch)
        seen_roles.add(role)

    diversified = locked + remaining
    diversified.sort(
        key=lambda item: (-item["total_score"], item["champion"].get("name", ""))
    )
    return diversified[:max_results]


def get_top10_recommendations(
    current_team: list[dict],
    target_role: str,
    all_champions: dict,
    already_picked: list[str],
    pure_only: bool = True,
) -> list[dict]:
    candidates = [
        champ
        for name, champ in all_champions.items()
        if target_role in champ.get("roles", []) and name not in already_picked
    ]

    if not candidates:
        return []

    if not current_team:
        scored = []
        for candidate in candidates:
            role_versatility = len(candidate.get("roles", [])) * 4
            arch_breadth = sum(
                1 for value in candidate.get("archetype_fit", {}).values() if value >= 65
            ) * 3
            score = (candidate.get("pro_tier", 5) * 10) + role_versatility + arch_breadth
            scored.append(
                {
                    "champion": candidate,
                    "total_score": round(min(score, 100.0), 1),
                    "delta": 0.0,
                    "specificity": 0.0,
                    "arch_fit": 0.0,
                    "gap": 0.0,
                    "_hyp_score": 0.0,
                    "reason": _reason_no_context(candidate),
                }
            )
        scored.sort(key=lambda item: (-item["total_score"], item["champion"].get("name", "")))
        return scored[:10]

    current_result = compute_team_synergy_mode1(current_team)
    current_score = current_result["total_score"]
    archetype_scores = compute_archetype_scores(current_team)
    dominant_arch = max(archetype_scores, key=archetype_scores.get)
    dominant_value = archetype_scores[dominant_arch]
    team_tags = {tag for champion in current_team for tag in champion.get("ability_tags", [])}

    raw_scored = []
    for candidate in candidates:
        candidate_tags = set(candidate.get("ability_tags", []))
        candidate_name = candidate.get("name", "")

        hypothetical = compute_team_synergy_mode1(current_team + [candidate])
        hypothetical_score = hypothetical["total_score"]
        delta = hypothetical_score - current_score
        delta_norm = max(0.0, min(100.0, (delta + 20.0) * 2.0))

        specific_score = 0.0
        for ally in current_team:
            ally_tags = set(ally.get("ability_tags", []))
            ally_name = ally.get("name", "")
            enables = len(set(candidate.get("synergy_keys", {}).get("enables", [])) & ally_tags)
            enables += len(set(ally.get("synergy_keys", {}).get("enables", [])) & candidate_tags)
            amplifies = len(set(candidate.get("synergy_keys", {}).get("amplifies", [])) & ally_tags)
            amplifies += len(set(ally.get("synergy_keys", {}).get("amplifies", [])) & candidate_tags)
            passive_bonus = get_passive_interaction_bonus(candidate_name, ally_name)
            iconic_bonus = get_iconic_combo_bonus(candidate_name, ally_name)
            specific_score += (enables * 8) + (amplifies * 6) + passive_bonus + iconic_bonus
        specific_norm = min(100.0, specific_score * 2.5)

        gap_bonus = compute_gap_filling_bonus(candidate, current_team)
        gap_norm = min(100.0, gap_bonus)

        arch_fit = candidate.get("archetype_fit", {}).get(dominant_arch, 0.0)
        arch_weight = min(1.0, dominant_value / 70.0)
        arch_norm = arch_fit * arch_weight

        requires_met = len(set(candidate.get("synergy_keys", {}).get("requires", [])) & team_tags)
        requires_norm = min(100.0, requires_met * 20.0)

        passive_interaction_count = sum(1 for key in PASSIVE_INTERACTIONS if candidate_name in key)
        universal_penalty = min(10.0, passive_interaction_count * 0.6)

        total = (
            (delta_norm * 0.45)
            + (specific_norm * 0.35)
            + (gap_norm * 0.08)
            + (arch_norm * 0.07)
            + (requires_norm * 0.05)
            - universal_penalty
        )
        total = max(0.0, min(100.0, round(total, 1)))

        raw_scored.append(
            {
                "champion": candidate,
                "total_score": total,
                "delta": round(delta, 1),
                "specificity": round(specific_norm, 1),
                "arch_fit": round(arch_fit, 1),
                "gap": round(gap_norm, 1),
                "_hyp_score": round(hypothetical_score, 1),
                "reason": _reason_contextual(
                    candidate,
                    current_team,
                    delta,
                    specific_score,
                    gap_bonus,
                    arch_fit,
                    dominant_arch,
                ),
            }
        )

    raw_scored.sort(key=lambda item: (-item["total_score"], item["champion"].get("name", "")))
    return _apply_diversity_pass(raw_scored, max_results=10)


def get_top5_recommendations(*args, **kwargs):
    return get_top10_recommendations(*args, **kwargs)


class SynergyEngine:
    def __init__(self, champion_pool: dict[str, dict]):
        self.champion_pool = {
            name: info for name, info in champion_pool.items()
            if isinstance(info, dict) and "roles" in info
        }

    def get_candidates_for_role(self, role: str, excluded: set[str] | None = None) -> list[str]:
        excluded = excluded or set()
        return sorted(
            [
                name
                for name, info in self.champion_pool.items()
                if role in info.get("roles", []) and name not in excluded
            ]
        )

    def compute_suggestions(
        self,
        picks: dict[str, str | None],
        limit: int = 10,
        pure_only: bool = False,
        include_filled_roles: bool = False,
    ) -> dict[str, list[dict]]:
        selected_names = [name for name in picks.values() if name]
        current_team = [self.champion_pool[name] for name in selected_names]
        results = {}
        for role in ROLES:
            current_pick = picks.get(role)
            if current_pick and not include_filled_roles:
                continue
            role_team = current_team
            role_already_picked = selected_names
            if current_pick:
                role_team = [
                    champion for champion in current_team if champion["name"] != current_pick
                ]
                role_already_picked = [name for name in selected_names if name != current_pick]
            results[role] = get_top10_recommendations(
                current_team=role_team,
                target_role=role,
                all_champions=self.champion_pool,
                already_picked=role_already_picked,
                pure_only=pure_only,
            )[:limit]
        return results

    def analyze_team(self, picks: dict[str, str | None], pure_only: bool = False) -> dict:
        team = [self.champion_pool[name] for name in picks.values() if name]
        if pure_only:
            return compute_team_synergy_mode1(team)
        return compute_team_synergy(team)

    def generate_composition_pool(self, archetype: str, limit: int = 250) -> list[dict]:
        from logic.mode2_generator import generate_composition_catalog

        requested_archetype = normalize_archetype_name(archetype)
        catalog = generate_composition_catalog(requested_archetype, self.champion_pool, limit=limit)
        results = []
        for index, entry in enumerate(catalog, start=1):
            team = entry["team"]
            picks = {role: champ["name"] for role, champ in zip(ROLES, team)}
            live_synergy = entry["live_synergy"]
            pure_synergy = entry["pure_synergy"]
            archetype_score = live_synergy["archetype_scores"].get(requested_archetype, 0.0)
            highlights = pure_synergy.get("synergy_highlights", [])
            strengths = live_synergy.get("strengths", [])
            summary_parts = []
            if highlights:
                summary_parts.append(highlights[0])
            if strengths:
                summary_parts.append(strengths[0])
            if not summary_parts:
                summary_parts.append("mantiene una estructura clara y herramientas coherentes entre roles")
            explanation = (
                f"Identidad {requested_archetype}: {archetype_score:.1f}/100. "
                f"Sinergia interna: {pure_synergy['total_score']:.1f}/100. "
                + " | ".join(summary_parts[:2])
                + "."
            )
            results.append(
                {
                    "variant_index": index,
                    "picks": picks,
                    "explanation": explanation,
                    "archetype_score": round(archetype_score, 1),
                    "team_score": live_synergy["total_score"],
                    "synergy_score": pure_synergy["total_score"],
                    "combined_score": entry["combined_score"],
                }
            )
        return results

    def generate_composition(self, archetype: str, randomize: bool = False) -> dict:
        pool_limit = 64 if randomize else 1
        pool = self.generate_composition_pool(archetype, limit=pool_limit)
        if not pool:
            from logic.mode2_generator import generate_best_composition

            requested_archetype = normalize_archetype_name(archetype)
            team = generate_best_composition(requested_archetype, self.champion_pool, randomize=randomize)
            picks = {role: champ["name"] for role, champ in zip(ROLES, team)}
            live_synergy = compute_team_synergy(team)
            pure_synergy = compute_team_synergy_mode1(team)
            archetype_score = live_synergy["archetype_scores"].get(requested_archetype, 0.0)
            return {
                "picks": picks,
                "explanation": (
                    f"Identidad {requested_archetype}: {archetype_score:.1f}/100. "
                    f"Sinergia interna: {pure_synergy['total_score']:.1f}/100."
                ),
                "archetype_score": round(archetype_score, 1),
                "team_score": live_synergy["total_score"],
                "synergy_score": pure_synergy["total_score"],
            }
        return pool[0] if not randomize else random.choice(pool[: min(24, len(pool))])
