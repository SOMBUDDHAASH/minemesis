"""
Voxel Intermediate Representation (VoxelSpec) for Milestone T1.

Defines:
- 16 Core Block Types with Minecraft Java resource mappings.
- Coordinate transformation between tile space (300x300) and voxel space (2400x2400 blocks).
- Bilinear terrain heightmap interpolation with organic sub-tile noise.
- Deterministic 3D Cave thresholding and depth-based ore distributions.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Optional, Sequence

from minemesis.systems.world_spec import WorldSpec, SettlementSite
from minemesis.terrain.noise import int_hash_2d, int_hash_3d
from minemesis.terrain.terrain_engine import (
    BIOME_BEACH,
    BIOME_DESERT,
    BIOME_FOREST,
    BIOME_GRASSLAND,
    BIOME_HILLS,
    BIOME_MOUNTAIN,
    BIOME_OCEAN,
    BIOME_SNOW,
    BIOME_SWAMP,
    BIOME_TAIGA,
    SEA_LEVEL,
    TerrainGrid,
    generate_terrain,
)


# Block Constants
BLOCK_AIR = 0
BLOCK_STONE = 1
BLOCK_DIRT = 2
BLOCK_GRASS_BLOCK = 3
BLOCK_OAK_WOOD = 4
BLOCK_OAK_LEAVES = 5
BLOCK_WATER = 6
BLOCK_SAND = 7
BLOCK_GRAVEL = 8
BLOCK_COAL_ORE = 9
BLOCK_IRON_ORE = 10
BLOCK_GOLD_ORE = 11
BLOCK_BEDROCK = 12
BLOCK_COBBLESTONE = 13
BLOCK_OAK_PLANKS = 14
BLOCK_SNOW_BLOCK = 15
BLOCK_DEEPSLATE = 16

BLOCK_NAMES: dict[int, str] = {
    BLOCK_AIR: "minecraft:air",
    BLOCK_STONE: "minecraft:stone",
    BLOCK_DIRT: "minecraft:dirt",
    BLOCK_GRASS_BLOCK: "minecraft:grass_block",
    BLOCK_OAK_WOOD: "minecraft:oak_log",
    BLOCK_OAK_LEAVES: "minecraft:oak_leaves",
    BLOCK_WATER: "minecraft:water",
    BLOCK_SAND: "minecraft:sand",
    BLOCK_GRAVEL: "minecraft:gravel",
    BLOCK_COAL_ORE: "minecraft:coal_ore",
    BLOCK_IRON_ORE: "minecraft:iron_ore",
    BLOCK_GOLD_ORE: "minecraft:gold_ore",
    BLOCK_BEDROCK: "minecraft:bedrock",
    BLOCK_COBBLESTONE: "minecraft:cobblestone",
    BLOCK_OAK_PLANKS: "minecraft:oak_planks",
    BLOCK_SNOW_BLOCK: "minecraft:snow_block",
    BLOCK_DEEPSLATE: "minecraft:deepslate",
}

# Solid blocks that have physical collision
SOLID_BLOCKS: frozenset[int] = frozenset({
    BLOCK_STONE,
    BLOCK_DIRT,
    BLOCK_GRASS_BLOCK,
    BLOCK_OAK_WOOD,
    BLOCK_OAK_LEAVES,
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
})

# Voxel World Dimensions
BLOCK_SCALE = 8  # 1 tile = 8x8 blocks
WORLD_TILES = 300
WORLD_BLOCKS_X = WORLD_TILES * BLOCK_SCALE  # 2400 blocks
WORLD_BLOCKS_Z = WORLD_TILES * BLOCK_SCALE  # 2400 blocks
WORLD_HEIGHT_Y = 256                         # 0 to 255
SEA_LEVEL_Y = 64                             # Sea level block height


@dataclass
class VoxelWorldSpec:
    """
    Adapter and spatial query provider converting macro WorldSpec into 3D voxel parameters.
    """
    world_spec: WorldSpec
    grid: TerrainGrid = field(init=False)
    block_scale: int = BLOCK_SCALE
    sea_level: int = SEA_LEVEL_Y

    def __post_init__(self) -> None:
        # Reconstruct or reuse 300x300 terrain grid deterministically from world_seed
        self.grid = generate_terrain(
            world_seed=self.world_spec.world_seed,
            width=self.world_spec.map_width,
            height=self.world_spec.map_height,
        )

    def block_to_tile(self, bx: int, bz: int) -> tuple[int, int]:
        """Converts block coordinates to tile coordinates."""
        tx = max(0, min(self.grid.width - 1, bx // self.block_scale))
        tz = max(0, min(self.grid.height - 1, bz // self.block_scale))
        return tx, tz

    def tile_to_block_center(self, tx: int, tz: int) -> tuple[int, int]:
        """Converts tile coordinates to center block coordinates."""
        return tx * self.block_scale + (self.block_scale // 2), tz * self.block_scale + (self.block_scale // 2)

    def get_interpolated_height(self, bx: int, bz: int) -> int:
        """
        Bilinearly interpolates surface block elevation (y: 0..255) from the 4 surrounding tiles
        plus high-frequency sub-block noise for natural rolling terrain.
        """
        fx = bx / float(self.block_scale)
        fz = bz / float(self.block_scale)

        tx0 = int(fx)
        tz0 = int(fz)
        tx1 = min(self.grid.width - 1, tx0 + 1)
        tz1 = min(self.grid.height - 1, tz0 + 1)

        tx0 = max(0, min(self.grid.width - 1, tx0))
        tz0 = max(0, min(self.grid.height - 1, tz0))

        u = fx - tx0
        v = fz - tz0

        e00 = self.grid.elevation[self.grid.index(tx0, tz0)]
        e10 = self.grid.elevation[self.grid.index(tx1, tz0)]
        e01 = self.grid.elevation[self.grid.index(tx0, tz1)]
        e11 = self.grid.elevation[self.grid.index(tx1, tz1)]

        # Bilinear blend
        elev_tile = (1.0 - u) * (1.0 - v) * e00 + u * (1.0 - v) * e10 + (1.0 - u) * v * e01 + u * v * e11

        # High-frequency integer hash sub-noise (-2 to +2 blocks variation)
        sub_hash = int_hash_2d(self.world_spec.world_seed, bx, bz, salt=83)
        sub_noise = ((sub_hash % 5) - 2) * 0.75

        # Sea / ocean clamp
        if e00 <= SEA_LEVEL and e10 <= SEA_LEVEL and e01 <= SEA_LEVEL and e11 <= SEA_LEVEL:
            return min(self.sea_level - 1, int(elev_tile * 0.95))

        # Map to block height (0..255)
        # Tile elevation 64 = block 64, tile 255 = block 220
        block_y = int(elev_tile + sub_noise)
        return max(5, min(250, block_y))

    def is_river_block(self, bx: int, bz: int) -> bool:
        """Determines if a block is inside an active riverbed."""
        tx, tz = self.block_to_tile(bx, bz)
        flow = self.grid.river_flow[self.grid.index(tx, tz)]
        if flow <= 0:
            return False

        width = self.grid.river_width[self.grid.index(tx, tz)]
        # Center of tile
        cx, cz = self.tile_to_block_center(tx, tz)
        dx = abs(bx - cx)
        dz = abs(bz - cz)
        return (dx <= width * 2 and dz <= width * 2)

    def is_road_block(self, bx: int, bz: int) -> bool:
        """Determines if a block lies on a paved trade road."""
        tx, tz = self.block_to_tile(bx, bz)
        # Check if tile has a road passing through
        for road in self.world_spec.roads:
            r_path = road.get("path", []) if isinstance(road, dict) else getattr(road, "path", [])
            for rx, ry in r_path:
                if rx == tx and ry == tz:
                    cx, cz = self.tile_to_block_center(tx, tz)
                    if abs(bx - cx) <= 2 and abs(bz - cz) <= 2:
                        return True
        return False

    def is_cave_voxel(self, bx: int, by: int, bz: int, surface_y: int) -> bool:
        """
        Determines 3D subterranean cave hollows using 3D integer noise.
        Caves only spawn between y=8 and surface_y - 4.
        """
        if by <= 6 or by >= surface_y - 3:
            return False

        # Multi-frequency 3D thresholding
        h1 = int_hash_3d(self.world_spec.world_seed, bx // 4, by // 4, bz // 4, salt=131)
        if (h1 % 1000) < 68:  # 6.8% cave density creates connected tunnels
            # Check secondary noise for organic cavern shape
            h2 = int_hash_3d(self.world_spec.world_seed, bx // 2, by // 2, bz // 2, salt=149)
            if (h2 % 100) < 65:
                return True
        return False

    def get_underground_block(self, bx: int, by: int, bz: int, ore_richness: int) -> int:
        """
        Returns underground stone, deepslate, or ore block based on depth and tile richness.
        """
        if by <= 2:
            return BLOCK_BEDROCK
        if by <= 16:
            base_rock = BLOCK_DEEPSLATE
        else:
            base_rock = BLOCK_STONE

        # Ore generation via keyed 3D hash
        h = int_hash_3d(self.world_spec.world_seed, bx, by, bz, salt=211)
        r_mult = max(1.0, ore_richness / 100.0)

        # Gold Ore (rare, deep: y=5..32)
        if 5 <= by <= 32 and (h % 1000) < int(8 * r_mult):
            return BLOCK_GOLD_ORE

        # Iron Ore (uncommon, mid-depth: y=8..64)
        if 8 <= by <= 64 and (h % 1000) < int(24 * r_mult):
            return BLOCK_IRON_ORE

        # Coal Ore (common: y=20..128)
        if 20 <= by <= 128 and (h % 1000) < int(45 * r_mult):
            return BLOCK_COAL_ORE

        # Gravel pockets
        if (h % 1000) < 15:
            return BLOCK_GRAVEL

        return base_rock

    def get_surface_block_id(self, biome: int, y: int, surface_y: int) -> int:
        """Determines top layer block (grass, sand, snow, water) based on biome."""
        depth = surface_y - y

        if biome == BIOME_DESERT or biome == BIOME_BEACH:
            return BLOCK_SAND

        if biome == BIOME_SNOW:
            return BLOCK_SNOW_BLOCK if depth == 0 else BLOCK_DIRT

        if biome == BIOME_MOUNTAIN:
            if surface_y > 185:
                return BLOCK_SNOW_BLOCK if depth == 0 else BLOCK_STONE
            return BLOCK_STONE if depth == 0 else BLOCK_GRAVEL

        # Grasslands, Forests, Taiga, Swamps
        if depth == 0:
            return BLOCK_GRASS_BLOCK
        elif depth <= 3:
            return BLOCK_DIRT
        else:
            return BLOCK_STONE
