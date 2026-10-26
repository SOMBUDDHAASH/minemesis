"""
Two-Way Construction Analyzer for Milestone T1.

Translates aggregated player voxel block edits (Chunk Deltas) into macroscopic
settlement-level events and economic updates for the simulation:
- Aggregates block placements and excavations within settlement bounding radii.
- Analyzes wall perimeter enclosures and defensibility improvements.
- Detects subterranean mine shafts and quarry excavations.
- Converts hundreds of raw block deltas into single meaningful historical events.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from minemesis.systems.world_spec import WorldSpec, SettlementSite
from translators.voxel.voxelspec import (
    BLOCK_AIR,
    BLOCK_COBBLESTONE,
    BLOCK_DIRT,
    BLOCK_OAK_PLANKS,
    BLOCK_OAK_WOOD,
    BLOCK_STONE,
    VoxelWorldSpec,
)


@dataclass
class ConstructionRecord:
    """
    Macroscopic architectural achievement evaluated from player chunk deltas.
    """
    settlement_id: str
    settlement_name: str
    construction_type: str        # "DefensiveFortification", "MineShaft", "SettlementHousing"
    block_count: int
    defensibility_delta: float = 0.0
    resource_bonuses: Dict[str, float] = field(default_factory=dict)
    summary: str = ""

    def to_event_payload(self) -> Dict[str, Any]:
        return {
            "settlement_id": self.settlement_id,
            "type": self.construction_type,
            "blocks_aggregated": self.block_count,
            "defensibility_delta": self.defensibility_delta,
            "resource_bonuses": self.resource_bonuses,
            "description": self.summary,
        }


class ConstructionAnalyzer:
    """
    Evaluates player chunk deltas and determines settlement-level improvements.
    """

    def __init__(self, world_spec: WorldSpec) -> None:
        self.world_spec = world_spec
        self.voxel_spec = VoxelWorldSpec(world_spec=world_spec)
        self.processed_blocks: set[Tuple[int, int, int]] = set()

    def analyze_chunk_deltas(
        self,
        chunk_deltas: Mapping[Tuple[int, int], Mapping[Tuple[int, int, int], int]],
    ) -> List[ConstructionRecord]:
        """
        Inspects all chunk deltas and returns macroscopic construction records.
        """
        records: List[ConstructionRecord] = []

        # Group all deltas by settlement catchment (radius 50 blocks from center)
        for s in self.world_spec.settlements:
            scx, scz = self.voxel_spec.tile_to_block_center(s.x, s.y)
            surface_y = self.voxel_spec.get_interpolated_height(scx, scz)

            placed_stone_wall = 0
            placed_housing_wood = 0
            excavated_quarry_mine = 0

            # Scan deltas in relevant chunks
            min_cx = (scx - 55) // 16
            max_cx = (scx + 55) // 16
            min_cz = (scz - 55) // 16
            max_cz = (scz + 55) // 16

            for cz in range(min_cz, max_cz + 1):
                for cx in range(min_cx, max_cx + 1):
                    c_edits = chunk_deltas.get((cx, cz), {})
                    for (gx, gy, gz), block_id in c_edits.items():
                        if (gx, gy, gz) in self.processed_blocks:
                            continue

                        dist = math.hypot(gx - scx, gz - scz)
                        if dist <= 50.0:
                            self.processed_blocks.add((gx, gy, gz))

                            if block_id == BLOCK_AIR:
                                # Block was mined / excavated
                                if gy < surface_y - 2:
                                    excavated_quarry_mine += 1
                            elif block_id in (BLOCK_STONE, BLOCK_COBBLESTONE):
                                # Placed stone fortification / wall
                                if gy >= surface_y:
                                    placed_stone_wall += 1
                            elif block_id in (BLOCK_OAK_PLANKS, BLOCK_OAK_WOOD):
                                # Placed residential wood
                                placed_housing_wood += 1

            # 1. Evaluate Wall Fortifications
            if placed_stone_wall >= 35:
                def_gain = min(0.8, round(placed_stone_wall * 0.012, 2))
                records.append(
                    ConstructionRecord(
                        settlement_id=s.id,
                        settlement_name=s.name,
                        construction_type="DefensiveFortification",
                        block_count=placed_stone_wall,
                        defensibility_delta=def_gain,
                        resource_bonuses={},
                        summary=(
                            f"The defenders of {s.name} completed substantial stone fortifications "
                            f"({placed_stone_wall} stone blocks placed), raising settlement defense by +{def_gain:.2f}."
                        ),
                    )
                )

            # 2. Evaluate Subterranean Mine Shafts
            if excavated_quarry_mine >= 25:
                ore_gain = round(excavated_quarry_mine * 0.4, 1)
                stone_gain = round(excavated_quarry_mine * 0.8, 1)
                records.append(
                    ConstructionRecord(
                        settlement_id=s.id,
                        settlement_name=s.name,
                        construction_type="MineShaft",
                        block_count=excavated_quarry_mine,
                        defensibility_delta=0.0,
                        resource_bonuses={"ore": ore_gain, "stone": stone_gain},
                        summary=(
                            f"A deep mining excavation at {s.name} cleared {excavated_quarry_mine} underground blocks, "
                            f"yielding +{ore_gain} raw ore and +{stone_gain} quarried stone."
                        ),
                    )
                )

            # 3. Evaluate Residential Expansion
            if placed_housing_wood >= 30:
                records.append(
                    ConstructionRecord(
                        settlement_id=s.id,
                        settlement_name=s.name,
                        construction_type="SettlementHousing",
                        block_count=placed_housing_wood,
                        defensibility_delta=0.0,
                        resource_bonuses={"wealth": 15.0},
                        summary=(
                            f"New timber buildings were erected in {s.name} ({placed_housing_wood} timber blocks), "
                            f"expanding residential living capacity and settlement wealth."
                        ),
                    )
                )

        return records

    def apply_records_to_simulation(self, records: Sequence[ConstructionRecord], sim: Any) -> int:
        """
        Applies evaluated construction records into the active Simulation instance:
        - Updates settlement defensibility score and economic stockpiles.
        - Appends macroscopic events into the event log.
        """
        applied = 0
        for rec in records:
            if rec.settlement_id in sim.settlements:
                s = sim.settlements[rec.settlement_id]
                # Apply defense update
                if rec.defensibility_delta > 0:
                    curr_def = getattr(s, "defensibility", getattr(s, "defensibility_score", 1.0))
                    if hasattr(s, "defensibility"):
                        s.defensibility = curr_def + rec.defensibility_delta
                    elif hasattr(s, "defensibility_score"):
                        s.defensibility_score = curr_def + rec.defensibility_delta

                # Apply resource bonuses
                for res, amt in rec.resource_bonuses.items():
                    if hasattr(s, res):
                        setattr(s, res, getattr(s, res) + amt)

                # Emit single macroscopic event to simulation
                from minemesis.core.types import EventType, Event
                evt = Event(
                    id=sim.event_log.next_id(),
                    tick=sim.tick,
                    type=EventType.COMMUNITY_CONSTRUCTION,
                    participants=[("settlement", s.id)],
                    description=rec.summary,
                    importance=1.4,
                )
                sim.event_log.append(evt)
                applied += 1

        return applied
