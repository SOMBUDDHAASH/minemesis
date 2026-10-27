"""
GLFW Window Wrapper and Event Loop Management for Minemesis Engine.
"""

from __future__ import annotations
import sys
from typing import Callable, Optional, Tuple
import glfw

from engine.core.input import InputManager


class Window:
    """Manages GLFW window lifecycle, input capture, and OpenGL 3.3 Core profile initialization."""

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        title: str = "Minemesis Voxel Civilization Simulator",
        vsync: bool = True,
        visible: bool = True,
    ) -> None:
        self.width = width
        self.height = height
        self.title = title
        self.vsync = vsync
        self.visible = visible

        if not glfw.init():
            raise RuntimeError("Failed to initialize GLFW library.")

        # Configure OpenGL 3.3 Core Profile hints
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
        glfw.window_hint(glfw.VISIBLE, visible)
        glfw.window_hint(glfw.RESIZABLE, True)
        glfw.window_hint(glfw.SAMPLES, 4)  # 4x MSAA

        self.handle = glfw.create_window(width, height, title, None, None)
        if not self.handle:
            glfw.terminate()
            raise RuntimeError(
                "Failed to create OpenGL 3.3 Core window.\n"
                "Please verify your GPU supports OpenGL 3.3 or newer."
            )

        glfw.make_context_current(self.handle)
        glfw.swap_interval(1 if vsync else 0)

        # Input Manager
        self.input = InputManager()
        self._bind_callbacks()

        # Window resize callback hook
        self.resize_callback: Optional[Callable[[int, int], None]] = None

    def _bind_callbacks(self) -> None:
        glfw.set_key_callback(self.handle, self.input.on_key)
        glfw.set_mouse_button_callback(self.handle, self.input.on_mouse_button)
        glfw.set_cursor_pos_callback(self.handle, self.input.on_cursor_pos)
        glfw.set_scroll_callback(self.handle, self.input.on_scroll)
        glfw.set_framebuffer_size_callback(self.handle, self._on_framebuffer_resize)

    def _on_framebuffer_resize(self, window: any, width: int, height: int) -> None:
        if width > 0 and height > 0:
            self.width = width
            self.height = height
            if self.resize_callback:
                self.resize_callback(width, height)

    def set_mouse_capture(self, capture: bool) -> None:
        self.input.mouse_captured = capture
        if capture:
            glfw.set_input_mode(self.handle, glfw.CURSOR, glfw.CURSOR_DISABLED)
        else:
            glfw.set_input_mode(self.handle, glfw.CURSOR, glfw.CURSOR_NORMAL)

    def poll_events(self) -> None:
        glfw.poll_events()

    def swap_buffers(self) -> None:
        glfw.swap_buffers(self.handle)
        self.input.post_frame()

    def should_close(self) -> bool:
        return glfw.window_should_close(self.handle)

    def close(self) -> None:
        glfw.set_window_should_close(self.handle, True)

    def destroy(self) -> None:
        if self.handle:
            glfw.destroy_window(self.handle)
            self.handle = None
        glfw.terminate()
