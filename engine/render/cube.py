"""
Textured 3D Voxel Cube Geometry for Stage E0 Bootstrap Spike.
"""

from __future__ import annotations
import math
import moderngl
import numpy as np

from engine.render.texture import TextureAtlas


class VoxelCubeMesh:
    """3D textured cube mesh with vertex normals and UV mappings."""

    def __init__(self, ctx: moderngl.Context, atlas: TextureAtlas) -> None:
        self.ctx = ctx
        self.atlas = atlas

        # Retrieve UV rectangles from atlas
        u_top = atlas.get_uv_rect("grass_top")
        u_side = atlas.get_uv_rect("grass_side")
        u_bot = atlas.get_uv_rect("dirt")

        # Each vertex: [x, y, z, u, v, nx, ny, nz, ao] (9 floats = 36 bytes)
        vertices: list[float] = []

        # Helper to push a quad (2 triangles = 6 vertices)
        def push_quad(v0, v1, v2, v3, uv_rect, normal):
            u0, v0_uv, u1, v1_uv = uv_rect
            nx, ny, nz = normal
            # Quad triangles: (0, 1, 2) and (0, 2, 3)
            quad_verts = [
                (*v0, u0, v0_uv, nx, ny, nz, 1.0),
                (*v1, u1, v0_uv, nx, ny, nz, 1.0),
                (*v2, u1, v1_uv, nx, ny, nz, 1.0),
                (*v0, u0, v0_uv, nx, ny, nz, 1.0),
                (*v2, u1, v1_uv, nx, ny, nz, 1.0),
                (*v3, u0, v1_uv, nx, ny, nz, 1.0),
            ]
            for v in quad_verts:
                vertices.extend(v)

        # 1. Top (+Y)
        push_quad(
            (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5),
            u_top, (0.0, 1.0, 0.0)
        )
        # 2. Bottom (-Y)
        push_quad(
            (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, -0.5, -0.5), (-0.5, -0.5, -0.5),
            u_bot, (0.0, -1.0, 0.0)
        )
        # 3. North (+Z)
        push_quad(
            (0.5, -0.5, 0.5), (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (0.5, 0.5, 0.5),
            u_side, (0.0, 0.0, 1.0)
        )
        # 4. South (-Z)
        push_quad(
            (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
            u_side, (0.0, 0.0, -1.0)
        )
        # 5. East (+X)
        push_quad(
            (0.5, -0.5, -0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (0.5, 0.5, -0.5),
            u_side, (1.0, 0.0, 0.0)
        )
        # 6. West (-X)
        push_quad(
            (-0.5, -0.5, 0.5), (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (-0.5, 0.5, 0.5),
            u_side, (-1.0, 0.0, 0.0)
        )

        v_data = np.array(vertices, dtype=np.float32)
        self.vbo = self.ctx.buffer(v_data.tobytes())
        self.vertex_count = len(vertices) // 9

    def create_vao(self, program: moderngl.Program) -> moderngl.VertexArray:
        # Buffer layout: 3f position, 2f texcoord, 3f normal, 1f ao
        return self.ctx.vertex_array(
            program,
            [(self.vbo, "3f 2f 3f 1f", "in_position", "in_texcoord", "in_normal", "in_ao")],
        )

    def render(self, vao: moderngl.VertexArray) -> None:
        vao.render(moderngl.TRIANGLES)
