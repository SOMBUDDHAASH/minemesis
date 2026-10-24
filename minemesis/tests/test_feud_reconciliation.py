"""
Acceptance Test 4: Feud Resolution and Reconciliation.

Verifies:
- Feuds do not last forever in a static deadlock.
- At least one feud ends in forgiveness, reconciliation, or peace.
- Either through truth revelation (correcting the false belief) or negotiated treaty.
"""

from minemesis.core.types import EventType
from minemesis.systems.simulation import Simulation


def test_feud_ends_in_peace_or_reconciliation() -> None:
    sim = Simulation(seed=42)
    sim.run_years(100)

    events = sim.event_log.all_events()
    peace_events = [e for e in events if e.type == EventType.PEACE]

    assert len(peace_events) >= 1, "Expected at least one feud to end in forgiveness, reconciliation, or peace"

    # Check payload of peace event
    reconciliation_types = [p.payload.get("reconciliation_type") for p in peace_events]
    assert any(
        t in ("Truth Revealed", "Negotiated Treaty") for t in reconciliation_types
    ), f"Expected recognized reconciliation type, got {reconciliation_types}"

    # Verify that the active feud list has resolved feuds
    resolved_feuds = [f for f in sim.active_feuds if not f.active]
    assert len(resolved_feuds) >= 1, "Expected at least one active feud to be marked inactive upon peace"
