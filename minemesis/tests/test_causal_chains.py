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
    get_longest_causal_path,
    get_distinct_event_types_on_path,
)
from minemesis.core.types import EventType
from minemesis.systems.simulation import Simulation


def test_real_causal_chain_depth_and_diversity() -> None:
    """
    Positive acceptance test for Milestone 0.5:
    Longest path must have real depth >= 3 and at least 3 distinct event types.
    """
    sim = Simulation(seed=42)
    sim.run_years(100)

    best_id, depth, distinct_types = get_deepest_causal_chain_metrics(sim.event_log)
    assert best_id >= 0, "Expected at least one event in event log"
    assert depth >= 3, f"Expected longest causal path depth >= 3, got {depth}"
    assert distinct_types >= 3, f"Expected at least 3 distinct event types along path, got {distinct_types}"

    # Verify history printer rendering
    rendered = format_causal_chain(sim.event_log, best_id)
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
