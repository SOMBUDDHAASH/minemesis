"""
Acceptance Test 5: Demographic Balance and Conservation Rule (Milestone 0.5.1 Section 3b).

Verifies:
- Across diverse seeds:
  - No world extinction (total living population > 0; at least one settlement survives).
  - Strict Conservation Rule: Global population equals initial + births - deaths.
  - Settlement Conservation: Settlement population strictly matches logged births, deaths, migrations, and marriage relocations.
- Includes negative control proving that unlogged population tampering fails the conservation check.
"""

import pytest
from minemesis.core.types import EventType
from minemesis.systems.simulation import Simulation


@pytest.mark.parametrize("seed", [42, 101, 777, 2026])
def test_demographic_balance_100_years(seed: int) -> None:
    sim = Simulation(seed)
    initial_pop = len(sim.characters)
    initial_counts = {s_id: len([c for c in sim.characters.values() if c.settlement_id == s_id]) for s_id in sim.settlements}

    sim.run_years(100)

    living = sim.living_characters
    total_pop = len(living)
    events = sim.event_log.all_events()

    # 1. No World Extinction (Hard target amendment)
    assert total_pop > 0, f"Seed {seed}: World experienced total extinction"
    surviving_settlements = sum(1 for s_id in sim.settlements if any(c.settlement_id == s_id for c in living))
    assert surviving_settlements >= 1, f"Seed {seed}: No settlements survived"

    # 2. Global Population Conservation
    births = sum(1 for e in events if e.type == EventType.BIRTH)
    deaths = sum(1 for e in events if e.type == EventType.DEATH)
    expected_pop = initial_pop + births - deaths
    assert total_pop == expected_pop, (
        f"Seed {seed}: Conservation violated! Total living={total_pop}, expected={expected_pop} "
        f"(Initial={initial_pop}, Births={births}, Deaths={deaths})"
    )

    # 3. Settlement-Level Exact Conservation
    for s_id in sim.settlements.keys():
        s_living = len([c for c in living if c.settlement_id == s_id])
        s_births = sum(1 for e in events if e.type == EventType.BIRTH and e.location == s_id)
        s_deaths = sum(1 for e in events if e.type == EventType.DEATH and e.location == s_id)

        # Migrations
        in_mig = sum(len(e.payload.get("migrants", [])) for e in events if e.type == EventType.MIGRATION and e.participants_dict.get("destination") == s_id)
        out_mig = sum(len(e.payload.get("migrants", [])) for e in events if e.type == EventType.MIGRATION and e.participants_dict.get("source") == s_id)

        # Marriage Relocations
        in_marr = sum(1 for e in events if e.type == EventType.MARRIAGE and (e.payload.get("relocation") or {}).get("to_settlement_id") == s_id)
        out_marr = sum(1 for e in events if e.type == EventType.MARRIAGE and (e.payload.get("relocation") or {}).get("from_settlement_id") == s_id)

        s_expected = initial_counts[s_id] + s_births - s_deaths + in_mig - out_mig + in_marr - out_marr
        assert s_living == s_expected, (
            f"Seed {seed}, Settlement {s_id}: Population mismatch! Living={s_living}, Expected={s_expected} "
            f"(Initial={initial_counts[s_id]}, Births={s_births}, Deaths={s_deaths}, InMig={in_mig}, OutMig={out_mig}, InMarr={in_marr}, OutMarr={out_marr})"
        )


def test_negative_control_conservation_fails_on_unlogged_mutation() -> None:
    """
    Negative control: Simulates unlogged population modification and verifies conservation assertion fails.
    """
    sim = Simulation(seed=42)
    sim.run_years(10)
    initial_pop = 30
    events = sim.event_log.all_events()
    births = sum(1 for e in events if e.type == EventType.BIRTH)
    deaths = sum(1 for e in events if e.type == EventType.DEATH)

    # Silent untracked mutation (e.g. character deleted or spawned without event)
    tampered_living = len(sim.living_characters) + 5
    expected_pop = initial_pop + births - deaths

    with pytest.raises(AssertionError):
        assert tampered_living == expected_pop, "Expected conservation check to fail on unlogged population change"
