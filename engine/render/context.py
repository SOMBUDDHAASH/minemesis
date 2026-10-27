"""
ModernGL Render Context and State Wrapper.
"""

from __future__ import annotations
import moderngl
from typing import Tuple


class RenderContext:
    """Encapsulates ModernGL context, state flags, and frame operations."""

    def __init__(self, width: int, height: int) -> None:
        self.ctx = moderngl.create_context()
        self.width = width
        self.height = height

        # Hardware capabilities
        self.vendor = self.ctx.info.get("GL_VENDOR", "Unknown")
        self.renderer = self.ctx.info.get("GL_RENDERER", "Unknown")
        self.gl_version = self.ctx.info.get("GL_VERSION", "Unknown")

        # Initial state setup
        self.set_viewport(0, 0, width, height)
        self.enable_depth_test(True)
        self.enable_cull_face(True)
        self.enable_blend(True)

    def set_viewport(self, x: int, y: int, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.ctx.viewport = (x, y, width, height)

    def enable_depth_test(self, enable: bool = True) -> None:
        if enable:
            self.ctx.enable(moderngl.DEPTH_TEST)
        else:
            self.ctx.disable(moderngl.DEPTH_TEST)

    def enable_cull_face(self, enable: bool = True) -> None:
        if enable:
            self.ctx.enable(moderngl.CULL_FACE)
        else:
            self.ctx.disable(moderngl.CULL_FACE)

    def enable_blend(self, enable: bool = True) -> None:
        if enable:
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        else:
            self.ctx.disable(moderngl.BLEND)

    def clear(self, r: float = 0.52, g: float = 0.75, b: float = 0.98, a: float = 1.0) -> None:
        self.ctx.clear(r, g, b, a, depth=1.0)
