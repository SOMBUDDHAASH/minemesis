"""
Character entity and family relationships.

Adheres to agent.md:
- Named characters with persistent identity.
- Family structures (spouse, parents, children).
- Status (alive/dead, age, settlement).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Character:
    id: str
    first_name: str
    last_name: str
    settlement_id: str
    age_ticks: int
    sex: str  # "M" or "F"
    alive: bool = True
    death_tick: Optional[int] = None
    death_event_id: Optional[int] = None
    spouse_id: Optional[str] = None
    father_id: Optional[str] = None
    mother_id: Optional[str] = None
    children_ids: list[str] = field(default_factory=list)
    # Personality traits in [0.0, 1.0] used for bias/distortion in belief formation
    suspicion: float = 0.5  # Higher suspicion -> more likely to interpret ambiguous intent as hostile
    forgiveness: float = 0.5  # Higher forgiveness -> memories decay faster, reconciliation easier

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def name(self) -> str:
        return self.full_name

    @property
    def age_years(self) -> int:
        return self.age_ticks // 12

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "settlement_id": self.settlement_id,
            "age_years": self.age_years,
            "sex": self.sex,
            "alive": self.alive,
            "death_tick": self.death_tick,
            "spouse_id": self.spouse_id,
            "father_id": self.father_id,
            "mother_id": self.mother_id,
            "children_ids": list(self.children_ids),
        }
