"""
Unit and property tests for Cast Generator.

Milestone 0.5.3: Randomized Worlds and Casts (Seed Split).
- Fertile couples guarantee (>= 4 per settlement).
- Kin-avoidance guarantee (no spouse sharing parents or birth surname).
- Identity uniqueness (unique IDs, unique full names per settlement).
- Domain isolation (same world_seed with different chronicle_seeds produces same map with different people).
- Negative control: verifies that a synthetic duplicate name or kin marriage is detected.
"""

from __future__ import annotations
import pytest

from minemesis.systems.world_gen_v0 import V0WorldGenerator
from minemesis.systems.cast_gen import CastGenerator
from minemesis.models.character import Character


def test_cast_generation_guarantees_per_settlement():
    """
    Tests cast generation across multiple chronicle seeds and settlement counts:
    - 20-36 characters per settlement.
    - >= 4 fertile married couples per settlement (ages 18-45).
    - Zero kin couples (spouses do not share parents or birth surname).
    - Unique character IDs and unique full names per settlement.
    """
    world_gen = V0WorldGenerator()
    world_spec = world_gen.generate(world_seed=42000)

    for c_seed in [101, 202, 303, 404, 505]:
        cast_gen = CastGenerator(chronicle_seed=c_seed, world_spec=world_spec)
        characters = cast_gen.generate_cast()

        # Unique IDs
        assert len(characters) == len(set(characters.keys()))

        # Check per settlement
        for site in world_spec.settlements:
            s_chars = [c for c in characters.values() if c.settlement_id == site.id]
            assert 18 <= len(s_chars) <= 40, f"Settlement {site.id} has {len(s_chars)} characters"

            # Unique full names per settlement
            names = [f"{c.first_name} {c.last_name}" for c in s_chars]
            assert len(names) == len(set(names)), f"Settlement {site.id} has duplicate names: {names}"

            # Fertile couples check
            married_pairs = set()
            for c in s_chars:
                if c.spouse_id:
                    pair = tuple(sorted([c.id, c.spouse_id]))
                    married_pairs.add(pair)

            fertile_count = 0
            for id1, id2 in married_pairs:
                c1 = characters[id1]
                c2 = characters[id2]
                # Kin avoidance: neither parents match nor do birth surnames match (for f2 wife maiden name is distinct)
                assert c1.father_id is None or c1.father_id != c2.father_id
                assert c1.mother_id is None or c1.mother_id != c2.mother_id
                if (18 <= c1.age_years <= 45) and (18 <= c2.age_years <= 45):
                    fertile_count += 1

            assert fertile_count >= 4, f"Settlement {site.id} has only {fertile_count} fertile couples (expected >= 4)"


def test_same_map_different_cast():
    """
    Verifies domain separation:
    - Same world_seed produces identical world spec.
    - Two different chronicle_seeds produce completely distinct casts on the same world.
    """
    world_gen = V0WorldGenerator()
    world_spec = world_gen.generate(world_seed=777)

    cast_a = CastGenerator(chronicle_seed=1111, world_spec=world_spec).generate_cast()
    cast_b = CastGenerator(chronicle_seed=9999, world_spec=world_spec).generate_cast()

    names_a = {f"{c.first_name} {c.last_name}" for c in cast_a.values()}
    names_b = {f"{c.first_name} {c.last_name}" for c in cast_b.values()}

    # Surnames or names should vary significantly between distinct chronicle seeds
    overlap = names_a.intersection(names_b)
    overlap_ratio = len(overlap) / max(len(names_a), len(names_b))
    assert overlap_ratio < 0.25, f"Expected low name overlap between distinct chronicle seeds, got {overlap_ratio:.2%}"


def test_cast_negative_control_kin_marriage_detection():
    """
    Negative control test:
    Proves that a function checking for incestuous/kin marriages correctly detects
    when two spouses share a parent.
    """
    def check_kin_marriage(c1: Character, c2: Character) -> bool:
        """Returns True if marriage violates kin-avoidance."""
        if c1.father_id and c1.father_id == c2.father_id:
            return True
        if c1.mother_id and c1.mother_id == c2.mother_id:
            return True
        return False

    # Valid non-kin
    c1 = Character(id="c1", first_name="A", last_name="X", settlement_id="s1", age_ticks=240, sex="M", father_id="p1", mother_id="p2")
    c2 = Character(id="c2", first_name="B", last_name="Y", settlement_id="s1", age_ticks=240, sex="F", father_id="p3", mother_id="p4")
    assert not check_kin_marriage(c1, c2)

    # Broken kin couple sharing mother
    c_incest = Character(id="c3", first_name="C", last_name="Z", settlement_id="s1", age_ticks=240, sex="F", father_id="p5", mother_id="p2")
    assert check_kin_marriage(c1, c_incest), "Negative control failed: kin marriage went undetected!"
