"""
Character entity and family relationships.

Adheres to agent.md:
- Named characters with persistent identity.
- Family structures (spouse, parents, children).
- Status (alive/dead, age, settlement).
- Name integrity and ordinals (Milestone 0.5.4 & Viewer V2).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


def int_to_roman(num: int) -> str:
    """Converts a positive integer into Roman numerals."""
    if num <= 0:
        return ""
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman_num = ""
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syb[i]
            num -= val[i]
        i += 1
    return roman_num


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
    profession: str = "Laborer"
    family_id: str = ""
    name_ordinal: int = 1
    display_name: str = ""

    def __post_init__(self):
        # Guarantee non-empty names
        if not self.first_name:
            self.first_name = "Citizen"
        if not self.last_name:
            self.last_name = "Commoner"
        if not self.family_id:
            self.family_id = self.last_name

        if not self.display_name:
            base = f"{self.first_name} {self.last_name}".strip()
            if self.name_ordinal > 1:
                self.display_name = f"{base} {int_to_roman(self.name_ordinal)}"
            else:
                self.display_name = base

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def name(self) -> str:
        return self.display_name if self.display_name else self.full_name

    @property
    def age_years(self) -> int:
        return self.age_ticks // 12

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "display_name": self.display_name,
            "name_ordinal": self.name_ordinal,
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
            "profession": self.profession,
            "family_id": self.family_id,
        }
