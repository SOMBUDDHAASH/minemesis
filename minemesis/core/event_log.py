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


class EventLog:
    """
    Append-only, immutable Event Log storing objective history.
    Validates causal grammar on every append.
    """
    def __init__(self) -> None:
        self._events: list[Event] = []
        self._by_id: dict[int, Event] = {}

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
        
        # Normalize participants to sorted tuple of pairs for determinism & immutability
        if isinstance(participants, Mapping):
            part_tuple = tuple(sorted(participants.items()))
        else:
            part_tuple = tuple(sorted(participants))
            
        causes_tuple = tuple(causes)
        payload_dict = dict(payload) if payload else {}

        # 1. Validate that referenced causes exist
        cause_events: list[tuple[int, EventType]] = []
        for cause_id in causes_tuple:
            if cause_id not in self._by_id:
                raise ValueError(f"Cause Event ID {cause_id} does not exist in EventLog")
            cause_events.append((cause_id, self._by_id[cause_id].type))

        # 2. Validate against CAUSE_GRAMMAR (Section 4.1)
        validate_causes(event_type, cause_events)

        evt = Event(
            id=next_id,
            tick=tick,
            location=location,
            type=event_type,
            participants=part_tuple,
            causes=causes_tuple,
            intent=intent,
            scale=scale,
            payload=payload_dict,
        )
        self._events.append(evt)
        self._by_id[next_id] = evt
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
