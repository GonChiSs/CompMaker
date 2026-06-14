from __future__ import annotations

from logic.champion_full_loader import load_champion_full, summarize_champion_kit
from logic.item_data_loader import get_latest_version, load_items, normalize_champion_key
from logic.patch_versioning import get_current_patch
from logic.rune_data_loader import build_rune_name_index, load_runes, strip_html

MAX_INJECTED_CHAMPIONS = 2
MAX_INJECTED_ITEMS = 4
MAX_INJECTED_RUNES = 4
MAX_ITEM_DESC_CHARS = 200


class KnowledgeBase:
    def __init__(self, all_champions: dict[str, dict]):
        self.all_champions = all_champions
        self.version = ""
        self.items: dict[int, dict] = {}
        self.runes: dict[int, dict] = {}
        self.item_name_index: dict[str, int] = {}
        self.rune_name_index: dict[str, int] = {}
        self.champion_name_index: dict[str, str] = {}
        self._champion_full_cache: dict[str, dict | None] = {}
        self._load_all()

    def _load_all(self, force_refresh: bool = False) -> None:
        self.version = get_latest_version() or get_current_patch()
        self.items = load_items(self.version, force_refresh=force_refresh)
        self.runes = load_runes(self.version, force_refresh=force_refresh)
        self.item_name_index = {
            str(item.get("name", "")).strip().lower(): int(item_id)
            for item_id, item in self.items.items()
            if str(item.get("name", "")).strip()
        }
        self.rune_name_index = build_rune_name_index(self.runes)
        self.champion_name_index = {
            str(name).strip().lower(): str(name)
            for name in self.all_champions.keys()
            if str(name).strip()
        }
        self._champion_full_cache.clear()

    def refresh_if_stale(self) -> bool:
        current_patch = get_current_patch()
        if current_patch and current_patch != self.version:
            self._load_all(force_refresh=True)
            return True
        return False

    def get_champion_kit_summary(self, champion_name: str) -> str:
        if champion_name not in self._champion_full_cache:
            champion_record = self.all_champions.get(champion_name, {})
            champion_id = normalize_champion_key(champion_name, image_key=champion_record.get("image_key"))
            full = load_champion_full(self.version, champion_id)
            self._champion_full_cache[champion_name] = full
        full_data = self._champion_full_cache.get(champion_name)
        return summarize_champion_kit(full_data) if full_data else ""

    def detect_entities(self, text: str) -> dict:
        text_lower = str(text or "").lower()

        champions: list[str] = []
        for lname, canonical in self.champion_name_index.items():
            if lname in text_lower and canonical not in champions:
                champions.append(canonical)
            if len(champions) >= MAX_INJECTED_CHAMPIONS:
                break

        item_ids: list[int] = []
        for lname, item_id in self.item_name_index.items():
            if len(lname) >= 5 and lname in text_lower and item_id not in item_ids:
                item_ids.append(item_id)
            if len(item_ids) >= MAX_INJECTED_ITEMS:
                break

        rune_ids: list[int] = []
        for lname, rune_id in self.rune_name_index.items():
            if len(lname) >= 5 and lname in text_lower and rune_id not in rune_ids:
                rune_ids.append(rune_id)
            if len(rune_ids) >= MAX_INJECTED_RUNES:
                break

        return {"champions": champions, "items": item_ids, "runes": rune_ids}

    def build_context_block(self, detected: dict, current_champion: str = "") -> str:
        if not any(detected.values()) and not current_champion:
            return ""

        lines = [f"=== CONTEXTO DEL PARCHE {self.version} ==="]
        champion_names = list(detected.get("champions", []))
        if current_champion and current_champion not in champion_names:
            champion_names.insert(0, current_champion)
        champion_names = champion_names[:MAX_INJECTED_CHAMPIONS]

        for champion_name in champion_names:
            kit = self.get_champion_kit_summary(champion_name)
            if kit:
                lines.append(f"\n--- KIT DE {champion_name.upper()} (parche {self.version}) ---")
                lines.append(kit)

        for item_id in detected.get("items", []):
            item = self.items.get(int(item_id))
            if not item:
                continue
            desc = strip_html(item.get("description", ""))[:MAX_ITEM_DESC_CHARS]
            stats_str = ", ".join(f"{key}={value}" for key, value in item.get("stats", {}).items())
            lines.append(
                f"\n--- ITEM: {item.get('name', f'Item {item_id}')} (ID {item_id}, {item.get('gold', 0)}g) ---\n"
                f"Stats: {stats_str or 'sin stats base'}\n"
                f"Efecto: {desc}"
            )

        for rune_id in detected.get("runes", []):
            rune = self.runes.get(int(rune_id))
            if not rune:
                continue
            lines.append(
                f"\n--- RUNA: {rune.get('name', f'Rune {rune_id}')} (ID {rune_id}, arbol {rune.get('tree', '-')}) ---\n"
                f"{rune.get('short_desc', '')}"
            )

        return "\n".join(lines)
