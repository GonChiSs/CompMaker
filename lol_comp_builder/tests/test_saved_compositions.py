from __future__ import annotations

import importlib
import json
import shutil
import sys
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_frozen_build_uses_localappdata_for_saved_compositions(monkeypatch) -> None:
    workspace_tmp = PROJECT_ROOT / ".test_tmp" / f"saved-comps-{uuid.uuid4().hex}"
    shutil.rmtree(workspace_tmp, ignore_errors=True)
    workspace_tmp.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCALAPPDATA", str(workspace_tmp / "localappdata"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    import logic.saved_compositions as saved_compositions

    module = importlib.reload(saved_compositions)

    assert module.SAVE_FILE == workspace_tmp / "localappdata" / "CompMaker" / "data" / "saved_compos.json"

    monkeypatch.delattr(sys, "frozen", raising=False)
    importlib.reload(module)
    shutil.rmtree(workspace_tmp, ignore_errors=True)


def test_load_saved_migrates_legacy_file(monkeypatch) -> None:
    workspace_tmp = PROJECT_ROOT / ".test_tmp" / f"saved-comps-{uuid.uuid4().hex}"
    shutil.rmtree(workspace_tmp, ignore_errors=True)
    workspace_tmp.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCALAPPDATA", str(workspace_tmp / "localappdata"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    import logic.saved_compositions as saved_compositions

    module = importlib.reload(saved_compositions)
    legacy_file = module.LEGACY_SAVE_FILE
    legacy_file.parent.mkdir(parents=True, exist_ok=True)
    expected = [{"id": "abc123", "name": "TEST COMPO"}]
    legacy_file.write_text(json.dumps(expected, ensure_ascii=False), encoding="utf-8")

    try:
        assert module.load_saved() == expected
        assert module.SAVE_FILE.exists()
        assert json.loads(module.SAVE_FILE.read_text(encoding="utf-8")) == expected
    finally:
        legacy_file.unlink(missing_ok=True)
        module.SAVE_FILE.unlink(missing_ok=True)
        monkeypatch.delattr(sys, "frozen", raising=False)
        importlib.reload(module)
        shutil.rmtree(workspace_tmp, ignore_errors=True)
