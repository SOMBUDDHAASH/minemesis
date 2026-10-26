"""
Minemesis Voxel Translation and Engine Package (Milestone T1).

Translates macro WorldSpec continental geography into a 3D block-level voxel world:
- Block scale: 1 tile = 8 blocks (2400x2400 block continent).
- Deterministic heightmap interpolation, 3D cave noise, and ore veins.
- Standalone Voxel Game Engine with 3D player movement, voxel collision, and raycasting.
- Chunk delta tracker and Two-Way Construction Analysis interface.
- Minecraft Java (1.20/1.21 Anvil .mca) Region Exporter.
"""

from __future__ import annotations

from translators.voxel.voxelspec import (
    BLOCK_AIR,
    BLOCK_STONE,
    BLOCK_DIRT,
    BLOCK_GRASS_BLOCK,
    BLOCK_OAK_WOOD,
    BLOCK_OAK_LEAVES,
    BLOCK_WATER,
    BLOCK_SAND,
    BLOCK_GRAVEL,
    BLOCK_COAL_ORE,
    BLOCK_IRON_ORE,
    BLOCK_GOLD_ORE,
    BLOCK_BEDROCK,
    BLOCK_COBBLESTONE,
    BLOCK_OAK_PLANKS,
    BLOCK_SNOW_BLOCK,
    BLOCK_DEEPSLATE,
    BLOCK_NAMES,
    VoxelWorldSpec,
)
from translators.voxel.chunk_generator import ChunkData, generate_chunk
from translators.voxel.game_engine import VoxelGameEngine, PlayerEntity
from translators.voxel.construction_analyzer import ConstructionAnalyzer, ConstructionRecord
from translators.voxel.minecraft_export import (
    export_settlement_region_to_anvil,
    export_full_world_to_anvil,
)

__all__ = [
    "BLOCK_AIR",
    "BLOCK_STONE",
    "BLOCK_DIRT",
    "BLOCK_GRASS_BLOCK",
    "BLOCK_OAK_WOOD",
    "BLOCK_OAK_LEAVES",
    "BLOCK_WATER",
    "BLOCK_SAND",
    "BLOCK_GRAVEL",
    "BLOCK_COAL_ORE",
    "BLOCK_IRON_ORE",
    "BLOCK_GOLD_ORE",
    "BLOCK_BEDROCK",
    "BLOCK_COBBLESTONE",
    "BLOCK_OAK_PLANKS",
    "BLOCK_SNOW_BLOCK",
    "BLOCK_DEEPSLATE",
    "BLOCK_NAMES",
    "VoxelWorldSpec",
    "ChunkData",
    "generate_chunk",
    "VoxelGameEngine",
    "PlayerEntity",
    "ConstructionAnalyzer",
    "ConstructionRecord",
    "export_settlement_region_to_anvil",
    "export_full_world_to_anvil",
]
