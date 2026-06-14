from __future__ import annotations

from pathlib import Path

import requests

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "ddragon_cache" / "icons"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
REQUEST_TIMEOUT = 10


def download_icon(url: str, cache_filename: str) -> bytes | None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / cache_filename
    if path.exists():
        try:
            return path.read_bytes()
        except Exception:
            pass

    session = requests.Session()
    session.trust_env = False
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        response.raise_for_status()
        path.write_bytes(response.content)
        return response.content
    except Exception:
        return None
