from __future__ import annotations

from dataclasses import dataclass, field

ROLES = ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]


@dataclass
class CompositionState:
    """Representa el estado del draft actual."""

    picks: dict[str, str | None] = field(
        default_factory=lambda: {role: None for role in ROLES}
    )

    def set_pick(self, role: str, champion_name: str | None) -> None:
        self.picks[role] = champion_name

    def get_pick(self, role: str) -> str | None:
        return self.picks.get(role)

    def clear(self) -> None:
        for role in ROLES:
            self.picks[role] = None

    def selected_champions(self) -> list[str]:
        return [champion for champion in self.picks.values() if champion]

    def empty_roles(self) -> list[str]:
        return [role for role, champion in self.picks.items() if not champion]

    def as_dict(self) -> dict[str, str | None]:
        return dict(self.picks)
