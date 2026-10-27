"""
Procedural ASCII Bitmap Font Atlas for Minemesis Engine HUD.
"""

from __future__ import annotations
import moderngl
from PIL import Image, ImageDraw, ImageFont


FONT_TEXTURE_SIZE = 256
CHAR_WIDTH = 12
CHAR_HEIGHT = 16
CHARS_PER_ROW = FONT_TEXTURE_SIZE // CHAR_WIDTH  # ~21


class BitmapFont:
    """Generates procedural monospaced font atlas and UV mappings."""

    def __init__(self, ctx: moderngl.Context) -> None:
        self.ctx = ctx
        self.char_w = CHAR_WIDTH
        self.char_h = CHAR_HEIGHT
        self.char_uvs: dict[str, tuple[float, float, float, float]] = {}

        img = Image.new("RGBA", (FONT_TEXTURE_SIZE, FONT_TEXTURE_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw ASCII characters 32 to 126
        for i in range(32, 127):
            ch = chr(i)
            idx = i - 32
            col = idx % CHARS_PER_ROW
            row = idx // CHARS_PER_ROW

            x0 = col * CHAR_WIDTH
            y0 = row * CHAR_HEIGHT

            # Draw white character with crisp outline
            draw.text((x0 + 2, y0), ch, fill=(255, 255, 255, 255))

            u0 = x0 / float(FONT_TEXTURE_SIZE)
            v0 = y0 / float(FONT_TEXTURE_SIZE)
            u1 = (x0 + CHAR_WIDTH) / float(FONT_TEXTURE_SIZE)
            v1 = (y0 + CHAR_HEIGHT) / float(FONT_TEXTURE_SIZE)
            self.char_uvs[ch] = (u0, v0, u1, v1)

        raw = img.tobytes()
        self.texture = self.ctx.texture((FONT_TEXTURE_SIZE, FONT_TEXTURE_SIZE), 4, raw)
        self.texture.filter = (moderngl.NEAREST, moderngl.NEAREST)

    def bind(self, unit: int = 1) -> None:
        self.texture.use(location=unit)
