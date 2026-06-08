from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Callable

import requests
from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from logic.patch_versioning import get_current_patch

IMAGE_DOWNLOAD_DELAY_SECONDS = 0.08

DEFAULT_ROLE_MAP = {
    "Aatrox": ["TOP"],
    "Ahri": ["MID"],
    "Akali": ["MID", "TOP"],
    "Akshan": ["MID", "ADC"],
    "Alistar": ["SUPPORT"],
    "Amumu": ["JUNGLE", "SUPPORT"],
    "Anivia": ["MID"],
    "Annie": ["MID", "SUPPORT"],
    "Aphelios": ["ADC"],
    "Ashe": ["ADC", "SUPPORT"],
    "Aurelion Sol": ["MID"],
    "Azir": ["MID"],
    "Bard": ["SUPPORT"],
    "Bel'Veth": ["JUNGLE"],
    "Blitzcrank": ["SUPPORT"],
    "Brand": ["MID", "SUPPORT"],
    "Braum": ["SUPPORT"],
    "Briar": ["JUNGLE"],
    "Caitlyn": ["ADC"],
    "Camille": ["TOP"],
    "Cassiopeia": ["MID"],
    "Cho'Gath": ["TOP", "MID"],
    "Corki": ["MID", "ADC"],
    "Darius": ["TOP"],
    "Diana": ["JUNGLE", "MID"],
    "Dr. Mundo": ["TOP"],
    "Draven": ["ADC"],
    "Ekko": ["JUNGLE", "MID"],
    "Elise": ["JUNGLE"],
    "Evelynn": ["JUNGLE"],
    "Ezreal": ["ADC"],
    "Fiddlesticks": ["JUNGLE", "SUPPORT"],
    "Fiora": ["TOP"],
    "Fizz": ["MID"],
    "Galio": ["MID", "SUPPORT"],
    "Gangplank": ["TOP"],
    "Garen": ["TOP"],
    "Gnar": ["TOP"],
    "Gragas": ["TOP", "JUNGLE"],
    "Graves": ["JUNGLE"],
    "Gwen": ["TOP"],
    "Hecarim": ["JUNGLE"],
    "Heimerdinger": ["MID", "SUPPORT"],
    "Hwei": ["MID"],
    "Illaoi": ["TOP"],
    "Irelia": ["TOP", "MID"],
    "Ivern": ["JUNGLE"],
    "Janna": ["SUPPORT"],
    "Jarvan IV": ["JUNGLE"],
    "Jax": ["TOP", "JUNGLE"],
    "Jayce": ["TOP", "MID"],
    "Jhin": ["ADC"],
    "Jinx": ["ADC"],
    "Kai'Sa": ["ADC"],
    "Kalista": ["ADC"],
    "Karma": ["SUPPORT", "MID"],
    "Karthus": ["JUNGLE", "MID"],
    "Kassadin": ["MID"],
    "Katarina": ["MID"],
    "Kayle": ["TOP"],
    "Kayn": ["JUNGLE"],
    "Kennen": ["TOP"],
    "Kha'Zix": ["JUNGLE"],
    "Kindred": ["JUNGLE"],
    "K'Sante": ["TOP"],
    "Kled": ["TOP"],
    "Kog'Maw": ["ADC"],
    "LeBlanc": ["MID"],
    "Lee Sin": ["JUNGLE"],
    "Leona": ["SUPPORT"],
    "Lillia": ["JUNGLE"],
    "Lissandra": ["MID"],
    "Lucian": ["ADC", "MID"],
    "Lulu": ["SUPPORT"],
    "Lux": ["MID", "SUPPORT"],
    "Malphite": ["TOP", "SUPPORT"],
    "Malzahar": ["MID"],
    "Maokai": ["JUNGLE", "SUPPORT", "TOP"],
    "Master Yi": ["JUNGLE"],
    "Milio": ["SUPPORT"],
    "Miss Fortune": ["ADC"],
    "Mordekaiser": ["TOP"],
    "Morgana": ["SUPPORT", "MID"],
    "Naafiri": ["MID", "JUNGLE"],
    "Nami": ["SUPPORT"],
    "Nasus": ["TOP"],
    "Nautilus": ["SUPPORT", "JUNGLE"],
    "Neeko": ["MID", "SUPPORT"],
    "Nidalee": ["JUNGLE"],
    "Nilah": ["ADC"],
    "Nocturne": ["JUNGLE"],
    "Nunu & Willump": ["JUNGLE"],
    "Olaf": ["TOP", "JUNGLE"],
    "Orianna": ["MID"],
    "Ornn": ["TOP"],
    "Pantheon": ["SUPPORT", "MID", "TOP"],
    "Poppy": ["TOP", "JUNGLE"],
    "Pyke": ["SUPPORT"],
    "Qiyana": ["MID", "JUNGLE"],
    "Quinn": ["TOP"],
    "Rakan": ["SUPPORT"],
    "Rammus": ["JUNGLE"],
    "Rek'Sai": ["JUNGLE"],
    "Rell": ["SUPPORT", "JUNGLE"],
    "Renata Glasc": ["SUPPORT"],
    "Renekton": ["TOP"],
    "Rengar": ["JUNGLE"],
    "Riven": ["TOP"],
    "Rumble": ["TOP"],
    "Ryze": ["MID", "TOP"],
    "Samira": ["ADC"],
    "Sejuani": ["JUNGLE"],
    "Senna": ["SUPPORT", "ADC"],
    "Seraphine": ["SUPPORT", "MID"],
    "Sett": ["TOP", "SUPPORT"],
    "Shaco": ["JUNGLE", "SUPPORT"],
    "Shen": ["TOP"],
    "Shyvana": ["JUNGLE"],
    "Singed": ["TOP"],
    "Sion": ["TOP"],
    "Sivir": ["ADC"],
    "Skarner": ["JUNGLE", "TOP"],
    "Smolder": ["ADC"],
    "Sona": ["SUPPORT"],
    "Soraka": ["SUPPORT"],
    "Swain": ["MID", "SUPPORT"],
    "Sylas": ["MID", "JUNGLE"],
    "Syndra": ["MID"],
    "Tahm Kench": ["SUPPORT", "TOP"],
    "Taliyah": ["MID", "JUNGLE"],
    "Talon": ["MID", "JUNGLE"],
    "Taric": ["SUPPORT"],
    "Teemo": ["TOP"],
    "Thresh": ["SUPPORT"],
    "Tristana": ["ADC", "MID"],
    "Trundle": ["JUNGLE", "TOP"],
    "Tryndamere": ["TOP"],
    "Twisted Fate": ["MID"],
    "Twitch": ["ADC"],
    "Udyr": ["JUNGLE", "TOP"],
    "Urgot": ["TOP"],
    "Varus": ["ADC"],
    "Vayne": ["ADC", "TOP"],
    "Veigar": ["MID", "SUPPORT"],
    "Vel'Koz": ["MID", "SUPPORT"],
    "Vex": ["MID"],
    "Vi": ["JUNGLE"],
    "Viego": ["JUNGLE"],
    "Viktor": ["MID"],
    "Vladimir": ["MID", "TOP"],
    "Volibear": ["JUNGLE", "TOP"],
    "Warwick": ["JUNGLE"],
    "Wukong": ["JUNGLE", "TOP"],
    "Xayah": ["ADC"],
    "Xerath": ["MID", "SUPPORT"],
    "Xin Zhao": ["JUNGLE"],
    "Yasuo": ["MID", "TOP"],
    "Yone": ["MID", "TOP"],
    "Yorick": ["TOP"],
    "Yuumi": ["SUPPORT"],
    "Zac": ["JUNGLE", "TOP"],
    "Zed": ["MID"],
    "Zeri": ["ADC"],
    "Ziggs": ["MID", "ADC"],
    "Zilean": ["SUPPORT", "MID"],
    "Zoe": ["MID"],
    "Zyra": ["SUPPORT"],
}

DEFAULT_TAG_SETS = {
    "TOP": ["Bruiser", "Skirmisher", "Engage"],
    "JUNGLE": ["Objective-Control", "Roamer", "Engage"],
    "MID": ["Burst", "Waveclear", "Long-Range"],
    "ADC": ["DPS", "Kiter", "Hypercarry"],
    "SUPPORT": ["Peel", "Vision", "Heal"],
}

DEFAULT_ARCHETYPES = {
    "TOP": ["Split Push"],
    "JUNGLE": ["Pick Comp"],
    "MID": ["Poke / Siege"],
    "ADC": ["Hypercarry Protect"],
    "SUPPORT": ["Hypercarry Protect"],
}


def _load_synergy_payload(data_path: Path) -> tuple[dict, dict[str, dict]]:
    payload = json.loads(data_path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and "champions" in payload:
        meta = payload.get("_meta", {}) if isinstance(payload.get("_meta", {}), dict) else {}
        champions = payload.get("champions", {})
        return meta, champions if isinstance(champions, dict) else {}
    if isinstance(payload, dict) and "_meta" in payload:
        meta = payload.get("_meta", {}) if isinstance(payload.get("_meta", {}), dict) else {}
        champions = {
            key: value for key, value in payload.items()
            if key != "_meta" and isinstance(value, dict)
        }
        return meta, champions
    return {}, payload if isinstance(payload, dict) else {}


def _champion_image_url(image_key: str) -> str:
    patch = get_current_patch()
    return f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/champion/{image_key}.png"


def load_all_champions(base_dir: Path | None = None) -> dict[str, dict]:
    """Carga el dataset principal de campeones para tests y utilidades offline."""
    if base_dir is None:
        base_dir = Path(__file__).resolve().parents[1]
    data_path = base_dir / "data" / "champions_synergy.json"
    _, champions = _load_synergy_payload(data_path)
    for name, payload in champions.items():
        payload.setdefault("name", name)
    return champions


def get_data_meta(base_dir: Path | None = None) -> dict:
    if base_dir is None:
        base_dir = Path(__file__).resolve().parents[1]
    data_path = base_dir / "data" / "champions_synergy.json"
    meta, champions = _load_synergy_payload(data_path)
    patch = meta.get("patch") or "unknown"
    current_patch = get_current_patch()
    return {
        "patch": patch,
        "current_patch": current_patch,
        "is_stale": patch != current_patch,
        "champion_count": len(champions),
        "source": meta.get("source", "embedded"),
        "updated_at": meta.get("updated_at", ""),
    }


class DataLoader:
    """Gestiona datos remotos, cache local e iconos/imágenes."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.bundle_dir = Path(getattr(sys, "_MEIPASS", str(base_dir)))
        self.is_frozen = bool(getattr(sys, "frozen", False))
        local_appdata = Path(os.getenv("LOCALAPPDATA", str(base_dir)))
        preferred_cache_root = (local_appdata / "CompMaker") if self.is_frozen else base_dir
        fallback_cache_root = base_dir / ".compmaker_cache"
        self.cache_root = preferred_cache_root

        self.data_dir = self.cache_root / "data"
        self.assets_dir = self.cache_root / "assets"
        self.images_dir = self.cache_root / "retratos"
        self.synergy_path = self.bundle_dir / "data" / "champions_synergy.json"
        self.raw_path = self.data_dir / "champions_raw.json"
        self.workspace_logo_path = base_dir.parent / "logo.png"
        self.workspace_inter_path = base_dir.parent / "inter.png"
        self.bundle_logo_path = self.bundle_dir / "assets" / "logo.png"
        self.bundle_inter_path = self.bundle_dir / "assets" / "inter.png"
        self.logo_path = self.assets_dir / "logo.png"
        self.inter_path = self.assets_dir / "inter.png"
        self.icon_path = self.assets_dir / "icon.ico"
        self.placeholder_path = self.assets_dir / "placeholder.png"
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.images_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.cache_root = fallback_cache_root
            self.data_dir = self.cache_root / "data"
            self.assets_dir = self.cache_root / "assets"
            self.images_dir = self.cache_root / "retratos"
            self.logo_path = self.assets_dir / "logo.png"
            self.inter_path = self.assets_dir / "inter.png"
            self.icon_path = self.assets_dir / "icon.ico"
            self.placeholder_path = self.assets_dir / "placeholder.png"
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.images_dir.mkdir(parents=True, exist_ok=True)

    def ensure_app_icon(self) -> Path:
        self._sync_logo_from_workspace()
        self._sync_inter_from_workspace()
        if not self.logo_path.exists():
            return self.icon_path
        if (not self.icon_path.exists()) or (self.logo_path.stat().st_mtime > self.icon_path.stat().st_mtime):
            self._build_square_icon(self.logo_path, self.icon_path)
        return self.icon_path

    def _sync_logo_from_workspace(self) -> None:
        if self.workspace_logo_path.exists():
            if (not self.logo_path.exists()) or (
                self.workspace_logo_path.stat().st_mtime > self.logo_path.stat().st_mtime
            ):
                shutil.copy2(self.workspace_logo_path, self.logo_path)
        elif self.bundle_logo_path.exists() and not self.logo_path.exists():
            shutil.copy2(self.bundle_logo_path, self.logo_path)

    def _sync_inter_from_workspace(self) -> None:
        if self.workspace_inter_path.exists():
            if (not self.inter_path.exists()) or (
                self.workspace_inter_path.stat().st_mtime > self.inter_path.stat().st_mtime
            ):
                shutil.copy2(self.workspace_inter_path, self.inter_path)
        elif self.bundle_inter_path.exists() and not self.inter_path.exists():
            shutil.copy2(self.bundle_inter_path, self.inter_path)

    def _build_square_icon(self, source: Path, target: Path) -> None:
        """Genera un icono cuadrado preservando la proporcion del logo."""
        image = Image.open(source).convert("RGBA")
        base_size = 256
        canvas = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
        image.thumbnail((240, 240), Image.Resampling.LANCZOS)
        offset_x = (base_size - image.width) // 2
        offset_y = (base_size - image.height) // 2
        canvas.paste(image, (offset_x, offset_y), image)
        canvas.save(
            target,
            format="ICO",
            sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
        )

    def prepare_runtime_data(self, progress_callback: Callable[[str, int], None] | None = None) -> dict:
        self.ensure_app_icon()
        self._ensure_placeholder()
        if progress_callback:
            progress_callback("Iniciando CompMaker...", 0)
            progress_callback("Preparando recursos locales...", 5)
            progress_callback("Descargando lista de campeones...", 15)

        remote_payload = self._fetch_remote_champions()
        remote_available = remote_payload is not None
        remote_data = remote_payload or self._load_cached_raw()
        if not remote_data:
            remote_data = {"data": {}}

        if progress_callback:
            progress_callback("Combinando datos locales y roles...", 35)
        champion_pool = self._merge_champion_data(remote_data)

        if progress_callback:
            progress_callback("Preparando retratos de campeones...", 50)
        self._download_missing_images(champion_pool, progress_callback, remote_available)

        if progress_callback:
            progress_callback("Finalizando primer inicio...", 100)

        return {
            "champion_pool": champion_pool,
            "placeholder_path": self.placeholder_path,
            "icon_path": self.icon_path,
            "inter_path": self.inter_path,
            "data_meta": get_data_meta(self.bundle_dir),
        }

    def _ensure_placeholder(self) -> None:
        if self.placeholder_path.exists():
            return
        image = Image.new("RGBA", (96, 96), "#1E2A3A")
        image.save(self.placeholder_path)

    def _fetch_remote_champions(self) -> dict | None:
        try:
            patch = get_current_patch()
            champion_list_url = f"https://ddragon.leagueoflegends.com/cdn/{patch}/data/en_US/champion.json"
            response = requests.get(champion_list_url, timeout=15)
            response.raise_for_status()
            payload = response.json()
            self.raw_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            return payload
        except Exception:
            return None

    def _load_cached_raw(self) -> dict | None:
        if not self.raw_path.exists():
            return None
        return json.loads(self.raw_path.read_text(encoding="utf-8"))

    def _merge_champion_data(self, raw_payload: dict) -> dict[str, dict]:
        _, synergy_data = _load_synergy_payload(self.synergy_path)
        champion_pool: dict[str, dict] = {}

        for champion_name, record in synergy_data.items():
            champion_pool[champion_name] = self._normalize_runtime_record(
                champion_name,
                dict(record),
                champion_name.replace(" ", "").replace("'", "").replace(".", ""),
            )
            champion_pool[champion_name]["image_path"] = str(self.images_dir / f"{champion_name}.png")

        for champion_key, raw_info in raw_payload.get("data", {}).items():
            champion_name = raw_info.get("name", champion_key)
            existing = champion_pool.get(champion_name)
            roles = DEFAULT_ROLE_MAP.get(champion_name, ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"])
            image_key = raw_info.get("id", champion_key)
            if existing:
                champion_pool[champion_name] = self._normalize_runtime_record(
                    champion_name,
                    existing,
                    image_key,
                    roles=roles,
                )
                existing = champion_pool[champion_name]
                existing["image_path"] = str(self.images_dir / f"{champion_name}.png")
                existing["image_key"] = image_key
            else:
                champion_pool[champion_name] = self._normalize_runtime_record(
                    champion_name,
                    {},
                    image_key,
                    roles=roles,
                )
                champion_pool[champion_name]["image_path"] = str(self.images_dir / f"{champion_name}.png")

        for champion_name, roles in DEFAULT_ROLE_MAP.items():
            if champion_name in champion_pool:
                continue
            champion_pool[champion_name] = self._normalize_runtime_record(
                champion_name,
                {},
                champion_name.replace(" ", "").replace("'", "").replace(".", ""),
                roles=roles,
            )
            champion_pool[champion_name]["image_path"] = str(self.images_dir / f"{champion_name}.png")
        return dict(sorted(champion_pool.items()))

    def _normalize_runtime_record(
        self,
        champion_name: str,
        record: dict,
        image_key: str,
        roles: list[str] | None = None,
    ) -> dict:
        normalized = dict(record)
        resolved_roles = list(
            normalized.get("roles")
            or roles
            or DEFAULT_ROLE_MAP.get(champion_name, ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"])
        )
        normalized.setdefault("name", champion_name)
        normalized["roles"] = resolved_roles
        normalized.setdefault("damage_type", self._default_damage_types_for_roles(resolved_roles))
        normalized.setdefault("mobility", 3)
        normalized.setdefault("range_type", self._default_range_type_for_roles(resolved_roles))
        normalized.setdefault("ability_tags", self._default_ability_tags_for_roles(resolved_roles))
        normalized.setdefault(
            "synergy_keys",
            {
                "enables": [],
                "requires": [],
                "amplifies": [],
                "countered_by_tags": [],
            },
        )
        normalized.setdefault("archetype_fit", self._default_archetype_fit_for_roles(resolved_roles))
        normalized.setdefault("pro_tier", int(normalized.get("power_score", 5)))
        normalized.setdefault("self_sufficiency", 5)
        normalized.setdefault("counters", [])
        normalized.setdefault("countered_by", [])
        normalized.setdefault("counter_tags", [])
        normalized.setdefault("tags", self._default_tags_for_roles(resolved_roles))
        normalized.setdefault("archetypes", self._default_archetypes_for_roles(resolved_roles))
        normalized.setdefault("synergizes_with_tags", self._default_synergy_triggers(normalized["tags"]))
        normalized.setdefault("power_score", normalized["pro_tier"])
        normalized["image_key"] = image_key
        return normalized

    def _default_tags_for_roles(self, roles: list[str]) -> list[str]:
        tags = []
        for role in roles:
            tags.extend(DEFAULT_TAG_SETS.get(role, []))
        result = []
        for tag in tags:
            if tag not in result:
                result.append(tag)
        return result[:4]

    def _default_archetypes_for_roles(self, roles: list[str]) -> list[str]:
        result = []
        for role in roles:
            for archetype in DEFAULT_ARCHETYPES.get(role, []):
                if archetype not in result:
                    result.append(archetype)
        return result[:2]

    def _default_synergy_triggers(self, tags: list[str]) -> list[str]:
        mapping = {
            "Engage": "AoE-Follow-Up",
            "Knockup": "Knockup-Beneficiary",
            "Hypercarry": "Peel",
            "Splitpusher": "Global",
            "Poke": "Long-Range",
            "Lockdown": "Assassin",
        }
        result = []
        for tag in tags:
            trigger = mapping.get(tag)
            if trigger and trigger not in result:
                result.append(trigger)
        return result or tags[:2]

    def _default_ability_tags_for_roles(self, roles: list[str]) -> list[str]:
        role_tag_map = {
            "TOP": ["SINGLE_TARGET_DPS", "DIVE_ENGAGE", "MID_GAME_SPIKE"],
            "JUNGLE": ["HARD_ENGAGE", "OBJECTIVE_CONTROL", "ROAM_THREAT"],
            "MID": ["AP_BURST", "WAVECLEAR", "MID_GAME_SPIKE"],
            "ADC": ["HYPERCARRY", "SINGLE_TARGET_DPS", "LATE_GAME"],
            "SUPPORT": ["PEEL", "CHAIN_CC", "HARD_PEEL"],
        }
        result = []
        for role in roles:
            for tag in role_tag_map.get(role, []):
                if tag not in result:
                    result.append(tag)
        return result[:6]

    def _default_damage_types_for_roles(self, roles: list[str]) -> list[str]:
        if "MID" in roles:
            return ["AP"]
        if "SUPPORT" in roles and "ADC" not in roles:
            return ["AP"]
        return ["AD"]

    def _default_range_type_for_roles(self, roles: list[str]) -> str:
        if "ADC" in roles or "MID" in roles:
            return "RANGED"
        return "MELEE"

    def _default_archetype_fit_for_roles(self, roles: list[str]) -> dict[str, int]:
        base = {
            "Wombo Combo": 25,
            "Engage Teamfight": 25,
            "Poke Siege": 25,
            "Split Push": 25,
            "Pick Comp": 25,
            "Hypercarry Protect": 25,
            "Disengage": 25,
            "Skirmish": 25,
        }
        boosts = {
            "TOP": {"Split Push": 25, "Skirmish": 15},
            "JUNGLE": {"Engage Teamfight": 20, "Pick Comp": 20},
            "MID": {"Poke Siege": 20, "Pick Comp": 15},
            "ADC": {"Hypercarry Protect": 25, "Poke Siege": 10},
            "SUPPORT": {"Hypercarry Protect": 20, "Disengage": 15, "Engage Teamfight": 10},
        }
        for role in roles:
            for archetype, bonus in boosts.get(role, {}).items():
                base[archetype] = min(95, base[archetype] + bonus)
        return base

    def _download_missing_images(
        self,
        champion_pool: dict[str, dict],
        progress_callback: Callable[[str, int], None] | None,
        remote_available: bool,
    ) -> None:
        all_names = sorted(champion_pool)
        total = len(all_names)
        if total == 0:
            return

        if not remote_available:
            cached = sum(
                1 for name in all_names if Path(champion_pool[name]["image_path"]).exists()
            )
            if progress_callback:
                progress_callback(
                    f"Sin conexion a Data Dragon. Usando caché local y placeholders | Caché: {cached}",
                    90,
                )
            return

        downloaded = 0
        cached = 0
        if progress_callback:
            progress_callback("Comprobando caché local de retratos...", 50)

        for index, champion_name in enumerate(all_names, start=1):
            champion_info = champion_pool[champion_name]
            target_path = Path(champion_info["image_path"])
            if target_path.exists():
                cached += 1
                action = "Usando caché"
            else:
                self._download_single_image(champion_info)
                if target_path.exists():
                    downloaded += 1
                    action = "Descargando retratos"
                else:
                    action = "No se pudo descargar, usando placeholder"

            if progress_callback:
                percent = 50 + int((index / total) * 40)
                progress_callback(
                    f"{action} ({index}/{total}) | Nuevos: {downloaded} | Caché: {cached}",
                    percent,
                )

        if progress_callback:
            progress_callback(
                f"Retratos listos | Nuevos: {downloaded} | Caché: {cached}",
                90,
            )

    def _download_single_image(self, champion_info: dict) -> None:
        """Descarga individual con reintentos suaves y caché persistente en disco."""
        target_path = Path(champion_info["image_path"])
        url = _champion_image_url(champion_info["image_key"])

        for attempt in range(3):
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                target_path.write_bytes(response.content)
                time.sleep(IMAGE_DOWNLOAD_DELAY_SECONDS)
                return
            except Exception:
                time.sleep((attempt + 1) * 0.35)

    def get_champion_pixmap(self, champion_name: str | None, size: int = 64) -> QPixmap:
        image_path = self.placeholder_path
        if champion_name:
            candidate_path = self.images_dir / f"{champion_name}.png"
            if candidate_path.exists():
                image_path = candidate_path
        pixmap = QPixmap(str(image_path))
        return pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
