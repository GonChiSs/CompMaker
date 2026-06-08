from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
LEGACY_SAVE_FILE = BASE_DIR / "data" / "saved_compos.json"


def _resolve_save_file() -> Path:
    local_appdata = Path(os.getenv("LOCALAPPDATA", str(BASE_DIR)))
    preferred_root = (local_appdata / "CompMaker") if getattr(sys, "frozen", False) else BASE_DIR
    fallback_root = BASE_DIR / ".compmaker_cache"

    for root in (preferred_root, fallback_root):
        try:
            data_dir = root / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            return data_dir / "saved_compos.json"
        except OSError:
            continue

    return LEGACY_SAVE_FILE


SAVE_FILE = _resolve_save_file()


def _migrate_legacy_save() -> None:
    if SAVE_FILE == LEGACY_SAVE_FILE or not LEGACY_SAVE_FILE.exists() or SAVE_FILE.exists():
        return
    try:
        SAVE_FILE.write_text(LEGACY_SAVE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError:
        pass


def load_saved() -> list:
    """Devuelve la lista de composiciones guardadas."""
    _migrate_legacy_save()
    if not SAVE_FILE.exists():
        return []
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_composition(name: str, team: list, synergy_score: float, archetype: str = "") -> dict:
    """
    Guarda una composicion en el JSON local.
    team: lista ordenada de campeones del equipo actual.
    """
    saved = load_saved()

    entry = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
        "name": name.upper(),
        "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "synergy_score": round(synergy_score, 1),
        "archetype": archetype,
        "champions": [
            {
                "name": champion.get("name", ""),
                "roles": champion.get("roles", []),
                "damage_type": champion.get("damage_type", []),
                "ability_tags": champion.get("ability_tags", [])[:6],
                "slot_role": champion.get("slot_role", ""),
            }
            for champion in team
            if champion
        ],
    }

    saved.append(entry)
    SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SAVE_FILE, "w", encoding="utf-8") as file:
        json.dump(saved, file, ensure_ascii=False, indent=2)

    return entry


def delete_composition(comp_id: str) -> bool:
    saved = load_saved()
    new_saved = [entry for entry in saved if entry.get("id") != comp_id]
    if len(new_saved) == len(saved):
        return False
    SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SAVE_FILE, "w", encoding="utf-8") as file:
        json.dump(new_saved, file, ensure_ascii=False, indent=2)
    return True


def rename_composition(comp_id: str, new_name: str) -> bool:
    saved = load_saved()
    for entry in saved:
        if entry.get("id") == comp_id:
            entry["name"] = new_name.upper()
            break
    else:
        return False

    SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SAVE_FILE, "w", encoding="utf-8") as file:
        json.dump(saved, file, ensure_ascii=False, indent=2)
    return True


def export_to_text(comp_ids: list[str] | None = None) -> str:
    saved = load_saved()
    if comp_ids is not None:
        allowed_ids = set(comp_ids)
        saved = [entry for entry in saved if entry.get("id") in allowed_ids]

    if not saved:
        return ""

    lines = ["=== COMPMAKER EXPORT v1 ===", ""]
    for entry in saved:
        score = float(entry.get("synergy_score", 0) or 0)
        champion_names = " / ".join(champion.get("name", "?") for champion in entry.get("champions", []))
        lines.append(f"[COMPO] {entry.get('name', 'SIN NOMBRE')}")
        lines.append(f"Fecha: {entry.get('date', '?')}")
        lines.append(f"Sinergia: {score:.1f} / 100")
        lines.append(f"Arquetipo: {entry.get('archetype', '') or 'Sin arquetipo'}")
        lines.append(f"Campeones: {champion_names}")
        lines.append("")

    lines.append("=== FIN EXPORT ===")
    return "\n".join(lines)


def import_from_text(text: str) -> tuple[int, int, list[str]]:
    imported = 0
    skipped = 0
    errors: list[str] = []

    if "=== COMPMAKER EXPORT v1 ===" not in text:
        return 0, 0, ["Formato no reconocido. ¿Es un archivo de exportación de CompMaker?"]

    existing = load_saved()
    existing_keys = {_make_dedup_key(entry) for entry in existing}

    for block in _parse_export_blocks(text):
        try:
            name = block.get("name", "SIN NOMBRE")
            score = float(block.get("sinergia", "0").split("/")[0].strip())
            archetype = block.get("arquetipo", "")
            champion_names = [
                champion.strip()
                for champion in block.get("campeones", "").split("/")
                if champion.strip()
            ]
            champions = [
                {
                    "name": champion_name,
                    "roles": [],
                    "damage_type": [],
                    "ability_tags": [],
                }
                for champion_name in champion_names
            ]

            entry_key = _make_dedup_key({"name": name, "champions": champions})
            if entry_key in existing_keys:
                skipped += 1
                continue

            save_composition(
                name=name,
                team=champions,
                synergy_score=score,
                archetype=archetype,
            )
            existing_keys.add(entry_key)
            imported += 1
        except Exception as exc:
            errors.append(f"Error en bloque '{block.get('name', '?')}': {exc}")
            skipped += 1

    return imported, skipped, errors


def _parse_export_blocks(text: str) -> list[dict]:
    blocks: list[dict] = []
    current: dict | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("[COMPO] "):
            if current is not None:
                blocks.append(current)
            current = {"name": line[len("[COMPO] ") :].strip()}
            continue

        if current is None:
            continue

        if line == "=== FIN EXPORT ===":
            blocks.append(current)
            current = None
            continue

        if ":" in line:
            key_raw, _, value = line.partition(":")
            current[key_raw.strip().lower()] = value.strip()

    if current is not None:
        blocks.append(current)

    return blocks


def _make_dedup_key(entry: dict) -> str:
    name = entry.get("name", "").upper().strip()
    champions = sorted(champion.get("name", "") for champion in entry.get("champions", []))
    return f"{name}|{'|'.join(champions)}"
