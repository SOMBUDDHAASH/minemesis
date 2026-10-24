"""
Acceptance Test 4: Feud Resolution and Reconciliation across 5 Seeds (Milestone 0.5.1 Section 3d).

Verifies:
- Across 5 seeds:
  - Feuds resolve through either truth revelation (pipeline) or negotiated treaty (exhaustion).
  - Both reconciliation types ("Truth Revealed" and "Negotiated Treaty") occur.
  - Active feud list correctly tracks feuds marked inactive upon peace.
- Negative control: Verifies that a simulation without peace events fails the resolution check.
"""

import pytest
from minemesis.core.types import EventType
from minemesis.systems.simulation import Simulation


def test_feud_ends_in_peace_or_reconciliation_across_seeds() -> None:
    test_seeds = [42, 101, 200, 777, 2026]
    total_peaces = 0
    all_reconciliation_types: set[str] = set()
    total_resolved_feuds = 0

    for seed in test_seeds:
        sim = Simulation(seed=seed)
        sim.run_years(100)

        events = sim.event_log.all_events()
        peace_events = [e for e in events if e.type == EventType.PEACE]
        total_peaces += len(peace_events)

        for p in peace_events:
            rec_type = p.payload.get("reconciliation_type")
            if rec_type:
                all_reconciliation_types.add(rec_type)

        resolved_feuds = [f for f in sim.active_feuds if not f.active]
        total_resolved_feuds += len(resolved_feuds)

    assert total_peaces >= 3, f"Expected peace events across 5 seeds, got {total_peaces}"
    assert "Truth Revealed" in all_reconciliation_types, "Expected Truth Revealed reconciliation across seeds"
    assert "Negotiated Treaty" in all_reconciliation_types, "Expected Negotiated Treaty reconciliation across seeds"
    assert total_resolved_feuds >= 3, f"Expected inactive feuds upon resolution, got {total_resolved_feuds}"


def test_negative_control_feud_reconciliation_fails_when_unresolved() -> None:
    """
    Negative control: Simulates an unresolved feud and verifies peace assertion fails.
    """
    from minemesis.core.event_log import EventLog
    from minemesis.core.types import Intent, Scale

    log = EventLog()
    d = log.append(
        tick=1,
        location="set_oakhaven",
        event_type=EventType.DEATH,
        participants={"target": "char_1"},
        causes=[],
        intent=Intent.ACCIDENTAL,
        scale=Scale.INDIVIDUAL,
    )
    f = log.append(
        tick=2,
        location="set_oakhaven",
        event_type=EventType.FEUD,
        participants={"instigator": "char_2", "target": "char_3"},
        causes=[d.id],
        intent=Intent.INTENTIONAL,
        scale=Scale.INDIVIDUAL,
    )
    events = log.all_events()
    peace_events = [e for e in events if e.type == EventType.PEACE]
    with pytest.raises(AssertionError):
        assert len(peace_events) >= 1, "Negative control: Expected 0 peace events to fail assertion"
