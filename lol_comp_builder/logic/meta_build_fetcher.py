from __future__ import annotations

import threading
import time
from collections.abc import Iterable

import requests

from logic.genetic_build_optimizer import OptimizationTarget, ROLE_DEFAULT_TARGET

QDATA_URL = "https://lolalytics.com/lol/{champion}/build/q-data.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://lolalytics.com/",
}
DEFAULT_PARAMS = {
    "tier": "emerald_plus",
}
REQUEST_TIMEOUT = 10
CACHE_TTL = 15 * 60
CACHE_TTL_FALLBACK = 5 * 60
LANE_FALLBACK_ORDER = ("top", "jungle", "middle", "bottom", "support")
CHAMPION_SLUG_ALIASES = {
    "Dr. Mundo": "drmundo",
    "Jarvan IV": "jarvaniv",
    "K'Sante": "ksante",
    "Nunu & Willump": "nunu",
    "Renata Glasc": "renata",
}
QDATA_BUILD_KEYS = ("item1", "boots", "item2", "item3", "item4", "item5")
QDATA_REQUIRED_BUILD_KEYS = ("header", "item1", "item2", "item3", "boots")
PRIMARY_STYLE_IDS = {8000, 8100, 8200, 8300, 8400}
STAT_SHARD_IDS = {5001, 5002, 5003, 5005, 5007, 5008}

_cache: dict[str, dict] = {}
_lock = threading.Lock()


def _http_get_json(url: str, *, params: dict) -> dict:
    session = requests.Session()
    session.trust_env = False
    response = session.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def _build_champion_slug(champion: str) -> str:
    alias = CHAMPION_SLUG_ALIASES.get(champion)
    if alias:
        return alias
    return champion.lower().replace("'", "").replace(" ", "").replace(".", "").replace("&", "")


def _resolve_qdata_ref(ref: str, objects: list, seen: set[int] | None = None):
    if not isinstance(ref, str):
        return ref
    try:
        index = int(ref, 36)
    except Exception:
        return ref
    if index < 0 or index >= len(objects):
        return ref
    next_seen = set(seen or ())
    if index in next_seen:
        return ref
    next_seen.add(index)
    return _resolve_qdata_value(objects[index], objects, next_seen)


def _resolve_qdata_value(value, objects: list, seen: set[int] | None = None):
    if isinstance(value, str):
        return _resolve_qdata_ref(value, objects, seen)
    if isinstance(value, list):
        return [_resolve_qdata_value(entry, objects, set(seen or ())) for entry in value]
    if isinstance(value, dict):
        return {key: _resolve_qdata_value(entry, objects, set(seen or ())) for key, entry in value.items()}
    return value


def _iter_qdata_build_payloads(objects: list) -> list[dict]:
    matches: list[dict] = []
    for entry in objects:
        if not isinstance(entry, dict):
            continue
        if all(key in entry for key in QDATA_REQUIRED_BUILD_KEYS):
            matches.append(entry)
    return matches


def _extract_header_lane(raw_data: dict, objects: list) -> str:
    header = _resolve_qdata_value(raw_data.get("header"), objects)
    if not isinstance(header, dict):
        return ""
    return str(header.get("lane", "")).strip().lower()


def _score_qdata_build_payload(raw_data: dict, objects: list, requested_lane: str) -> tuple[int, int, int, int]:
    header = _resolve_qdata_value(raw_data.get("header"), objects)
    header_lane = str(header.get("lane", "")).strip().lower() if isinstance(header, dict) else ""
    lane_match = 1 if requested_lane and header_lane == requested_lane else 0
    slot_count = sum(1 for key in QDATA_BUILD_KEYS if key in raw_data)
    has_item_sets = 1 if "itemSets" in raw_data else 0
    games = 0
    if isinstance(header, dict):
        try:
            games = int(float(header.get("n", 0) or 0))
        except Exception:
            games = 0
    return (lane_match, slot_count, has_item_sets, games)


def _find_qdata_build_payload(objects: list, requested_lane: str = "") -> dict | None:
    candidates = _iter_qdata_build_payloads(objects)
    if not candidates:
        return None
    return max(candidates, key=lambda entry: _score_qdata_build_payload(entry, objects, requested_lane))


def _normalize_item_row(row) -> dict | None:
    if not isinstance(row, list) or len(row) < 5:
        return None
    try:
        return {
            "item_id": int(row[0]),
            "winrate": float(row[1]),
            "pickrate": float(row[2]),
            "games": int(row[3]),
            "time": float(row[4]),
        }
    except Exception:
        return None


def _first_item_row(rows) -> dict | None:
    if not isinstance(rows, list):
        return None
    for row in rows:
        normalized = _normalize_item_row(row)
        if normalized and normalized["item_id"] > 0:
            return normalized
    return None


def _unique_rows_in_time_order(rows: Iterable[tuple[str, dict | None]]) -> list[dict]:
    ordered: list[tuple[int, int, dict]] = []
    for fallback_index, (_, row) in enumerate(rows):
        if row is None:
            continue
        ordered.append((int(row["time"]), fallback_index, row))
    ordered.sort(key=lambda entry: (entry[0], entry[1]))

    unique: list[dict] = []
    seen_ids: set[int] = set()
    for _, _, row in ordered:
        item_id = int(row["item_id"])
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        unique.append(row)
    return unique


def _best_rune_row(rows, index: int = 0) -> tuple[float, float, int]:
    if not isinstance(rows, list) or index >= len(rows):
        return (0.0, 0.0, 0)
    row = rows[index]
    if not isinstance(row, list) or len(row) < 3:
        return (0.0, 0.0, 0)
    try:
        return (float(row[0]), float(row[1]), int(row[2]))
    except Exception:
        return (0.0, 0.0, 0)


def _extract_runes_from_sections(resolved_sections: dict, requested_lane: str) -> dict:
    runes_payload = resolved_sections.get("runes")
    if not isinstance(runes_payload, dict):
        return {
            "primary_style_id": 0,
            "secondary_style_id": 0,
            "primary_runes": [],
            "secondary_runes": [],
            "stat_shards": [],
            "stats": {},
            "found": False,
            "requested_lane": requested_lane,
        }

    stats = runes_payload.get("stats", {})
    if not isinstance(stats, dict):
        stats = {}

    primary_style_id = 0
    primary_games = -1
    primary_pickrate = -1.0
    for rune_id_str, rows in stats.items():
        try:
            rune_id = int(rune_id_str)
        except Exception:
            continue
        if rune_id not in PRIMARY_STYLE_IDS:
            continue
        _, pickrate, games = _best_rune_row(rows, 0)
        if games > primary_games or (games == primary_games and pickrate > primary_pickrate):
            primary_games = games
            primary_pickrate = pickrate
            primary_style_id = rune_id

    secondary_style_id = 0
    secondary_games = -1
    secondary_pickrate = -1.0
    for rune_id_str, rows in stats.items():
        try:
            rune_id = int(rune_id_str)
        except Exception:
            continue
        if rune_id not in PRIMARY_STYLE_IDS or rune_id == primary_style_id:
            continue
        _, pickrate, games = _best_rune_row(rows, 1)
        if games > secondary_games or (games == secondary_games and pickrate > secondary_pickrate):
            secondary_games = games
            secondary_pickrate = pickrate
            secondary_style_id = rune_id

    primary_runes: list[int] = []
    secondary_runes: list[int] = []
    stat_shards: list[int] = []
    for rune_id_str, rows in stats.items():
        try:
            rune_id = int(rune_id_str)
        except Exception:
            continue
        if rune_id in PRIMARY_STYLE_IDS:
            continue
        if rune_id in STAT_SHARD_IDS:
            _, pickrate, games = _best_rune_row(rows, 0)
            if games > 0 or pickrate > 0:
                stat_shards.append(rune_id)
            continue
        primary_row = _best_rune_row(rows, 0)
        secondary_row = _best_rune_row(rows, 1)
        if primary_row[2] > 0:
            primary_runes.append(rune_id)
        if secondary_row[2] > 0:
            secondary_runes.append(rune_id)

    return {
        "primary_style_id": primary_style_id,
        "secondary_style_id": secondary_style_id,
        "primary_runes": primary_runes,
        "secondary_runes": secondary_runes,
        "stat_shards": stat_shards,
        "stats": stats,
        "found": bool(primary_style_id or primary_runes or secondary_runes or stat_shards),
        "requested_lane": requested_lane,
    }


def _extract_meta_from_qdata(payload: dict, requested_lane: str = "") -> dict:
    objects = payload.get("_objs", [])
    if not isinstance(objects, list) or not objects:
        raise ValueError("q-data payload sin objetos")

    normalized_requested_lane = str(requested_lane or "").strip().lower()
    raw_data = _find_qdata_build_payload(objects, normalized_requested_lane)
    if raw_data is None:
        raise ValueError("q-data sin secciones de build")

    resolved_sections = {
        key: _resolve_qdata_value(raw_data[key], objects)
        for key in ("header", "runes", *QDATA_BUILD_KEYS, "itemSets", "popularItem", "winningItem")
        if key in raw_data
    }

    slot_rows = [(key, _first_item_row(resolved_sections.get(key))) for key in QDATA_BUILD_KEYS if key in resolved_sections]
    ordered_rows = _unique_rows_in_time_order(slot_rows)

    for fallback_key in ("popularItem", "winningItem"):
        if len(ordered_rows) >= 6:
            break
        fallback_rows = resolved_sections.get(fallback_key)
        if not isinstance(fallback_rows, list):
            continue
        for row in fallback_rows:
            normalized = _normalize_item_row(row)
            if normalized is None:
                continue
            if any(existing["item_id"] == normalized["item_id"] for existing in ordered_rows):
                continue
            ordered_rows.append(normalized)
            if len(ordered_rows) >= 6:
                break

    full_build = [int(row["item_id"]) for row in ordered_rows[:6]]
    non_boots = [int(row["item_id"]) for key, row in slot_rows if key != "boots" and row is not None]
    representative = next((row for key, row in reversed(slot_rows) if row is not None and key != "boots"), None)
    header = resolved_sections.get("header", {})
    header_lane = str(header.get("lane", "")).strip().lower() if isinstance(header, dict) else ""
    header_wr = float(header.get("wr", 0.0)) if isinstance(header, dict) and str(header.get("wr", "")).replace(".", "", 1).isdigit() else 0.0
    header_pr = float(header.get("pr", 0.0)) if isinstance(header, dict) and str(header.get("pr", "")).replace(".", "", 1).isdigit() else 0.0

    return {
        "core_items": non_boots[:3],
        "boots": next((row["item_id"] for key, row in slot_rows if key == "boots" and row is not None), None),
        "full_build": full_build,
        "winrate": float(representative["winrate"]) if representative is not None else header_wr,
        "pickrate": float(representative["pickrate"]) if representative is not None else header_pr,
        "found": len(full_build) >= 4,
        "source": "lolalytics-qdata",
        "error": "",
        "requested_lane": normalized_requested_lane,
        "header_lane": header_lane,
        "exact_lane": bool(normalized_requested_lane and header_lane == normalized_requested_lane),
        "build_slots": len(slot_rows),
        "build_size": len(full_build),
        "runes": _extract_runes_from_sections(resolved_sections, normalized_requested_lane),
    }


def _lane_candidates(lane: str) -> list[str]:
    normalized = str(lane or "").strip().lower()
    candidates: list[str] = []
    if normalized:
        candidates.append(normalized)
    for fallback_lane in LANE_FALLBACK_ORDER:
        if fallback_lane not in candidates:
            candidates.append(fallback_lane)
    return candidates


def _fetch_meta_for_lane(champion_slug: str, lane: str) -> dict:
    data = _http_get_json(
        QDATA_URL.format(champion=champion_slug),
        params={**DEFAULT_PARAMS, "lane": lane},
    )
    result = _extract_meta_from_qdata(data, lane)
    result["resolved_lane"] = lane
    return result


def _cache_ttl_for_result(result: dict, requested_lane: str) -> int:
    resolved_lane = str(result.get("resolved_lane", "")).strip().lower()
    header_lane = str(result.get("header_lane", "")).strip().lower()
    requested = str(requested_lane or "").strip().lower()
    if requested and resolved_lane == requested and header_lane == requested:
        return CACHE_TTL
    return CACHE_TTL_FALLBACK


def fetch_meta_build(champion: str, lane: str) -> dict:
    champ_lower = _build_champion_slug(champion)
    cache_key = f"meta_{champ_lower}_{lane}"

    with _lock:
        entry = _cache.get(cache_key)
        if entry and (time.time() - entry["ts"]) < int(entry.get("ttl", CACHE_TTL)):
            return entry["data"]

    result = {
        "core_items": [],
        "boots": None,
        "full_build": [],
        "winrate": 50.0,
        "pickrate": 0.0,
        "found": False,
        "source": "unavailable",
        "error": "",
        "resolved_lane": "",
    }

    last_error = ""
    try:
        for candidate_lane in _lane_candidates(lane):
            try:
                result = _fetch_meta_for_lane(champ_lower, candidate_lane)
                if candidate_lane != str(lane or "").strip().lower():
                    result["source"] = f'{result["source"]}:fallback:{candidate_lane}'
                break
            except Exception as exc:
                last_error = str(exc)
        else:
            raise ValueError(last_error or f"sin build para {champion}")
    except Exception as exc:
        result["error"] = str(exc)

    if result.get("found") and not result.get("error"):
        with _lock:
            _cache[cache_key] = {"data": result, "ts": time.time(), "ttl": _cache_ttl_for_result(result, lane)}
    return result


def infer_target_from_meta(meta_build: dict, all_items: dict[int, dict]) -> str:
    if not meta_build.get("found"):
        return OptimizationTarget.PHYSICAL_DPS

    totals = {
        "ad": 0.0,
        "ap": 0.0,
        "armor": 0.0,
        "mr": 0.0,
        "hp": 0.0,
        "lethality": 0.0,
        "lifesteal": 0.0,
        "ah": 0.0,
    }

    for item_id in meta_build.get("full_build", []):
        item = all_items.get(int(item_id), {})
        for stat, value in item.get("stats", {}).items():
            if stat in totals:
                totals[stat] += float(value)

    if totals["lethality"] > 15:
        return OptimizationTarget.LETHALITY
    if totals["ap"] > 60:
        return OptimizationTarget.MAGIC_DPS
    if totals["armor"] > 60 or totals["mr"] > 60 or totals["hp"] > 800:
        return OptimizationTarget.TANK_ARMOR if totals["armor"] >= totals["mr"] else OptimizationTarget.TANK_MR
    if totals["ah"] > 20 and totals["ad"] < 30 and totals["ap"] < 30:
        return OptimizationTarget.UTILITY
    if totals["lifesteal"] > 0.10:
        return OptimizationTarget.LIFESTEAL_DPS
    if totals["ad"] > 30 and totals["ap"] > 30:
        return OptimizationTarget.HYBRID_DPS
    return OptimizationTarget.PHYSICAL_DPS


def infer_target_for_context(
    meta_build: dict,
    all_items: dict[int, dict],
    champion_record: dict | None = None,
    role: str = "middle",
) -> str:
    if meta_build.get("found"):
        return infer_target_from_meta(meta_build, all_items)

    record = champion_record or {}
    damage_types = {str(value).upper() for value in record.get("damage_type", []) if str(value).strip()}
    roles = {str(value).upper() for value in record.get("roles", []) if str(value).strip()}
    range_type = str(record.get("range_type", "")).upper()

    if damage_types == {"AP"}:
        if "SUPPORT" in roles:
            return OptimizationTarget.UTILITY
        return OptimizationTarget.MAGIC_DPS
    if damage_types == {"AD", "AP"} or damage_types == {"AP", "AD"}:
        return OptimizationTarget.HYBRID_DPS
    if "SUPPORT" in roles:
        return OptimizationTarget.UTILITY
    if "TOP" in roles and not damage_types:
        return OptimizationTarget.TANK_HP
    if range_type == "RANGED" and "BOTTOM" in roles:
        return OptimizationTarget.PHYSICAL_DPS

    return ROLE_DEFAULT_TARGET.get(role, OptimizationTarget.PHYSICAL_DPS)


def builds_are_similar(meta_items: list[int], ga_items: list[int], threshold: float = 0.5) -> bool:
    if not meta_items or not ga_items:
        return False
    meta_set = set(meta_items)
    ga_set = set(ga_items)
    overlap = len(meta_set & ga_set)
    return (overlap / max(1, len(meta_set))) >= threshold
