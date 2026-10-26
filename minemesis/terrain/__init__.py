"""
Minemesis Terrain & Geography Engine Package (Milestone T0).
"""

from minemesis.terrain.terrain_engine import (
    TerrainGrid,
    generate_terrain,
    BIOME_OCEAN,
    BIOME_BEACH,
    BIOME_GRASSLAND,
    BIOME_FOREST,
    BIOME_TAIGA,
    BIOME_SNOW,
    BIOME_DESERT,
    BIOME_SWAMP,
    BIOME_HILLS,
    BIOME_MOUNTAIN,
    BIOME_NAMES,
    SEA_LEVEL,
)
from minemesis.terrain.catchment import place_settlements, analyze_catchment
from minemesis.terrain.roads import astar_road, generate_road_network
from minemesis.terrain.world_provider_t0 import T0WorldProvider

__all__ = [
    "TerrainGrid",
    "generate_terrain",
    "place_settlements",
    "analyze_catchment",
    "astar_road",
    "generate_road_network",
    "T0WorldProvider",
    "BIOME_OCEAN",
    "BIOME_BEACH",
    "BIOME_GRASSLAND",
    "BIOME_FOREST",
    "BIOME_TAIGA",
    "BIOME_SNOW",
    "BIOME_DESERT",
    "BIOME_SWAMP",
    "BIOME_HILLS",
    "BIOME_MOUNTAIN",
    "BIOME_NAMES",
    "SEA_LEVEL",
]
