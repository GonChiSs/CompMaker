from __future__ import annotations

import json
import threading
from pathlib import Path

import requests
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from logic.icon_cache import download_icon
from logic.patch_versioning import get_current_patch

VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
REQUEST_TIMEOUT = 12
HEADERS = {
    "User-Agent": (
        "CompMaker/1.0 (+https://ddragon.leagueoflegends.com) "
        "Windows NT 10.0; Win64; x64"
    )
}


def _http_get_json(url: str) -> dict | list:
    session = requests.Session()
    session.trust_env = False
    response = session.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def _http_get_bytes(url: str) -> bytes:
    session = requests.Session()
    session.trust_env = False
    response = session.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    return response.content

STAT_KEYS = {
    "FlatHPPoolMod": "hp",
    "FlatMPPoolMod": "mp",
    "FlatArmorMod": "armor",
    "FlatSpellBlockMod": "mr",
    "FlatPhysicalDamageMod": "ad",
    "FlatMagicDamageMod": "ap",
    "PercentAttackSpeedMod": "as_bonus",
    "FlatCritChanceMod": "crit",
    "FlatArmorPenetrationMod": "lethality",
    "PercentArmorPenetrationMod": "arpen_pct",
    "FlatMagicPenetrationMod": "mpen",
    "PercentMagicPenetrationMod": "mpen_pct",
    "FlatMovementSpeedMod": "ms",
    "PercentMovementSpeedMod": "ms_pct",
    "FlatHPRegenMod": "hp_regen",
    "FlatMPRegenMod": "mp_regen",
    "PercentLifeStealMod": "lifesteal",
    "PercentCooldownMod": "cdr",
    "FlatCooldownMod": "ah",
}

EXCLUDED_ITEM_TAGS = {"Jungle", "Consumable", "Trinket"}
EXCLUDED_ITEM_IDS = {
    1001, 1004, 1006, 1026, 1031, 1033, 1036, 1037, 1038, 1042, 1043, 1052, 1053, 1054, 1055,
    1056, 1057, 1082, 1083, 2003, 2004, 2138, 2139, 2140, 2141, 3599, 3600, 3865, 3866, 3867,
    3869, 3870, 3871, 3901, 3902, 3903,
}
MANUAL_EXCLUSION_LIST = {
    443, 444, 445, 446,
    3056, 3057,
    6664, 6665, 6666,
    9999,
}
ARENA_EXCLUSIVE_PREFIXES = ("44",)
TIER1_BOOTS_ID = 1001
FINAL_ITEM_GOLD_FLOOR = 900
SPECIAL_MODE_ITEM_ID_THRESHOLD = 100000

CHAMPION_KEY_ALIASES = {
    "Aurelion Sol": "AurelionSol",
    "Bel'Veth": "Belveth",
    "Cho'Gath": "Chogath",
    "Dr. Mundo": "DrMundo",
    "Jarvan IV": "JarvanIV",
    "Kai'Sa": "Kaisa",
    "Kha'Zix": "Khazix",
    "Kog'Maw": "KogMaw",
    "K'Sante": "KSante",
    "LeBlanc": "Leblanc",
    "Master Yi": "MasterYi",
    "Miss Fortune": "MissFortune",
    "Nunu & Willump": "Nunu",
    "Rek'Sai": "RekSai",
    "Renata Glasc": "Renata",
    "Tahm Kench": "TahmKench",
    "Twisted Fate": "TwistedFate",
    "Vel'Koz": "Velkoz",
    "Wukong": "MonkeyKing",
    "Xin Zhao": "XinZhao",
}

AP_RATIOS = {
    "Ahri": 0.90,
    "Akali": 0.70,
    "Anivia": 1.00,
    "Annie": 0.95,
    "AurelionSol": 1.00,
    "Azir": 0.85,
    "Brand": 1.00,
    "Cassiopeia": 1.00,
    "Corki": 0.55,
    "Diana": 0.85,
    "Ekko": 0.80,
    "Fizz": 0.85,
    "Galio": 0.75,
    "Heimerdinger": 1.00,
    "Karma": 0.85,
    "Katarina": 0.75,
    "Karthus": 1.00,
    "Kennen": 0.80,
    "Leblanc": 0.95,
    "Lissandra": 0.90,
    "Lux": 0.95,
    "Malzahar": 0.95,
    "Morgana": 0.90,
    "Neeko": 0.95,
    "Nidalee": 0.80,
    "Orianna": 0.90,
    "Ryze": 1.00,
    "Seraphine": 0.90,
    "Sona": 0.90,
    "Syndra": 1.00,
    "Taliyah": 0.95,
    "TwistedFate": 0.85,
    "Veigar": 1.00,
    "Velkoz": 1.00,
    "Viktor": 1.00,
    "Vladimir": 0.90,
    "Xerath": 1.00,
    "Ziggs": 1.00,
    "Zoe": 0.95,
    "Zyra": 1.00,
}

FALLBACK_ITEMS = {
    3006: {"name": "Berserker's Greaves", "gold": 1100, "stats": {"as_bonus": 0.35, "ms": 45}, "tags": ["Boots", "AttackSpeed"], "is_mythic": False, "is_boots": True, "boots_tier": "tier2", "description": ""},
    3020: {"name": "Sorcerer's Shoes", "gold": 1100, "stats": {"ms": 45, "mpen": 18}, "tags": ["Boots", "MagicPenetration"], "is_mythic": False, "is_boots": True, "boots_tier": "tier2", "description": ""},
    3047: {"name": "Plated Steelcaps", "gold": 1200, "stats": {"armor": 25, "ms": 45}, "tags": ["Boots", "Armor"], "is_mythic": False, "is_boots": True, "boots_tier": "tier2", "description": ""},
    3078: {"name": "Trinity Force", "gold": 3333, "stats": {"ad": 36, "as_bonus": 0.30, "ah": 15, "ms_pct": 0.04, "hp": 333}, "tags": ["Damage", "AttackSpeed"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": ""},
    3031: {"name": "Infinity Edge", "gold": 3400, "stats": {"ad": 80, "crit": 0.25}, "tags": ["Damage", "CriticalStrike"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": ""},
    3094: {"name": "Rapid Firecannon", "gold": 2600, "stats": {"as_bonus": 0.35, "crit": 0.25, "ms_pct": 0.04}, "tags": ["AttackSpeed", "CriticalStrike"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": ""},
    3072: {"name": "Bloodthirster", "gold": 3400, "stats": {"ad": 80, "lifesteal": 0.18}, "tags": ["Damage", "LifeSteal"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": ""},
    3089: {"name": "Rabadon's Deathcap", "gold": 3600, "stats": {"ap": 140}, "tags": ["SpellDamage"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": ""},
    3135: {"name": "Void Staff", "gold": 3000, "stats": {"ap": 95, "mpen_pct": 0.40}, "tags": ["SpellDamage", "MagicPenetration"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": ""},
    3157: {"name": "Zhonya's Hourglass", "gold": 3250, "stats": {"ap": 105, "armor": 50, "ah": 15}, "tags": ["SpellDamage", "Armor"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": ""},
    3116: {"name": "Rylai's Crystal Scepter", "gold": 2600, "stats": {"ap": 75, "hp": 400}, "tags": ["SpellDamage", "Health"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": ""},
    3026: {"name": "Guardian Angel", "gold": 3200, "stats": {"ad": 55, "armor": 45}, "tags": ["Damage", "Armor"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": ""},
    3075: {"name": "Thornmail", "gold": 2450, "stats": {"hp": 150, "armor": 75}, "tags": ["Armor", "Health"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": ""},
    3065: {"name": "Spirit Visage", "gold": 2700, "stats": {"hp": 400, "mr": 50, "ah": 10}, "tags": ["Health", "SpellBlock"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": ""},
    3083: {"name": "Warmog's Armor", "gold": 3100, "stats": {"hp": 1000, "hp_regen": 2}, "tags": ["Health"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": ""},
    3107: {"name": "Redemption", "gold": 2300, "stats": {"hp": 200, "ah": 15, "hp_regen": 1.0}, "tags": ["Health", "ManaRegen"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": ""},
    3504: {"name": "Ardent Censer", "gold": 2300, "stats": {"ap": 60, "ah": 8, "ms_pct": 0.08}, "tags": ["SpellDamage", "ManaRegen"], "is_mythic": False, "is_boots": False, "boots_tier": None, "description": ""},
}

EXCLUDED_ITEM_IDS = EXCLUDED_ITEM_IDS | MANUAL_EXCLUSION_LIST


def _classify_boots(raw_items: dict) -> dict[int, str]:
    classification: dict[int, str] = {}
    for item_id_str, item in raw_items.get("data", {}).items():
        item_id = int(item_id_str)
        tags = item.get("tags", [])
        if "Boots" not in tags and item.get("group") != "BootsOfSpeed":
            continue

        from_list = [int(source) for source in item.get("from", []) if str(source).isdigit()]
        if item_id == TIER1_BOOTS_ID:
            classification[item_id] = "tier1"
        elif TIER1_BOOTS_ID in from_list:
            classification[item_id] = "tier2"
        else:
            total_gold = int(item.get("gold", {}).get("total", 0) or 0)
            classification[item_id] = "tier2" if total_gold >= 800 else "tier1"
    return classification


def normalize_champion_key(champion_name: str, image_key: str | None = None) -> str:
    if image_key:
        return image_key
    if champion_name in CHAMPION_KEY_ALIASES:
        return CHAMPION_KEY_ALIASES[champion_name]
    return (
        champion_name.replace(" ", "")
        .replace("'", "")
        .replace(".", "")
        .replace("&", "")
    )


class ItemDataLoader:
    def __init__(self, base_dir: Path, preferred_patch: str | None = None):
        self.base_dir = Path(base_dir)
        self.preferred_patch = str(preferred_patch).strip() if preferred_patch else ""
        self.cache_dir = self.base_dir / "data" / "ddragon_cache"
        self.icon_dir = self.cache_dir / "icons"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.icon_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, dict] = {}
        self._pixmap_cache: dict[tuple[int, str, int], QPixmap] = {}
        self._lock = threading.Lock()

    def get_latest_version(self) -> str:
        try:
            versions = _http_get_json(VERSIONS_URL)
            if isinstance(versions, list) and versions:
                return str(versions[0])
        except Exception:
            pass
        if self.preferred_patch:
            return self.preferred_patch
        return get_current_patch()

    def _json_cache_path(self, filename: str) -> Path:
        return self.cache_dir / filename

    def _icon_cache_path(self, version: str, item_id: int) -> Path:
        return self.icon_dir / version / f"{item_id}.png"

    def _load_json_cached(self, url: str, filename: str, force_refresh: bool = False) -> dict | None:
        path = self._json_cache_path(filename)
        if path.exists() and not force_refresh:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        try:
            payload = _http_get_json(url)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return payload
        except Exception:
            if path.exists():
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    return None
            return None

    def load_items(self, version: str, force_refresh: bool = False) -> dict[int, dict]:
        cache_key = f"items::{version}"
        with self._lock:
            if cache_key in self._memory_cache and not force_refresh:
                return self._memory_cache[cache_key]

        raw = self._load_json_cached(
            f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/item.json",
            f"items_{version}.json",
            force_refresh=force_refresh,
        )
        items: dict[int, dict] = {}
        if raw:
            boots_classification = _classify_boots(raw)
            for item_id_str, item in raw.get("data", {}).items():
                item_id = int(item_id_str)
                if item_id in EXCLUDED_ITEM_IDS:
                    continue
                if item_id >= SPECIAL_MODE_ITEM_ID_THRESHOLD:
                    continue
                if item.get("requiredChampion") or item.get("requiredAlly"):
                    continue
                if any(str(item_id).startswith(prefix) for prefix in ARENA_EXCLUSIVE_PREFIXES):
                    continue
                gold = item.get("gold", {})
                maps = item.get("maps", {})
                tags = list(item.get("tags", []))
                if not gold.get("purchasable", False):
                    continue
                if not maps.get("11", False):
                    continue
                if any(tag in EXCLUDED_ITEM_TAGS for tag in tags):
                    continue
                total_cost = int(gold.get("total", 0) or 0)
                depth = int(item.get("depth", 0) or 0)
                into_list = [int(target) for target in item.get("into", []) if str(target).isdigit()]
                is_boots = item_id in boots_classification
                boots_tier = boots_classification.get(item_id)
                if is_boots and boots_tier == "tier1":
                    continue
                if not is_boots and total_cost < FINAL_ITEM_GOLD_FLOOR:
                    continue
                if not is_boots and depth < 2 and total_cost < 1000:
                    continue
                if into_list and depth < 3 and not is_boots:
                    continue

                stats: dict[str, float] = {}
                for raw_key, normalized_key in STAT_KEYS.items():
                    value = item.get("stats", {}).get(raw_key, 0)
                    if value:
                        stats[normalized_key] = stats.get(normalized_key, 0.0) + float(value)

                description = str(item.get("description", ""))
                from_items = [int(source) for source in item.get("from", []) if str(source).isdigit()]
                is_mythic = "mythic passive" in description.lower() or "mythic" in description.lower()
                is_boots = is_boots or "Boots" in tags or TIER1_BOOTS_ID in from_items or item.get("group") == "BootsOfSpeed"

                items[item_id] = {
                    "id": item_id,
                    "name": item.get("name", f"Item {item_id}"),
                    "gold": total_cost,
                    "stats": stats,
                    "tags": tags,
                    "is_mythic": is_mythic,
                    "is_boots": is_boots,
                    "boots_tier": boots_tier,
                    "description": description,
                    "icon_url": f"https://ddragon.leagueoflegends.com/cdn/{version}/img/item/{item_id}.png",
                }

        if not items:
            for item_id, item in FALLBACK_ITEMS.items():
                items[item_id] = {
                    "id": item_id,
                    "name": item["name"],
                    "gold": item["gold"],
                    "stats": dict(item["stats"]),
                    "tags": list(item["tags"]),
                    "is_mythic": bool(item["is_mythic"]),
                    "is_boots": bool(item["is_boots"]),
                    "boots_tier": item.get("boots_tier"),
                    "description": item.get("description", ""),
                    "icon_url": f"https://ddragon.leagueoflegends.com/cdn/{version}/img/item/{item_id}.png",
                }

        with self._lock:
            self._memory_cache[cache_key] = items
        return items

    def load_champion_stats(
        self,
        version: str,
        champion_name: str,
        image_key: str | None = None,
        champion_record: dict | None = None,
        force_refresh: bool = False,
    ) -> dict | None:
        champion_key = normalize_champion_key(champion_name, image_key=image_key)
        raw = self._load_json_cached(
            f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion/{champion_key}.json",
            f"champion_{champion_key}_{version}.json",
            force_refresh=force_refresh,
        )
        if not raw:
            return self._build_fallback_champion_stats(champion_name, champion_key, champion_record or {})
        data = raw.get("data", {})
        if not data:
            return self._build_fallback_champion_stats(champion_name, champion_key, champion_record or {})
        champion_payload = next(iter(data.values()))
        stats = champion_payload.get("stats", {})
        return {
            "champion_key": champion_key,
            "hp": float(stats.get("hp", 580)),
            "hp_per_level": float(stats.get("hpperlevel", 96)),
            "armor": float(stats.get("armor", 30)),
            "armor_per_level": float(stats.get("armorperlevel", 4)),
            "mr": float(stats.get("spellblock", 30)),
            "mr_per_level": float(stats.get("spellblockperlevel", 1.3)),
            "ad": float(stats.get("attackdamage", 60)),
            "ad_per_level": float(stats.get("attackdamageperlevel", 3.5)),
            "as_base": float(stats.get("attackspeed", 0.658)),
            "as_ratio": float(stats.get("attackspeedperlevel", 2.5)),
            "range": float(stats.get("attackrange", 175)),
            "ms": float(stats.get("movespeed", 335)),
            "ap_ratio": float(AP_RATIOS.get(champion_key, 0.55)),
        }

    def _build_fallback_champion_stats(
        self,
        champion_name: str,
        champion_key: str,
        champion_record: dict,
    ) -> dict:
        roles = [str(role).upper() for role in champion_record.get("roles", [])]
        damage_types = [str(damage_type).upper() for damage_type in champion_record.get("damage_type", [])]
        is_ranged = str(champion_record.get("range_type", "")).upper() == "RANGED"
        is_support = "SUPPORT" in roles
        is_tank = "TOP" in roles and "AD" not in damage_types and "AP" not in damage_types
        is_ap = "AP" in damage_types

        return {
            "champion_key": champion_key,
            "hp": 620.0 if is_tank else (560.0 if is_ranged else 590.0),
            "hp_per_level": 108.0 if is_tank else (92.0 if is_support else 102.0),
            "armor": 34.0 if "TOP" in roles or "JUNGLE" in roles else 28.0,
            "armor_per_level": 4.7 if "TOP" in roles or "JUNGLE" in roles else 4.0,
            "mr": 32.0,
            "mr_per_level": 2.05 if is_support else 1.3,
            "ad": 54.0 if is_ap else (60.0 if is_ranged else 64.0),
            "ad_per_level": 2.8 if is_ap else 3.5,
            "as_base": 0.658 if is_ranged else 0.625,
            "as_ratio": 2.2 if is_support else 2.8,
            "range": 550.0 if is_ranged else 175.0,
            "ms": 325.0 if is_ranged else 340.0,
            "ap_ratio": float(AP_RATIOS.get(champion_key, 0.8 if is_ap else 0.25)),
        }

    def get_item_icon_path(self, item_id: int, version: str) -> Path | None:
        path = self._icon_cache_path(version, item_id)
        if path.exists():
            return path
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = download_item_icon(item_id, version)
            if not data:
                return path if path.exists() else None
            path.write_bytes(data)
            return path
        except Exception:
            return path if path.exists() else None

    def get_item_pixmap(self, item_id: int, version: str, size: int = 48) -> QPixmap:
        cache_key = (item_id, version, size)
        if cache_key in self._pixmap_cache:
            return self._pixmap_cache[cache_key]
        path = self.get_item_icon_path(item_id, version)
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


_shared_loader: ItemDataLoader | None = None
_shared_loader_lock = threading.Lock()


def _get_shared_loader() -> ItemDataLoader:
    global _shared_loader
    with _shared_loader_lock:
        if _shared_loader is None:
            _shared_loader = ItemDataLoader(Path(__file__).resolve().parents[1])
        return _shared_loader


def get_latest_version() -> str:
    return _get_shared_loader().get_latest_version()


def load_items(version: str, force_refresh: bool = False) -> dict[int, dict]:
    return _get_shared_loader().load_items(version, force_refresh=force_refresh)


def load_champion_stats(
    version: str,
    champion_name: str,
    image_key: str | None = None,
    champion_record: dict | None = None,
    force_refresh: bool = False,
) -> dict | None:
    return _get_shared_loader().load_champion_stats(
        version,
        champion_name,
        image_key=image_key,
        champion_record=champion_record,
        force_refresh=force_refresh,
    )


def _load_json_cached(url: str, filename: str, force_refresh: bool = False) -> dict | None:
    return _get_shared_loader()._load_json_cached(url, filename, force_refresh=force_refresh)


def download_item_icon(item_id: int, version: str) -> bytes | None:
    url = f"https://ddragon.leagueoflegends.com/cdn/{version}/img/item/{item_id}.png"
    return download_icon(url, f"item_{item_id}.png")
