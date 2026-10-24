"""
Acceptance Test 1: Byte-Identical Determinism.

Verifies that re-running the same seed produces 100% byte-identical simulation output,
verifying zero shared RNG state, fixed update order, deterministic hashing,
and cross-process independence across different PYTHONHASHSEED environments.
"""

import hashlib
import os
import subprocess
import sys
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


def test_cross_process_determinism_under_different_hashseeds() -> None:
    """
    Validates cross-process determinism when PYTHONHASHSEED is set to different values.
    Ensures simulation does not rely on Python's salted hash() or unseeded state.
    Includes negative control proving that distinct seeds yield distinct hashes.
    """
    script = """
import hashlib
import sys
from minemesis.systems.simulation import Simulation

seed = int(sys.argv[1])
sim = Simulation(seed)
sim.run_years(20)
json_data = sim.event_log.to_json(indent=None)
print(hashlib.sha256(json_data.encode('utf-8')).hexdigest())
"""

    env_0 = os.environ.copy()
    env_0["PYTHONHASHSEED"] = "0"
    proc_0 = subprocess.run(
        [sys.executable, "-c", script, "42"],
        env=env_0,
        capture_output=True,
        text=True,
        check=True,
    )
    hash_0 = proc_0.stdout.strip()

    env_12345 = os.environ.copy()
    env_12345["PYTHONHASHSEED"] = "12345"
    proc_12345 = subprocess.run(
        [sys.executable, "-c", script, "42"],
        env=env_12345,
        capture_output=True,
        text=True,
        check=True,
    )
    hash_12345 = proc_12345.stdout.strip()

    # Assert exact byte-parity across separate processes with different hash seeds
    assert hash_0 == hash_12345, f"Cross-process hash mismatch: {hash_0} != {hash_12345}"

    # Negative control: running a different seed (seed 43) MUST produce a different digest
    proc_diff = subprocess.run(
        [sys.executable, "-c", script, "43"],
        env=env_0,
        capture_output=True,
        text=True,
        check=True,
    )
    hash_diff = proc_diff.stdout.strip()
    assert hash_0 != hash_diff, "Negative control failed: different seeds produced identical hash!"


def test_engine_toggle_off_zero_overhead_and_determinism() -> None:
    """
    Validates that when religion and lore engines are toggled OFF,
    zero religious or literary events are produced, and determinism holds.
    Includes negative control proving that when engines are ON, those events are produced.
    """
    import minemesis.religion.religion_config as r_cfg
    import minemesis.lore.lore_engine as l_eng

    orig_r = r_cfg.ENABLE_RELIGION_ENGINE
    orig_l = l_eng.ENABLE_LORE_ENGINE

    try:
        r_cfg.ENABLE_RELIGION_ENGINE = False
        l_eng.ENABLE_LORE_ENGINE = False

        sim_off1 = Simulation(42)
        sim_off1.run_years(20)
        json_off1 = sim_off1.event_log.to_json(indent=None)
        hash_off1 = hashlib.sha256(json_off1.encode("utf-8")).hexdigest()

        sim_off2 = Simulation(42)
        sim_off2.run_years(20)
        json_off2 = sim_off2.event_log.to_json(indent=None)
        hash_off2 = hashlib.sha256(json_off2.encode("utf-8")).hexdigest()

        assert json_off1 == json_off2
        assert hash_off1 == hash_off2

        event_types = {e.type.value for e in sim_off1.event_log.all_events()}
        rel_types = {
            "ReligiousSpread", "HeresySpawned", "ReligiousSchism", "HolyWarDeclared",
            "SaintCanonized", "DoctrinalDispute", "TheologicalCouncil", "HolySiteFounded",
            "PilgrimageCompleted", "LocalCustomCelebrated"
        }
        lore_types = {"BookWritten", "BookDamaged", "BookDestroyed"}

        assert not (event_types & rel_types), f"Found religious events with engine off: {event_types & rel_types}"
        assert not (event_types & lore_types), f"Found lore events with engine off: {event_types & lore_types}"

        # Negative control: turn engines ON and verify religious and lore events appear
        r_cfg.ENABLE_RELIGION_ENGINE = True
        l_eng.ENABLE_LORE_ENGINE = True

        sim_on = Simulation(42)
        sim_on.run_years(20)
        on_types = {e.type.value for e in sim_on.event_log.all_events()}
        assert (on_types & rel_types), "Negative control failed: no religious events with engine ON"
        assert (on_types & lore_types), "Negative control failed: no lore events with engine ON"

    finally:
        r_cfg.ENABLE_RELIGION_ENGINE = orig_r
        l_eng.ENABLE_LORE_ENGINE = orig_l

