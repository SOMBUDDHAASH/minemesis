"""
Chunk Generation Engine for Milestone T1.

Generates 16x16x256 voxel chunks deterministically from VoxelWorldSpec:
- Subterranean Bedrock, Deepslate, Stone, and 3D Cave Systems.
- Depth-based Ore distribution (Coal, Iron, Gold).
- Biome Surface Layers, Ocean Water, Rivers, and Paved Roads.
- Organic Procedural Trees (Oak Logs + Leaves).
- Settlement Footprints, Buildings (Foundations, Plank Walls), and Perimeter Fortifications.
- Two-way Chunk Delta overrides for player block modifications.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Mapping, Optional, Sequence, Tuple

from minemesis.terrain.noise import int_hash_2d
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
)
from translators.voxel.voxelspec import (
    BLOCK_AIR,
    BLOCK_BEDROCK,
    BLOCK_COAL_ORE,
    BLOCK_COBBLESTONE,
    BLOCK_DEEPSLATE,
    BLOCK_DIRT,
    BLOCK_GOLD_ORE,
    BLOCK_GRASS_BLOCK,
    BLOCK_GRAVEL,
    BLOCK_IRON_ORE,
    BLOCK_OAK_LEAVES,
    BLOCK_OAK_PLANKS,
    BLOCK_OAK_WOOD,
    BLOCK_SAND,
    BLOCK_SNOW_BLOCK,
    BLOCK_STONE,
    BLOCK_WATER,
    VoxelWorldSpec,
)


CHUNK_SIZE_X = 16
CHUNK_SIZE_Z = 16
CHUNK_HEIGHT_Y = 256
CHUNK_VOXEL_COUNT = CHUNK_SIZE_X * CHUNK_SIZE_Z * CHUNK_HEIGHT_Y  # 65,536 blocks


@dataclass
class ChunkData:
    """
    Compact container representing a 16x16x256 voxel chunk.
    Stores block IDs in a single 64 KB flat bytearray.
    """
    cx: int
    cz: int
    voxels: bytearray = field(default_factory=lambda: bytearray(CHUNK_VOXEL_COUNT))

    @staticmethod
    def voxel_index(lx: int, ly: int, lz: int) -> int:
        """Layout index: (ly * 16 + lz) * 16 + lx"""
        return (ly * CHUNK_SIZE_Z + lz) * CHUNK_SIZE_X + lx

    def get_block(self, lx: int, ly: int, lz: int) -> int:
        if 0 <= lx < 16 and 0 <= ly < 256 and 0 <= lz < 16:
            return self.voxels[self.voxel_index(lx, ly, lz)]
        return BLOCK_AIR

    def set_block(self, lx: int, ly: int, lz: int, block_id: int) -> None:
        if 0 <= lx < 16 and 0 <= ly < 256 and 0 <= lz < 16:
            self.voxels[self.voxel_index(lx, ly, lz)] = block_id & 0xFF

    def get_highest_solid_y(self, lx: int, lz: int) -> int:
        for y in range(255, -1, -1):
            b = self.get_block(lx, y, lz)
            if b != BLOCK_AIR and b != BLOCK_WATER:
                return y
        return 0


def generate_chunk(
    cx: int,
    cz: int,
    spec: VoxelWorldSpec,
    deltas: Optional[Mapping[Tuple[int, int, int], int]] = None,
) -> ChunkData:
    """
    Generates a full 16x16x256 block chunk at chunk coordinates (cx, cz).
    Applies procedural terrain, depth layers, caves, trees, structures, and player deltas.
    """
    chunk = ChunkData(cx=cx, cz=cz)
    world_seed = spec.world_spec.world_seed

    bx_base = cx * 16
    bz_base = cz * 16

    # 1. Base Terrain Columns
    heights = [[0] * 16 for _ in range(16)]
    biomes = [[0] * 16 for _ in range(16)]
    ore_richness = [[0] * 16 for _ in range(16)]

    for lz in range(16):
        bz = bz_base + lz
        for lx in range(16):
            bx = bx_base + lx

            tx, tz = spec.block_to_tile(bx, bz)
            tile_idx = spec.grid.index(tx, tz)

            b_id = spec.grid.biome[tile_idx]
            biomes[lx][lz] = b_id
            ore_richness[lx][lz] = spec.grid.ore_richness[tile_idx]

            sy = spec.get_interpolated_height(bx, bz)
            heights[lx][lz] = sy

            # Fill vertical column
            for y in range(sy + 1):
                # 3D Caves (empty hollows)
                if spec.is_cave_voxel(bx, y, bz, sy):
                    continue

                if y == sy:
                    block = spec.get_surface_block_id(b_id, y, sy)
                elif y >= sy - 3:
                    # Near surface soil
                    if b_id in (BIOME_DESERT, BIOME_BEACH):
                        block = BLOCK_SAND
                    elif b_id in (BIOME_MOUNTAIN, BIOME_SNOW):
                        block = BLOCK_STONE
                    else:
                        block = BLOCK_DIRT
                else:
                    # Underground rock and ores
                    block = spec.get_underground_block(bx, y, bz, ore_richness[lx][lz])

                chunk.set_block(lx, y, lz, block)

            # Ocean / Lake Water Filling
            if sy < spec.sea_level:
                for y in range(sy + 1, spec.sea_level + 1):
                    chunk.set_block(lx, y, lz, BLOCK_WATER)

            # River Carving
            if spec.is_river_block(bx, bz):
                # Carve 2 blocks down and fill with water
                river_surf = max(spec.sea_level, sy)
                for ry in range(max(1, sy - 2), river_surf + 1):
                    chunk.set_block(lx, ry, lz, BLOCK_WATER)
                # Sandy/Gravel riverbed
                chunk.set_block(lx, max(1, sy - 3), lz, BLOCK_GRAVEL)

            # Road Paving
            if spec.is_road_block(bx, bz) and sy >= spec.sea_level:
                chunk.set_block(lx, sy, lz, BLOCK_COBBLESTONE)

    # 2. Vegetation (Trees)
    # Check if trees should spawn in this chunk
    for lz in range(2, 14, 3):
        bz = bz_base + lz
        for lx in range(2, 14, 3):
            bx = bx_base + lx
            b_id = biomes[lx][lz]
            sy = heights[lx][lz]

            if b_id in (BIOME_FOREST, BIOME_TAIGA, BIOME_SWAMP) and sy >= spec.sea_level:
                # Tree placement hash
                th = int_hash_2d(world_seed, bx, bz, salt=307)
                density = 45 if b_id == BIOME_FOREST else (35 if b_id == BIOME_TAIGA else 20)
                if (th % 100) < density:
                    # Place Oak/Spruce Tree
                    # Trunk: 4 blocks tall
                    for ty in range(1, 5):
                        chunk.set_block(lx, sy + ty, lz, BLOCK_OAK_WOOD)
                    # Leaves canopy
                    for dy in range(3, 6):
                        rad = 2 if dy < 5 else 1
                        for lox in range(-rad, rad + 1):
                            for loz in range(-rad, rad + 1):
                                if (lox * lox + loz * loz) <= (rad * rad + 1):
                                    if chunk.get_block(lx + lox, sy + dy, lz + loz) == BLOCK_AIR:
                                        chunk.set_block(lx + lox, sy + dy, lz + loz, BLOCK_OAK_LEAVES)

    # 3. Settlement Structures & Fortifications
    for s in spec.world_spec.settlements:
        scx, scz = spec.tile_to_block_center(s.x, s.y)
        # Check if settlement radius overlaps this chunk
        if abs(bx_base + 8 - scx) < 40 and abs(bz_base + 8 - scz) < 40:
            # Place settlement buildings
            _generate_settlement_features(chunk, bx_base, bz_base, scx, scz, s, spec)

    # 4. Player Chunk Deltas Overlay (Two-way interaction)
    if deltas:
        for (gx, gy, gz), block_id in deltas.items():
            if bx_base <= gx < bx_base + 16 and bz_base <= gz < bz_base + 16:
                chunk.set_block(gx - bx_base, gy, gz - bz_base, block_id)

    return chunk


def _generate_settlement_features(
    chunk: ChunkData,
    bx_base: int,
    bz_base: int,
    scx: int,
    scz: int,
    settlement: Any,
    spec: VoxelWorldSpec,
) -> None:
    """
    Constructs settlement footprints, buildings, and perimeter walls within chunk bounds.
    """
    # Deterministic building footprints around settlement center
    building_offsets = [
        (-12, -12), (8, -14), (-14, 10), (10, 10),
        (-22, -4), (18, -6), (-6, -22), (4, 20)
    ]

    for ox, oz in building_offsets:
        b_center_x = scx + ox
        b_center_z = scz + oz

        # Check if this 6x6 house intersects this chunk
        if bx_base <= b_center_x < bx_base + 16 and bz_base <= b_center_z < bz_base + 16:
            lx = b_center_x - bx_base
            lz = b_center_z - bz_base
            base_y = spec.get_interpolated_height(b_center_x, b_center_z)

            if base_y > spec.sea_level + 1:
                # 5x5 house structure
                for hx in range(-2, 3):
                    for hz in range(-2, 3):
                        clx = lx + hx
                        clz = lz + hz
                        if 0 <= clx < 16 and 0 <= clz < 16:
                            # Cobblestone foundation
                            chunk.set_block(clx, base_y, clz, BLOCK_COBBLESTONE)
                            # Oak Plank walls (height: 3)
                            is_wall = (abs(hx) == 2 or abs(hz) == 2)
                            for hy in range(1, 4):
                                if is_wall and not (hx == 0 and hz == 2 and hy <= 2):  # Doorway
                                    chunk.set_block(clx, base_y + hy, clz, BLOCK_OAK_PLANKS)
                                else:
                                    chunk.set_block(clx, base_y + hy, clz, BLOCK_AIR)
                            # Roof
                            chunk.set_block(clx, base_y + 4, clz, BLOCK_OAK_WOOD)

    # Defensive Perimeter Wall (if settlement has defensibility >= 1.5)
    def_score = getattr(settlement, "defensibility", getattr(settlement, "defensibility_score", 1.0))
    if def_score >= 1.4:
        wall_radius = 28
        for lx in range(16):
            gx = bx_base + lx
            for lz in range(16):
                gz = bz_base + lz
                dist = int(math.hypot(gx - scx, gz - scz))
                if dist == wall_radius or dist == wall_radius - 1:
                    sy = spec.get_interpolated_height(gx, gz)
                    if sy >= spec.sea_level:
                        # 4-block high defensive stone wall
                        for wy in range(sy + 1, sy + 5):
                            chunk.set_block(lx, wy, lz, BLOCK_COBBLESTONE)
