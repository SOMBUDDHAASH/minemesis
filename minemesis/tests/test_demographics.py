"""
Acceptance Test 5: Demographic Balance across Seeds.

Verifies:
- Across diverse seeds:
  - No total extinction (population > 0).
  - No single faction world domination (all 3 settlements maintain a population).
- Simulation successfully runs for 100 simulated years without deadlock or unhandled crashes.
"""

import pytest
from minemesis.systems.simulation import Simulation


@pytest.mark.parametrize("seed", [42, 101, 777, 2026])
def test_demographic_balance_100_years(seed: int) -> None:
    sim = Simulation(seed)
    sim.run_years(100)

    living = sim.living_characters
    total_pop = len(living)

    # 1. No total extinction
    assert total_pop >= 15, f"Seed {seed}: Population collapsed to {total_pop}"

    # 2. Check each settlement
    settlement_counts = {}
    for s_id in sim.settlements.keys():
        count = len([c for c in living if c.settlement_id == s_id])
        settlement_counts[s_id] = count
        # No single faction world domination: all 3 settlements must have living members
        assert count > 0, f"Seed {seed}: Settlement {s_id} was depopulated to 0"

    # Verify no single settlement holds more than 75% of total population
    for s_id, count in settlement_counts.items():
        ratio = count / total_pop
        assert ratio < 0.75, f"Seed {seed}: Settlement {s_id} dominated with {ratio:.1%} of population"
