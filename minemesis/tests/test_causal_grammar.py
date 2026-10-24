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


def test_negative_control_death_cannot_cite_death_without_feud() -> None:
    """
    Negative control (Grammar diff): Death citing Death is rejected unless it also cites Feud (revenge).
    """
    log = EventLog()
    e_d1 = log.append(
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
            event_type=EventType.DEATH,
            participants={"actor": "char_2", "target": "char_3"},
            causes=[e_d1.id],  # Death citing Death without Feud
            intent=Intent.INTENTIONAL,
            scale=Scale.INDIVIDUAL,
        )
    assert "Death can only cite another Death if it also cites a Feud" in str(exc_info.value)


def test_negative_control_settlement_collapse_requires_crisis_cause() -> None:
    """
    Negative control: SettlementCollapse cannot be root and cannot cite Birth.
    """
    log = EventLog()
    with pytest.raises(CausalGrammarError) as exc_info:
        log.append(
            tick=1,
            location="set_oakhaven",
            event_type=EventType.SETTLEMENT_COLLAPSE,
            participants={"settlement": "set_oakhaven"},
            causes=[],  # Root not allowed
            intent=Intent.ACCIDENTAL,
            scale=Scale.AGGREGATE,
        )
    assert "cannot be a root event" in str(exc_info.value)

    e_birth = log.append(
        tick=2,
        location="set_oakhaven",
        event_type=EventType.BIRTH,
        participants={"child": "char_1"},
        causes=[],
        intent=Intent.INTENTIONAL,
        scale=Scale.INDIVIDUAL,
    )
    with pytest.raises(CausalGrammarError) as exc_info2:
        log.append(
            tick=3,
            location="set_oakhaven",
            event_type=EventType.SETTLEMENT_COLLAPSE,
            participants={"settlement": "set_oakhaven"},
            causes=[e_birth.id],
            intent=Intent.ACCIDENTAL,
            scale=Scale.AGGREGATE,
        )
    assert "cannot cite cause Event" in str(exc_info2.value)


def test_negative_control_migration_requires_collapse_or_scarcity() -> None:
    """
    Negative control: Migration cannot be root and must cite SettlementCollapse, Famine, or Raid.
    """
    log = EventLog()
    with pytest.raises(CausalGrammarError) as exc_info:
        log.append(
            tick=1,
            location="set_oakhaven",
            event_type=EventType.MIGRATION,
            participants={"source": "set_oakhaven", "destination": "set_riverbend"},
            causes=[],  # Root not allowed
            intent=Intent.INTENTIONAL,
            scale=Scale.AGGREGATE,
        )
    assert "cannot be a root event" in str(exc_info.value)


def test_positive_control_revenge_and_collapse_migration() -> None:
    """
    Positive control: Valid revenge killing (Death citing [Death, Feud]),
    valid SettlementCollapse citing Famine, and valid Migration citing SettlementCollapse.
    """
    log = EventLog()
    d1 = log.append(
        tick=1,
        location="set_oakhaven",
        event_type=EventType.DEATH,
        participants={"target": "char_1"},
        causes=[],
        intent=Intent.ACCIDENTAL,
        scale=Scale.INDIVIDUAL,
    )
    feud = log.append(
        tick=2,
        location="set_oakhaven",
        event_type=EventType.FEUD,
        participants={"instigator": "char_2", "target": "char_3"},
        causes=[d1.id],
        intent=Intent.INTENTIONAL,
        scale=Scale.INDIVIDUAL,
    )
    # Revenge killing: Death citing both original Death and Feud
    rev_death = log.append(
        tick=3,
        location="set_riverbend",
        event_type=EventType.DEATH,
        participants={"actor": "char_2", "target": "char_3"},
        causes=[d1.id, feud.id],
        intent=Intent.INTENTIONAL,
        scale=Scale.INDIVIDUAL,
        payload={"cause_of_death": "Revenge"},
    )
    assert rev_death.id == 2

    # Famine -> SettlementCollapse -> Migration
    famine = log.append(
        tick=4,
        location="set_oakhaven",
        event_type=EventType.FAMINE,
        participants={"settlement": "set_oakhaven"},
        causes=[],
        intent=Intent.ACCIDENTAL,
        scale=Scale.AGGREGATE,
    )
    collapse = log.append(
        tick=5,
        location="set_oakhaven",
        event_type=EventType.SETTLEMENT_COLLAPSE,
        participants={"settlement": "set_oakhaven"},
        causes=[famine.id],
        intent=Intent.ACCIDENTAL,
        scale=Scale.AGGREGATE,
    )
    migration = log.append(
        tick=6,
        location="set_oakhaven",
        event_type=EventType.MIGRATION,
        participants={"source": "set_oakhaven", "destination": "set_riverbend"},
        causes=[collapse.id],
        intent=Intent.INTENTIONAL,
        scale=Scale.AGGREGATE,
        payload={"migrants": ["char_2"]},
    )
    assert migration.id == 5
