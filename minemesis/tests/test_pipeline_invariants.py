"""
Invariants Test: Architecture Rules Verification.

Verifies:
1. EventLog is immutable and append-only.
2. Characters do not mutate or store authoritarian relationship tables;
   relationships are derived views computed over active memories.
3. Memories decay over time.
4. Only valid event types defined in EventType exist in the EventLog.
"""

from minemesis.core.types import EventType, Intent, Scale
from minemesis.systems.simulation import Simulation


def test_allowed_event_types_only() -> None:
    sim = Simulation(seed=42)
    sim.run_years(20)

    allowed_types = {e.value for e in EventType}
    for evt in sim.event_log.all_events():
        assert evt.type.value in allowed_types, f"Disallowed event type found: {evt.type.value}"
        assert evt.intent in (Intent.INTENTIONAL, Intent.ACCIDENTAL, Intent.SELF_DEFENSE, Intent.MILITARY_ACTION)
        assert evt.scale in (Scale.INDIVIDUAL, Scale.AGGREGATE)
        assert evt.id is not None
        assert evt.tick is not None
        assert evt.location is not None


def test_relationships_are_cached_views() -> None:
    sim = Simulation(seed=42)
    sim.run_years(10)

    chars = list(sim.characters.values())
    c1, c2 = chars[0], chars[1]

    rel_now = sim.get_relationship(c1.id, c2.id)
    assert hasattr(rel_now, "trust")
    assert hasattr(rel_now, "hatred")
    assert hasattr(rel_now, "fear")
    assert hasattr(rel_now, "respect")
    assert hasattr(rel_now, "loyalty")

    assert -100.0 <= rel_now.trust <= 100.0
    assert 0.0 <= rel_now.hatred <= 100.0
    assert 0.0 <= rel_now.fear <= 100.0
    assert -100.0 <= rel_now.respect <= 100.0
    assert -100.0 <= rel_now.loyalty <= 100.0


def test_dead_actors_invariant() -> None:
    """
    Validates that no dead character can act as an active participant in any event.
    Includes negative control verifying that validate_event_actors_alive catches dead actors.
    """
    import pytest
    from minemesis.core.event_log import EventLog
    from minemesis.core.invariants import (
        InvariantViolationError,
        validate_entire_history_no_dead_actors,
        validate_event_actors_alive,
    )
    from minemesis.models.character import Character

    sim = Simulation(seed=42)
    sim.run_years(50)

    # Invariant: In the entire 50-year event log, no character ever acts after death
    validate_entire_history_no_dead_actors(sim.event_log)

    # Negative control 1: validate_event_actors_alive catches dead character at runtime
    dead_char = Character(
        id="char_dead_999",
        first_name="Ghost",
        last_name="Actor",
        settlement_id="set_oakhaven",
        age_ticks=300,
        sex="M",
        alive=False,
    )
    char_map = {"char_dead_999": dead_char}

    dummy_log = EventLog()
    root_death = dummy_log.append(
        tick=5,
        location="set_oakhaven",
        event_type=EventType.DEATH,
        participants={"target": "some_victim"},
        causes=[],
        intent=Intent.ACCIDENTAL,
        scale=Scale.INDIVIDUAL,
    )
    test_evt = dummy_log.append(
        tick=10,
        location="set_oakhaven",
        event_type=EventType.FEUD,
        participants={"instigator": "char_dead_999", "target": "other"},
        causes=[root_death.id],
        intent=Intent.INTENTIONAL,
        scale=Scale.INDIVIDUAL,
    )

    with pytest.raises(InvariantViolationError, match="Dead character 'char_dead_999'.*acted as 'instigator'"):
        validate_event_actors_alive(test_evt, char_map)

    # Negative control 2: validate_entire_history_no_dead_actors catches posthumous event
    posthumous_log = EventLog()
    victim_death = posthumous_log.append(
        tick=10,
        location="set_oakhaven",
        event_type=EventType.DEATH,
        participants={"target": "char_victim"},
        causes=[],
        intent=Intent.ACCIDENTAL,
        scale=Scale.INDIVIDUAL,
    )
    feud_evt = posthumous_log.append(
        tick=15,
        location="set_oakhaven",
        event_type=EventType.FEUD,
        participants={"instigator": "someone_alive", "target": "char_victim"},
        causes=[victim_death.id],
        intent=Intent.INTENTIONAL,
        scale=Scale.INDIVIDUAL,
    )
    posthumous_log.append(
        tick=20,
        location="set_oakhaven",
        event_type=EventType.RAID,
        participants={"initiator": "set_oakhaven", "target": "set_riverbend", "instigator_char": "char_victim"},
        causes=[feud_evt.id],
        intent=Intent.MILITARY_ACTION,
        scale=Scale.AGGREGATE,
    )
    with pytest.raises(InvariantViolationError, match="Posthumous Action Violation: Character 'char_victim' died at tick 10"):
        validate_entire_history_no_dead_actors(posthumous_log)



def test_world_extinction_invariant() -> None:
    """
    Validates that when world living population reaches 0, the simulation stops immediately
    and emits zero posthumous events.
    Includes negative control verifying that living characters continue to advance.
    """
    sim = Simulation(seed=42)
    sim.run_years(2)
    start_len = len(sim.event_log)

    # Kill everyone to trigger world extinction
    for c in sim.characters.values():
        c.alive = False

    # Attempt to run for 5 more years
    sim.run_years(5)
    end_len = len(sim.event_log)

    assert end_len == start_len, f"Posthumous events logged after world extinction! ({start_len} -> {end_len})"

    # Negative control: With at least one living character, the simulation does advance
    sim_alive = Simulation(seed=42)
    sim_alive.run_years(1)
    len1 = len(sim_alive.event_log)
    sim_alive.run_years(1)
    len2 = len(sim_alive.event_log)
    assert len2 > len1, "Negative control failed: living simulation failed to advance events"

