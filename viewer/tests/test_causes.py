"""
Tests for causal DAG links and antecedent tracing in the Story Viewer.
"""

from __future__ import annotations
import pytest

from minemesis.core.types import EventType, Intent, Scale
from viewer.model import EventProxy, EventLogProxy
from viewer.formatter import format_event_sentence, format_because_clause


def test_causal_dag_multi_step_trace():
    chars = {
        "char_1": {"full_name": "Alden"},
        "char_2": {"full_name": "Brynn"},
        "char_3": {"full_name": "Cael"},
    }
    settlements = {
        "set_a": {"name": "Alpha"},
        "set_b": {"name": "Beta"},
    }

    # Step 0: Root Death
    e0 = EventProxy(
        id=100, tick=12, location="set_a", type_val="Death",
        participants=(("deceased", "char_1"),), causes=(),
        intent_val="Unintended", scale_val="Individual", payload={"cause": "accident"},
    )
    # Step 1: Feud caused by Death
    e1 = EventProxy(
        id=101, tick=24, location="set_a", type_val="Feud",
        participants=(("instigator", "char_2"), ("target", "char_3")), causes=(100,),
        intent_val="Intentional", scale_val="Communal", payload={"target_settlement": "set_b"},
    )
    # Step 2: Raid caused by Feud
    e2 = EventProxy(
        id=102, tick=36, location="set_b", type_val="Raid",
        participants=(("attacker", "char_2"),), causes=(101,),
        intent_val="Intentional", scale_val="Regional", payload={"source_settlement": "set_a"},
    )
    # Step 3: Peace caused by Raid
    e3 = EventProxy(
        id=103, tick=48, location="set_a", type_val="Peace",
        participants=(), causes=(102,),
        intent_val="Intentional", scale_val="Regional", payload={"settlement_a": "set_a", "settlement_b": "set_b"},
    )

    log_proxy = EventLogProxy(_events=[e0, e1, e2, e3])

    # Trace backward from peace
    ancestors = []
    curr = e3
    while curr.causes:
        parent_id = curr.causes[0]
        curr = log_proxy.get(parent_id)
        assert curr is not None
        ancestors.append(curr.id)

    assert ancestors == [102, 101, 100]
    assert e0.causes == ()  # e0 is the root cause


def test_negative_control_orphan_cause_handling():
    """Negative control: handling an event whose cause points to a non-existent ID."""
    orphan_evt = EventProxy(
        id=200, tick=10, location="set_a", type_val="Feud",
        participants=(), causes=(99999,), intent_val="Intentional", scale_val="Communal", payload={},
    )
    log_proxy = EventLogProxy(_events=[orphan_evt])

    # format_because_clause must not crash on missing cause ID
    clause = format_because_clause(orphan_evt, log_proxy, {}, {})
    assert clause == "because: event #99999"
