"""
Belief System Data Model.

Adheres strictly to agent.md and Milestone 0.5 (Sections 4.3 & 4.4):
- Immutable subjective belief records.
- Belief supersession tracking via `supersedes_belief_id`.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional
from minemesis.core.types import BeliefSource, EventType, Intent


@dataclass(frozen=True)
class Belief:
    belief_id: int
    believer_id: str
    event_ref: int  # Reference to Event ID in EventLog
    source: BeliefSource
    source_character_id: Optional[str]  # None if Witnessed/Inferred, or character_id if Told
    confidence: float  # [0.0, 1.0]
    tick_acquired: int

    # Believed Fields (Derived interpretation of the event)
    believed_type: EventType
    believed_intent: Intent
    believed_actor: Optional[str]
    believed_target: Optional[str]
    believed_location: str
    believed_payload: Mapping[str, Any] = field(default_factory=dict)

    # Belief supersession (Section 4.4)
    supersedes_belief_id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "belief_id": self.belief_id,
            "believer_id": self.believer_id,
            "event_ref": self.event_ref,
            "source": self.source.value,
            "source_character_id": self.source_character_id,
            "confidence": round(self.confidence, 3),
            "tick_acquired": self.tick_acquired,
            "believed_type": self.believed_type.value,
            "believed_intent": self.believed_intent.value,
            "believed_actor": self.believed_actor,
            "believed_target": self.believed_target,
            "believed_location": self.believed_location,
            "believed_payload": dict(self.believed_payload),
            "supersedes_belief_id": self.supersedes_belief_id,
        }
