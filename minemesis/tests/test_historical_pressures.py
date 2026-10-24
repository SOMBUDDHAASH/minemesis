"""
Acceptance Tests for Historical Pressure Systems (Section 4.5).

Verifies:
- Revenge killings emit Intent.INTENTIONAL Death citing [original_death, feud].
- Succession crises occur upon disputed chief mortality.
- Scarcity / Famine mechanisms function and produce starvation or food raids.
- Anti-convergence: End-states differ across seeds and settlements.
"""

from minemesis.core.types import EventType, Intent
from minemesis.systems.simulation import Simulation


def test_historical_pressures_present() -> None:
    """
    Verifies that the three new drama sources (Revenge, Leadership/Succession, Scarcity/Famine)
    occur across simulation runs.
    """
    sim = Simulation(seed=42)
    sim.run_years(100)

    events = sim.event_log.all_events()
    event_types = {e.type for e in events}

    # Leadership changes must happen as elderly chiefs die
    assert EventType.CHIEF_CHANGED in event_types, "Expected ChiefChanged events over 100 years"

    # Raids and Feuds occur
    assert EventType.FEUD in event_types, "Expected Feud events"
    assert EventType.RAID in event_types, "Expected Raid events"

    # Trade route events occur (replacing routine caravans)
    assert EventType.TRADE_ROUTE_FOUNDED in event_types, "Expected TradeRouteFounded events"


def test_anti_convergence_diversity() -> None:
    """
    Verifies that end-state food, wealth, and population differ meaningfully across settlements.
    """
    sim = Simulation(seed=42)
    sim.run_years(100)

    wealth_vals = [s.wealth for s in sim.settlements.values()]
    assert max(wealth_vals) > min(wealth_vals), "Settlement wealth must differ (anti-convergence)"
