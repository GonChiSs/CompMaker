from __future__ import annotations

import re
import threading
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from logic.icon_cache import download_icon
from logic.item_data_loader import _load_json_cached
from logic.patch_versioning import get_current_patch

RUNES_URL_TMPL = "https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/runesReforged.json"
RUNE_ICON_BASE = "https://ddragon.leagueoflegends.com/cdn/img/{icon_path}"

STAT_SHARDS = {
    5001: {"name": "Health Scaling", "icon_url": ""},
    5002: {"name": "Armor", "icon_url": ""},
    5003: {"name": "Magic Resist", "icon_url": ""},
    5005: {"name": "Attack Speed", "icon_url": ""},
    5007: {"name": "Ability Haste", "icon_url": ""},
    5008: {"name": "Adaptive Force", "icon_url": ""},
    5011: {"name": "Health", "icon_url": ""},
    5013: {"name": "Tenacity and Slow Resist", "icon_url": ""},
}


def strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", str(text or ""), flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_runes(version: str, force_refresh: bool = False) -> dict[int, dict]:
    raw = _load_json_cached(
        RUNES_URL_TMPL.format(version=version),
        f"runes_{version}.json",
        force_refresh=force_refresh,
    )
    if not isinstance(raw, list):
        return {}

    result: dict[int, dict] = {}
    for tree in raw:
        tree_id = int(tree.get("id", 0) or 0)
        tree_name = str(tree.get("name", ""))
        tree_icon = RUNE_ICON_BASE.format(icon_path=tree.get("icon", "")) if tree.get("icon") else ""
        if tree_id > 0:
            result[tree_id] = {
                "id": tree_id,
                "name": tree_name,
                "short_desc": "",
                "long_desc": "",
                "icon_url": tree_icon,
                "icon": tree_icon,
                "tree": tree_name,
                "tree_id": tree_id,
                "style_id": tree_id,
                "style_name": tree_name,
                "slot": -1,
                "slot_index": -1,
                "is_style": True,
            }
        for slot_idx, slot in enumerate(tree.get("slots", [])):
            for rune in slot.get("runes", []):
                rune_id = int(rune.get("id", 0) or 0)
                if rune_id <= 0:
                    continue
                result[rune_id] = {
                    "id": rune_id,
                    "name": str(rune.get("name", "")),
                    "short_desc": strip_html(rune.get("shortDesc", "")),
                    "long_desc": strip_html(rune.get("longDesc", "")),
                    "icon_url": RUNE_ICON_BASE.format(icon_path=rune.get("icon", "")),
                    "icon": str(rune.get("icon", "")),
                    "tree": tree_name,
                    "tree_id": tree_id,
                    "style_id": tree_id,
                    "style_name": tree_name,
                    "slot": slot_idx,
                    "slot_index": slot_idx,
                    "is_style": False,
                }

    for rune_id, shard in STAT_SHARDS.items():
        result.setdefault(
            int(rune_id),
            {
                "id": int(rune_id),
                "name": str(shard["name"]),
                "short_desc": "",
                "long_desc": "",
                "icon_url": str(shard["icon_url"]),
                "icon": "",
                "tree": "Stat Shard",
                "tree_id": 0,
                "style_id": 0,
                "style_name": "Stat Shard",
                "slot": 99,
                "slot_index": 99,
                "is_style": False,
            },
        )

    return result


def download_rune_icon(rune_id: int, runes_data: dict[int, dict]) -> bytes | None:
    rune = runes_data.get(int(rune_id))
    if not rune:
        return None
    icon_url = str(rune.get("icon_url", "")).strip()
    if not icon_url:
        return None
    return download_icon(icon_url, f"rune_{int(rune_id)}.png")


def build_rune_name_index(runes_data: dict[int, dict]) -> dict[str, int]:
    return {
        str(rune.get("name", "")).strip().lower(): int(rune_id)
        for rune_id, rune in runes_data.items()
        if str(rune.get("name", "")).strip()
    }


class RuneDataLoader:
    def __init__(self, base_dir: Path, preferred_patch: str | None = None):
        self.base_dir = Path(base_dir)
        self.preferred_patch = str(preferred_patch).strip() if preferred_patch else ""
        self._memory_cache: dict[str, dict[int, dict]] = {}
        self._pixmap_cache: dict[tuple[int, str, int], QPixmap] = {}
        self._lock = threading.Lock()

    def get_latest_version(self) -> str:
        return self.preferred_patch or get_current_patch()

    def load_runes(self, version: str, force_refresh: bool = False) -> dict[int, dict]:
        cache_key = f"runes::{version}"
        with self._lock:
            if cache_key in self._memory_cache and not force_refresh:
                return self._memory_cache[cache_key]
        runes = load_runes(version, force_refresh=force_refresh)
        with self._lock:
            self._memory_cache[cache_key] = runes
        return runes

    def get_rune_icon_path(self, rune_id: int, version: str) -> Path | None:
        runes = self.load_runes(version)
        rune = runes.get(int(rune_id))
        if not rune:
            return None
        icon_url = str(rune.get("icon_url", "")).strip()
        if not icon_url:
            return None
        icon_dir = self.base_dir / "data" / "ddragon_cache" / "rune_icons" / version
        path = icon_dir / f"{int(rune_id)}.png"
        if path.exists():
            return path
        icon_dir.mkdir(parents=True, exist_ok=True)
        data = download_rune_icon(int(rune_id), runes)
        if not data:
            return path if path.exists() else None
        path.write_bytes(data)
        return path

    def get_rune_pixmap(self, rune_id: int, version: str, size: int = 36) -> QPixmap:
        cache_key = (int(rune_id), version, size)
        if cache_key in self._pixmap_cache:
            return self._pixmap_cache[cache_key]
        path = self.get_rune_icon_path(int(rune_id), version)
        pixmap = QPixmap()
        if path and path.exists():
            pixmap.load(str(path))
        if pixmap.isNull():
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
        scaled = pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._pixmap_cache[cache_key] = scaled
        return scaled
