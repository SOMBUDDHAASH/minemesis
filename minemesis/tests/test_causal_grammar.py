"""
Acceptance Tests for Causal Grammar and Schema Validation (Section 4.1).

Includes explicit negative controls demonstrating that invalid causal links are rejected.
"""

import pytest
from minemesis.core.causal_grammar import CausalGrammarError
from minemesis.core.event_log import EventLog
from minemesis.core.types import EventType, Intent, Scale


def test_grammar_accepts_valid_causal_chain() -> None:
    """
    Positive control: Valid progression from Death -> Feud -> Raid -> Peace.
    """
    log = EventLog()
    e_death = log.append(
        tick=1,
        location="set_oakhaven",
        event_type=EventType.DEATH,
        participants={"target": "char_1"},
        causes=[],
        intent=Intent.ACCIDENTAL,
        scale=Scale.INDIVIDUAL,
    )
    e_feud = log.append(
        tick=2,
        location="set_oakhaven",
        event_type=EventType.FEUD,
        participants={"instigator": "char_2", "target": "char_3"},
        causes=[e_death.id],
        intent=Intent.INTENTIONAL,
        scale=Scale.INDIVIDUAL,
    )
    e_raid = log.append(
        tick=3,
        location="set_riverbend",
        event_type=EventType.RAID,
        participants={"initiator": "set_oakhaven", "target": "set_riverbend"},
        causes=[e_feud.id],
        intent=Intent.MILITARY_ACTION,
        scale=Scale.AGGREGATE,
    )
    e_peace = log.append(
        tick=4,
        location="set_oakhaven",
        event_type=EventType.PEACE,
        participants={"initiator": "set_oakhaven", "target": "set_riverbend"},
        causes=[e_feud.id, e_raid.id],
        intent=Intent.INTENTIONAL,
        scale=Scale.AGGREGATE,
    )
    assert len(log) == 4


def test_negative_control_birth_causing_accidental_death() -> None:
    """
    Negative control: A Birth cited as the cause of an accidental Death must be rejected.
    """
    log = EventLog()
    e_birth = log.append(
        tick=1,
        location="set_oakhaven",
        event_type=EventType.BIRTH,
        participants={"child": "char_1"},
        causes=[],
        intent=Intent.INTENTIONAL,
        scale=Scale.INDIVIDUAL,
    )
    with pytest.raises(CausalGrammarError) as exc_info:
        log.append(
            tick=2,
            location="set_oakhaven",
            event_type=EventType.DEATH,
            participants={"target": "char_1"},
            causes=[e_birth.id],  # Illegal cause type
            intent=Intent.ACCIDENTAL,
            scale=Scale.INDIVIDUAL,
        )
    assert "cannot cite cause Event #0 of type 'Birth'" in str(exc_info.value)


def test_negative_control_feud_cannot_be_root() -> None:
    """
    Negative control: Feud requires citing a Death or Raid; cannot be a root event.
    """
    log = EventLog()
    with pytest.raises(CausalGrammarError) as exc_info:
        log.append(
            tick=1,
            location="set_oakhaven",
            event_type=EventType.FEUD,
            participants={"instigator": "char_1", "target": "char_2"},
            causes=[],  # Root not allowed
            intent=Intent.INTENTIONAL,
            scale=Scale.INDIVIDUAL,
        )
    assert "cannot be a root event" in str(exc_info.value)


def test_negative_control_peace_requires_feud() -> None:
    """
    Negative control: Peace must cite the Feud being ended.
    """
    log = EventLog()
    e_raid = log.append(
        tick=1,
        location="set_oakhaven",
        event_type=EventType.DEATH,
        participants={"target": "char_1"},
        causes=[],
        intent=Intent.ACCIDENTAL,
        scale=Scale.INDIVIDUAL,
    )
    with pytest.raises(CausalGrammarError) as exc_info:
        log.append(
            tick=2,
            location="set_oakhaven",
            event_type=EventType.PEACE,
            participants={"party1": "char_1", "party2": "char_2"},
            causes=[e_raid.id],  # Missing Feud
            intent=Intent.INTENTIONAL,
            scale=Scale.AGGREGATE,
        )
    assert "Peace requires citing the Feud being resolved" in str(exc_info.value)


def test_negative_control_revelation_requires_death() -> None:
    """
    Negative control: Revelation must cite the Death whose truth is revealed.
    """
    log = EventLog()
    e_feud = log.append(
        tick=1,
        location="set_oakhaven",
        event_type=EventType.DEATH,
        participants={"target": "char_1"},
        causes=[],
        intent=Intent.ACCIDENTAL,
        scale=Scale.INDIVIDUAL,
    )
    f_evt = log.append(
        tick=2,
        location="set_oakhaven",
        event_type=EventType.FEUD,
        participants={"instigator": "char_2", "target": "char_3"},
        causes=[e_feud.id],
        intent=Intent.INTENTIONAL,
        scale=Scale.INDIVIDUAL,
    )
    with pytest.raises(CausalGrammarError) as exc_info:
        log.append(
            tick=3,
            location="set_oakhaven",
            event_type=EventType.REVELATION,
            participants={"witness": "char_4", "recipient": "char_2"},
            causes=[f_evt.id],  # Missing Death
            intent=Intent.INTENTIONAL,
            scale=Scale.INDIVIDUAL,
        )
    assert "Revelation requires citing the Death whose truth is revealed" in str(exc_info.value)
