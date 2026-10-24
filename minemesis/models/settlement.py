"""
Settlement and Trade Route State Models.

Adheres strictly to agent.md and Milestone 0.5 (Sections 4.2 & 4.5):
- Asymmetric productivity endowments (farmland, forest, ore_richness, defensibility).
- Routine trade demoted to continuous TradeRoute state.
- Stability tracking for leadership/succession crises.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TradeRoute:
    """
    Continuous trade route state between two settlements.
    Routine caravan movements update this state without cluttering the EventLog.
    """
    settlement_a: str
    settlement_b: str
    volume: int = 10
    health: float = 1.0  # [0.0, 1.0]
    active: bool = False
    founded_event_id: Optional[int] = None

    @property
    def key(self) -> tuple[str, str]:
        return tuple(sorted([self.settlement_a, self.settlement_b]))


@dataclass
class Settlement:
    id: str
    name: str
    x: int
    y: int
    leader_id: Optional[str] = None
    food: int = 100
    wood: int = 100
    ore: int = 50
    wealth: int = 50
    member_ids: list[str] = field(default_factory=list)

    # Asymmetric terrain & productivity endowments (Section 4.5)
    farmland: float = 1.0       # Food output multiplier
    forest: float = 1.0         # Wood output multiplier
    ore_richness: float = 1.0   # Ore output multiplier
    defensibility: float = 1.0  # Reduces raid plunder/casualties

    # Internal civic state
    stability: float = 1.0      # Reduced by SuccessionCrisis; increases raid risk
    consecutive_starvation_ticks: int = 0
    active_famine_event_id: Optional[int] = None
    active_famine_start_tick: Optional[int] = None
    adequate_food_ticks: int = 12

    def distance_to(self, other: Settlement) -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "pos": [self.x, self.y],
            "leader_id": self.leader_id,
            "food": self.food,
            "wood": self.wood,
            "ore": self.ore,
            "wealth": self.wealth,
            "population": len(self.member_ids),
            "stability": round(self.stability, 2),
            "farmland": round(self.farmland, 2),
            "ore_richness": round(self.ore_richness, 2),
            "defensibility": round(self.defensibility, 2),
        }
