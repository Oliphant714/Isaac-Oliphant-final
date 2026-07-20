import pytest
from app.encounter import Combatant, Encounter, InvalidCombatantError


class TestCombatant:
    def test_starts_at_max_hp_by_default(self):
        c = Combatant(name="Goblin", initiative=10, max_hp=7)
        assert c.current_hp == 7
        assert c.is_alive is True

    def test_rejects_non_positive_max_hp(self):
        with pytest.raises(InvalidCombatantError):
            Combatant(name="Ghost", initiative=5, max_hp=0)

    def test_damage_clamps_at_zero(self):
        c = Combatant(name="Goblin", initiative=10, max_hp=7)
        c.apply_damage(100)
        assert c.current_hp == 0
        assert c.is_alive is False

    def test_healing_clamps_at_max_hp(self):
        c = Combatant(name="Goblin", initiative=10, max_hp=7)
        c.apply_damage(5)
        c.apply_healing(100)
        assert c.current_hp == 7

    def test_negative_damage_raises(self):
        c = Combatant(name="Goblin", initiative=10, max_hp=7)
        with pytest.raises(InvalidCombatantError):
            c.apply_damage(-5)

    def test_negative_healing_raises(self):
        c = Combatant(name="Goblin", initiative=10, max_hp=7)
        with pytest.raises(InvalidCombatantError):
            c.apply_healing(-5)


class TestEncounterTurnOrder:
    def test_turn_order_sorted_by_initiative_descending(self):
        e = Encounter(name="Ambush")
        e.add_combatant(name="Slow Guy", initiative=3, max_hp=10)
        e.add_combatant(name="Fast Guy", initiative=18, max_hp=10)
        e.add_combatant(name="Mid Guy", initiative=10, max_hp=10)

        names = [c.name for c in e.turn_order]
        assert names == ["Fast Guy", "Mid Guy", "Slow Guy"]

    def test_ties_broken_alphabetically_for_determinism(self):
        e = Encounter(name="Ambush")
        e.add_combatant(name="Zed", initiative=10, max_hp=10)
        e.add_combatant(name="Alice", initiative=10, max_hp=10)

        names = [c.name for c in e.turn_order]
        assert names == ["Alice", "Zed"]

    def test_next_turn_advances_through_order(self):
        e = Encounter(name="Ambush")
        a = e.add_combatant(name="Alice", initiative=20, max_hp=10)
        b = e.add_combatant(name="Bob", initiative=10, max_hp=10)

        assert e.current_combatant.id == a.id
        e.next_turn()
        assert e.current_combatant.id == b.id

    def test_next_turn_wraps_and_increments_round(self):
        e = Encounter(name="Ambush")
        e.add_combatant(name="Alice", initiative=20, max_hp=10)
        e.add_combatant(name="Bob", initiative=10, max_hp=10)

        assert e.round == 1
        e.next_turn()  # -> Bob
        e.next_turn()  # -> wraps to Alice, round 2
        assert e.round == 2
        assert e.current_combatant.name == "Alice"

    def test_current_combatant_skips_dead_combatants(self):
        e = Encounter(name="Ambush")
        a = e.add_combatant(name="Alice", initiative=20, max_hp=10)
        b = e.add_combatant(name="Bob", initiative=10, max_hp=10)
        e.add_combatant(name="Carl", initiative=5, max_hp=10)

        a.apply_damage(100)  # kill Alice, who is first in turn order
        assert e.current_combatant.name == "Bob"

    def test_current_combatant_is_none_when_all_dead(self):
        e = Encounter(name="Ambush")
        a = e.add_combatant(name="Alice", initiative=20, max_hp=10)
        a.apply_damage(100)
        assert e.current_combatant is None

    def test_remove_combatant_updates_turn_order(self):
        e = Encounter(name="Ambush")
        a = e.add_combatant(name="Alice", initiative=20, max_hp=10)
        e.add_combatant(name="Bob", initiative=10, max_hp=10)

        e.remove_combatant(a.id)
        assert len(e.turn_order) == 1
        assert e.turn_order[0].name == "Bob"

    def test_remove_unknown_combatant_raises(self):
        e = Encounter(name="Ambush")
        with pytest.raises(InvalidCombatantError):
            e.remove_combatant("nonexistent-id")

    def test_get_unknown_combatant_raises(self):
        e = Encounter(name="Ambush")
        with pytest.raises(InvalidCombatantError):
            e.get_combatant("nonexistent-id")
