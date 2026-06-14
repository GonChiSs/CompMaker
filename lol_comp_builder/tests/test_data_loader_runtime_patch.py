from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.data_loader import DataLoader


def test_prepare_runtime_data_updates_runtime_patch(monkeypatch) -> None:
    workspace_tmp = PROJECT_ROOT / ".test_tmp" / f"runtime-patch-{uuid.uuid4().hex}"
    shutil.rmtree(workspace_tmp, ignore_errors=True)
    (workspace_tmp / "data").mkdir(parents=True, exist_ok=True)
    bundle_path = workspace_tmp / "data" / "champions_synergy.json"
    bundle_payload = {
        "_meta": {
            "patch": "16.11.1",
            "source": "embedded",
            "updated_at": "2026-06-08",
        },
        "Aatrox": {
            "name": "Aatrox",
            "roles": ["TOP"],
            "damage_type": ["AD"],
            "mobility": 3,
            "range_type": "MELEE",
            "ability_tags": ["AD_BURST"],
        },
    }
    bundle_path.write_text(json.dumps(bundle_payload, ensure_ascii=False), encoding="utf-8")

    loader = DataLoader(workspace_tmp)
    monkeypatch.setattr("logic.data_loader.get_current_patch", lambda: "99.1.1")
    monkeypatch.setattr(loader, "ensure_app_icon", lambda: loader.icon_path)
    monkeypatch.setattr(loader, "_download_missing_images", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        loader,
        "_fetch_remote_champions",
        lambda patch: {
            "data": {
                "Aatrox": {"id": "Aatrox", "name": "Aatrox"},
                "Ahri": {"id": "Ahri", "name": "Ahri"},
            }
        },
    )

    try:
        bundle = loader.prepare_runtime_data()
        runtime_payload = json.loads(loader.synergy_path.read_text(encoding="utf-8"))

        assert bundle["data_meta"]["patch"] == "99.1.1"
        assert bundle["data_meta"]["current_patch"] == "99.1.1"
        assert bundle["data_meta"]["is_stale"] is False
        assert runtime_payload["_meta"]["patch"] == "99.1.1"
        assert runtime_payload["_meta"]["source"] == "runtime-auto"
        assert runtime_payload["Aatrox"]["name"] == "Aatrox"
        assert "Ahri" in bundle["champion_pool"]
    finally:
        shutil.rmtree(workspace_tmp, ignore_errors=True)


def test_prepare_runtime_data_auto_registers_new_champions(monkeypatch) -> None:
    workspace_tmp = PROJECT_ROOT / ".test_tmp" / f"runtime-register-{uuid.uuid4().hex}"
    shutil.rmtree(workspace_tmp, ignore_errors=True)
    (workspace_tmp / "data").mkdir(parents=True, exist_ok=True)
    bundle_path = workspace_tmp / "data" / "champions_synergy.json"
    bundle_payload = {
        "_meta": {
            "patch": "16.11.1",
            "source": "embedded",
            "updated_at": "2026-06-08",
        },
        "Aatrox": {
            "name": "Aatrox",
            "roles": ["TOP"],
            "damage_type": ["AD"],
            "mobility": 3,
            "range_type": "MELEE",
            "ability_tags": ["AD_BURST"],
        },
    }
    bundle_path.write_text(json.dumps(bundle_payload, ensure_ascii=False), encoding="utf-8")

    loader = DataLoader(workspace_tmp)
    monkeypatch.setattr("logic.data_loader.get_current_patch", lambda: "99.2.1")
    monkeypatch.setattr(loader, "ensure_app_icon", lambda: loader.icon_path)
    monkeypatch.setattr(loader, "_download_missing_images", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        loader,
        "_fetch_remote_champions",
        lambda patch: {
            "data": {
                "Aatrox": {"id": "Aatrox", "name": "Aatrox"},
                "NewChamp": {"id": "NewChamp", "name": "NewChamp"},
            }
        },
    )

    try:
        loader.prepare_runtime_data()
        runtime_payload = json.loads(loader.synergy_path.read_text(encoding="utf-8"))

        assert "NewChamp" in runtime_payload
        assert runtime_payload["NewChamp"]["name"] == "NewChamp"
        assert runtime_payload["NewChamp"]["roles"] == ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]
        assert runtime_payload["NewChamp"]["image_key"] == "NewChamp"
        assert runtime_payload["_meta"]["auto_registered_count"] == 1
        assert runtime_payload["_meta"]["source"] == "runtime-auto"
    finally:
        shutil.rmtree(workspace_tmp, ignore_errors=True)


def test_update_champion_configuration_persists_roles_and_tags() -> None:
    workspace_tmp = PROJECT_ROOT / ".test_tmp" / f"runtime-edit-{uuid.uuid4().hex}"
    shutil.rmtree(workspace_tmp, ignore_errors=True)
    (workspace_tmp / "data").mkdir(parents=True, exist_ok=True)
    bundle_path = workspace_tmp / "data" / "champions_synergy.json"
    bundle_payload = {
        "_meta": {
            "patch": "16.11.1",
            "source": "embedded",
            "updated_at": "2026-06-08",
        },
        "Ahri": {
            "name": "Ahri",
            "roles": ["MID"],
            "damage_type": ["AP"],
            "mobility": 4,
            "range_type": "RANGED",
            "ability_tags": ["AP_BURST", "WAVECLEAR"],
            "tags": ["Burst", "Roamer"],
            "image_key": "Ahri",
        },
    }
    bundle_path.write_text(json.dumps(bundle_payload, ensure_ascii=False), encoding="utf-8")

    loader = DataLoader(workspace_tmp)
    loader._sync_runtime_synergy_file()

    try:
        updated = loader.update_champion_configuration(
            "Ahri",
            roles=["MID", "SUPPORT", "MID"],
            ability_tags=["charm_cc", " waveclear ", "CHARM_CC"],
            tags=["Pick", "Roamer", "Pick"],
        )
        runtime_payload = json.loads(loader.synergy_path.read_text(encoding="utf-8"))

        assert updated["roles"] == ["MID", "SUPPORT"]
        assert updated["ability_tags"] == ["CHARM_CC", "WAVECLEAR"]
        assert updated["tags"] == ["Pick", "Roamer"]
        assert runtime_payload["Ahri"]["roles"] == ["MID", "SUPPORT"]
        assert runtime_payload["Ahri"]["ability_tags"] == ["CHARM_CC", "WAVECLEAR"]
        assert runtime_payload["Ahri"]["tags"] == ["Pick", "Roamer"]
    finally:
        shutil.rmtree(workspace_tmp, ignore_errors=True)


def test_sync_runtime_synergy_file_preserves_runtime_only_champions() -> None:
    workspace_tmp = PROJECT_ROOT / ".test_tmp" / f"runtime-sync-{uuid.uuid4().hex}"
    shutil.rmtree(workspace_tmp, ignore_errors=True)
    (workspace_tmp / "data").mkdir(parents=True, exist_ok=True)
    bundle_path = workspace_tmp / "data" / "champions_synergy.json"
    bundle_payload = {
        "_meta": {
            "patch": "16.11.1",
            "source": "embedded",
            "updated_at": "2026-06-08",
        },
        "Ahri": {
            "name": "Ahri",
            "roles": ["MID"],
            "damage_type": ["AP"],
            "mobility": 4,
            "range_type": "RANGED",
            "ability_tags": ["AP_BURST"],
            "tags": ["Burst"],
            "image_key": "Ahri",
        },
    }
    bundle_path.write_text(json.dumps(bundle_payload, ensure_ascii=False), encoding="utf-8")

    loader = DataLoader(workspace_tmp)
    loader._sync_runtime_synergy_file()

    runtime_payload = {
        "_meta": {
            "patch": "99.2.1",
            "source": "runtime-auto",
            "updated_at": "2026-06-12",
        },
        "Ahri": {
            "name": "Ahri",
            "roles": ["MID", "SUPPORT"],
            "damage_type": ["AP"],
            "mobility": 5,
            "range_type": "RANGED",
            "ability_tags": ["AP_BURST", "CHARM_CC"],
            "tags": ["Burst", "Roamer"],
            "image_key": "Ahri",
        },
        "Aurora": {
            "name": "Aurora",
            "roles": ["MID", "TOP"],
            "damage_type": ["AP"],
            "mobility": 4,
            "range_type": "RANGED",
            "ability_tags": ["AP_BURST", "WAVECLEAR"],
            "tags": ["Burst", "Roamer"],
            "image_key": "Aurora",
        },
    }
    loader.synergy_path.write_text(json.dumps(runtime_payload, ensure_ascii=False), encoding="utf-8")

    try:
        loader._sync_runtime_synergy_file()
        merged_payload = json.loads(loader.synergy_path.read_text(encoding="utf-8"))

        assert merged_payload["_meta"]["patch"] == "99.2.1"
        assert merged_payload["Ahri"]["roles"] == ["MID", "SUPPORT"]
        assert "Aurora" in merged_payload
        assert merged_payload["Aurora"]["roles"] == ["MID", "TOP"]
    finally:
        shutil.rmtree(workspace_tmp, ignore_errors=True)
