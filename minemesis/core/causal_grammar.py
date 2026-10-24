"""
Causal Grammar Specification and Validation.

Adheres strictly to Minemesis Agent Brief Milestone 0.5 (Section 4.1):
- Defines explicit rules for allowed and required causes per EventType.
- Rejects invalid causal links (e.g. routine trades or births causing accidental deaths).
- Ensures every cause pointer represents genuine causation.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence
from minemesis.core.types import EventType


class CausalGrammarError(ValueError):
    """Raised when an Event violates the Causal Grammar."""
    pass


@dataclass(frozen=True)
class GrammarRule:
    root_allowed: bool
    allowed_cause_types: frozenset[EventType]
    validator: Callable[[Sequence[EventType]], tuple[bool, str]] | None = None


def _validate_death(cause_types: Sequence[EventType]) -> tuple[bool, str]:
    if EventType.DEATH in cause_types:
        if EventType.FEUD not in cause_types:
            return False, "Death can only cite another Death if it also cites a Feud (revenge killing)."
    return True, ""


def _validate_settlement_collapse(cause_types: Sequence[EventType]) -> tuple[bool, str]:
    if not any(t in (EventType.RAID, EventType.FAMINE, EventType.FEUD, EventType.DEATH, EventType.SUCCESSION_CRISIS) for t in cause_types):
        return False, "SettlementCollapse must cite at least one of Raid, Famine, Feud, Death, or SuccessionCrisis."
    return True, ""


def _validate_migration(cause_types: Sequence[EventType]) -> tuple[bool, str]:
    if not any(t in (EventType.SETTLEMENT_COLLAPSE, EventType.FAMINE, EventType.RAID) for t in cause_types):
        return False, "Migration must cite at least one of SettlementCollapse, Famine, or Raid."
    return True, ""


def _validate_feud(cause_types: Sequence[EventType]) -> tuple[bool, str]:
    if not any(t in (EventType.DEATH, EventType.RAID) for t in cause_types):
        return False, "Feud must cite at least one Death or Raid as the inciting offence."
    return True, ""


def _validate_raid(cause_types: Sequence[EventType]) -> tuple[bool, str]:
    if not any(t in (EventType.FEUD, EventType.FAMINE, EventType.SUCCESSION_CRISIS, EventType.RAID) for t in cause_types):
        return False, "Raid must cite at least one of Feud, Famine, SuccessionCrisis, or retaliatory Raid."
    return True, ""


def _validate_peace(cause_types: Sequence[EventType]) -> tuple[bool, str]:
    if EventType.FEUD not in cause_types:
        return False, "Peace requires citing the Feud being resolved."
    has_revelation = EventType.REVELATION in cause_types
    has_exhaustion = any(t in (EventType.RAID, EventType.DEATH) for t in cause_types)
    if not (has_revelation or has_exhaustion):
        return False, "Peace must cite either Revelation (truth revealed) or exhaustion evidence (Raid/Death)."
    return True, ""


def _validate_revelation(cause_types: Sequence[EventType]) -> tuple[bool, str]:
    if EventType.DEATH not in cause_types:
        return False, "Revelation requires citing the Death whose truth is revealed."
    return True, ""


def _validate_chief_changed(cause_types: Sequence[EventType]) -> tuple[bool, str]:
    if not any(t in (EventType.DEATH, EventType.SUCCESSION_CRISIS) for t in cause_types):
        return False, "ChiefChanged must cite Death of prior chief or SuccessionCrisis."
    return True, ""


def _validate_succession_crisis(cause_types: Sequence[EventType]) -> tuple[bool, str]:
    if EventType.DEATH not in cause_types:
        return False, "SuccessionCrisis must cite the Death of the chief."
    return True, ""


CAUSE_GRAMMAR: Mapping[EventType, GrammarRule] = {
    EventType.BIRTH: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({EventType.MARRIAGE}),
    ),
    EventType.MARRIAGE: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({EventType.PEACE, EventType.TRADE_ROUTE_FOUNDED}),
    ),
    EventType.DEATH: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({
            EventType.RAID,
            EventType.FAMINE,
            EventType.FEUD,
            EventType.DEATH,
            EventType.SUCCESSION_CRISIS,
        }),
        validator=_validate_death,
    ),
    EventType.FEUD: GrammarRule(
        root_allowed=False,
        allowed_cause_types=frozenset({EventType.DEATH, EventType.RAID, EventType.FEUD}),
        validator=_validate_feud,
    ),
    EventType.RAID: GrammarRule(
        root_allowed=False,
        allowed_cause_types=frozenset({
            EventType.FEUD,
            EventType.FAMINE,
            EventType.SUCCESSION_CRISIS,
            EventType.RAID,
        }),
        validator=_validate_raid,
    ),
    EventType.PEACE: GrammarRule(
        root_allowed=False,
        allowed_cause_types=frozenset({
            EventType.FEUD,
            EventType.REVELATION,
            EventType.RAID,
            EventType.DEATH,
        }),
        validator=_validate_peace,
    ),
    EventType.REVELATION: GrammarRule(
        root_allowed=False,
        allowed_cause_types=frozenset({EventType.DEATH, EventType.FEUD}),
        validator=_validate_revelation,
    ),
    EventType.FAMINE: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({EventType.RAID}),
    ),
    EventType.TRADE_ROUTE_FOUNDED: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({EventType.PEACE, EventType.MARRIAGE, EventType.FAMINE}),
    ),
    EventType.TRADE_ROUTE_BROKEN: GrammarRule(
        root_allowed=False,
        allowed_cause_types=frozenset({
            EventType.RAID,
            EventType.FEUD,
            EventType.FAMINE,
            EventType.SUCCESSION_CRISIS,
        }),
    ),
    EventType.CHIEF_CHANGED: GrammarRule(
        root_allowed=False,
        allowed_cause_types=frozenset({EventType.DEATH, EventType.SUCCESSION_CRISIS}),
        validator=_validate_chief_changed,
    ),
    EventType.SUCCESSION_CRISIS: GrammarRule(
        root_allowed=False,
        allowed_cause_types=frozenset({EventType.DEATH}),
        validator=_validate_succession_crisis,
    ),
    EventType.SETTLEMENT_COLLAPSE: GrammarRule(
        root_allowed=False,
        allowed_cause_types=frozenset({
            EventType.RAID,
            EventType.FAMINE,
            EventType.FEUD,
            EventType.DEATH,
            EventType.SUCCESSION_CRISIS,
        }),
        validator=_validate_settlement_collapse,
    ),
    EventType.MIGRATION: GrammarRule(
        root_allowed=False,
        allowed_cause_types=frozenset({
            EventType.SETTLEMENT_COLLAPSE,
            EventType.FAMINE,
            EventType.RAID,
        }),
        validator=_validate_migration,
    ),
    # Milestone R0: Religion Engine event grammar rules
    EventType.CONVERSION: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({
            EventType.MARRIAGE,
            EventType.MIGRATION,
            EventType.RELIGIOUS_REFORM,
            EventType.RELIGIOUS_SCHISM,
            EventType.PILGRIMAGE,
        }),
    ),
    EventType.RELIGIOUS_REFORM: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({
            EventType.DEATH,
            EventType.FAMINE,
            EventType.SUCCESSION_CRISIS,
            EventType.RAID,
            EventType.FEUD,
        }),
    ),
    EventType.RELIGIOUS_SCHISM: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({
            EventType.RELIGIOUS_REFORM,
            EventType.FEUD,
            EventType.SUCCESSION_CRISIS,
            EventType.DEATH,
        }),
    ),
    EventType.SAINT_CANONIZED: GrammarRule(
        root_allowed=False,
        allowed_cause_types=frozenset({
            EventType.DEATH,
        }),
    ),
    EventType.PILGRIMAGE: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({
            EventType.HOLY_SITE_DISCOVERED,
            EventType.RELIGIOUS_REFORM,
        }),
    ),
    EventType.HOLY_SITE_DISCOVERED: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({
            EventType.FAMINE,
            EventType.DEATH,
            EventType.RELIGIOUS_REFORM,
            EventType.GREAT_FIGURE_EMERGENCE,
        }),
    ),
    # Milestone R1: Religion Becomes History rules
    EventType.HERESY_DECLARED: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({
            EventType.DEATH,
            EventType.FAMINE,
            EventType.RELIGIOUS_REFORM,
            EventType.FEUD,
            EventType.GREAT_FIGURE_EMERGENCE,
            EventType.RELIGIOUS_SCHISM,
        }),
    ),
    EventType.SECT_REUNIFICATION: GrammarRule(
        root_allowed=False,
        allowed_cause_types=frozenset({
            EventType.RELIGIOUS_SCHISM,
            EventType.HERESY_DECLARED,
            EventType.PEACE,
            EventType.RELIGIOUS_REFORM,
        }),
    ),
    EventType.RELIGIOUS_REFUGEE_MIGRATION: GrammarRule(
        root_allowed=False,
        allowed_cause_types=frozenset({
            EventType.HERESY_DECLARED,
            EventType.RELIGIOUS_SCHISM,
            EventType.RAID,
            EventType.FEUD,
        }),
    ),
    EventType.GREAT_FIGURE_EMERGENCE: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({
            EventType.DEATH,
            EventType.FAMINE,
            EventType.HOLY_SITE_DISCOVERED,
            EventType.PILGRIMAGE,
            EventType.REVELATION,
            EventType.HERESY_DECLARED,
            EventType.RELIGIOUS_REFORM,
        }),
    ),
    EventType.MYTH_RECORDED: GrammarRule(
        root_allowed=False,
        allowed_cause_types=frozenset({
            EventType.DEATH,
            EventType.RAID,
            EventType.FEUD,
            EventType.SAINT_CANONIZED,
            EventType.GREAT_FIGURE_EMERGENCE,
            EventType.FAMINE,
            EventType.HOLY_SITE_DISCOVERED,
        }),
    ),
    # Milestone R1.5 + R2: Syncretism, Cultural Evolution & Living Faith Systems
    EventType.RELIGIOUS_SYNCRETISM: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({
            EventType.MIGRATION,
            EventType.MARRIAGE,
            EventType.PILGRIMAGE,
            EventType.TRADE_ROUTE_FOUNDED,
            EventType.PEACE,
            EventType.RELIGIOUS_REFORM,
        }),
    ),
    EventType.DOCTRINAL_BORROWING: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({
            EventType.TRADE_ROUTE_FOUNDED,
            EventType.PILGRIMAGE,
            EventType.MARRIAGE,
            EventType.MIGRATION,
            EventType.PEACE,
        }),
    ),
    EventType.FOLK_TRADITION_ABSORBED: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({
            EventType.HOLY_SITE_DISCOVERED,
            EventType.MYTH_RECORDED,
            EventType.DEATH,
            EventType.REVELATION,
        }),
    ),
    EventType.LOCAL_CUSTOM_CELEBRATED: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({
            EventType.HOLY_SITE_DISCOVERED,
            EventType.FOLK_TRADITION_ABSORBED,
            EventType.PEACE,
            EventType.PILGRIMAGE,
            EventType.BIRTH,
        }),
    ),
    EventType.HOLY_SITE_ELEVATED: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({
            EventType.PILGRIMAGE,
            EventType.HOLY_SITE_DISCOVERED,
            EventType.SAINT_CANONIZED,
            EventType.GREAT_FIGURE_EMERGENCE,
        }),
    ),
    EventType.MYTH_EXCHANGED: GrammarRule(
        root_allowed=True,
        allowed_cause_types=frozenset({
            EventType.MYTH_RECORDED,
            EventType.TRADE_ROUTE_FOUNDED,
            EventType.PILGRIMAGE,
            EventType.MIGRATION,
        }),
    ),
}


def validate_causes(event_type: EventType, cause_events: Sequence[tuple[int, EventType]]) -> None:
    """
    Validates that cause_events conform to CAUSE_GRAMMAR for the given event_type.
    cause_events is a sequence of (event_id, event_type).
    Raises CausalGrammarError on violation.
    """
    rule = CAUSE_GRAMMAR.get(event_type)
    if rule is None:
        raise CausalGrammarError(f"No causal grammar rule defined for EventType: {event_type}")

    if not cause_events:
        if not rule.root_allowed:
            raise CausalGrammarError(
                f"EventType '{event_type.value}' cannot be a root event: requires at least one cause."
            )
        return

    cause_types = [c_type for _, c_type in cause_events]

    # Check allowed cause types
    for c_id, c_type in cause_events:
        if c_type not in rule.allowed_cause_types:
            allowed_names = ", ".join(t.value for t in sorted(rule.allowed_cause_types, key=lambda x: x.value))
            raise CausalGrammarError(
                f"EventType '{event_type.value}' cannot cite cause Event #{c_id} of type '{c_type.value}'. "
                f"Allowed cause types: [{allowed_names}]"
            )

    # Check specific validator requirements if present
    if rule.validator is not None:
        ok, msg = rule.validator(cause_types)
        if not ok:
            raise CausalGrammarError(
                f"Causal grammar violation for '{event_type.value}': {msg}"
            )
