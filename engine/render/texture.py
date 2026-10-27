"""
Procedural Texture Synthesis and ModernGL Texture Atlas for Minemesis Engine.
No external image files; all textures are mathematically synthesized in Python.
"""

from __future__ import annotations
import math
import moderngl
import numpy as np
from PIL import Image, ImageDraw


# Tile coordinates in atlas: (tile_col, tile_row) in a 16x16 grid (each tile 32x32 pixels)
ATLAS_GRID_SIZE = 16
TILE_PIXELS = 32
ATLAS_SIZE = ATLAS_GRID_SIZE * TILE_PIXELS  # 512x512 pixels


class TextureAtlas:
    """Generates procedural texture atlas and uploads to OpenGL texture unit 0."""

    def __init__(self, ctx: moderngl.Context) -> None:
        self.ctx = ctx
        self.image = Image.new("RGBA", (ATLAS_SIZE, ATLAS_SIZE), (0, 0, 0, 255))
        self.draw = ImageDraw.Draw(self.image)
        self.tile_map: dict[str, tuple[int, int]] = {}

        self._generate_all_procedural_tiles()

        # Convert to raw bytes and create ModernGL texture
        raw_data = self.image.tobytes()
        self.texture = self.ctx.texture((ATLAS_SIZE, ATLAS_SIZE), 4, raw_data)
        self.texture.filter = (moderngl.NEAREST_MIPMAP_LINEAR, moderngl.NEAREST)
        self.texture.build_mipmaps()

    def bind(self, unit: int = 0) -> None:
        self.texture.use(location=unit)

    def get_uv_rect(self, tile_name: str) -> tuple[float, float, float, float]:
        """Returns (u_min, v_min, u_max, v_max) for named tile."""
        col, row = self.tile_map.get(tile_name, (0, 0))
        u_min = col / float(ATLAS_GRID_SIZE)
        v_min = row / float(ATLAS_GRID_SIZE)
        u_max = (col + 1) / float(ATLAS_GRID_SIZE)
        v_max = (row + 1) / float(ATLAS_GRID_SIZE)
        return u_min, v_min, u_max, v_max

    def _draw_tile(self, col: int, row: int, name: str, painter_fn) -> None:
        self.tile_map[name] = (col, row)
        x0 = col * TILE_PIXELS
        y0 = row * TILE_PIXELS

        tile_img = Image.new("RGBA", (TILE_PIXELS, TILE_PIXELS), (0, 0, 0, 255))
        tile_draw = ImageDraw.Draw(tile_img)
        painter_fn(tile_draw, TILE_PIXELS)
        self.image.paste(tile_img, (x0, y0))

    def _generate_all_procedural_tiles(self) -> None:
        # 1. Limestone
        def paint_limestone(d, s):
            for y in range(s):
                for x in range(s):
                    noise = (math.sin(x * 0.7) * math.cos(y * 0.7) + 1.0) * 0.5
                    v = int(210 + noise * 35)
                    fossil = 1 if (x * 13 + y * 7) % 23 == 0 else 0
                    if fossil:
                        d.point((x, y), fill=(160, 150, 135, 255))
                    else:
                        d.point((x, y), fill=(v, int(v * 0.96), int(v * 0.88), 255))
        self._draw_tile(0, 0, "limestone", paint_limestone)

        # 2. Basalt
        def paint_basalt(d, s):
            for y in range(s):
                for x in range(s):
                    noise = (math.cos(x * 0.5 + y * 0.4) + 1.0) * 0.5
                    v = int(45 + noise * 25)
                    d.point((x, y), fill=(v, v, int(v * 1.05), 255))
        self._draw_tile(1, 0, "basalt", paint_basalt)

        # 3. Granite
        def paint_granite(d, s):
            for y in range(s):
                for x in range(s):
                    h = (x * 37 + y * 53) % 100
                    if h < 45:
                        d.point((x, y), fill=(185, 140, 130, 255))  # Feldspar pink
                    elif h < 75:
                        d.point((x, y), fill=(160, 160, 165, 255))  # Quartz gray
                    else:
                        d.point((x, y), fill=(50, 48, 52, 255))     # Biotite dark
        self._draw_tile(2, 0, "granite", paint_granite)

        # 4. Slate
        def paint_slate(d, s):
            for y in range(s):
                layer = (y // 3) % 2
                base = 80 if layer == 0 else 70
                for x in range(s):
                    n = (x * 19) % 15
                    d.point((x, y), fill=(base + n, base + n + 4, base + n + 10, 255))
        self._draw_tile(3, 0, "slate", paint_slate)

        # 5. Dirt / Loam
        def paint_dirt(d, s):
            for y in range(s):
                for x in range(s):
                    n = ((x * 11 + y * 17) % 31) - 15
                    d.point((x, y), fill=(125 + n, 85 + n, 50 + n, 255))
        self._draw_tile(4, 0, "dirt", paint_dirt)

        # 6. Grass Top
        def paint_grass_top(d, s):
            for y in range(s):
                for x in range(s):
                    n = ((x * 13 + y * 29) % 37) - 18
                    d.point((x, y), fill=(80 + n, 160 + n, 50 + n, 255))
        self._draw_tile(5, 0, "grass_top", paint_grass_top)

        # 7. Grass Side (Dirt with green overhang)
        def paint_grass_side(d, s):
            for y in range(s):
                for x in range(s):
                    overhang = 4 + int(math.sin(x * 0.8) * 2.5)
                    if y < overhang:
                        n = ((x * 13 + y * 29) % 37) - 18
                        d.point((x, y), fill=(80 + n, 160 + n, 50 + n, 255))
                    else:
                        n = ((x * 11 + y * 17) % 31) - 15
                        d.point((x, y), fill=(125 + n, 85 + n, 50 + n, 255))
        self._draw_tile(6, 0, "grass_side", paint_grass_side)

        # 8. Sand
        def paint_sand(d, s):
            for y in range(s):
                for x in range(s):
                    n = ((x * 7 + y * 13) % 23) - 11
                    d.point((x, y), fill=(225 + n, 205 + n, 145 + n, 255))
        self._draw_tile(7, 0, "sand", paint_sand)

        # 9. Oak Log Bark
        def paint_log(d, s):
            for y in range(s):
                for x in range(s):
                    strip = ((x // 4) % 2) * 15
                    n = (y * 11) % 12
                    d.point((x, y), fill=(105 + strip + n, 75 + strip + n, 45 + strip + n, 255))
        self._draw_tile(8, 0, "wood_log", paint_log)

        # 10. Cut Wooden Planks
        def paint_planks(d, s):
            for y in range(s):
                plank_idx = y // 8
                is_gap = (y % 8 == 0)
                for x in range(s):
                    if is_gap:
                        d.point((x, y), fill=(70, 50, 30, 255))
                    else:
                        grain = ((x + plank_idx * 7) % 6) * 5
                        d.point((x, y), fill=(175 + grain, 135 + grain, 85 + grain, 255))
        self._draw_tile(9, 0, "wood_planks", paint_planks)

        # 11. Stone Bricks
        def paint_bricks(d, s):
            for y in range(s):
                row_idx = y // 8
                shift = (row_idx % 2) * 8
                is_horiz = (y % 8 == 0)
                for x in range(s):
                    is_vert = ((x + shift) % 16 == 0)
                    if is_horiz or is_vert:
                        d.point((x, y), fill=(75, 75, 80, 255))
                    else:
                        n = ((x * 7 + y * 13) % 20) - 10
                        d.point((x, y), fill=(145 + n, 145 + n, 150 + n, 255))
        self._draw_tile(10, 0, "stone_bricks", paint_bricks)

        # 12. Copper Ore
        def paint_copper_ore(d, s):
            for y in range(s):
                for x in range(s):
                    h = (x * 19 + y * 31) % 100
                    if 25 < h < 45:
                        d.point((x, y), fill=(215, 115, 65, 255))  # Metallic copper
                    elif 45 <= h < 55:
                        d.point((x, y), fill=(65, 180, 150, 255))  # Verdigris green
                    else:
                        n = (x * 7 + y * 11) % 16
                        d.point((x, y), fill=(130 + n, 130 + n, 135 + n, 255))
        self._draw_tile(11, 0, "copper_ore", paint_copper_ore)

        # 13. Iron Ore
        def paint_iron_ore(d, s):
            for y in range(s):
                for x in range(s):
                    h = (x * 23 + y * 29) % 100
                    if 30 < h < 50:
                        d.point((x, y), fill=(185, 155, 130, 255)) # Iron metallic
                    else:
                        n = (x * 7 + y * 11) % 16
                        d.point((x, y), fill=(130 + n, 130 + n, 135 + n, 255))
        self._draw_tile(12, 0, "iron_ore", paint_iron_ore)

        # 14. Water
        def paint_water(d, s):
            for y in range(s):
                for x in range(s):
                    wave = int(math.sin(x * 0.4 + y * 0.4) * 20)
                    d.point((x, y), fill=(40, 110 + wave, 215 + wave, 210))
        self._draw_tile(13, 0, "water", paint_water)

        # 15. Foliage Leaves
        def paint_leaves(d, s):
            for y in range(s):
                for x in range(s):
                    h = (x * 17 + y * 23) % 100
                    if h < 20:
                        d.point((x, y), fill=(0, 0, 0, 0))  # Cutout transparency
                    else:
                        n = ((x * 11 + y * 13) % 30) - 15
                        d.point((x, y), fill=(45 + n, 135 + n, 35 + n, 255))
        self._draw_tile(14, 0, "leaves", paint_leaves)

        # 16. Glass Pane
        def paint_glass(d, s):
            for y in range(s):
                for x in range(s):
                    is_edge = (x == 0 or x == s - 1 or y == 0 or y == s - 1)
                    streak = (x == y or x == y + 1)
                    if is_edge:
                        d.point((x, y), fill=(180, 210, 240, 255))
                    elif streak:
                        d.point((x, y), fill=(240, 250, 255, 160))
                    else:
                        d.point((x, y), fill=(160, 200, 230, 45))
        self._draw_tile(15, 0, "glass", paint_glass)

        # === ROW 1: Civil Architecture & NPCs ===
        # 17. Town Archive Bookshelf
        def paint_bookshelf(d, s):
            # Wood plank background
            for y in range(s):
                for x in range(s):
                    d.point((x, y), fill=(140, 100, 60, 255))
            # Shelf dividers
            d.rectangle((0, 0, s - 1, 3), fill=(90, 60, 35, 255))
            d.rectangle((0, 14, s - 1, 17), fill=(90, 60, 35, 255))
            d.rectangle((0, 28, s - 1, 31), fill=(90, 60, 35, 255))
            # Book spines on top shelf
            book_colors = [
                (180, 40, 40), (40, 80, 180), (30, 140, 50),
                (190, 160, 30), (120, 50, 150), (160, 90, 40),
            ]
            bx = 2
            for c in book_colors:
                w = 4
                d.rectangle((bx, 4, bx + w - 1, 13), fill=(c[0], c[1], c[2], 255))
                # Gold spine detail
                d.line((bx, 8, bx + w - 1, 8), fill=(230, 200, 80, 255))
                bx += w + 1
            # Book spines on bottom shelf
            bx = 2
            for c in reversed(book_colors):
                w = 4
                d.rectangle((bx, 18, bx + w - 1, 27), fill=(c[0], c[1], c[2], 255))
                d.line((bx, 22, bx + w - 1, 22), fill=(230, 200, 80, 255))
                bx += w + 1
        self._draw_tile(0, 1, "bookshelf", paint_bookshelf)

        # 18. Scholar Lectern
        def paint_lectern(d, s):
            for y in range(s):
                for x in range(s):
                    d.point((x, y), fill=(130, 90, 50, 255))
            # Slanted reading desk
            d.rectangle((3, 3, s - 4, s - 4), fill=(160, 120, 75, 255))
            # Open parchment pages
            d.rectangle((6, 6, 14, 25), fill=(245, 240, 220, 255))
            d.rectangle((17, 6, 25, 25), fill=(245, 240, 220, 255))
            # Red bookmark ribbon
            d.line((15, 4, 16, 28), fill=(200, 30, 30, 255))
            # Text lines on parchment
            for ly in [10, 14, 18, 22]:
                d.line((8, ly, 13, ly), fill=(60, 55, 50, 255))
                d.line((19, ly, 24, ly), fill=(60, 55, 50, 255))
        self._draw_tile(1, 1, "lectern", paint_lectern)

        # 19. NPC Skin Tone
        def paint_skin(d, s):
            for y in range(s):
                for x in range(s):
                    n = ((x * 7 + y * 13) % 15) - 7
                    d.point((x, y), fill=(225 + n, 185 + n, 150 + n, 255))
        self._draw_tile(2, 1, "npc_skin", paint_skin)

        # 20. Profession Clothing and Hair
        professions_meta = {
            "Chief": {"body": (215, 165, 40), "legs": (65, 40, 25), "hair": (190, 190, 190)},
            "Scholar": {"body": (50, 90, 165), "legs": (40, 45, 65), "hair": (90, 65, 40)},
            "Priest": {"body": (205, 215, 230), "legs": (75, 50, 90), "hair": (200, 200, 200)},
            "Smith": {"body": (115, 90, 65), "legs": (50, 50, 55), "hair": (40, 40, 40)},
            "Farmer": {"body": (100, 155, 75), "legs": (90, 65, 40), "hair": (130, 90, 50)},
            "Guard": {"body": (140, 148, 158), "legs": (75, 82, 90), "hair": (50, 40, 25)},
            "Citizen": {"body": (155, 115, 90), "legs": (65, 55, 50), "hair": (75, 50, 40)},
        }

        col_idx = 3
        for prof, pcols in professions_meta.items():
            # Body cloth
            bc = pcols["body"]
            def _pb(c):
                return lambda d, s: d.rectangle((0, 0, s, s), fill=(c[0], c[1], c[2], 255))
            self._draw_tile(col_idx, 1, f"npc_body_{prof}", _pb(bc))

            # Legs cloth
            lc = pcols["legs"]
            self._draw_tile(col_idx, 2, f"npc_legs_{prof}", _pb(lc))

            # Hair
            hc = pcols["hair"]
            self._draw_tile(col_idx, 3, f"npc_hair_{prof}", _pb(hc))

            col_idx += 1
