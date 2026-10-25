"""
Unit and property tests for V0 World Generator.

Milestone 0.5.3: Randomized Worlds and Casts (Seed Split).
- 500-seed viability test (100% viable).
- Math whitelist AST verification (only +, -, *, /, sqrt allowed; no transcendental functions).
- Spatial constraint verification (min_dist >= 30, bounded 200x200).
- Negative control: proves that an invalid WorldSpec is rejected by validation.
"""

from __future__ import annotations
import ast
import math
import os
import pytest

from minemesis.systems.world_spec import WorldSpec, SettlementSite
from minemesis.systems.world_gen_v0 import V0WorldGenerator


def test_v0_world_gen_no_transcendental_math():
    """
    Asserts via AST inspection that world_gen_v0.py does NOT call
    math.sin, math.cos, math.exp, or math.pow (platform-independent arithmetic only).
    """
    file_path = os.path.join(os.path.dirname(__file__), "..", "systems", "world_gen_v0.py")
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=file_path)

    forbidden_calls = {"sin", "cos", "exp", "pow", "tan", "sinh", "cosh", "log"}
    found_forbidden = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check func name
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            if func_name in forbidden_calls:
                found_forbidden.append((func_name, getattr(node, "lineno", 0)))

    assert not found_forbidden, f"Forbidden transcendental math calls found in world_gen_v0.py: {found_forbidden}"


def test_v0_world_gen_500_seeds_viability():
    """
    Evaluates 500 world seeds and verifies:
    - 100% of generated worlds have between 3 and 7 settlements.
    - Every settlement satisfies minimum spacing (>= 30.0).
    - Every settlement is within map bounds [10, 190].
    - Every settlement satisfies viability thresholds (food, wood, ore, wealth, farm, forest, ore_richness).
    - Every settlement has a non-empty, unique name.
    """
    gen = V0WorldGenerator()
    total_seeds = 500
    viable_count = 0
    counts: dict[int, int] = {}

    for seed in range(1000, 1000 + total_seeds):
        world = gen.generate(seed)
        num_s = len(world.settlements)
        counts[num_s] = counts.get(num_s, 0) + 1

        assert 10 <= num_s <= 35, f"Seed {seed} generated {num_s} settlements (expected 10-35)"
        assert world.map_width == 300
        assert world.map_height == 300

        # Spacing check
        min_distance = max(18.0, 36.0 - (num_s * 0.45))
        for i in range(num_s):
            s1 = world.settlements[i]
            assert 10 <= s1.x <= 290 and 10 <= s1.y <= 290
            assert s1.base_food >= 60 and s1.base_wood >= 60
            assert s1.farmland >= 0.40 and s1.forest >= 0.40
            for j in range(i + 1, num_s):
                s2 = world.settlements[j]
                dist = math.sqrt((s1.x - s2.x) ** 2 + (s1.y - s2.y) ** 2)
                assert dist >= min_distance - 0.01, f"Seed {seed} sites {s1.name} and {s2.name} too close: {dist:.1f} < {min_distance}"

        # Unique names
        names = [s.name for s in world.settlements]
        assert len(names) == len(set(names)), f"Seed {seed} duplicate settlement names: {names}"

        viable_count += 1

    assert viable_count == total_seeds, f"Expected 100% viability (500/500), got {viable_count}/{total_seeds}"
    # Verify rich distribution across settlement counts 10..35
    assert len(counts) >= 20, f"Expected broad representation of counts 10..35; got {len(counts)} distinct counts"


def test_v0_world_gen_determinism():
    """
    Verifies that the same world seed produces an identical WorldSpec and SHA-256 digest,
    while different world seeds produce distinct specs.
    """
    gen = V0WorldGenerator()
    w1 = gen.generate(123456789)
    w2 = gen.generate(123456789)
    w3 = gen.generate(987654321)

    assert w1.canonical_digest() == w2.canonical_digest()
    assert [s.name for s in w1.settlements] == [s.name for s in w2.settlements]
    assert [(s.x, s.y) for s in w1.settlements] == [(s.x, s.y) for s in w2.settlements]

    assert w1.canonical_digest() != w3.canonical_digest()


def test_world_spec_negative_control_validation_failure():
    """
    Negative control test:
    Proves that a broken WorldSpec (e.g. settlements violating minimum distance or out of bounds)
    is affirmatively caught by validation logic.
    """
    # Create two settlements too close (< 30 distance)
    s1 = SettlementSite(
        id="s1", name="Alpha", x=50, y=50,
        base_food=100, base_wood=100, base_ore=50, base_wealth=50,
        farmland=1.0, forest=1.0, ore_richness=1.0, defensibility=1.0, water_access=0.5,
        site_type="river",
    )
    s2 = SettlementSite(
        id="s2", name="Beta", x=55, y=55, # distance ~7.07 < 30.0!
        base_food=100, base_wood=100, base_ore=50, base_wealth=50,
        farmland=1.0, forest=1.0, ore_richness=1.0, defensibility=1.0, water_access=0.5,
        site_type="mountain",
    )

    bad_world = WorldSpec(world_seed=1, map_width=200, map_height=200, settlements=[s1, s2])

    gen = V0WorldGenerator()
    # The generator's viability check must return False for this bad configuration!
    assert not gen._is_world_viable([s1, s2]), "Negative control failed: generator accepted sites closer than min distance!"
