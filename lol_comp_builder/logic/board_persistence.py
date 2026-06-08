from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
LEGACY_BOARDS_FILE = BASE_DIR / "data" / "pizarra_boards.json"


def _resolve_boards_file() -> Path:
    local_appdata = Path(os.getenv("LOCALAPPDATA", str(BASE_DIR)))
    preferred_root = (local_appdata / "CompMaker") if getattr(sys, "frozen", False) else BASE_DIR
    fallback_root = BASE_DIR / ".compmaker_cache"

    for root in (preferred_root, fallback_root):
        try:
            data_dir = root / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            return data_dir / "pizarra_boards.json"
        except OSError:
            continue

    return LEGACY_BOARDS_FILE


BOARDS_FILE = _resolve_boards_file()


def _migrate_legacy_boards() -> None:
    if BOARDS_FILE == LEGACY_BOARDS_FILE or not LEGACY_BOARDS_FILE.exists() or BOARDS_FILE.exists():
        return
    try:
        BOARDS_FILE.write_text(LEGACY_BOARDS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError:
        pass


def save_all_boards(board_states: dict) -> None:
    try:
        BOARDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        serializable = {str(key): value for key, value in board_states.items()}
        with open(BOARDS_FILE, "w", encoding="utf-8") as file:
            json.dump(serializable, file, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"[pizarra] Could not save boards: {exc}")


def load_all_boards() -> dict:
    result = {idx: {} for idx in range(1, 6)}
    _migrate_legacy_boards()
    if not BOARDS_FILE.exists():
        return result
    try:
        with open(BOARDS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        for key, value in data.items():
            try:
                idx = int(key)
            except (TypeError, ValueError):
                continue
            if 1 <= idx <= 5 and isinstance(value, dict):
                result[idx] = value
    except Exception as exc:
        print(f"[pizarra] Could not load boards: {exc}")
    return result
