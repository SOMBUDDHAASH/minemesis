"""
Targeted Block Bounding Box Highlight, Face Normal Indicator, and Ghost Placement Preview.
"""

from __future__ import annotations
import math
from typing import Optional, Tuple
import moderngl
import numpy as np

from engine.render.camera import Camera3D


HIGHLIGHT_VERT_SHADER = """
#version 330 core
layout (location = 0) in vec3 in_position;
layout (location = 1) in vec4 in_color;

uniform mat4 u_proj;
uniform mat4 u_view;

out vec4 v_color;

void main() {
    v_color = in_color;
    gl_Position = u_proj * u_view * vec4(in_position, 1.0);
}
"""

HIGHLIGHT_FRAG_SHADER = """
#version 330 core
in vec4 v_color;
out vec4 fragColor;

void main() {
    fragColor = v_color;
}
"""


class BlockHighlightRenderer:
    """
    Renders:
    1. Targeted Block Bounding Box Outline (Lines with slight offset to prevent Z-fighting)
    2. Targeted Face Normal Highlight (Translucent Quad)
    3. Ghost Placement Preview (Translucent box at hit_pos + normal)
    """

    def __init__(self, ctx: moderngl.Context) -> None:
        self.ctx = ctx
        self.program = ctx.program(
            vertex_shader=HIGHLIGHT_VERT_SHADER,
            fragment_shader=HIGHLIGHT_FRAG_SHADER,
        )

        # Dynamic buffers for lines (12 lines = 24 vertices) and quads (6 faces = 36 vertices)
        # Vertex format: 3 floats position, 4 floats color = 7 floats (28 bytes)
        self.line_vbo = ctx.buffer(reserve=256 * 28, dynamic=True)
        self.line_vao = ctx.vertex_array(
            self.program,
            [(self.line_vbo, "3f 4f", "in_position", "in_color")],
        )

        self.quad_vbo = ctx.buffer(reserve=256 * 28, dynamic=True)
        self.quad_vao = ctx.vertex_array(
            self.program,
            [(self.quad_vbo, "3f 4f", "in_position", "in_color")],
        )

    def render_highlight(
        self,
        camera: Camera3D,
        hit_pos: Tuple[int, int, int],
        face_normal: Tuple[int, int, int],
        preview_block_id: Optional[int] = None,
        dig_progress: float = 0.0,
    ) -> None:
        bx, by, bz = hit_pos
        nx, ny, nz = face_normal

        # Expand box by 0.002 to avoid z-fighting with chunk terrain
        eps = 0.002
        x0, y0, z0 = bx - eps, by - eps, bz - eps
        x1, y1, z1 = bx + 1.0 + eps, by + 1.0 + eps, bz + 1.0 + eps

        # -------------------------------------------------------------
        # 1. Wireframe Bounding Box (12 lines = 24 vertices)
        # -------------------------------------------------------------
        line_verts: list[float] = []
        cr, cg, cb, ca = 0.1, 0.1, 0.1, 0.95  # Crisp dark outline

        def add_line(p0, p1, col=(cr, cg, cb, ca)):
            r, g, b, a = col
            line_verts.extend([p0[0], p0[1], p0[2], r, g, b, a])
            line_verts.extend([p1[0], p1[1], p1[2], r, g, b, a])

        # Bottom 4 edges
        add_line((x0, y0, z0), (x1, y0, z0))
        add_line((x1, y0, z0), (x1, y0, z1))
        add_line((x1, y0, z1), (x0, y0, z1))
        add_line((x0, y0, z1), (x0, y0, z0))

        # Top 4 edges
        add_line((x0, y1, z0), (x1, y1, z0))
        add_line((x1, y1, z0), (x1, y1, z1))
        add_line((x1, y1, z1), (x0, y1, z1))
        add_line((x0, y1, z1), (x0, y1, z0))

        # 4 Vertical edges
        add_line((x0, y0, z0), (x0, y1, z0))
        add_line((x1, y0, z0), (x1, y1, z0))
        add_line((x1, y0, z1), (x1, y1, z1))
        add_line((x0, y0, z1), (x0, y1, z1))

        # -------------------------------------------------------------
        # 2. Targeted Face Highlight Quad
        # -------------------------------------------------------------
        quad_verts: list[float] = []
        fr, fg, fb, fa = 0.2, 0.7, 1.0, 0.35  # Translucent cyan face

        def add_quad(p0, p1, p2, p3, col=(fr, fg, fb, fa)):
            r, g, b, a = col
            quad_verts.extend([
                p0[0], p0[1], p0[2], r, g, b, a,
                p1[0], p1[1], p1[2], r, g, b, a,
                p2[0], p2[1], p2[2], r, g, b, a,

                p0[0], p0[1], p0[2], r, g, b, a,
                p2[0], p2[1], p2[2], r, g, b, a,
                p3[0], p3[1], p3[2], r, g, b, a,
            ])

        f_eps = 0.003
        if ny > 0:  # Top
            add_quad((x0, y1 + f_eps, z0), (x1, y1 + f_eps, z0), (x1, y1 + f_eps, z1), (x0, y1 + f_eps, z1))
        elif ny < 0:  # Bottom
            add_quad((x0, y0 - f_eps, z1), (x1, y0 - f_eps, z1), (x1, y0 - f_eps, z0), (x0, y0 - f_eps, z0))
        elif nx > 0:  # East
            add_quad((x1 + f_eps, y0, z0), (x1 + f_eps, y0, z1), (x1 + f_eps, y1, z1), (x1 + f_eps, y1, z0))
        elif nx < 0:  # West
            add_quad((x0 - f_eps, y0, z1), (x0 - f_eps, y0, z0), (x0 - f_eps, y1, z0), (x0 - f_eps, y1, z1))
        elif nz > 0:  # North
            add_quad((x1, y0, z1 + f_eps), (x0, y0, z1 + f_eps), (x0, y1, z1 + f_eps), (x1, y1, z1 + f_eps))
        elif nz < 0:  # South
            add_quad((x0, y0, z0 - f_eps), (x1, y0, z0 - f_eps), (x1, y1, z0 - f_eps), (x0, y1, z0 - f_eps))

        # -------------------------------------------------------------
        # 3. Ghost Placement Preview Box (at hit_pos + normal)
        # -------------------------------------------------------------
        if preview_block_id and preview_block_id > 0:
            px0, py0, pz0 = bx + nx + 0.02, by + ny + 0.02, bz + nz + 0.02
            px1, py1, pz1 = bx + nx + 0.98, by + ny + 0.98, bz + nz + 0.98
            gr, gg, gb, ga = 0.3, 0.9, 0.4, 0.25  # Translucent green ghost preview

            # Add 6 ghost preview faces
            add_quad((px0, py1, pz0), (px1, py1, pz0), (px1, py1, pz1), (px0, py1, pz1), (gr, gg, gb, ga))
            add_quad((px0, py0, pz1), (px1, py0, pz1), (px1, py0, pz0), (px0, py0, pz0), (gr, gg, gb, ga))
            add_quad((px1, py0, pz0), (px1, py0, pz1), (px1, py1, pz1), (px1, py1, pz0), (gr, gg, gb, ga))
            add_quad((px0, py0, pz1), (px0, py0, pz0), (px0, py1, pz0), (px0, py1, pz1), (gr, gg, gb, ga))
            add_quad((px1, py0, pz1), (px0, py0, pz1), (px0, py1, pz1), (px1, py1, pz1), (gr, gg, gb, ga))
            add_quad((px0, py0, pz0), (px1, py0, pz0), (px1, py1, pz0), (px0, py1, pz0), (gr, gg, gb, ga))

            # Add ghost wireframe
            gcol = (0.2, 0.8, 0.3, 0.6)
            add_line((px0, py0, pz0), (px1, py0, pz0), gcol)
            add_line((px1, py0, pz0), (px1, py0, pz1), gcol)
            add_line((px1, py0, pz1), (px0, py0, pz1), gcol)
            add_line((px0, py0, pz1), (px0, py0, pz0), gcol)
            add_line((px0, py1, pz0), (px1, py1, pz0), gcol)
            add_line((px1, py1, pz0), (px1, py1, pz1), gcol)
            add_line((px1, py1, pz1), (px0, py1, pz1), gcol)
            add_line((px0, py1, pz1), (px0, py1, pz0), gcol)
            add_line((px0, py0, pz0), (px0, py1, pz0), gcol)
            add_line((px1, py0, p0 := z0), (px1, py1, p0), gcol)
            add_line((px1, py0, p1 := z1), (px1, py1, p1), gcol)
            add_line((px0, py0, p1), (px0, py1, p1), gcol)

        # -------------------------------------------------------------
        # 4. Progressive Mining Crack Lines (if dig_progress > 0.05)
        # -------------------------------------------------------------
        if dig_progress > 0.05:
            crk_col = (0.05, 0.05, 0.05, 0.98)
            if ny > 0:  # Top
                c0, c1, c2, c3 = (x0, y1 + f_eps, z0), (x1, y1 + f_eps, z0), (x1, y1 + f_eps, z1), (x0, y1 + f_eps, z1)
            elif ny < 0:  # Bottom
                c0, c1, c2, c3 = (x0, y0 - f_eps, z1), (x1, y0 - f_eps, z1), (x1, y0 - f_eps, z0), (x0, y0 - f_eps, z0)
            elif nx > 0:  # East
                c0, c1, c2, c3 = (x1 + f_eps, y0, z0), (x1 + f_eps, y0, z1), (x1 + f_eps, y1, z1), (x1 + f_eps, y1, z0)
            elif nx < 0:  # West
                c0, c1, c2, c3 = (x0 - f_eps, y0, z1), (x0 - f_eps, y0, z0), (x0 - f_eps, y1, z0), (x0 - f_eps, y1, z1)
            elif nz > 0:  # North
                c0, c1, c2, c3 = (x1, y0, z1 + f_eps), (x0, y0, z1 + f_eps), (x0, y1, z1 + f_eps), (x1, y1, z1 + f_eps)
            else:  # South
                c0, c1, c2, c3 = (x0, y0, z0 - f_eps), (x1, y0, z0 - f_eps), (x1, y1, z0 - f_eps), (x0, y1, z0 - f_eps)

            cx = (c0[0] + c1[0] + c2[0] + c3[0]) * 0.25
            cy = (c0[1] + c1[1] + c2[1] + c3[1]) * 0.25
            cz = (c0[2] + c1[2] + c2[2] + c3[2]) * 0.25
            fc = (cx, cy, cz)

            f_scale = min(1.0, dig_progress * 1.2)
            for corner in (c0, c1, c2, c3):
                target_pt = (
                    cx + (corner[0] - cx) * 0.65 * f_scale,
                    cy + (corner[1] - cy) * 0.65 * f_scale,
                    cz + (corner[2] - cz) * 0.65 * f_scale,
                )
                add_line(fc, target_pt, crk_col)

            if dig_progress > 0.40:
                m0 = ((c0[0] + c1[0]) * 0.5, (c0[1] + c1[1]) * 0.5, (c0[2] + c1[2]) * 0.5)
                m1 = ((c1[0] + c2[0]) * 0.5, (c1[1] + c2[1]) * 0.5, (c1[2] + c2[2]) * 0.5)
                m2 = ((c2[0] + c3[0]) * 0.5, (c2[1] + c3[1]) * 0.5, (c2[2] + c3[2]) * 0.5)
                m3 = ((c3[0] + c0[0]) * 0.5, (c3[1] + c0[1]) * 0.5, (c3[2] + c0[2]) * 0.5)
                add_line(fc, m0, crk_col)
                add_line(fc, m1, crk_col)
                add_line(fc, m2, crk_col)
                add_line(fc, m3, crk_col)

            if dig_progress > 0.70:
                add_line(c0, c2, crk_col)
                add_line(c1, c3, crk_col)

        # -------------------------------------------------------------
        # OpenGL Render Passes
        # -------------------------------------------------------------
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.depth_func = "<="
        self.ctx.enable(moderngl.BLEND)

        self.program["u_proj"].write(np.ascontiguousarray(camera.projection_matrix.T, dtype=np.float32).tobytes())
        self.program["u_view"].write(np.ascontiguousarray(camera.get_view_matrix().T, dtype=np.float32).tobytes())

        # Render translucent quads
        if quad_verts:
            raw_quads = np.array(quad_verts, dtype=np.float32).tobytes()
            self.quad_vbo.write(raw_quads)
            self.quad_vao.render(moderngl.TRIANGLES, vertices=len(quad_verts) // 7)

        # Render wireframe lines
        if line_verts:
            raw_lines = np.array(line_verts, dtype=np.float32).tobytes()
            self.line_vbo.write(raw_lines)
            self.line_vao.render(moderngl.LINES, vertices=len(line_verts) // 7)
