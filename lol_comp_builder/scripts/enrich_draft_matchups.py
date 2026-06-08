from __future__ import annotations

import json
from pathlib import Path


COUNTER_OVERRIDES = {
    "Poppy": {"counters": ["Camille", "Rakan", "Jarvan IV", "Lee Sin", "K'Sante"]},
    "Malphite": {"counters": ["Yasuo", "Tryndamere", "Jinx", "Aphelios", "Zeri"]},
    "Janna": {"counters": ["Rakan", "Hecarim", "Nocturne", "Jarvan IV"]},
    "Lulu": {"counters": ["Zed", "Kha'Zix", "Nocturne", "Rengar"]},
    "Twisted Fate": {"counters": ["Akali", "Katarina", "Yone"]},
    "Taliyah": {"counters": ["Kalista", "Samira", "Rakan", "Zeri", "Lee Sin"]},
    "Caitlyn": {"counters": ["Vayne", "Kog'Maw", "Kai'Sa"]},
    "Xayah": {"counters": ["Rakan", "Hecarim", "Jarvan IV", "Nocturne"]},
    "Vayne": {"counters": ["Sion", "Ornn", "K'Sante", "Tahm Kench"]},
    "Brand": {"counters": ["Ornn", "Sion", "Rell", "Alistar"]},
    "Morgana": {"counters": ["Leona", "Nautilus", "Blitzcrank", "Thresh"]},
    "Trundle": {"counters": ["Sejuani", "Ornn", "Sion", "Rammus"]},
    "Renata Glasc": {"counters": ["Jinx", "Kog'Maw", "Aphelios", "Zeri"]},
    "Blitzcrank": {"counters": ["Jinx", "Aphelios", "Kog'Maw", "Lux"]},
    "Cassiopeia": {"counters": ["K'Sante", "Rakan", "Kalista", "Yasuo"]},
}


def infer_counter_tags(champion: dict) -> list[str]:
    tags = set(champion.get("ability_tags", []))
    result = set(champion.get("counter_tags", []))
    if {"DISENGAGE", "PEEL", "KNOCKBACK_PEEL"} & tags:
        result.add("BEATS_ENGAGE")
    if {"HARD_ENGAGE", "DIVE_ENGAGE", "POINT_AND_CLICK_CC", "PULL"} & tags:
        result.add("BEATS_POKE")
    if {"ANTI_ASSASSIN", "HARD_PEEL", "SHIELD", "INVULNERABILITY"} & tags:
        result.add("BEATS_ASSASSIN")
    if {"PERCENT_HP_DAMAGE", "TRUE_DAMAGE", "SHRED_ARMOR", "SHRED_MR"} & tags:
        result.add("BEATS_TANK")
    if {"GLOBAL_PRESENCE", "ROAM_THREAT", "POINT_AND_CLICK_CC"} & tags:
        result.add("BEATS_SPLIT")
    if {"HARD_ENGAGE", "DIVE_ENGAGE", "EXECUTE", "POINT_AND_CLICK_CC"} & tags:
        result.add("BEATS_HYPERCARRY")
    if {"LONG_RANGE_POKE", "AOE_FOLLOW_UP", "FLANK_ENGAGE"} & tags:
        result.add("BEATS_DISENGAGE")
    return sorted(result)


def add_reverse_relations(payload: dict[str, dict]) -> None:
    for name, champion in payload.items():
        champion.setdefault("counters", [])
        champion.setdefault("countered_by", [])
        champion.setdefault("counter_tags", [])
        for target in champion["counters"]:
            if target in payload:
                enemy = payload[target]
                enemy.setdefault("countered_by", [])
                if name not in enemy["countered_by"]:
                    enemy["countered_by"].append(name)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "data" / "champions_synergy.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    for name, champion in payload.items():
        champion.setdefault("counters", [])
        champion.setdefault("countered_by", [])
        champion.setdefault("counter_tags", [])
        override = COUNTER_OVERRIDES.get(name, {})
        for key, values in override.items():
            merged = list(dict.fromkeys(champion.get(key, []) + values))
            champion[key] = merged
        champion["counter_tags"] = infer_counter_tags(champion)

    add_reverse_relations(payload)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Enriched matchup data for {len(payload)} champions.")


if __name__ == "__main__":
    main()
