from __future__ import annotations

from dataclasses import dataclass, field

from logic.composition import ROLES


DRAFT_ORDER = [
    ("BLUE", "BAN", 0),
    ("RED", "BAN", 0),
    ("BLUE", "BAN", 1),
    ("RED", "BAN", 1),
    ("BLUE", "BAN", 2),
    ("RED", "BAN", 2),
    ("BLUE", "PICK", 0),
    ("RED", "PICK", 0),
    ("RED", "PICK", 1),
    ("BLUE", "PICK", 1),
    ("BLUE", "PICK", 2),
    ("RED", "PICK", 2),
    ("RED", "BAN", 3),
    ("BLUE", "BAN", 3),
    ("RED", "BAN", 4),
    ("BLUE", "BAN", 4),
    ("RED", "PICK", 3),
    ("BLUE", "PICK", 3),
    ("BLUE", "PICK", 4),
    ("RED", "PICK", 4),
]


@dataclass
class DraftState:
    user_side: str
    current_turn: int = 0
    blue_bans: list[dict] = field(default_factory=list)
    red_bans: list[dict] = field(default_factory=list)
    blue_picks: list[dict] = field(default_factory=list)
    red_picks: list[dict] = field(default_factory=list)
    phase: str = "BAN_1"
    hovered_champion: dict | None = None

    def current_action(self) -> tuple[str, str, int]:
        if self.current_turn >= len(DRAFT_ORDER):
            return ("COMPLETE", "COMPLETE", -1)
        return DRAFT_ORDER[self.current_turn]

    def active_team(self) -> str:
        return self.current_action()[0]

    def is_user_turn(self) -> bool:
        return self.active_team() == self.user_side

    def get_all_banned(self) -> list[dict]:
        return self.blue_bans + self.red_bans

    def get_all_picked(self) -> list[dict]:
        return self.blue_picks + self.red_picks

    def get_unavailable(self) -> set[str]:
        return {champ["name"] for champ in self.get_all_banned() + self.get_all_picked()}

    def ally_team(self) -> list[dict]:
        return self.blue_picks if self.user_side == "BLUE" else self.red_picks

    def enemy_team(self) -> list[dict]:
        return self.red_picks if self.user_side == "BLUE" else self.blue_picks

    def team_for_side(self, side: str) -> list[dict]:
        return self.blue_picks if side == "BLUE" else self.red_picks

    def bans_for_side(self, side: str) -> list[dict]:
        return self.blue_bans if side == "BLUE" else self.red_bans

    def assign_phase(self) -> None:
        if self.current_turn >= len(DRAFT_ORDER):
            self.phase = "COMPLETE"
        elif self.current_turn <= 5:
            self.phase = "BAN_1"
        elif self.current_turn <= 11:
            self.phase = "PICK_1"
        elif self.current_turn <= 15:
            self.phase = "BAN_2"
        else:
            self.phase = "PICK_2"

    def add_ban(self, side: str, champion: dict) -> None:
        target = self.blue_bans if side == "BLUE" else self.red_bans
        target.append(dict(champion))
        self.advance_turn()

    def add_pick(self, side: str, champion: dict, assigned_role: str) -> None:
        target = self.blue_picks if side == "BLUE" else self.red_picks
        existing_by_role = self.role_map_for_side(side)
        displaced = existing_by_role.get(assigned_role)
        if displaced is not None:
            filled_roles = {picked.get("assigned_role") for picked in target if picked.get("assigned_role")}
            fallback_role = next((role for role in ROLES if role not in filled_roles), None)
            if fallback_role is not None:
                for picked in target:
                    if picked.get("name") == displaced.get("name") and picked.get("assigned_role") == assigned_role:
                        picked["assigned_role"] = fallback_role
                        break

        payload = dict(champion)
        payload["assigned_role"] = assigned_role
        target.append(payload)
        self.advance_turn()

    def role_map_for_side(self, side: str) -> dict[str, dict]:
        mapping = {}
        for champion in self.team_for_side(side):
            role = champion.get("assigned_role")
            if role:
                mapping[role] = champion
        return mapping

    def filled_roles_for_side(self, side: str) -> list[str]:
        return list(self.role_map_for_side(side).keys())

    def available_roles_for_side(self, side: str, champion: dict) -> list[str]:
        return list(ROLES)

    def free_roles_for_side(self, side: str) -> list[str]:
        filled = set(self.filled_roles_for_side(side))
        return [role for role in ROLES if role not in filled]

    def advance_turn(self) -> None:
        self.current_turn += 1
        self.assign_phase()

    def clone_for_side(self, side: str) -> "DraftState":
        return DraftState(
            user_side=side,
            current_turn=self.current_turn,
            blue_bans=[dict(champ) for champ in self.blue_bans],
            red_bans=[dict(champ) for champ in self.red_bans],
            blue_picks=[dict(champ) for champ in self.blue_picks],
            red_picks=[dict(champ) for champ in self.red_picks],
            phase=self.phase,
            hovered_champion=dict(self.hovered_champion) if self.hovered_champion else None,
        )
