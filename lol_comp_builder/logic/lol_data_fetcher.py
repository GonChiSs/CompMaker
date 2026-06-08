from __future__ import annotations

import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://lolalytics.com/lol"
TIER_URL = f"{BASE_URL}/tierlist/api/"
BUILD_URL = f"{BASE_URL}/{{champion}}/build/api/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://lolalytics.com/",
    "Origin": "https://lolalytics.com",
}

DEFAULT_PARAMS = {
    "patch": "current",
    "tier": "platinum_plus",
    "region": "all",
    "queue": "420",
}

CACHE_TTL = 15 * 60
REQUEST_TIMEOUT = 10
DDRAGON_FALLBACK_VERSION = "16.11.1"
MAX_TIERLIST_WORKERS = 24
BOOT_ITEM_IDS = {
    1001, 3005, 3006, 3009, 3047, 3111, 3117, 3158, 2422, 2501, 2502, 3010, 3020,
    3118, 4005, 4643, 4638, 1459, 1460, 1461, 1462, 3170,
}

_cache: dict[str, dict[str, Any]] = {}
_cache_lock = threading.Lock()
_ddragon_version: str | None = None
_ddragon_lock = threading.Lock()


def _normalize_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _get_cached(key: str) -> Any | None:
    with _cache_lock:
        entry = _cache.get(key)
        if entry and (time.time() - entry["ts"]) < CACHE_TTL:
            return entry["data"]
    return None


def _set_cached(key: str, data: Any) -> None:
    with _cache_lock:
        _cache[key] = {"data": data, "ts": time.time()}


def _get_ddragon_version() -> str:
    global _ddragon_version
    with _ddragon_lock:
        if _ddragon_version:
            return _ddragon_version
        try:
            response = requests.get(
                "https://ddragon.leagueoflegends.com/api/versions.json",
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            versions = response.json()
            if versions:
                _ddragon_version = versions[0]
                return _ddragon_version
        except Exception:
            pass
        _ddragon_version = DDRAGON_FALLBACK_VERSION
        return _ddragon_version


def fetch_tier_list(lane: str, champion_names: list[str] | None = None) -> list[dict]:
    cache_key = f"tier::{lane}::{'all' if not champion_names else len(champion_names)}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    items = _fetch_tier_list_api(lane) or _fetch_rendered_tier_list(lane)
    normalized: dict[str, dict] = {}
    for item in items:
        norm_id = item.get("norm_id") or _normalize_name(item.get("id", ""))
        if not norm_id:
            continue
        normalized[norm_id] = {
            "id": item.get("id", ""),
            "norm_id": norm_id,
            "tier": str(item.get("tier") or "C").upper()[:1],
            "rank": int(item.get("rank") or 999),
            "winrate": float(item.get("winrate") or 50.0),
            "pickrate": float(item.get("pickrate") or 0.0),
            "games": int(item.get("games") or 0),
        }

    if champion_names:
        missing = [name for name in champion_names if _normalize_name(name) not in normalized]
        if missing:
            snapshots = _fetch_missing_champion_snapshots(missing, lane)
            normalized.update(snapshots)

    result = sorted(normalized.values(), key=lambda item: item["rank"])
    _set_cached(cache_key, result)
    return result


def fetch_matchup_data(champion: str, lane: str) -> dict:
    champion_key = _normalize_name(champion)
    cache_key = f"matchup::{champion_key}::{lane}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    result = _fetch_matchup_api(champion_key, lane)
    if not result["counters"] and not result["best_build"]:
        result = _fetch_champion_page_snapshot(champion, lane)
    _set_cached(cache_key, result)
    return result


def filter_boots(item_ids: list[int], limit: int = 6) -> list[int]:
    filtered = [item_id for item_id in item_ids if item_id not in BOOT_ITEM_IDS]
    return filtered[:limit]


def _fetch_tier_list_api(lane: str) -> list[dict]:
    try:
        response = requests.get(
            TIER_URL,
            params={**DEFAULT_PARAMS, "lane": lane},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        if not response.ok:
            return []
        data = response.json()
        items = data.get("tierListItems") or data.get("data") or []
        return [_normalize_tier_item(item) for item in items if item]
    except Exception:
        return []


def _fetch_rendered_tier_list(lane: str) -> list[dict]:
    try:
        response = requests.get(
            f"{BASE_URL}/tierlist/",
            headers=HEADERS,
            params={"lane": lane, "tier": DEFAULT_PARAMS["tier"]},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return _parse_rendered_tier_rows(response.text)
    except Exception:
        return []


def _fetch_matchup_api(champion_key: str, lane: str) -> dict:
    empty = {"counters": [], "best_build": [], "start_items": []}
    try:
        response = requests.get(
            BUILD_URL.format(champion=champion_key),
            params={**DEFAULT_PARAMS, "lane": lane},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        if not response.ok:
            return empty
        return _extract_matchup_payload(response.json())
    except Exception:
        return empty


def _normalize_tier_item(item: dict) -> dict:
    champ_id = item.get("id") or item.get("name") or item.get("champion") or ""
    return {
        "id": champ_id,
        "norm_id": _normalize_name(champ_id),
        "tier": str(item.get("tier") or "C").upper()[:1],
        "rank": int(item.get("rank") or 999),
        "winrate": float(item.get("winrate") or item.get("wr") or 50.0),
        "pickrate": float(item.get("pickrate") or item.get("pr") or 0.0),
        "games": int(item.get("games") or 0),
    }


def _extract_matchup_payload(data: dict) -> dict:
    raw_counters = data.get("counters", {}).get("counters") or data.get("counters") or []
    counters = sorted(
        [
            {
                "id": item.get("id") or item.get("champion") or "",
                "norm_id": _normalize_name(item.get("id") or item.get("champion") or ""),
                "winrate": float(item.get("wr") or item.get("winrate") or 50.0),
                "games": int(item.get("games") or 0),
            }
            for item in raw_counters
            if item.get("id") or item.get("champion")
        ],
        key=lambda item: (-item["winrate"], -item["games"]),
    )[:3]

    best_build = [
        int(item_id)
        for item_id in (data.get("items", {}).get("build") or data.get("build") or [])
        if str(item_id).isdigit()
    ]
    start_items = [
        int(item_id)
        for item_id in (data.get("startItems", {}).get("build") or data.get("startBuild") or [])
        if str(item_id).isdigit()
    ]
    return {
        "counters": counters,
        "best_build": filter_boots(best_build),
        "start_items": start_items[:2],
    }


def _fetch_missing_champion_snapshots(champion_names: list[str], lane: str) -> dict[str, dict]:
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=MAX_TIERLIST_WORKERS) as executor:
        futures = {
            executor.submit(_fetch_champion_tier_snapshot, champion_name, lane): champion_name
            for champion_name in champion_names
        }
        for future in as_completed(futures):
            snapshot = future.result()
            if snapshot:
                results[snapshot["norm_id"]] = snapshot
    return results


def _fetch_champion_tier_snapshot(champion_name: str, lane: str) -> dict | None:
    cache_key = f"champion_tier::{_normalize_name(champion_name)}::{lane}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    snapshot = _fetch_champion_page_snapshot(champion_name, lane)
    tier = snapshot.get("tier")
    rank = snapshot.get("rank")
    if not tier or rank is None:
        return None
    result = {
        "id": champion_name,
        "norm_id": _normalize_name(champion_name),
        "tier": tier,
        "rank": rank,
        "winrate": float(snapshot.get("winrate", 50.0)),
        "pickrate": float(snapshot.get("pickrate", 0.0)),
        "games": int(snapshot.get("games", 0)),
    }
    _set_cached(cache_key, result)
    return result


def _fetch_champion_page_snapshot(champion: str, lane: str) -> dict:
    champion_key = _normalize_name(champion)
    cache_key = f"champion_page::{champion_key}::{lane}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    empty = {
        "counters": [],
        "best_build": [],
        "start_items": [],
        "tier": None,
        "rank": None,
        "winrate": 50.0,
        "pickrate": 0.0,
        "games": 0,
    }
    try:
        response = requests.get(
            f"{BASE_URL}/{champion_key}/build/",
            headers=HEADERS,
            params={"lane": lane, "tier": DEFAULT_PARAMS["tier"]},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        result = _parse_rendered_matchup(response.text)
        _set_cached(cache_key, result)
        return result
    except Exception:
        return empty


def _parse_rendered_tier_rows(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    for row in soup.find_all("div"):
        class_text = " ".join(row.get("class") or [])
        if "odd:bg-[#181818]" not in class_text or "justify-between" not in class_text:
            continue
        text = row.get_text("|", strip=True)
        if not text:
            continue
        links = row.find_all("a", href=re.compile(r"^/lol/.+/build/"))
        if len(links) < 2:
            continue
        tokens = [token.strip() for token in text.split("|") if token.strip()]
        tier_token = next((token for token in tokens if re.fullmatch(r"[SABCDF][+-]?", token)), None)
        if not tier_token:
            continue
        numbers = [
            float(token.replace(",", ""))
            for token in tokens
            if re.fullmatch(r"\d+(?:,\d{3})*(?:\.\d+)?", token)
        ]
        if len(numbers) < 8:
            continue
        rows.append(
            {
                "id": links[1].get_text(" ", strip=True),
                "norm_id": _normalize_name(links[1].get_text(" ", strip=True)),
                "tier": tier_token[0],
                "rank": int(numbers[0]),
                "winrate": float(numbers[2]),
                "pickrate": float(numbers[4]),
                "games": int(numbers[7]),
            }
        )
    return rows


def _parse_rendered_matchup(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    summary_node = soup.find("p", class_=lambda value: value and "lolx-links" in value)
    summary_text = summary_node.get_text(" ", strip=True) if summary_node else soup.get_text(" ", strip=True)
    summary_html = str(summary_node) if summary_node else html

    counters: list[dict] = []
    summary_match = re.search(r"countered most by (.+?)\.</", summary_html, re.IGNORECASE | re.DOTALL)
    if summary_match:
        names = re.findall(r">([^<]+)</a>", summary_match.group(1))
        for part in names[:3]:
            counters.append(
                {
                    "id": part.strip(),
                    "norm_id": _normalize_name(part),
                    "winrate": 0.0,
                    "games": 0,
                }
            )

    rank_match = re.search(r"rank\s+(\d+)\s+of\s+\d+\s+and graded\s+([SABCDF][+-]?)\s+Tier", summary_text, re.IGNORECASE)
    winrate_match = re.search(r"has a\s+(\d+(?:\.\d+)?)%\s+win rate", summary_text, re.IGNORECASE)

    best_build = _extract_item_ids_from_section(html, "Core Build", max_items=7)
    if len(best_build) < 4:
        best_build = _extract_item_ids_from_section(html, "Highest Win Build", max_items=7) or best_build
    start_items = _extract_item_ids_from_section(html, "Starting Items", max_items=2)

    return {
        "counters": counters,
        "best_build": filter_boots(best_build),
        "start_items": start_items[:2],
        "tier": rank_match.group(2)[0] if rank_match else None,
        "rank": int(rank_match.group(1)) if rank_match else None,
        "winrate": float(winrate_match.group(1)) if winrate_match else 50.0,
        "pickrate": 0.0,
        "games": 0,
    }


def _extract_item_ids_from_section(html: str, label: str, max_items: int) -> list[int]:
    idx = html.find(label)
    if idx == -1:
        return []
    section = html[idx:idx + 14000]
    ids: list[int] = []
    for match in re.finditer(r"/item64/(\d+)\.webp", section):
        item_id = int(match.group(1))
        if item_id not in ids:
            ids.append(item_id)
        if len(ids) >= max_items:
            break
    return ids


def get_item_icon_url(item_id: int, version: str | None = None) -> str:
    resolved_version = version or _get_ddragon_version()
    return f"https://ddragon.leagueoflegends.com/cdn/{resolved_version}/img/item/{item_id}.png"


def fetch_item_pixmap(item_id: int, version: str | None = None) -> bytes | None:
    try:
        resolved_version = version or _get_ddragon_version()
        response = requests.get(
            get_item_icon_url(item_id, resolved_version),
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.content
    except Exception:
        if version is None and resolved_version != DDRAGON_FALLBACK_VERSION:
            try:
                response = requests.get(
                    get_item_icon_url(item_id, DDRAGON_FALLBACK_VERSION),
                    headers=HEADERS,
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                return response.content
            except Exception:
                return None
        return None
