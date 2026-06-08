from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.draft_state import DRAFT_ORDER


def test_second_pick_phase_matches_pro_draft_sequence() -> None:
    assert DRAFT_ORDER[16:20] == [
        ("RED", "PICK", 3),
        ("BLUE", "PICK", 3),
        ("BLUE", "PICK", 4),
        ("RED", "PICK", 4),
    ]
