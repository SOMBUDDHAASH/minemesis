"""
Tests for SeedPair model, Crockford Base32 encoding, Subsystem Derivation,
Minecraft-style world seeds, and Generator Version tracking.
"""

from __future__ import annotations
import pytest

from minemesis.core.seed import (
    SeedPair,
    new_game,
    parse_world_seed,
    parse_history_seed,
    CURRENT_GENERATOR_VERSION,
)


def test_seed_pair_encode_decode_roundtrip():
    # Test random seeds
    for _ in range(20):
        pair = new_game()
        code = pair.encode()
        restored = SeedPair.decode(code)
        assert restored == pair, f"Failed roundtrip for {pair} (code: {code})"
        assert restored.generator_version == CURRENT_GENERATOR_VERSION


def test_seed_pair_boundary_values():
    zero_pair = SeedPair(world=0, history=0)
    max_pair = SeedPair(world=(1 << 64) - 1, history=(1 << 64) - 1)

    assert SeedPair.decode(zero_pair.encode()) == zero_pair
    assert SeedPair.decode(max_pair.encode()) == max_pair


def test_seed_pair_typo_tolerance():
    pair = SeedPair(world=1234567890, history=9876543210)
    code = pair.encode()

    # Lowercase tolerance
    assert SeedPair.decode(code.lower()) == pair

    # Spaces and hyphen variations
    no_hyphens = code.replace("-", "").replace(":", "")
    assert SeedPair.decode(no_hyphens) == pair


def test_negative_control_corrupted_check_symbol():
    """Negative control: proves corrupted check symbol is rejected."""
    pair = SeedPair(world=42, history=100)
    code = pair.encode()
    # Flip the check symbol
    bad_check = "X" if code[-1] != "X" else "Y"
    corrupted_code = code[:-1] + bad_check

    with pytest.raises(ValueError, match="check symbol mismatch"):
        SeedPair.decode(corrupted_code)


def test_new_game_distinct_entropy():
    pair1 = new_game()
    pair2 = new_game()
    assert pair1 != pair2, "Two new_game() calls produced identical seeds"
    assert pair1.world != pair2.world
    assert pair1.history != pair2.history
    assert pair1.chronicle == pair1.history


def test_subsystem_derivation_isolation():
    pair = SeedPair(world=1000, history=2000)

    # World derivations strictly depend on world seed
    w1 = pair.derive_world_subsystem("sites", 0)
    w2 = pair.derive_world_subsystem("sites", 0)
    assert w1 == w2

    # Different history seed on same world must yield identical world derivations
    pair_alt_history = SeedPair(world=1000, history=9999)
    assert pair_alt_history.derive_world_subsystem("sites", 0) == w1

    # Different world seed must yield different world derivation
    pair_alt_world = SeedPair(world=1001, history=2000)
    assert pair_alt_world.derive_world_subsystem("sites", 0) != w1


def test_minecraft_style_world_seed_parsing():
    # 1. Integer strings
    assert parse_world_seed("12345") == 12345
    assert parse_world_seed(42) == 42
    # Negative integer wraps to uint64
    assert parse_world_seed("-1") == (1 << 64) - 1

    # 2. Text strings produce deterministic 64-bit uint
    s1 = parse_world_seed("EmeraldValley")
    s2 = parse_world_seed("EmeraldValley")
    s3 = parse_world_seed("VolcanoRidge")
    assert s1 == s2
    assert s1 != s3
    assert 0 <= s1 < (1 << 64)

    # 3. Blank or None produces random uint
    r1 = parse_world_seed("")
    r2 = parse_world_seed(None)
    assert r1 != r2
    assert 0 <= r1 < (1 << 64)


def test_history_seed_parsing():
    assert parse_history_seed("999") == 999
    assert parse_history_seed(777) == 777
    h1 = parse_history_seed("CustomDrama")
    h2 = parse_history_seed("CustomDrama")
    assert h1 == h2
    assert 0 <= h1 < (1 << 64)
    # Blank gives random
    b1 = parse_history_seed("")
    b2 = parse_history_seed(None)
    assert b1 != b2


def test_generator_version_tracking_and_detection():
    pair = SeedPair(world=123, history=456, generator_version="v0")
    code = pair.encode()
    assert ":V0:" in code

    decoded = SeedPair.decode(code)
    assert decoded.generator_version == "v0"
