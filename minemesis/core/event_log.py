"""
Event Log and Event schema.

Adheres strictly to agent.md Architecture Freeze v1.0 and Milestone 0.5:
- Single source of truth.
- Immutable, append-only.
- Records objective reality, never interpretations.
- Validates every event's causes against CAUSE_GRAMMAR.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence
import json

from minemesis.core.causal_grammar import CausalGrammarError, validate_causes
from minemesis.core.entity_table import EntityTable
from minemesis.core.types import EventType, Intent, Scale


@dataclass(frozen=True)
class Event:
    """
    Objective Event recorded in the immutable Event Log.
    """
    id: int
    tick: int
    location: str  # Settlement ID or Coordinate description
    type: EventType
    participants: tuple[tuple[str, str], ...]  # Tuple of (role, entity_id) for immutability & hashability
    causes: tuple[int, ...]  # Event IDs that caused this event
    intent: Intent
    scale: Scale
    payload: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tick": self.tick,
            "location": self.location,
            "type": self.type.value,
            "participants": dict(self.participants),
            "causes": list(self.causes),
            "intent": self.intent.value,
            "scale": self.scale.value,
            "payload": dict(self.payload),
        }

    @property
    def participants_dict(self) -> dict[str, str]:
        return dict(self.participants)

    @property
    def description(self) -> str:
        """
        Lazily reconstructs a human-readable English description from objective facts
        and payload parameters, eliminating the need to store static prose strings in RAM.
        """
        if "description" in self.payload:
            return str(self.payload["description"])
        return self._render_default_description()

    def _render_default_description(self) -> str:
        parts = self.participants_dict
        t = self.type
        loc = self.location or "the world"
        if t == EventType.BIRTH:
            child = parts.get("child", "Child")
            father = parts.get("father")
            mother = parts.get("mother")
            if father and mother:
                return f"Birth of {child} to {father} and {mother}"
            return f"Birth of {child} in {loc}"
        elif t == EventType.MARRIAGE:
            s1 = parts.get("spouse1", "Spouse1")
            s2 = parts.get("spouse2", "Spouse2")
            alliance = " (Alliance Marriage)" if self.payload.get("is_alliance") else ""
            return f"Marriage of {s1} and {s2}{alliance}"
        elif t == EventType.DEATH:
            victim = parts.get("target") or parts.get("deceased") or parts.get("victim", "Victim")
            cause = self.payload.get("cause") or self.payload.get("cause_of_death")
            if not cause:
                cause = "Accident" if self.intent == Intent.ACCIDENTAL else "Natural"
            actor = parts.get("actor")
            if actor:
                return f"Death of {victim} in {cause.lower()} with {actor}"
            return f"Death of {victim} ({cause})"
        elif t == EventType.RAID:
            init = parts.get("initiator", "Raiders")
            target = parts.get("target", loc)
            return f"Raid by {init} on {target}"
        elif t == EventType.FAMINE:
            return f"Severe famine struck {loc} as winter food stores collapsed."
        elif t == EventType.PEACE:
            return f"Peace established between {parts.get('initiator', '')} and {parts.get('target', '')}"
        elif t in (EventType.FEUD, EventType.FEUD_BEGINS):
            is_wrongful = self.payload.get("is_wrongful")
            prefix = "Wrongful feud" if is_wrongful else "Blood feud"
            return f"{prefix} declared by {parts.get('instigator', '')} against {parts.get('target', '')}"
        elif t == EventType.REVELATION:
            return f"Truth revealed to {parts.get('recipient', '')} by {parts.get('witness', '')}"
        elif t == EventType.SETTLEMENT_COLLAPSE:
            return f"Settlement {loc} collapsed under sustained pressure"
        elif t == EventType.TRADE_ROUTE_FOUNDED:
            return f"Trade route founded at {loc}"
        elif t == EventType.TRADE_ROUTE_BROKEN:
            return f"Trade route broken at {loc}"
        elif t == EventType.CHIEF_CHANGED:
            new_c = parts.get("new_chief") or parts.get("successor", "new chief")
            return f"Chief changed in {loc}: {new_c} took leadership"
        elif t == EventType.SUCCESSION_CRISIS:
            return f"Succession crisis erupted in {loc}"
        elif t == EventType.BOOK_WRITTEN:
            title = self.payload.get("title", "a book")
            return f"Book penned: {title} by {parts.get('author', 'scholar')}"
        elif t == EventType.MIGRATION:
            return f"Migration from {parts.get('source', '')} to {parts.get('destination', '')}"
        return f"{t.value} at {loc}"


class EventLog:
    """
    Append-only, immutable Event Log storing objective history.
    Validates causal grammar on every append.
    """
    def __init__(self) -> None:
        self._events: list[Event] = []
        self._by_id: dict[int, Event] = {}
        self._listeners: list[Callable[[Event], None]] = []

    def add_listener(self, listener: Callable[[Event], None]) -> None:
        self._listeners.append(listener)

    def append(
        self,
        tick: int,
        location: str,
        event_type: EventType,
        participants: Mapping[str, str] | Sequence[tuple[str, str]],
        causes: Sequence[int],
        intent: Intent,
        scale: Scale,
        payload: Mapping[str, Any] | None = None,
    ) -> Event:
        next_id = len(self._events)
        loc_interned = EntityTable.intern(location)
        
        # Normalize participants to sorted tuple of pairs for determinism & immutability
        if isinstance(participants, Mapping):
            raw_items = participants.items()
        else:
            raw_items = participants
        part_tuple = tuple(sorted((EntityTable.intern(str(k)), EntityTable.intern(str(v))) for k, v in raw_items))
            
        causes_tuple = tuple(causes)
        payload_dict = dict(payload) if payload else {}

        # 1. Validate that referenced causes exist and respect lag caps
        cause_events: list[tuple[int, EventType]] = []
        for cause_id in causes_tuple:
            if cause_id not in self._by_id:
                raise ValueError(f"Cause Event ID {cause_id} does not exist in EventLog")
            cause_evt = self._by_id[cause_id]
            cause_events.append((cause_id, cause_evt.type))

            # Directive 11: Lag caps on cause edges
            lag = tick - cause_evt.tick
            if event_type == EventType.MARRIAGE:
                if cause_evt.type == EventType.PEACE and lag > 12:
                    raise CausalGrammarError(
                        f"Marriage at tick {tick} citing Peace #{cause_id} exceeds lag cap "
                        f"(lag={lag} ticks > 12 max allowed)"
                    )
                if cause_evt.type == EventType.TRADE_ROUTE_FOUNDED and lag > 24:
                    raise CausalGrammarError(
                        f"Marriage at tick {tick} citing TradeRouteFounded #{cause_id} exceeds lag cap "
                        f"(lag={lag} ticks > 24 max allowed)"
                    )

        # 2. Validate against CAUSE_GRAMMAR (Section 4.1)
        validate_causes(event_type, cause_events)

        evt = Event(
            id=next_id,
            tick=tick,
            location=loc_interned,
            type=event_type,
            participants=part_tuple,
            causes=causes_tuple,
            intent=intent,
            scale=scale,
            payload=payload_dict,
        )
        self._events.append(evt)
        self._by_id[next_id] = evt
        for fn in self._listeners:
            fn(evt)
        return evt

    def get(self, event_id: int) -> Event:
        if event_id not in self._by_id:
            raise KeyError(f"Event ID {event_id} not found in EventLog")
        return self._by_id[event_id]

    def get_event(self, event_id: int) -> Event | None:
        return self._by_id.get(event_id)

    def all_events(self) -> Sequence[Event]:
        return list(self._events)

    def __len__(self) -> int:
        return len(self._events)

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps([e.to_dict() for e in self._events], indent=indent)
