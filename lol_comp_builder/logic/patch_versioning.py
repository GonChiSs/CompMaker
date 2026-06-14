from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import requests

DDRAGON_FALLBACK_VERSION = "16.12.1"
VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
REQUEST_TIMEOUT = 8


def _http_get_json(url: str) -> dict | list:
    session = requests.Session()
    session.trust_env = False
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _normalize_patch(value: str | None) -> str:
    if not value:
        return DDRAGON_FALLBACK_VERSION
    return str(value).strip()


@lru_cache(maxsize=1)
def get_current_patch() -> str:
    try:
        payload = _http_get_json(VERSIONS_URL)
        if payload:
            return _normalize_patch(payload[0])
    except Exception:
        pass
    return DDRAGON_FALLBACK_VERSION


def get_embedded_patch(base_dir: Path) -> str:
    data_path = base_dir / "data" / "champions_synergy.json"
    try:
        payload = json.loads(data_path.read_text(encoding="utf-8"))
    except Exception:
        return DDRAGON_FALLBACK_VERSION

    if isinstance(payload, dict):
        meta = payload.get("_meta", {})
        if isinstance(meta, dict):
            return _normalize_patch(meta.get("patch"))
    return DDRAGON_FALLBACK_VERSION


def is_patch_stale(local_patch: str | None, current_patch: str | None = None) -> bool:
    local = _normalize_patch(local_patch)
    current = _normalize_patch(current_patch or get_current_patch())
    return local != current
