"""
Relationship System: Cached derived views computed strictly from memories.

Adheres to agent.md Architecture Freeze v1.0 and Milestone 0.5:
- Relationships are cached views.
- Relationships are NEVER source of truth.
- Relationships are computed from active, non-superseded memories.
- Supports memory re-appraisal (Regret, Relief, Respect).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional, Set
from minemesis.core.types import Emotion
from minemesis.models.memory import Memory


@dataclass(frozen=True)
class Relationship:
    source_id: str
    target_id: str
    trust: float    # [-100.0, 100.0]
    fear: float     # [0.0, 100.0]
    respect: float  # [-100.0, 100.0]
    hatred: float   # [0.0, 100.0]
    loyalty: float  # [-100.0, 100.0]

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "trust": round(self.trust, 1),
            "fear": round(self.fear, 1),
            "respect": round(self.respect, 1),
            "hatred": round(self.hatred, 1),
            "loyalty": round(self.loyalty, 1),
        }


def compute_relationship(
    source_id: str,
    target_id: str,
    memories: Iterable[Memory],
    current_tick: int,
    is_family: bool = False,
    is_spouse: bool = False,
    same_settlement: bool = False,
    superseded_memory_ids: Set[int] | None = None,
) -> Relationship:
    """
    Computes relationship purely as a derived view over active, non-superseded memories.
    Never stores or persists relationship state as an authoritative primitive.
    """
    # Baseline affinities
    trust = 15.0 if same_settlement else 0.0
    fear = 0.0
    respect = 10.0 if same_settlement else 0.0
    hatred = 0.0
    loyalty = 10.0 if same_settlement else 0.0

    if is_family:
        trust += 35.0
        loyalty += 50.0
        respect += 20.0
    if is_spouse:
        trust += 40.0
        loyalty += 50.0
        respect += 25.0

    superseded = superseded_memory_ids or set()

    for mem in memories:
        if mem.observer_id != source_id or mem.target_entity_id != target_id:
            continue
        
        # Exclude memories stemming from superseded beliefs
        if mem.id in superseded:
            continue

        intensity = mem.current_intensity(current_tick)
        if intensity <= 0.01:
            continue

        if mem.emotion in (Emotion.HATRED, Emotion.ANGER):
            hatred += intensity
            trust -= intensity * 1.2
            respect -= intensity * 0.8
            loyalty -= intensity * 1.5
        elif mem.emotion == Emotion.FEAR:
            fear += intensity
            trust -= intensity * 0.4
        elif mem.emotion in (Emotion.GRATITUDE, Emotion.AFFECTION):
            trust += intensity * 0.9
            respect += intensity * 0.7
            loyalty += intensity * 0.9
            hatred -= intensity * 0.8
        elif mem.emotion == Emotion.RESPECT:
            respect += intensity
            trust += intensity * 0.5
        elif mem.emotion == Emotion.RELIEF:
            trust += intensity * 0.5
            hatred -= intensity * 0.6
        elif mem.emotion == Emotion.REGRET:
            # Re-appraisal memory: feeling regret or remorse toward wrongly accused
            hatred -= intensity * 1.5
            trust += intensity * 0.6
            respect += intensity * 0.8
        elif mem.emotion == Emotion.GRIEF:
            hatred += intensity * 0.5
            trust -= intensity * 0.6

    # Clamp to valid ranges
    trust = max(-100.0, min(100.0, trust))
    fear = max(0.0, min(100.0, fear))
    respect = max(-100.0, min(100.0, respect))
    hatred = max(0.0, min(100.0, hatred))
    loyalty = max(-100.0, min(100.0, loyalty))

    return Relationship(
        source_id=source_id,
        target_id=target_id,
        trust=trust,
        fear=fear,
        respect=respect,
        hatred=hatred,
        loyalty=loyalty,
    )
