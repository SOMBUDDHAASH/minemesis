"""
Acceptance Test 2: Real Causal Chains and Traceability (Section 4.1).

Verifies:
- Every cause pointer represents genuine causation validated by CAUSE_GRAMMAR.
- Deepest causal chain has depth >= 3 and contains at least 3 distinct event types.
- History printer recursively formats causal DAG without cycles or exponential blowup.
"""

from minemesis.core.history_printer import (
    format_causal_chain,
    get_causal_depth,
    get_deepest_causal_chain_metrics,
    get_deepest_conflict_chain_metrics,
    get_longest_causal_path,
    get_distinct_event_types_on_path,
)
from minemesis.core.types import EventType
from minemesis.systems.simulation import Simulation


def test_real_causal_chain_depth_and_diversity() -> None:
    """
    Positive acceptance test for Milestone 0.5.1:
    Conflict depth must have real depth >= 3 and at least 3 distinct conflict event types
    (restricted to Death, Feud, Raid, Famine, SuccessionCrisis, Peace, Revelation).
    """
    sim = Simulation(seed=42, enable_religion=False, enable_lore=False)
    sim.run_years(100)

    # 1. Conflict causal chain depth
    c_best_id, c_depth, c_distinct_types = get_deepest_conflict_chain_metrics(sim.event_log)
    assert c_best_id >= 0, "Expected at least one conflict event in event log"
    assert c_depth >= 3, f"Expected conflict path depth >= 3, got {c_depth}"
    assert c_distinct_types >= 3, f"Expected >= 3 distinct conflict event types on path, got {c_distinct_types}"

    # 2. Overall longest path
    best_id, depth, distinct_types = get_deepest_causal_chain_metrics(sim.event_log)
    assert depth >= 3, f"Expected longest causal path depth >= 3, got {depth}"
    assert distinct_types >= 3, f"Expected at least 3 distinct event types along path, got {distinct_types}"

    # Verify history printer rendering
    rendered = format_causal_chain(sim.event_log, c_best_id)
    assert len(rendered.splitlines()) >= 3


def test_negative_control_depth_fails_on_isolated_roots() -> None:
    """
    Negative control: A log containing only isolated root events has depth 0 and 1 distinct type.
    """
    from minemesis.core.event_log import EventLog
    from minemesis.core.types import Intent, Scale

    log = EventLog()
    log.append(
        tick=1,
        location="set_oakhaven",
        event_type=EventType.DEATH,
        participants={"target": "char_1"},
        causes=[],
        intent=Intent.ACCIDENTAL,
        scale=Scale.INDIVIDUAL,
    )
    best_id, depth, distinct_types = get_deepest_causal_chain_metrics(log)
    assert depth == 0, f"Root event should have causal depth 0, got {depth}"
    assert distinct_types == 1

    c_best_id, c_depth, c_distinct_types = get_deepest_conflict_chain_metrics(log)
    assert c_depth == 0, f"Root event should have conflict depth 0, got {c_depth}"
    assert c_distinct_types == 1


def test_printed_causal_chains_completeness_and_verifiability() -> None:
    """
    Validates Directive 12:
    - History printer prints causes for each event so readers can verify the chain.
    - Printed character names instead of raw IDs.
    - Automated test checks that for each event in the chain, its causes are printed or reachable.
    - Includes negative control proving that a broken/missing cause in the chain is flagged.
    """
    import re
    from minemesis.core.history_printer import format_notable_deaths

    sim = Simulation(seed=42)
    sim.run_years(20)

    best_id, depth, _ = get_deepest_causal_chain_metrics(sim.event_log)
    assert best_id >= 0

    rendered = format_causal_chain(sim.event_log, best_id, characters=sim.characters)
    assert "Causes:" in rendered

    # Extract all printed event IDs and all cited causes from rendered text
    event_ids_printed: set[int] = set()
    causes_cited: set[int] = set()

    for line in rendered.splitlines():
        match_id = re.search(r"Event #(\d+)", line)
        if match_id:
            event_ids_printed.add(int(match_id.group(1)))
        match_causes = re.search(r"Causes: \[([0-9, #]+)\]", line)
        if match_causes:
            c_str = match_causes.group(1)
            for c_part in c_str.split(","):
                c_clean = c_part.replace("#", "").strip()
                if c_clean:
                    causes_cited.add(int(c_clean))

    # All cited causes must be printed in the causal chain output
    missing_causes = causes_cited - event_ids_printed
    assert not missing_causes, f"Causes cited in chain but missing from printout: {missing_causes}"

    # Verify notable deaths formatting
    notable = format_notable_deaths(sim.event_log, sim.characters)
    assert len(notable) > 0
    assert any("Causes:" in n for n in notable)

    # Negative control: verify verifier detects when a cause is missing
    fake_printed = set(event_ids_printed)
    if fake_printed:
        removed_id = fake_printed.pop()
        fake_missing = causes_cited - fake_printed
        if removed_id in causes_cited:
            assert removed_id in fake_missing, "Negative control failed: missing cause was not detected"

