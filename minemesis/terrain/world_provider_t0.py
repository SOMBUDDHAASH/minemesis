"""
T0 Terrain World Provider for Minemesis.

Implements the WorldProvider interface to generate full 300x300 continental geography,
catchment-derived settlement endowments, and A* road networks from the world_seed.
Compresses terrain grids with zlib to keep memory strictly bounded.
"""

from __future__ import annotations
import zlib
from typing import Optional

from minemesis.systems.world_spec import SettlementSite, WorldSpec, WorldProvider
from minemesis.terrain.catchment import place_settlements
from minemesis.terrain.roads import generate_road_network
from minemesis.terrain.terrain_engine import generate_terrain, TerrainGrid


class T0WorldProvider(WorldProvider):
    """
    Milestone T0 Headless Terrain & Geography Engine.
    Generates 300x300 continent, 10 viable settlements, and road networks exclusively from world_seed.
    """

    def __init__(self, map_width: int = 300, map_height: int = 300, settlement_count: int = 10) -> None:
        self.map_width = map_width
        self.map_height = map_height
        self.settlement_count = settlement_count
        self._last_grid: Optional[TerrainGrid] = None

    def generate(self, world_seed: int, name_salt: int = 0) -> WorldSpec:
        # 1. Generate 300x300 terrain grid
        grid = generate_terrain(world_seed=world_seed, width=self.map_width, height=self.map_height)
        self._last_grid = grid

        # 2. Place 10 viable settlements based on catchment survival suitability
        sites = place_settlements(
            grid=grid,
            world_seed=world_seed,
            settlement_count=self.settlement_count,
            min_spacing=28,
        )

        # 3. Derive A* road network
        roads = generate_road_network(grid=grid, settlements=sites)

        # 4. Pack core terrain arrays into compressed bytes (elevation + biome + river_flow + travel_cost)
        # 4 arrays * 90,000 bytes = 360 KB uncompressed -> ~65 KB zlib compressed!
        raw_bytes = bytes(grid.elevation) + bytes(grid.biome) + bytes(grid.river_flow) + bytes(grid.travel_cost)
        compressed_terrain = zlib.compress(raw_bytes, level=6)

        spec = WorldSpec(
            world_seed=world_seed,
            map_width=self.map_width,
            map_height=self.map_height,
            settlements=tuple(sites),
            roads=tuple(roads),
            generator_version="T0",
            terrain_data=compressed_terrain,
        )
        return spec
