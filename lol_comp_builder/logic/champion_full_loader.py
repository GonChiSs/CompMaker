from __future__ import annotations

from logic.item_data_loader import _load_json_cached
from logic.rune_data_loader import strip_html

CHAMP_FULL_URL_TMPL = "https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion/{champion_id}.json"


def load_champion_full(version: str, champion_id: str, force_refresh: bool = False) -> dict | None:
    raw = _load_json_cached(
        CHAMP_FULL_URL_TMPL.format(version=version, champion_id=champion_id),
        f"champ_full_{champion_id}_{version}.json",
        force_refresh=force_refresh,
    )
    if not isinstance(raw, dict):
        return None
    data = raw.get("data", {})
    if not isinstance(data, dict) or not data:
        return None
    champ = next(iter(data.values()))
    passive = champ.get("passive", {}) or {}
    spells = champ.get("spells", []) or []
    keys = ["Q", "W", "E", "R"]
    return {
        "name": str(champ.get("name", champion_id)),
        "title": str(champ.get("title", "")),
        "tags": list(champ.get("tags", []) or []),
        "passive": {
            "name": str(passive.get("name", "")),
            "description": strip_html(passive.get("description", "")),
        },
        "spells": [
            {
                "key": keys[index] if index < 4 else f"S{index}",
                "name": str(spell.get("name", "")),
                "description": strip_html(spell.get("description", "")),
            }
            for index, spell in enumerate(spells)
        ],
        "stats": dict(champ.get("stats", {}) or {}),
    }


def summarize_champion_kit(full_data: dict, max_chars_per_ability: int = 220) -> str:
    if not full_data:
        return ""
    lines = [f"{full_data['name']} - {full_data['title']}"]
    passive = full_data.get("passive", {})
    lines.append(f"PASIVA ({passive.get('name', '')}): {str(passive.get('description', ''))[:max_chars_per_ability]}")
    for spell in full_data.get("spells", []):
        lines.append(
            f"{spell.get('key', '?')} ({spell.get('name', '')}): "
            f"{str(spell.get('description', ''))[:max_chars_per_ability]}"
        )
    return "\n".join(lines)
