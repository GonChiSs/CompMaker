from __future__ import annotations

import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication

from ui.pizarra_mode import MapCanvas


def _load_champions() -> tuple[dict[str, dict], dict[str, object]]:
    data_path = PROJECT_ROOT / "data" / "champions_synergy.json"
    champions = json.loads(data_path.read_text(encoding="utf-8"))
    normalized: dict[str, dict] = {}
    for name, payload in champions.items():
        if name == "_meta":
            continue
        payload.setdefault("name", name)
        normalized[name] = payload
    return normalized, {}


def test_capture_board_snapshot_hides_toolbars_temporarily() -> None:
    app = QApplication.instance() or QApplication([])
    champions, champion_images = _load_champions()
    canvas = MapCanvas(champions, champion_images)
    canvas.resize(900, 600)
    canvas.show()
    app.processEvents()

    canvas.strokes.append(
        {
            "points": [QPoint(100, 100), QPoint(220, 180)],
            "color": canvas.current_color,
            "width": 2,
        }
    )

    snapshot = canvas.capture_board_snapshot()

    assert not snapshot.isNull()
    assert snapshot.size() == canvas.size()
    assert canvas.left_toolbar.isVisible()
    assert canvas.right_toolbar.isVisible()

    canvas.close()
