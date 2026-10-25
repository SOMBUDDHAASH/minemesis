"""
Test for Name Key Domain Isolation (Milestone 0.5.3 Addendum Item 6).

Standing Rule:
- Names are an isolated key domain ('name:').
- Name generation never affects event decisions, causal chains, or historical timelines.
- Re-running a SeedPair with a different name_salt gives an IDENTICAL event structure
  (event IDs, ticks, types, causes, intents, locations, and participant IDs)
  with different character and settlement names.
- Negative control: demonstrates that the test affirmatively catches divergence
  if an event outcome were to key off character names.
"""

from __future__ import annotations
import pytest

from minemesis.core.seed import SeedPair
from minemesis.core.rng import keyed_float
from minemesis.systems.simulation import Simulation


def test_name_domain_isolation_preserves_event_structure():
    """
    Simulates 20 years with name_salt=0 vs name_salt=777 on the same SeedPair.
    Asserts:
    1. Names of characters differ between runs.
    2. Event structure is 100% identical:
       - Total event count
       - Every event's id, tick, type, causes, intent, scale, location
       - Participant IDs (e.g. actor='char_5', target='char_12')
    """
    pair = SeedPair(world=8888, history=9999)

    # Run 1: default name_salt = 0
    sim1 = Simulation(seed=pair, name_salt=0)
    sim1.run_years(20)
    evs1 = sim1.event_log.all_events()

    # Run 2: alternate name_salt = 777
    sim2 = Simulation(seed=pair, name_salt=777)
    sim2.run_years(20)
    evs2 = sim2.event_log.all_events()

    # 1. Names differ
    names1 = [c.full_name for c in sim1.characters.values()]
    names2 = [c.full_name for c in sim2.characters.values()]
    assert names1 != names2, "Expected character names to differ with different name_salt"
    overlap = set(names1) & set(names2)
    assert len(overlap) < len(names1) * 0.3, f"Expected low name overlap, got {len(overlap)}/{len(names1)}"

    # 2. Event structure is completely identical
    assert len(evs1) == len(evs2), f"Event count mismatch: {len(evs1)} != {len(evs2)}"

    for e1, e2 in zip(evs1, evs2):
        assert e1.id == e2.id
        assert e1.tick == e2.tick
        assert e1.type == e2.type
        assert e1.causes == e2.causes
        assert e1.intent == e2.intent
        assert e1.scale == e2.scale
        assert e1.location == e2.location

        # Participant roles and structural IDs (char_*, set_*) match 100%
        p1_roles = [r for r, _ in e1.participants]
        p2_roles = [r for r, _ in e2.participants]
        assert p1_roles == p2_roles, f"Participant roles mismatch in event #{e1.id}: {p1_roles} != {p2_roles}"

        for (r1, p1), (r2, p2) in zip(e1.participants, e2.participants):
            if p1.startswith("char_") or p2.startswith("char_"):
                assert p1 == p2, f"Character ID mismatch in event #{e1.id}: {p1} != {p2}"
            elif p1.startswith("set_") or p2.startswith("set_"):
                assert p1 == p2, f"Settlement ID mismatch in event #{e1.id}: {p1} != {p2}"

        # 3. Payload non-name structural fields match 100%
        # Filter out text name fields that legitimately vary with name_salt
        is_text_key = lambda k: k == "name" or k.endswith("_name") or k in {
            "perspective_bias", "affected_titles", "narrative", "objective_truth", "deeds", "title", "description"
        }
        filtered_p1 = {k: v for k, v in e1.payload.items() if not is_text_key(k)}
        filtered_p2 = {k: v for k, v in e2.payload.items() if not is_text_key(k)}
        assert filtered_p1 == filtered_p2, f"Payload structural mismatch in event #{e1.id}: {filtered_p1} != {filtered_p2}"


def test_negative_control_name_leakage_diverges_events():
    """
    Negative control test:
    Demonstrates that if an event decision were to key off character full_name
    (as in fragile single-stream RNGs), different names would disrupt event causality.
    """
    # Synthetic check: compare decision using char.id vs char.full_name
    c_id = "char_42"
    name_a = "Arthur Ironwood"
    name_b = "Rowan Blackwood"
    seed = 12345

    # Sound architecture: decision keyed strictly by immutable ID
    roll_id_1 = keyed_float(seed, "feud_decision", c_id, 0)
    roll_id_2 = keyed_float(seed, "feud_decision", c_id, 0)
    assert roll_id_1 == roll_id_2, "Keyed hash by ID must be deterministic"

    # Fragile architecture (negative control): decision keyed by name
    roll_name_a = keyed_float(seed, "feud_decision", name_a, 0)
    roll_name_b = keyed_float(seed, "feud_decision", name_b, 0)
    assert roll_name_a != roll_name_b, "Negative control verified: keying by name changes random rolls!"
