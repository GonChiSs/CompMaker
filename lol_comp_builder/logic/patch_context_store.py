from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from logic.item_data_loader import ItemDataLoader
from logic.lol_data_fetcher import fetch_tier_list
from logic.rune_data_loader import RuneDataLoader

ROLE_ORDER = ("top", "jungle", "middle", "bottom", "support")
ROLE_LABELS = {
    "top": "TOP",
    "jungle": "JGL",
    "middle": "MID",
    "bottom": "ADC",
    "support": "SUP",
}
MAX_ROLE_POOL = 8
MAX_ARCHETYPE_ENTRIES = 3
MAX_COUNTER_ENTRIES = 4


def _slugify(value: str) -> str:
    return "".join(ch.lower() for ch in str(value or "") if ch.isalnum()) or "unknown"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class PatchContextStore:
    def __init__(
        self,
        base_dir: Path,
        champion_pool: dict[str, dict],
        item_loader: ItemDataLoader,
        rune_loader: RuneDataLoader,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.champion_pool = champion_pool
        self.item_loader = item_loader
        self.rune_loader = rune_loader
        self.cache_dir = self.base_dir / "data" / "context_cache"
        self.champion_dir = self.cache_dir / "champion_context"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.champion_dir.mkdir(parents=True, exist_ok=True)

    def _patch_snapshot_path(self, version: str) -> Path:
        return self.cache_dir / f"patch_context_min_{version}.json"

    def _champion_context_path(self, champion: str, role: str) -> Path:
        return self.champion_dir / f"{_slugify(champion)}_{_slugify(role)}.json"

    def ensure_patch_snapshot(self, version: str, force_refresh: bool = False) -> dict:
        path = self._patch_snapshot_path(version)
        if path.exists() and not force_refresh:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if str(payload.get("version", "")).strip() == version:
                    return payload
            except Exception:
                pass

        items = self.item_loader.load_items(version, force_refresh=force_refresh)
        runes = self.rune_loader.load_runes(version, force_refresh=force_refresh)

        role_pools: dict[str, list[dict]] = {}
        for role in ROLE_ORDER:
            try:
                entries = fetch_tier_list(role)
            except Exception:
                entries = []
            role_pools[role] = [
                {
                    "champion": str(entry.get("id", "")),
                    "tier": str(entry.get("tier", "C")),
                    "rank": int(entry.get("rank", 999)),
                    "winrate": round(float(entry.get("winrate", 0.0)), 2),
                    "pickrate": round(float(entry.get("pickrate", 0.0)), 2),
                }
                for entry in entries[:MAX_ROLE_POOL]
                if str(entry.get("id", "")).strip()
            ]

        champion_aliases = {
            _slugify(champion_name): champion_name
            for champion_name in sorted(self.champion_pool)
            if str(champion_name).strip()
        }
        item_aliases = {
            _slugify(item.get("name", "")): int(item_id)
            for item_id, item in items.items()
            if str(item.get("name", "")).strip()
        }
        rune_aliases = {
            _slugify(rune.get("name", "")): int(rune_id)
            for rune_id, rune in runes.items()
            if str(rune.get("name", "")).strip()
        }

        prompt_lines = [
            f"PATCH {version}.",
            "Usa solo informacion coherente con este parche.",
            f"Items validos: {len(items)}. Runas validas: {len(runes)}. Campeones disponibles: {len(self.champion_pool)}.",
            "Pool meta resumido por rol:",
        ]
        for role in ROLE_ORDER:
            pool = role_pools.get(role, [])
            if not pool:
                continue
            pool_text = ", ".join(
                f"{entry['champion']}({entry['tier']},{entry['winrate']:.1f}% WR)"
                for entry in pool[:5]
            )
            prompt_lines.append(f"{ROLE_LABELS[role]}: {pool_text}.")
        prompt_lines.append("Si faltan cifras exactas para una pregunta, responde con criterio y marca la parte como inferencia.")

        payload = {
            "version": version,
            "generated_at": _utc_now_iso(),
            "important_changes": [],
            "valid_items": [
                {"id": int(item_id), "name": str(item.get("name", ""))}
                for item_id, item in sorted(items.items())
                if str(item.get("name", "")).strip()
            ],
            "valid_runes": [
                {"id": int(rune_id), "name": str(rune.get("name", "")), "tree": str(rune.get("tree", ""))}
                for rune_id, rune in sorted(runes.items())
                if str(rune.get("name", "")).strip()
            ],
            "role_meta_pools": role_pools,
            "champion_aliases": champion_aliases,
            "item_aliases": item_aliases,
            "rune_aliases": rune_aliases,
            "prompt_min": "\n".join(prompt_lines),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    def get_patch_prompt(self, version: str) -> str:
        path = self._patch_snapshot_path(version)
        if not path.exists():
            return f"PATCH {version}. Usa informacion de este parche y evita datos fuera de version."
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return str(payload.get("prompt_min", "")).strip() or f"PATCH {version}."
        except Exception:
            return f"PATCH {version}."

    def write_champion_context(
        self,
        *,
        version: str,
        champion: str,
        role: str,
        current_meta: dict,
        current_runes: dict,
        current_items: dict[int, dict],
        rune_entries: dict[int, dict],
        champion_record: dict,
    ) -> dict:
        build_ids = [int(item_id) for item_id in current_meta.get("full_build", []) if int(item_id) in current_items][:6]
        build_names = [str(current_items[item_id].get("name", f"Item {item_id}")) for item_id in build_ids]

        primary_runes = [
            str(rune_entries[int(rune_id)].get("name", f"Rune {rune_id}"))
            for rune_id in current_runes.get("primary_runes", [])[:4]
            if int(rune_id) in rune_entries
        ]
        secondary_runes = [
            str(rune_entries[int(rune_id)].get("name", f"Rune {rune_id}"))
            for rune_id in current_runes.get("secondary_runes", [])[:3]
            if int(rune_id) in rune_entries
        ]
        stat_shards = [
            str(rune_entries[int(rune_id)].get("name", f"Rune {rune_id}"))
            for rune_id in current_runes.get("stat_shards", [])[:3]
            if int(rune_id) in rune_entries
        ]
        archetypes = champion_record.get("archetype_fit", {}) if isinstance(champion_record, dict) else {}
        top_archetypes = [
            name
            for name, _ in sorted(archetypes.items(), key=lambda entry: entry[1], reverse=True)[:MAX_ARCHETYPE_ENTRIES]
            if str(name).strip()
        ]
        counters = [
            str(name)
            for name in (champion_record.get("countered_by", []) if isinstance(champion_record, dict) else [])
            if str(name).strip()
        ][:MAX_COUNTER_ENTRIES]
        tags = [
            str(tag)
            for tag in (champion_record.get("ability_tags", []) if isinstance(champion_record, dict) else [])
            if str(tag).strip()
        ][:6]

        prompt_lines = [
            f"Campeon activo: {champion} {ROLE_LABELS.get(role, role.upper())}.",
            f"Build meta visible: {' > '.join(build_names) if build_names else 'sin build meta verificada'}.",
            (
                f"Runas meta: primaria {', '.join(primary_runes) if primary_runes else 'sin datos'}; "
                f"secundaria {', '.join(secondary_runes) if secondary_runes else 'sin datos'}; "
                f"shards {', '.join(stat_shards) if stat_shards else 'sin datos'}."
            ),
        ]
        if top_archetypes:
            prompt_lines.append(f"Arquetipos afines: {', '.join(top_archetypes)}.")
        if tags:
            prompt_lines.append(f"Etiquetas del pick: {', '.join(tags)}.")
        if counters:
            prompt_lines.append(f"Rivales historicamente incomodos en datos locales: {', '.join(counters)}.")
        if current_meta.get("found"):
            prompt_lines.append(
                f"Meta actual: WR {float(current_meta.get('winrate', 0.0)):.1f}% y PR {float(current_meta.get('pickrate', 0.0)):.1f}%."
            )

        payload = {
            "version": version,
            "champion": champion,
            "role": role,
            "generated_at": _utc_now_iso(),
            "meta_build_ids": build_ids,
            "meta_build_names": build_names,
            "runes_primary": primary_runes,
            "runes_secondary": secondary_runes,
            "stat_shards": stat_shards,
            "top_archetypes": top_archetypes,
            "tags": tags,
            "countered_by": counters,
            "prompt_min": "\n".join(prompt_lines),
        }
        self._champion_context_path(champion, role).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return payload

    def get_champion_prompt(self, champion: str, role: str) -> str:
        path = self._champion_context_path(champion, role)
        if not path.exists():
            return f"Campeon activo: {champion} {ROLE_LABELS.get(role, role.upper())}."
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return str(payload.get("prompt_min", "")).strip() or f"Campeon activo: {champion}."
        except Exception:
            return f"Campeon activo: {champion}."
