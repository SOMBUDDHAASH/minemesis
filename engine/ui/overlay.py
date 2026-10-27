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

    def get_inventory_slot_coords(self) -> list[tuple[str, any, float, float, float, float]]:
        """
        Returns list of (slot_type, slot_id, x, y, width, height) in screen pixel coordinates.
        Layout:
        - Equipment (head, chest, legs, offhand): 4 boxes along top row
        - Main Storage: 3 rows x 9 columns
        - Active Hotbar: 1 row x 9 columns along bottom
        """
        slots = []
        win_w = 620.0
        win_h = 430.0
        win_x = max(10.0, (self.width - win_w) / 2.0)
        win_y = max(10.0, (self.height - win_h) / 2.0)

        slot_w = 58.0
        slot_h = 44.0
        spacing = 6.0

        # 1. Equipment slots (top)
        eq_keys = ["head", "chest", "legs", "offhand"]
        eq_x = win_x + 36.0
        eq_y = win_y + 42.0
        for i, k in enumerate(eq_keys):
            sx = eq_x + i * (slot_w + 16.0)
            slots.append(("equipment", k, sx, eq_y, slot_w, slot_h))

        # 2. Main Storage (3 rows x 9 columns)
        grid_x = win_x + 24.0
        grid_y = win_y + 120.0
        for row in range(3):
            for col in range(9):
                idx = row * 9 + col
                sx = grid_x + col * (slot_w + spacing)
                sy = grid_y + row * (slot_h + spacing)
                slots.append(("main", idx, sx, sy, slot_w, slot_h))

        # 3. Hotbar (1 row x 9 columns)
        hotbar_y = win_y + 295.0
        for col in range(9):
            sx = grid_x + col * (slot_w + spacing)
            slots.append(("hotbar", col, sx, hotbar_y, slot_w, slot_h))

        return slots

    def get_inventory_slot_under_cursor(self, mouse_x: float, mouse_y: float) -> Optional[tuple[str, any]]:
        """Hit tests screen coordinates to determine which inventory slot was clicked/hovered."""
        for slot_type, slot_id, sx, sy, sw, sh in self.get_inventory_slot_coords():
            if sx <= mouse_x <= sx + sw and sy <= mouse_y <= sy + sh:
                return (slot_type, slot_id)
        return None

    def render_inventory_gui(self, inv: any, mouse_x: float = -1.0, mouse_y: float = -1.0) -> None:
        """
        Renders interactive Minecraft/Luanti-grade 2D graphical inventory GUI:
        - Equipment slots
        - 3x9 Main Grid
        - 1x9 Hotbar
        - Mouse hover highlighting
        - Item counts and labels
        - Floating tooltip card for hovered slot
        - Attached cursor stack for drag & drop
        """
        win_w = 620.0
        win_h = 430.0
        win_x = max(10.0, (self.width - win_w) / 2.0)
        win_y = max(10.0, (self.height - win_h) / 2.0)

        bg_verts: list[float] = []
        text_verts: list[float] = []

        # 1. Main Background Panel & Outer Border
        self.draw_rect(bg_verts, win_x - 3.0, win_y - 3.0, win_w + 6.0, win_h + 6.0, (0.18, 0.22, 0.30, 0.98))
        self.draw_rect(bg_verts, win_x, win_y, win_w, win_h, (0.05, 0.07, 0.11, 0.96))

        # Title
        self.draw_text(text_verts, "=== INVENTORY & EQUIPMENT ===", win_x + 24.0, win_y + 14.0, (0.22, 0.82, 1.0, 1.0))
        self.draw_text(text_verts, "Storage (3x9)", win_x + 24.0, win_y + 102.0, (0.75, 0.78, 0.82, 0.9))
        self.draw_text(text_verts, "Active Hotbar", win_x + 24.0, win_y + 276.0, (0.75, 0.78, 0.82, 0.9))

        hovered_slot = self.get_inventory_slot_under_cursor(mouse_x, mouse_y) if mouse_x >= 0 else None
        hovered_item = None

        # 2. Render Slots
        slot_coords = self.get_inventory_slot_coords()
        for slot_type, slot_id, sx, sy, sw, sh in slot_coords:
            is_hovered = (hovered_slot == (slot_type, slot_id))
            is_selected_hotbar = (slot_type == "hotbar" and slot_id == inv.selected_slot)
            item = inv.get_slot_item(slot_type, slot_id)

            if is_hovered:
                hovered_item = item

            # Slot border color
            if is_hovered:
                border_col = (0.35, 0.90, 1.0, 1.0)
            elif is_selected_hotbar:
                border_col = (1.0, 0.85, 0.20, 1.0)
            else:
                border_col = (0.22, 0.25, 0.32, 0.9)

            # Slot background color
            slot_bg = (0.10, 0.13, 0.18, 0.98) if not is_hovered else (0.14, 0.18, 0.26, 0.98)

            # Draw 1px border around slot
            self.draw_rect(bg_verts, sx - 1.0, sy - 1.0, sw + 2.0, sh + 2.0, border_col)
            self.draw_rect(bg_verts, sx, sy, sw, sh, slot_bg)

            if item:
                # Truncate item name to fit slot (max 4-5 chars)
                short_name = item.name[:4] if len(item.name) > 4 else item.name
                item_col = (0.95, 0.95, 0.95, 1.0)
                self.draw_text(text_verts, short_name, sx + 4.0, sy + 4.0, item_col)

                # Count in bottom-right
                count_str = f"x{item.count}"
                cw = len(count_str) * self.font.char_w
                self.draw_text(text_verts, count_str, sx + sw - cw - 3.0, sy + sh - 16.0, (1.0, 0.9, 0.4, 1.0))
            else:
                if slot_type == "equipment":
                    lbl = str(slot_id)[:4].capitalize()
                    self.draw_text(text_verts, lbl, sx + 6.0, sy + 14.0, (0.4, 0.45, 0.52, 0.6))
                elif slot_type == "hotbar":
                    self.draw_text(text_verts, str(slot_id + 1), sx + 6.0, sy + 14.0, (0.32, 0.36, 0.44, 0.5))

        # Footer controls
        footer_str = "L-Click: Pick/Drop/Swap | R-Click: Split/Drop 1 | Shift-Click: Fast Move | [Esc/Tab/I] Close"
        self.draw_text(text_verts, footer_str, win_x + 16.0, win_y + win_h - 26.0, (0.60, 0.64, 0.70, 0.85))

        # 3. Hover Tooltip
        if hovered_item and mouse_x >= 0 and mouse_y >= 0:
            tt_lines = [
                hovered_item.name,
                f"Count: {hovered_item.count} | Block #{hovered_item.block_id}",
                f"Category: {hovered_item.category}",
            ]
            tt_w = max(len(l) for l in tt_lines) * self.font.char_w + 16.0
            tt_h = len(tt_lines) * 18.0 + 12.0
            tt_x = min(self.width - tt_w - 10.0, mouse_x + 14.0)
            tt_y = min(self.height - tt_h - 10.0, mouse_y + 14.0)

            self.draw_rect(bg_verts, tt_x - 1.0, tt_y - 1.0, tt_w + 2.0, tt_h + 2.0, (0.3, 0.8, 1.0, 0.95))
            self.draw_rect(bg_verts, tt_x, tt_y, tt_w, tt_h, (0.04, 0.06, 0.10, 0.98))
            for i, line in enumerate(tt_lines):
                col = (0.3, 0.9, 1.0, 1.0) if i == 0 else (0.85, 0.88, 0.92, 0.9)
                self.draw_text(text_verts, line, tt_x + 8.0, tt_y + 6.0 + i * 18.0, col)

        # 4. Attached Cursor Stack (Drag and Drop Floating Element)
        if inv.cursor_stack and mouse_x >= 0 and mouse_y >= 0:
            cs = inv.cursor_stack
            cs_text = f"{cs.name} x{cs.count}"
            cs_w = len(cs_text) * self.font.char_w + 14.0
            cs_h = 24.0
            cx = mouse_x + 12.0
            cy = mouse_y - 28.0

            self.draw_rect(bg_verts, cx - 1.0, cy - 1.0, cs_w + 2.0, cs_h + 2.0, (1.0, 0.85, 0.2, 1.0))
            self.draw_rect(bg_verts, cx, cy, cs_w, cs_h, (0.12, 0.16, 0.24, 0.98))
            self.draw_text(text_verts, cs_text, cx + 7.0, cy + 4.0, (1.0, 0.95, 0.7, 1.0))

        # 5. Render All Quads and Text
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

    def render_settings_menu(self, settings: any) -> None:
        """Renders the Settings Menu for mouse sensitivity, smoothing, FOV, and fly mode."""
        lines = [
            "=== MINEMESIS SETTINGS & CONTROLS ===",
            "Configure mouse response, visual presentation, and movement dynamics.",
            "--------------------------------------------------------------------------------",
            f" [1] Mouse Sensitivity:   {settings.mouse_sensitivity:.2f}   (Press [1] to cycle: 0.05 -> 0.08 -> 0.12 -> 0.16 -> 0.22 -> 0.30)",
            f" [2] Camera Smoothing:    {'ENABLED (Exponential)' if settings.camera_smoothing else 'DISABLED (Raw Motion)'}   (Press [2] to toggle)",
            f" [3] Field of View (FOV): {settings.fov:.0f} deg   (Press [3] to cycle: 65 -> 75 -> 85 -> 95)",
            f" [4] Invert Y Axis:       {'ENABLED' if settings.invert_y else 'DISABLED'}   (Press [4] to toggle)",
            f" [5] Debug Fly Mode:      {'ENABLED (Free Flight)' if settings.fly_mode else 'DISABLED (Terrestrial Gravity)'}   (Press [5] to toggle)",
            "--------------------------------------------------------------------------------",
            "[Esc / O] Save and Return to Game",
        ]
        self.render_centered_overlay(lines, title_color=(1.0, 0.85, 0.25, 1.0))
