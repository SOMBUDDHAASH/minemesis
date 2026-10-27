"""
High-Performance Chunk Mesher with Face Culling, Vertex Ambient Occlusion, and Two-Pass Rendering.
"""

from __future__ import annotations
import moderngl
import numpy as np
from typing import List, Optional, Tuple

from engine.render.texture import TextureAtlas
from engine.world.block_registry import registry
from engine.world.chunk import Chunk


# Face Definitions: (dx, dy, dz, normal, vertex_offsets)
# Offset ordering: 4 quad vertices (0, 1, 2, 3)
FACES = [
    # 0. Top (+Y)
    (0, 1, 0, (0.0, 1.0, 0.0), ((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1))),
    # 1. Bottom (-Y)
    (0, -1, 0, (0.0, -1.0, 0.0), ((0, 0, 1), (1, 0, 1), (1, 0, 0), (0, 0, 0))),
    # 2. East (+X)
    (1, 0, 0, (1.0, 0.0, 0.0), ((1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0))),
    # 3. West (-X)
    (-1, 0, 0, (-1.0, 0.0, 0.0), ((0, 0, 1), (0, 0, 0), (0, 1, 0), (0, 1, 1))),
    # 4. North (+Z)
    (0, 0, 1, (0.0, 0.0, 1.0), ((1, 0, 1), (0, 0, 1), (0, 1, 1), (1, 1, 1))),
    # 5. South (-Z)
    (0, 0, -1, (0.0, 0.0, -1.0), ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0))),
]

# Block Texture Mappings (Defaults for quick UV lookup)
TEXTURE_OVERRIDES = {
    19: ("grass_top", "grass_side", "dirt"),  # Grass Turf (top, side, bottom)
    51: ("wood_log", "wood_log", "wood_log"), # Oak Log
    52: ("wood_planks", "wood_planks", "wood_planks"),
    89: ("stone_bricks", "stone_bricks", "stone_bricks"),
    97: ("glass", "glass", "glass"),
    100: ("wood_planks", "bookshelf", "wood_planks"),
    101: ("lectern", "wood_planks", "wood_planks"),
    136: ("water", "water", "water"),
}


def compute_vertex_ao(side1: bool, side2: bool, corner: bool) -> float:
    """Calculates vertex ambient occlusion factor: 0.0 (dark) to 1.0 (light)."""
    if side1 and side2:
        return 0.35  # Fully enclosed corner
    count = int(side1) + int(side2) + int(corner)
    if count == 3:
        return 0.45
    elif count == 2:
        return 0.65
    elif count == 1:
        return 0.85
    return 1.0


class ChunkMesher:
    """Builds ModernGL VAO/VBOs for a chunk column."""

    def __init__(self, ctx: moderngl.Context, atlas: TextureAtlas, program: moderngl.Program) -> None:
        self.ctx = ctx
        self.atlas = atlas
        self.program = program

    def build_mesh(self, chunk: Chunk) -> None:
        """Constructs opaque and transparent vertex arrays for the chunk."""
        opaque_verts: List[float] = []
        trans_verts: List[float] = []

        world_offset_x = chunk.cx * 16
        world_offset_z = chunk.cz * 16

        for y in range(0, 256):
            for z in range(16):
                for x in range(16):
                    bid = chunk.get_block(x, y, z)
                    if bid == 0:
                        continue

                    b_def = registry.get_by_id(bid)
                    is_trans = b_def.transparent if b_def else False
                    target_list = trans_verts if is_trans else opaque_verts

                    # Determine texture name per face
                    if bid in TEXTURE_OVERRIDES:
                        tex_top, tex_side, tex_bot = TEXTURE_OVERRIDES[bid]
                    else:
                        tname = b_def.texture if b_def else "limestone"
                        tex_top = tname
                        tex_side = tname
                        tex_bot = tname

                    # Check each of the 6 faces
                    for f_idx, (dx, dy, dz, normal, v_offs) in enumerate(FACES):
                        nx = x + dx
                        ny = y + dy
                        nz = z + dz

                        neighbor_bid = chunk.get_block(nx, ny, nz)
                        # Face culling: only draw if neighbor is air or transparent
                        if neighbor_bid != 0 and not registry.is_transparent(neighbor_bid):
                            continue
                        if is_trans and neighbor_bid == bid:
                            continue  # Cull identical adjacent transparent faces (e.g. water-water)

                        # Select texture for this face
                        if f_idx == 0:
                            tex_choice = tex_top
                        elif f_idx == 1:
                            tex_choice = tex_bot
                        else:
                            tex_choice = tex_side

                        u0, v0, u1, v1 = self.atlas.get_uv_rect(tex_choice)
                        norm_x, norm_y, norm_z = normal

                        # Quad vertices: 0, 1, 2, 3
                        # Triangle 1: (0, 1, 2), Triangle 2: (0, 2, 3)
                        q_pts = []
                        for ox, oy, oz in v_offs:
                            wx = world_offset_x + x + ox
                            wy = y + oy
                            wz = world_offset_z + z + oz
                            q_pts.append((wx, wy, wz))

                        # Push 6 vertices
                        # V0
                        target_list.extend([q_pts[0][0], q_pts[0][1], q_pts[0][2], u0, v0, norm_x, norm_y, norm_z, 1.0])
                        # V1
                        target_list.extend([q_pts[1][0], q_pts[1][1], q_pts[1][2], u1, v0, norm_x, norm_y, norm_z, 1.0])
                        # V2
                        target_list.extend([q_pts[2][0], q_pts[2][1], q_pts[2][2], u1, v1, norm_x, norm_y, norm_z, 1.0])
                        # V0
                        target_list.extend([q_pts[0][0], q_pts[0][1], q_pts[0][2], u0, v0, norm_x, norm_y, norm_z, 1.0])
                        # V2
                        target_list.extend([q_pts[2][0], q_pts[2][1], q_pts[2][2], u1, v1, norm_x, norm_y, norm_z, 1.0])
                        # V3
                        target_list.extend([q_pts[3][0], q_pts[3][1], q_pts[3][2], u0, v1, norm_x, norm_y, norm_z, 1.0])

        # Create or update GPU buffers
        if opaque_verts:
            raw_op = np.array(opaque_verts, dtype=np.float32).tobytes()
            vbo_op = self.ctx.buffer(raw_op)
            vao_op = self.ctx.vertex_array(
                self.program,
                [(vbo_op, "3f 2f 3f 1f", "in_position", "in_texcoord", "in_normal", "in_ao")],
            )
            chunk.opaque_mesh = (vao_op, len(opaque_verts) // 9)
        else:
            chunk.opaque_mesh = None

        if trans_verts:
            raw_tr = np.array(trans_verts, dtype=np.float32).tobytes()
            vbo_tr = self.ctx.buffer(raw_tr)
            vao_tr = self.ctx.vertex_array(
                self.program,
                [(vbo_tr, "3f 2f 3f 1f", "in_position", "in_texcoord", "in_normal", "in_ao")],
            )
            chunk.transparent_mesh = (vao_tr, len(trans_verts) // 9)
        else:
            chunk.transparent_mesh = None

        chunk.is_dirty = False
