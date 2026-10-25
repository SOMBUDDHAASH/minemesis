"""
Pluggable Event Narration Service for Viewer V2.
Converts events into human-readable English prose, with safe fallbacks
so unknown or novel event types NEVER crash the viewer.
"""

from __future__ import annotations
import json
import re
from typing import Any, Callable, Mapping

from viewer.services.names import name_resolver

# Registry of specialized narrators: event_type -> callable(event_dict, participants) -> str
_NARRATORS: dict[str, Callable[[dict[str, Any], list[dict[str, Any]]], str]] = {}


def register_narrator(event_type: str):
    def decorator(fn: Callable[[dict[str, Any], list[dict[str, Any]]], str]):
        _NARRATORS[event_type] = fn
        return fn
    return decorator


def _get_participant_name(participants: list[dict[str, Any]], role: str, default: str = "") -> str:
    for p in participants:
        if p.get("role") == role:
            return p.get("name_at_time") or p.get("character_id") or default
    return default


@register_narrator("Birth")
def _narrate_birth(evt: dict[str, Any], participants: list[dict[str, Any]]) -> str:
    child = _get_participant_name(participants, "child", "A child")
    father = _get_participant_name(participants, "father")
    mother = _get_participant_name(participants, "mother")
    if father and mother:
        return f"{child} was born to {father} and {mother}."
    return f"{child} was born."


@register_narrator("Marriage")
def _narrate_marriage(evt: dict[str, Any], participants: list[dict[str, Any]]) -> str:
    s1 = _get_participant_name(participants, "spouse1", "Someone")
    s2 = _get_participant_name(participants, "spouse2", "someone")
    return f"{s1} and {s2} were united in marriage."


@register_narrator("Death")
def _narrate_death(evt: dict[str, Any], participants: list[dict[str, Any]]) -> str:
    victim = _get_participant_name(participants, "target") or _get_participant_name(participants, "deceased") or _get_participant_name(participants, "victim", "A resident")
    actor = _get_participant_name(participants, "actor")
    if actor:
        return f"{victim} was slain in conflict with {actor}."
    desc = evt.get("description", "")
    if "(" in desc and ")" in desc:
        cause = desc[desc.find("(") + 1 : desc.rfind(")")]
        return f"{victim} died ({cause})."
    return f"{victim} passed away."


@register_narrator("Feud")
@register_narrator("FeudBegins")
def _narrate_feud(evt: dict[str, Any], participants: list[dict[str, Any]]) -> str:
    inst = _get_participant_name(participants, "instigator", "A house")
    tgt = _get_participant_name(participants, "target", "a rival house")
    return f"A bitter blood feud erupted between {inst} and {tgt}."


@register_narrator("FeudReconciliation")
def _narrate_reconciliation(evt: dict[str, Any], participants: list[dict[str, Any]]) -> str:
    p1 = _get_participant_name(participants, "instigator") or _get_participant_name(participants, "party1", "House")
    p2 = _get_participant_name(participants, "target") or _get_participant_name(participants, "party2", "Rival")
    return f"Peace and reconciliation were achieved, ending the feud between {p1} and {p2}."


@register_narrator("Revelation")
def _narrate_revelation(evt: dict[str, Any], participants: list[dict[str, Any]]) -> str:
    rec = _get_participant_name(participants, "recipient", "Someone")
    wit = _get_participant_name(participants, "witness", "a witness")
    return f"The truth of past events was revealed to {rec} by {wit}."


@register_narrator("Raid")
def _narrate_raid(evt: dict[str, Any], participants: list[dict[str, Any]]) -> str:
    init = _get_participant_name(participants, "initiator", "Raiders")
    tgt = _get_participant_name(participants, "target", "the settlement")
    return f"Raiders from {init} launched a devastating raid upon {tgt}."


@register_narrator("Peace")
def _narrate_peace(evt: dict[str, Any], participants: list[dict[str, Any]]) -> str:
    init = _get_participant_name(participants, "initiator", "One settlement")
    tgt = _get_participant_name(participants, "target", "another")
    return f"A formal peace accord was concluded between {init} and {tgt}."


@register_narrator("BookWritten")
def _narrate_book(evt: dict[str, Any], participants: list[dict[str, Any]]) -> str:
    author = _get_participant_name(participants, "author", "A scholar")
    desc = evt.get("description", "")
    return desc if desc else f"A new manuscript was penned by {author}."


@register_narrator("ReligiousSchism")
def _narrate_schism(evt: dict[str, Any], participants: list[dict[str, Any]]) -> str:
    desc = evt.get("description", "A theological schism fractured the faith.")
    return _clean_raw_ids(desc)


@register_narrator("ReligiousSyncretism")
def _narrate_syncretism(evt: dict[str, Any], participants: list[dict[str, Any]]) -> str:
    desc = evt.get("description", "Two traditions fused into a syncretic faith.")
    return _clean_raw_ids(desc)


def _clean_raw_ids(text: str) -> str:
    """Replaces raw settlement and religion IDs with clean names."""
    def rep_rel(match):
        return name_resolver.resolve_religion(match.group(0))

    def rep_set(match):
        return name_resolver.resolve_settlement(match.group(0))

    text = re.sub(r"\brel_\w+\b", rep_rel, text)
    text = re.sub(r"\bset_\w+\b", rep_set, text)
    return text


def narrate_event(evt: dict[str, Any], participants: Optional[list[dict[str, Any]]] = None) -> str:
    """
    Main entry point for event narration.
    Guaranteed never to throw exceptions; falls back cleanly.
    """
    try:
        t = evt.get("type", "")
        parts = participants if participants is not None else evt.get("participants", [])

        if t in _NARRATORS:
            return _NARRATORS[t](evt, parts)

        # Fallback to description with raw ID cleaning
        raw_desc = evt.get("description")
        if raw_desc:
            return _clean_raw_ids(raw_desc)

        # Ultimate fallback
        return f"Event of type {t} recorded in Year {evt.get('year', 1)}."
    except Exception as e:
        return evt.get("description") or f"Event {evt.get('event_id', '?')} ({evt.get('type', 'Unknown')})"
