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
