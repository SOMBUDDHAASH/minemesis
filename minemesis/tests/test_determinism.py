"""
Acceptance Test 1: Byte-Identical Determinism.

Verifies that re-running the same seed produces 100% byte-identical simulation output,
verifying zero shared RNG state, fixed update order, and deterministic hashing.
"""

import hashlib
import pytest
from minemesis.systems.simulation import Simulation


@pytest.mark.parametrize("seed", [42, 101, 999])
def test_byte_identical_simulation(seed: int) -> None:
    # Run 1
    sim_1 = Simulation(seed)
    sim_1.run_years(50)
    json_1 = sim_1.event_log.to_json(indent=None)
    hash_1 = hashlib.sha256(json_1.encode("utf-8")).hexdigest()

    # Run 2
    sim_2 = Simulation(seed)
    sim_2.run_years(50)
    json_2 = sim_2.event_log.to_json(indent=None)
    hash_2 = hashlib.sha256(json_2.encode("utf-8")).hexdigest()

    assert json_1 == json_2, f"Event log JSON mismatch for seed {seed}"
    assert hash_1 == hash_2, f"SHA-256 hash mismatch for seed {seed}"
    assert len(sim_1.event_log) == len(sim_2.event_log)
