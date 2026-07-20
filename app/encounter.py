"""
Core D&D encounter tracking logic.

This module has NO Flask dependency on purpose - it's pure Python so it can
be unit tested in isolation from the web layer. The API layer (api.py)
wraps these classes with HTTP routes.
"""
import uuid
from dataclasses import dataclass, field


class InvalidCombatantError(Exception):
    """Raised when a combatant operation is invalid (bad HP, unknown id, etc.)."""
    pass


@dataclass
class Combatant:
    name: str
    initiative: int
    max_hp: int
    current_hp: int = None
    is_pc: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def __post_init__(self):
        if self.max_hp <= 0:
            raise InvalidCombatantError(f"max_hp must be positive, got {self.max_hp}")
        if self.current_hp is None:
            self.current_hp = self.max_hp
        # Clamp starting HP into a valid range
        self.current_hp = max(0, min(self.current_hp, self.max_hp))

    @property
    def is_alive(self) -> bool:
        return self.current_hp > 0

    def apply_damage(self, amount: int) -> int:
        """Apply damage, clamped so HP never drops below 0. Returns new HP."""
        if amount < 0:
            raise InvalidCombatantError("damage amount cannot be negative")
        self.current_hp = max(0, self.current_hp - amount)
        return self.current_hp

    def apply_healing(self, amount: int) -> int:
        """Apply healing, clamped so HP never exceeds max_hp. Returns new HP."""
        if amount < 0:
            raise InvalidCombatantError("healing amount cannot be negative")
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "initiative": self.initiative,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "is_pc": self.is_pc,
            "is_alive": self.is_alive,
        }


class Encounter:
    """Tracks a single combat encounter: combatants, turn order, and round count."""

    def __init__(self, name: str):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.combatants: dict[str, Combatant] = {}
        self.round = 1
        self.turn_index = 0
        self._turn_order: list[str] = []

    def add_combatant(self, name: str, initiative: int, max_hp: int, is_pc: bool = False) -> Combatant:
        combatant = Combatant(name=name, initiative=initiative, max_hp=max_hp, is_pc=is_pc)
        self.combatants[combatant.id] = combatant
        self._recompute_turn_order()
        return combatant

    def remove_combatant(self, combatant_id: str) -> None:
        if combatant_id not in self.combatants:
            raise InvalidCombatantError(f"no combatant with id {combatant_id}")
        del self.combatants[combatant_id]
        self._recompute_turn_order()

    def get_combatant(self, combatant_id: str) -> Combatant:
        if combatant_id not in self.combatants:
            raise InvalidCombatantError(f"no combatant with id {combatant_id}")
        return self.combatants[combatant_id]

    def _recompute_turn_order(self) -> None:
        """Sort combatant ids by initiative, highest first. Ties broken by name for determinism."""
        self._turn_order = sorted(
            self.combatants.keys(),
            key=lambda cid: (-self.combatants[cid].initiative, self.combatants[cid].name),
        )
        # Keep turn_index in range if combatants were removed
        if self._turn_order:
            self.turn_index %= len(self._turn_order)
        else:
            self.turn_index = 0

    @property
    def turn_order(self) -> list[Combatant]:
        return [self.combatants[cid] for cid in self._turn_order]

    @property
    def current_combatant(self) -> Combatant | None:
        living_order = [cid for cid in self._turn_order if self.combatants[cid].is_alive]
        if not living_order:
            return None
        # Advance turn_index to the next living combatant if current one is dead
        while self._turn_order and not self.combatants[self._turn_order[self.turn_index]].is_alive:
            self.turn_index = (self.turn_index + 1) % len(self._turn_order)
        return self.combatants[self._turn_order[self.turn_index]]

    def next_turn(self) -> Combatant | None:
        """Advance to the next combatant's turn. Increments round when it wraps around."""
        if not self._turn_order:
            return None
        self.turn_index += 1
        if self.turn_index >= len(self._turn_order):
            self.turn_index = 0
            self.round += 1
        return self.current_combatant

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "round": self.round,
            "current_turn": self.current_combatant.to_dict() if self.current_combatant else None,
            "combatants": [c.to_dict() for c in self.turn_order],
        }


class EncounterStore:
    """In-memory store of encounters, keyed by id. Swap this out for SQLite-backed
    storage without touching the Encounter/Combatant logic above."""

    def __init__(self):
        self._encounters: dict[str, Encounter] = {}

    def create(self, name: str) -> Encounter:
        encounter = Encounter(name=name)
        self._encounters[encounter.id] = encounter
        return encounter

    def get(self, encounter_id: str) -> Encounter:
        if encounter_id not in self._encounters:
            raise InvalidCombatantError(f"no encounter with id {encounter_id}")
        return self._encounters[encounter_id]

    def list_all(self) -> list[Encounter]:
        return list(self._encounters.values())

    def delete(self, encounter_id: str) -> None:
        if encounter_id not in self._encounters:
            raise InvalidCombatantError(f"no encounter with id {encounter_id}")
        del self._encounters[encounter_id]
