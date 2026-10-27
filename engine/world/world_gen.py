"""
Deterministic Procedural Voxel Chunk Generation from WorldSpec.
Consumes continental terrain, biomes, river networks, settlements, and architectural blueprints.
"""

from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

from minemesis.systems.world_spec import WorldSpec, SettlementSite
from minemesis.terrain.terrain_engine import BIOME_NAMES, SEA_LEVEL
from engine.world.block_registry import registry
from engine.world.chunk import Chunk, CHUNK_WIDTH, CHUNK_DEPTH, CHUNK_HEIGHT


# Coordinate scaling: 1 macro tile = 8x8 voxel blocks
BLOCK_SCALE = 8


class WorldGenerator:
    """Generates 16x16x256 voxel chunks deterministically from WorldSpec."""

    def __init__(self, world_spec: WorldSpec) -> None:
        self.world_spec = world_spec
        self.grid = None
        self._load_terrain_grid()
        self._load_biome_palettes()
        self._load_blueprints()

        # Cache block IDs
        self.id_air = 0
        self.id_water = registry.get_by_name("Fresh River Water").id if registry.get_by_name("Fresh River Water") else 1
        self.id_ocean_water = registry.get_by_name("Deep Ocean Water").id if registry.get_by_name("Deep Ocean Water") else self.id_water
        self.id_bedrock = registry.get_by_name("Basalt").id if registry.get_by_name("Basalt") else 1
        self.id_deepslate = registry.get_by_name("Deepslate Basalt").id if registry.get_by_name("Deepslate Basalt") else 1
        self.id_cobble = registry.get_by_name("Cobblestone Pavement").id if registry.get_by_name("Cobblestone Pavement") else 1
        self.id_gravel = registry.get_by_name("River Gravel").id if registry.get_by_name("River Gravel") else 1

    def _load_terrain_grid(self) -> None:
        from minemesis.terrain.terrain_engine import generate_terrain
        self.grid = generate_terrain(
            world_seed=self.world_spec.world_seed,
            width=self.world_spec.map_width,
            height=self.world_spec.map_height,
        )

    def _load_biome_palettes(self) -> None:
        import sys
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent))
        p = base / "data" / "biome_palettes.json"
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.biomes_data: Dict[str, dict] = data.get("biomes", {})

    def _load_blueprints(self) -> None:
        import sys
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent))
        bp_dir = base / "data" / "blueprints"
        self.blueprints: Dict[str, dict] = {}
        if bp_dir.is_dir():
            for f in bp_dir.glob("*.json"):
                with open(f, "r", encoding="utf-8") as fp:
                    self.blueprints[f.stem] = json.load(fp)

    def block_to_tile(self, bx: int, bz: int) -> Tuple[int, int]:
        tx = max(0, min(self.grid.width - 1, bx // BLOCK_SCALE))
        tz = max(0, min(self.grid.height - 1, bz // BLOCK_SCALE))
        return tx, tz

    def get_interpolated_height(self, bx: int, bz: int) -> int:
        fx = bx / float(BLOCK_SCALE)
        fz = bz / float(BLOCK_SCALE)
        tx0 = int(fx)
        tz0 = int(fz)
        tx1 = min(self.grid.width - 1, tx0 + 1)
        tz1 = min(self.grid.height - 1, tz0 + 1)

        dx = fx - tx0
        dz = fz - tz0

        idx00 = self.grid.index(tx0, tz0)
        idx10 = self.grid.index(tx1, tz0)
        idx01 = self.grid.index(tx0, tz1)
        idx11 = self.grid.index(tx1, tz1)

        e00 = float(self.grid.elevation[idx00])
        e10 = float(self.grid.elevation[idx10])
        e01 = float(self.grid.elevation[idx01])
        e11 = float(self.grid.elevation[idx11])

        # Bilinear interpolation
        e_top = e00 * (1.0 - dx) + e10 * dx
        e_bot = e01 * (1.0 - dx) + e11 * dx
        macro_elev = e_top * (1.0 - dz) + e_bot * dz

        # Scale macro elevation (0..255) to realistic voxel height (30..190)
        base_h = 40.0 + (macro_elev / 255.0) * 125.0

        # Sub-tile noise for rolling natural contours
        h_noise = math.sin(bx * 0.12) * math.cos(bz * 0.12) * 2.2 + math.sin(bx * 0.05 + bz * 0.05) * 4.0
        return int(max(10, min(240, base_h + h_noise)))

    def generate_chunk(self, cx: int, cz: int) -> Chunk:
        chunk = Chunk(cx, cz)

        start_bx = cx * 16
        start_bz = cz * 16

        # Sea level block height
        sea_level_y = 62

        for lz in range(16):
            bz = start_bz + lz
            for lx in range(16):
                bx = start_bx + lx

                tile_x, tile_z = self.block_to_tile(bx, bz)
                t_idx = self.grid.index(tile_x, tile_z)
                biome_id = self.grid.biome[t_idx]
                biome_name = BIOME_NAMES[biome_id] if 0 <= biome_id < len(BIOME_NAMES) else "Grassland"
                is_river = (self.grid.river_flow[t_idx] > 0)

                b_data = self.biomes_data.get(biome_name, self.biomes_data.get("Grassland", {}))
                surf_name = b_data.get("surface_block", "Grass Turf")
                sub_name = b_data.get("subsurface_block", "Loam Dirt")
                stone_name = b_data.get("stone_base", "Limestone")

                id_surf = registry.get_by_name(surf_name).id if registry.get_by_name(surf_name) else 19
                id_sub = registry.get_by_name(sub_name).id if registry.get_by_name(sub_name) else 18
                id_stone = registry.get_by_name(stone_name).id if registry.get_by_name(stone_name) else 1

                terrain_y = self.get_interpolated_height(bx, bz)

                # River channel carving
                if is_river and terrain_y > sea_level_y:
                    terrain_y = max(sea_level_y - 2, terrain_y - 6)

                # 1. Fill Bedrock & Deepslate (y: 0..45)
                chunk.set_block(lx, 0, lz, self.id_bedrock, record_delta=False)
                chunk.set_block(lx, 1, lz, self.id_bedrock, record_delta=False)

                for y in range(2, min(terrain_y, 42)):
                    # Ore distribution in deep layer
                    h_val = (bx * 31 + y * 47 + bz * 71) % 1000
                    if h_val < 15:
                        chunk.set_block(lx, y, lz, 30, record_delta=False)  # Magnetite Iron
                    elif h_val < 25:
                        chunk.set_block(lx, y, lz, 35, record_delta=False)  # Gold Vein
                    else:
                        chunk.set_block(lx, y, lz, self.id_deepslate, record_delta=False)

                # 2. Main Rock Layer
                for y in range(42, max(42, terrain_y - 4)):
                    h_val = (bx * 19 + y * 29 + bz * 43) % 1000
                    if h_val < 25:
                        chunk.set_block(lx, y, lz, 27, record_delta=False)  # Coal Seam
                    elif h_val < 45:
                        chunk.set_block(lx, y, lz, 29, record_delta=False)  # Native Copper
                    else:
                        chunk.set_block(lx, y, lz, id_stone, record_delta=False)

                # 3. Subsurface Soil Layer (3 blocks)
                for y in range(max(1, terrain_y - 4), terrain_y):
                    chunk.set_block(lx, y, lz, id_sub, record_delta=False)

                # 4. Surface Block
                if terrain_y >= sea_level_y:
                    chunk.set_block(lx, terrain_y, lz, id_surf, record_delta=False)
                else:
                    # Underwater bed
                    chunk.set_block(lx, terrain_y, lz, self.id_gravel, record_delta=False)

                # 5. Water Fill up to Sea Level
                if terrain_y < sea_level_y:
                    water_id = self.id_ocean_water if biome_name == "Ocean" else self.id_water
                    for y in range(terrain_y + 1, sea_level_y + 1):
                        chunk.set_block(lx, y, lz, water_id, record_delta=False)

                # 6. Flora & Vegetation on Surface
                if terrain_y >= sea_level_y and lx % 3 == 0 and lz % 3 == 0:
                    flora_hash = (bx * 73 + bz * 97) % 100
                    if flora_hash < 25:
                        flora_list = b_data.get("flora_mix", [])
                        if flora_list:
                            f_name = flora_list[flora_hash % len(flora_list)][0]
                            f_b = registry.get_by_name(f_name)
                            if f_b:
                                chunk.set_block(lx, terrain_y + 1, lz, f_b.id, record_delta=False)

        # 7. Procedural Trees
        self._populate_trees(chunk, start_bx, start_bz)

        # 8. Settlement Architectural Blueprints (Pillars 11 & 12)
        self._populate_settlement_structures(chunk, start_bx, start_bz)

        # 9. Historical Ruins in Wilderness (Pillar 1)
        self._populate_historical_ruins(chunk, start_bx, start_bz)

        # 10. Subterranean Archaeological Crypts (Pillar 3)
        self._populate_archaeological_crypts(chunk, start_bx, start_bz)

        chunk.is_dirty = False
        return chunk

    def _populate_trees(self, chunk: Chunk, start_bx: int, start_bz: int) -> None:
        """Places procedural trees with solid trunks and foliage domes."""
        for lz in range(2, 14, 4):
            bz = start_bz + lz
            for lx in range(2, 14, 4):
                bx = start_bx + lx

                tile_x, tile_z = self.block_to_tile(bx, bz)
                t_idx = self.grid.index(tile_x, tile_z)
                biome_id = self.grid.biome[t_idx]
                biome_name = BIOME_NAMES[biome_id] if 0 <= biome_id < len(BIOME_NAMES) else "Grassland"

                tree_density = self.biomes_data.get(biome_name, {}).get("tree_density", 0.02)
                tree_hash = ((bx * 131 + bz * 179) % 1000) / 1000.0

                if tree_hash < tree_density:
                    surface_y = self.get_interpolated_height(bx, bz)
                    if surface_y < 63 or surface_y > 180:
                        continue

                    # Trunk (4 to 6 blocks high)
                    trunk_h = 4 + (bx % 3)
                    id_log = registry.get_by_name("Oak Log").id if registry.get_by_name("Oak Log") else 51
                    id_leaves = registry.get_by_name("Oak Leaves").id if registry.get_by_name("Oak Leaves") else 53

                    for th in range(1, trunk_h + 1):
                        chunk.set_block(lx, surface_y + th, lz, id_log, record_delta=False)

                    # Foliage Crown (3x3 foliage dome)
                    top_y = surface_y + trunk_h
                    for dy in range(0, 3):
                        radius = 2 if dy == 0 else 1
                        for dz in range(-radius, radius + 1):
                            for dx in range(-radius, radius + 1):
                                if dx == 0 and dz == 0 and dy == 0:
                                    continue
                                fx = lx + dx
                                fz = lz + dz
                                fy = top_y + dy
                                if 0 <= fx < 16 and 0 <= fz < 16 and fy < 256:
                                    chunk.set_block(fx, fy, fz, id_leaves, record_delta=False)

    def _populate_settlement_structures(self, chunk: Chunk, start_bx: int, start_bz: int) -> None:
        """
        Pastes settlement architectural blueprints.
        Pillar 11: Settlements evolve physically based on defensibility, wealth, and ore richness.
        Pillar 12: Geography shapes culture (mountain stone vs river timber).
        """
        for s in self.world_spec.settlements:
            sc_x = s.x * BLOCK_SCALE + 4
            sc_z = s.y * BLOCK_SCALE + 4

            dx = start_bx - sc_x
            dz = start_bz - sc_z
            dist_sq = dx * dx + dz * dz

            if dist_sq < 1400:
                # If high defensibility or near perimeter, prioritize watchtower & palisade
                if dist_sq > 700 and s.defensibility > 1.2:
                    bp_key = "watchtower_palisade"
                elif s.base_ore > 75 and (chunk.cx + chunk.cz) % 2 == 0:
                    bp_key = "craft_smithy"
                else:
                    slot_hash = (chunk.cx * 17 + chunk.cz * 31) % 8
                    bp_keys = [
                        "peasant_cottage",
                        "farmhouse_field",
                        "chieftain_longhouse",
                        "craft_smithy",
                        "village_shrine",
                        "town_archive",
                        "watchtower_palisade",
                        "village_well",
                    ]
                    bp_key = bp_keys[slot_hash]

                selected_bp = self.blueprints.get(bp_key)
                if not selected_bp:
                    continue

                origin_lx = 4
                origin_lz = 4
                base_bx = start_bx + origin_lx
                base_bz = start_bz + origin_lz
                base_y = self.get_interpolated_height(base_bx, base_bz)

                is_mountain = (s.site_type == "mountain" or base_y > 110)

                for b in selected_bp.get("blocks", []):
                    bx_off = b["x"]
                    by_off = b["y"]
                    bz_off = b["z"]
                    block_name = b["block"]

                    # Pillar 12: Mountain culture adapts planks to Cut Stone Bricks
                    if is_mountain and "Plank" in block_name:
                        block_name = "Cut Stone Bricks"

                    target_lx = origin_lx + bx_off
                    target_lz = origin_lz + bz_off
                    target_y = base_y + by_off

                    if 0 <= target_lx < 16 and 0 <= target_lz < 16 and target_y < 256:
                        b_def = registry.get_by_name(block_name)
                        if b_def:
                            chunk.set_block(target_lx, target_y, target_lz, b_def.id, record_delta=False)

    def _populate_historical_ruins(self, chunk: Chunk, start_bx: int, start_bz: int) -> None:
        """
        Pillar 1: Historical Ruins & Forgotten Shrines in Wilderness.
        Places ancient crumbled stone shrines and columns in uninhabited hills.
        """
        # Deterministic wilderness placement
        if (chunk.cx * 19 + chunk.cz * 37) % 31 != 0:
            return

        # Ensure far from any active settlement
        for s in self.world_spec.settlements:
            sc_x = s.x * BLOCK_SCALE + 4
            sc_z = s.y * BLOCK_SCALE + 4
            if (start_bx - sc_x) ** 2 + (start_bz - sc_z) ** 2 < 2500:
                return

        surf_y = self.get_interpolated_height(start_bx + 8, start_bz + 8)
        if surf_y < 65 or surf_y > 190:
            return

        id_rubble = registry.get_by_name("Fieldstone Rubble").id if registry.get_by_name("Fieldstone Rubble") else 1
        id_cut = registry.get_by_name("Cut Stone Bricks").id if registry.get_by_name("Cut Stone Bricks") else 89
        id_column = registry.get_by_name("Carved Stone Column").id if registry.get_by_name("Carved Stone Column") else 95
        id_lectern = registry.get_by_name("Scholar Lectern").id if registry.get_by_name("Scholar Lectern") else 101

        # Ruined 5x5 stone foundation
        for dx in range(6, 11):
            for dz in range(6, 11):
                chunk.set_block(dx, surf_y, dz, id_rubble, record_delta=False)
                if (dx in (6, 10) or dz in (6, 10)) and (dx + dz) % 2 == 0:
                    chunk.set_block(dx, surf_y + 1, dz, id_cut, record_delta=False)

        # Broken columns at corners
        chunk.set_block(6, surf_y + 1, 6, id_column, record_delta=False)
        chunk.set_block(6, surf_y + 2, 6, id_column, record_delta=False)
        chunk.set_block(10, surf_y + 1, 10, id_column, record_delta=False)

        # Central ancient altar / lectern
        chunk.set_block(8, surf_y + 1, 8, id_cut, record_delta=False)
        chunk.set_block(8, surf_y + 2, 8, id_lectern, record_delta=False)

    def _populate_archaeological_crypts(self, chunk: Chunk, start_bx: int, start_bz: int) -> None:
        """
        Pillar 3: Subterranean Archaeological Crypts & Lost Dynasty Vaults.
        Generates stone burial vaults containing sarcophagi and ancient knowledge archives.
        """
        if (chunk.cx * 23 + chunk.cz * 47) % 27 != 0:
            return

        crypt_y = 22  # Deep basalt stone layer
        id_basalt = registry.get_by_name("Basalt").id if registry.get_by_name("Basalt") else 1
        id_cobble = registry.get_by_name("Cobblestone Pavement").id if registry.get_by_name("Cobblestone Pavement") else 90
        id_shelf = registry.get_by_name("Town Archive Bookshelf").id if registry.get_by_name("Town Archive Bookshelf") else 100
        id_lectern = registry.get_by_name("Scholar Lectern").id if registry.get_by_name("Scholar Lectern") else 101

        # Carve 6x4x6 vault
        for lx in range(5, 11):
            for lz in range(5, 11):
                # Floor
                chunk.set_block(lx, crypt_y, lz, id_cobble, record_delta=False)
                # Air interior
                chunk.set_block(lx, crypt_y + 1, lz, 0, record_delta=False)
                chunk.set_block(lx, crypt_y + 2, lz, 0, record_delta=False)
                # Ceiling
                chunk.set_block(lx, crypt_y + 3, lz, id_basalt, record_delta=False)

                # Outer walls
                if lx in (5, 10) or lz in (5, 10):
                    chunk.set_block(lx, crypt_y + 1, lz, id_basalt, record_delta=False)
                    chunk.set_block(lx, crypt_y + 2, lz, id_basalt, record_delta=False)

        # Central stone tomb sarcophagus & ancient bookshelf
        chunk.set_block(8, crypt_y + 1, 7, id_cobble, record_delta=False)
        chunk.set_block(8, crypt_y + 1, 8, id_lectern, record_delta=False)
        chunk.set_block(6, crypt_y + 1, 8, id_shelf, record_delta=False)
