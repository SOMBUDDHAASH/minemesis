"""
World Chunk Manager and Streaming Pipeline.
Handles chunk loading radius around player, meshing, and rendering.
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Set, Tuple
import moderngl

from minemesis.systems.world_spec import WorldSpec
from engine.render.texture import TextureAtlas
from engine.world.block_registry import registry
from engine.world.chunk import Chunk
from engine.world.mesher import ChunkMesher
from engine.world.world_gen import WorldGenerator


class ChunkManager:
    """Manages active voxel chunks, streaming radius, and GPU rendering passes."""

    def __init__(
        self,
        ctx: moderngl.Context,
        atlas: TextureAtlas,
        program: moderngl.Program,
        world_spec: WorldSpec,
        view_distance: int = 8,
    ) -> None:
        self.ctx = ctx
        self.atlas = atlas
        self.program = program
        self.world_spec = world_spec
        self.view_distance = view_distance

        self.generator = WorldGenerator(world_spec)
        self.mesher = ChunkMesher(ctx, atlas, program)

        self.chunks: Dict[Tuple[int, int], Chunk] = {}
        self.chunk_deltas: Dict[Tuple[int, int], Dict[Tuple[int, int, int], int]] = {}

    def get_chunk(self, cx: int, cz: int) -> Chunk:
        key = (cx, cz)
        if key not in self.chunks:
            chunk = self.generator.generate_chunk(cx, cz)
            # Re-apply any stored player chunk deltas
            if key in self.chunk_deltas:
                for (lx, y, lz), bid in self.chunk_deltas[key].items():
                    chunk.set_block(lx, y, lz, bid, record_delta=False)
            self.mesher.build_mesh(chunk)
            self.chunks[key] = chunk
        return self.chunks[key]

    def update_player_position(self, px: float, pz: float) -> None:
        """Loads chunks in view distance radius around player."""
        pcx = int(px) // 16
        pcz = int(pz) // 16
        vd = self.view_distance

        for dz in range(-vd, vd + 1):
            for dx in range(-vd, vd + 1):
                if dx * dx + dz * dz <= vd * vd:
                    self.get_chunk(pcx + dx, pcz + dz)

    def get_block_at(self, bx: int, by: int, bz: int) -> int:
        if by < 0 or by >= 256:
            return 0
        cx = bx // 16
        cz = bz // 16
        lx = bx % 16
        lz = bz % 16
        chunk = self.get_chunk(cx, cz)
        return chunk.get_block(lx, by, lz)

    def set_block_at(self, bx: int, by: int, bz: int, block_id: int) -> bool:
        if by < 0 or by >= 256:
            return False
        cx = bx // 16
        cz = bz // 16
        lx = bx % 16
        lz = bz % 16
        chunk = self.get_chunk(cx, cz)
        changed = chunk.set_block(lx, by, lz, block_id, record_delta=True)
        if changed:
            # Record in global chunk deltas
            key = (cx, cz)
            if key not in self.chunk_deltas:
                self.chunk_deltas[key] = {}
            self.chunk_deltas[key][(lx, by, lz)] = block_id

            # Re-mesh chunk
            self.mesher.build_mesh(chunk)
            return True
        return False

    def render(self, px: float, pz: float) -> int:
        """Renders all loaded chunk meshes. Returns total draw calls."""
        pcx = int(px) // 16
        pcz = int(pz) // 16
        vd = self.view_distance
        draw_calls = 0

        # Pass 1: Opaque Geometries (depth write ON)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.depth_func = "<="
        self.ctx.enable(moderngl.CULL_FACE)

        for (cx, cz), chunk in self.chunks.items():
            if abs(cx - pcx) <= vd and abs(cz - pcz) <= vd:
                if chunk.opaque_mesh:
                    vao, count = chunk.opaque_mesh
                    vao.render(moderngl.TRIANGLES, vertices=count)
                    draw_calls += 1

        # Pass 2: Transparent Geometries (water, leaves, glass)
        self.ctx.enable(moderngl.BLEND)
        for (cx, cz), chunk in self.chunks.items():
            if abs(cx - pcx) <= vd and abs(cz - pcz) <= vd:
                if chunk.transparent_mesh:
                    vao, count = chunk.transparent_mesh
                    vao.render(moderngl.TRIANGLES, vertices=count)
                    draw_calls += 1

        return draw_calls
