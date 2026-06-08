from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "champions_synergy.json"


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def normalize_current_dataset() -> tuple[int, int]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    changed = 0
    total_duplicates_removed = 0

    for champion in data.values():
        tags = champion.get("ability_tags", [])
        deduped = _dedupe_keep_order(tags)
        removed = len(tags) - len(deduped)
        if removed:
            champion["ability_tags"] = deduped
            changed += 1
            total_duplicates_removed += removed

    DATA_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return changed, total_duplicates_removed


def print_summary() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    tag_counts = Counter(tag for champ in data.values() for tag in champ.get("ability_tags", []))
    print(f"champions={len(data)}")
    print(f"unique_tags={len(tag_counts)}")
    print(f"most_common_tags={tag_counts.most_common(15)}")


if __name__ == "__main__":
    changed, removed = normalize_current_dataset()
    print(f"normalized_champions={changed}")
    print(f"duplicates_removed={removed}")
    print_summary()
