from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic.data_loader import load_all_champions
from logic.synergy_engine import ICONIC_COMBOS
from logic.synergy_engine import PASSIVE_INTERACTIONS


CHAMPS = load_all_champions(PROJECT_ROOT)


def test_special_mode1_interactions_reference_existing_champions() -> None:
    missing: list[tuple[str, list[str], float]] = []
    for label, mapping in (("PASSIVE", PASSIVE_INTERACTIONS), ("ICONIC", ICONIC_COMBOS)):
        for duo, value in mapping.items():
            names = sorted(duo)
            if any(name not in CHAMPS for name in names):
                missing.append((label, names, float(value)))

    assert not missing, f"Unknown champions in special mode1 interactions: {missing}"
