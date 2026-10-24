"""
Memory System Data Model.

Adheres strictly to agent.md and Milestone 0.5 (Sections 4.3 & 4.4):
- Memories are emotional reactions to beliefs, NOT to events.
- Tracks source_belief_id to support derived supersession filtering without mutation.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from minemesis.core.types import Emotion


@dataclass(frozen=True)
class Memory:
    id: int
    observer_id: str
    belief_event_ref: int  # EventRef from belief
    target_entity_id: Optional[str]  # The person/settlement this emotional reaction focuses on
    emotion: Emotion
    initial_intensity: float  # e.g., 0.0 to 100.0
    decay_rate: float  # Per tick decay rate
    tick_formed: int
    source_belief_id: int = 0  # Belief ID that produced this memory

    def current_intensity(self, current_tick: int) -> float:
        """
        Calculates emotional intensity at the current tick using exponential decay.
        """
        elapsed = max(0, current_tick - self.tick_formed)
        intensity = self.initial_intensity * ((1.0 - self.decay_rate) ** elapsed)
        return max(0.0, intensity)

    def to_dict(self, current_tick: Optional[int] = None) -> dict:
        cur_int = self.current_intensity(current_tick) if current_tick is not None else self.initial_intensity
        return {
            "id": self.id,
            "observer_id": self.observer_id,
            "belief_event_ref": self.belief_event_ref,
            "target_entity_id": self.target_entity_id,
            "emotion": self.emotion.value,
            "initial_intensity": round(self.initial_intensity, 2),
            "current_intensity": round(cur_int, 2),
            "decay_rate": self.decay_rate,
            "tick_formed": self.tick_formed,
            "source_belief_id": self.source_belief_id,
        }
