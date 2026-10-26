"""
Immutable World Specification & WorldProvider Interface.

Milestone 0.5.3: Randomized Worlds and Casts (Seed Split).

Serves as the boundary contract between world/terrain generation and simulation.
Milestone T0 will implement WorldProvider to generate tile-based maps without
modifying the simulation interface.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import json
from typing import Protocol, Sequence


@dataclass(frozen=True)
class SettlementSite:
    """
    Immutable specification of a settlement location and economic endowment.
    Derived strictly from the world seed.
    """
    id: str                       # e.g. "set_0", "set_1"
    name: str                     # e.g. "Riverford", "Highpeak"
    x: int                        # integer coordinate on map
    y: int                        # integer coordinate on map
    farmland: float               # [0.50, 2.50]
    forest: float                 # [0.50, 2.50]
    ore_richness: float           # [0.50, 2.50]
    defensibility: float          # [0.50, 2.50]
    water_access: float           # [0.0, 1.0]
    site_type: str                # "river", "mountain", "forest", "plain"
    base_food: int = 140
    base_wood: int = 110
    base_ore: int = 60
    base_wealth: int = 70

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "farmland": self.farmland,
            "forest": self.forest,
            "ore_richness": self.ore_richness,
            "defensibility": self.defensibility,
            "water_access": self.water_access,
            "site_type": self.site_type,
            "base_food": self.base_food,
            "base_wood": self.base_wood,
            "base_ore": self.base_ore,
            "base_wealth": self.base_wealth,
        }


@dataclass(frozen=True)
class WorldSpec:
    """
    Immutable specification of the world geometry, sites, and endowments.
    Output exclusively from world_seed.
    """
    world_seed: int
    map_width: int
    map_height: int
    settlements: tuple[SettlementSite, ...]
    roads: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    generator_version: str = "T0"
    digest: str = ""
    terrain_data: Optional[bytes] = None

    def __post_init__(self):
        if not self.digest:
            # Compute canonical SHA-256 digest
            canonical_data = {
                "world_seed": self.world_seed,
                "map_width": self.map_width,
                "map_height": self.map_height,
                "generator_version": self.generator_version,
                "settlements": [s.to_dict() for s in self.settlements],
                "road_count": len(self.roads),
            }
            json_bytes = json.dumps(canonical_data, sort_keys=True).encode("utf-8")
            h = hashlib.sha256(json_bytes).hexdigest()
            # Assign through object.__setattr__ because dataclass is frozen
            object.__setattr__(self, "digest", h)

    @property
    def settlement_count(self) -> int:
        return len(self.settlements)

    def canonical_digest(self) -> str:
        return self.digest

    def get_site(self, settlement_id: str) -> SettlementSite | None:
        for s in self.settlements:
            if s.id == settlement_id:
                return s
        return None

    def to_dict(self) -> dict:
        return {
            "world_seed": self.world_seed,
            "map_width": self.map_width,
            "map_height": self.map_height,
            "generator_version": self.generator_version,
            "digest": self.digest,
            "settlements": [s.to_dict() for s in self.settlements],
            "roads": list(self.roads),
        }
        return {
            "world_seed": self.world_seed,
            "map_width": self.map_width,
            "map_height": self.map_height,
            "generator_version": self.generator_version,
            "digest": self.digest,
            "settlements": [s.to_dict() for s in self.settlements],
        }


class WorldProvider(Protocol):
    """
    Interface for world generators.
    Allows Milestone T0 Headless Terrain Engine to seamlessly plug in.
    """
    def generate(self, world_seed: int) -> WorldSpec:
        ...
