"""
2D Text and HUD Profiling Overlay Renderer.
"""

from __future__ import annotations
import moderngl
import numpy as np

from engine.ui.font import BitmapFont


OVERLAY_VERT_SHADER = """
#version 330 core

layout (location = 0) in vec2 in_position;
layout (location = 1) in vec2 in_texcoord;
layout (location = 2) in vec4 in_color;

uniform mat4 u_ortho;

out vec2 v_texcoord;
out vec4 v_color;

void main() {
    v_texcoord = in_texcoord;
    v_color = in_color;
    gl_Position = u_ortho * vec4(in_position, 0.0, 1.0);
}
"""

OVERLAY_FRAG_SHADER = """
#version 330 core

in vec2 v_texcoord;
in vec4 v_color;

uniform sampler2D u_font_tex;
uniform int u_is_text;

out vec4 fragColor;

void main() {
    if (u_is_text == 1) {
        float alpha = texture(u_font_tex, v_texcoord).a;
        if (alpha < 0.1) discard;
        fragColor = vec4(v_color.rgb, v_color.a * alpha);
    } else {
        fragColor = v_color;
    }
}
"""


class OverlayRenderer:
    """Renders 2D HUD panels and profiling text on top of the 3D scene."""

    def __init__(self, ctx: moderngl.Context, width: int, height: int) -> None:
        self.ctx = ctx
        self.width = width
        self.height = height
        self.font = BitmapFont(ctx)

        self.program = ctx.program(
            vertex_shader=OVERLAY_VERT_SHADER,
            fragment_shader=OVERLAY_FRAG_SHADER,
        )

        # Dynamic vertex buffer (capacity: 2048 quads = 12288 vertices)
        self.max_quads = 2048
        # Each vertex: [x, y, u, v, r, g, b, a] (8 floats = 32 bytes)
        self.vbo = ctx.buffer(reserve=self.max_quads * 6 * 32, dynamic=True)
        self.vao = ctx.vertex_array(
            self.program,
            [(self.vbo, "2f 2f 4f", "in_position", "in_texcoord", "in_color")],
        )

        self.update_projection(width, height)

    def update_projection(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

        # Orthographic 2D projection (top-left is (0, 0))
        ortho = np.zeros((4, 4), dtype=np.float32)
        ortho[0, 0] = 2.0 / width
        ortho[1, 1] = -2.0 / height
        ortho[2, 2] = -1.0
        ortho[0, 3] = -1.0
        ortho[1, 3] = 1.0
        ortho[3, 3] = 1.0

        if "u_ortho" in self.program:
            self.program["u_ortho"].write(np.ascontiguousarray(ortho.T, dtype=np.float32).tobytes())

    def draw_rect(
        self,
        verts: list[float],
        x: float, y: float, w: float, h: float,
        color: tuple[float, float, float, float],
    ) -> None:
        r, g, b, a = color
        x1, y1 = x + w, y + h
        # Quad (2 triangles = 6 vertices)
        verts.extend([
            x, y, 0.0, 0.0, r, g, b, a,
            x1, y, 1.0, 0.0, r, g, b, a,
            x1, y1, 1.0, 1.0, r, g, b, a,
            x, y, 0.0, 0.0, r, g, b, a,
            x1, y1, 1.0, 1.0, r, g, b, a,
            x, y1, 0.0, 1.0, r, g, b, a,
        ])

    def draw_text(
        self,
        verts: list[float],
        text: str,
        x: float, y: float,
        color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    ) -> None:
        cur_x = x
        r, g, b, a = color
        cw = self.font.char_w
        ch = self.font.char_h

        for char in text:
            if char in self.font.char_uvs:
                u0, v0, u1, v1 = self.font.char_uvs[char]
                x1 = cur_x + cw
                y1 = y + ch
                verts.extend([
                    cur_x, y, u0, v0, r, g, b, a,
                    x1, y, u1, v0, r, g, b, a,
                    x1, y1, u1, v1, r, g, b, a,
                    cur_x, y, u0, v0, r, g, b, a,
                    x1, y1, u1, v1, r, g, b, a,
                    cur_x, y1, u0, v1, r, g, b, a,
                ])
            cur_x += cw

    def render_crosshair(self) -> None:
        """Renders a centered screen crosshair."""
        cx = self.width / 2.0
        cy = self.height / 2.0
        verts: list[float] = []
        # Horizontal bar (16x2)
        self.draw_rect(verts, cx - 8.0, cy - 1.0, 16.0, 2.0, (1.0, 1.0, 1.0, 0.85))
        # Vertical bar (2x16)
        self.draw_rect(verts, cx - 1.0, cy - 8.0, 2.0, 16.0, (1.0, 1.0, 1.0, 0.85))

        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.BLEND)
        if "u_is_text" in self.program:
            self.program["u_is_text"].value = 0
        raw_bg = np.array(verts, dtype=np.float32).tobytes()
        self.vbo.write(raw_bg)
        self.vao.render(moderngl.TRIANGLES, vertices=len(verts) // 8)
        self.ctx.enable(moderngl.DEPTH_TEST)

    def render_overlay(self, lines: list[str]) -> None:
        if not lines:
            return

        bg_verts: list[float] = []
        text_verts: list[float] = []

        # Background box dimensions
        pad_x, pad_y = 12.0, 10.0
        line_h = 18.0
        max_chars = max(len(l) for l in lines)
        box_w = max_chars * self.font.char_w + pad_x * 2
        box_h = len(lines) * line_h + pad_y * 2

        self.draw_rect(bg_verts, 12.0, 12.0, box_w, box_h, (0.05, 0.08, 0.12, 0.85))

        for i, line in enumerate(lines):
            col = (0.22, 0.74, 0.98, 1.0) if i == 0 else (0.9, 0.93, 0.96, 1.0)
            self.draw_text(text_verts, line, 12.0 + pad_x, 12.0 + pad_y + i * line_h, col)

        # Disable depth testing for 2D UI overlay
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.BLEND)

        # 1. Render Background Rect
        if bg_verts:
            if "u_is_text" in self.program:
                self.program["u_is_text"].value = 0
            raw_bg = np.array(bg_verts, dtype=np.float32).tobytes()
            self.vbo.write(raw_bg)
            self.vao.render(moderngl.TRIANGLES, vertices=len(bg_verts) // 8)

        # 2. Render Text Glyphs
        if text_verts:
            self.font.bind(unit=1)
            if "u_font_tex" in self.program:
                self.program["u_font_tex"].value = 1
            if "u_is_text" in self.program:
                self.program["u_is_text"].value = 1
            raw_text = np.array(text_verts, dtype=np.float32).tobytes()
            self.vbo.write(raw_text)
            self.vao.render(moderngl.TRIANGLES, vertices=len(text_verts) // 8)

        # Restore depth testing
        self.ctx.enable(moderngl.DEPTH_TEST)

    def render_centered_overlay(
        self,
        lines: list[str],
        title_color: tuple[float, float, float, float] = (1.0, 0.85, 0.25, 1.0),
        body_color: tuple[float, float, float, float] = (0.92, 0.94, 0.96, 1.0),
        bg_color: tuple[float, float, float, float] = (0.04, 0.06, 0.10, 0.92),
    ) -> None:
        if not lines:
            return

        bg_verts: list[float] = []
        text_verts: list[float] = []

        pad_x, pad_y = 24.0, 20.0
        line_h = 20.0
        max_chars = max(len(l) for l in lines)
        box_w = max_chars * self.font.char_w + pad_x * 2
        box_h = len(lines) * line_h + pad_y * 2

        # Center in window
        start_x = max(20.0, (self.width - box_w) / 2.0)
        start_y = max(20.0, (self.height - box_h) / 2.0)

        self.draw_rect(bg_verts, start_x, start_y, box_w, box_h, bg_color)

        for i, line in enumerate(lines):
            col = title_color if i == 0 else body_color
            self.draw_text(text_verts, line, start_x + pad_x, start_y + pad_y + i * line_h, col)

        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.BLEND)

        if bg_verts:
            if "u_is_text" in self.program:
                self.program["u_is_text"].value = 0
            raw_bg = np.array(bg_verts, dtype=np.float32).tobytes()
            self.vbo.write(raw_bg)
            self.vao.render(moderngl.TRIANGLES, vertices=len(bg_verts) // 8)

        if text_verts:
            self.font.bind(unit=1)
            if "u_font_tex" in self.program:
                self.program["u_font_tex"].value = 1
            if "u_is_text" in self.program:
                self.program["u_is_text"].value = 1
            raw_text = np.array(text_verts, dtype=np.float32).tobytes()
            self.vbo.write(raw_text)
            self.vao.render(moderngl.TRIANGLES, vertices=len(text_verts) // 8)

        self.ctx.enable(moderngl.DEPTH_TEST)
