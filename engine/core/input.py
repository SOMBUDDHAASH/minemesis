"""
Input State Tracking for Keyboard and Mouse in GLFW.
"""

from __future__ import annotations
import glfw
from typing import Dict, Set, Tuple


class InputManager:
    """Tracks continuous key states, mouse button clicks, and mouse delta movement."""

    def __init__(self) -> None:
        self.keys_down: Set[int] = set()
        self.keys_pressed: Set[int] = set()
        self.mouse_buttons_down: Set[int] = set()
        self.mouse_buttons_pressed: Set[int] = set()

        self.mouse_x: float = 0.0
        self.mouse_y: float = 0.0
        self.delta_x: float = 0.0
        self.delta_y: float = 0.0
        self.scroll_delta: float = 0.0

        self._first_mouse: bool = True
        self.mouse_captured: bool = False

    def on_key(self, window: any, key: int, scancode: int, action: int, mods: int) -> None:
        if action == glfw.PRESS:
            self.keys_down.add(key)
            self.keys_pressed.add(key)
        elif action == glfw.RELEASE:
            self.keys_down.discard(key)

    def on_mouse_button(self, window: any, button: int, action: int, mods: int) -> None:
        if action == glfw.PRESS:
            self.mouse_buttons_down.add(button)
            self.mouse_buttons_pressed.add(button)
        elif action == glfw.RELEASE:
            self.mouse_buttons_down.discard(button)

    def on_cursor_pos(self, window: any, xpos: float, ypos: float) -> None:
        if self._first_mouse:
            self.mouse_x = xpos
            self.mouse_y = ypos
            self._first_mouse = False

        self.delta_x = xpos - self.mouse_x
        self.delta_y = ypos - self.mouse_y
        self.mouse_x = xpos
        self.mouse_y = ypos

    def on_scroll(self, window: any, xoffset: float, yoffset: float) -> None:
        self.scroll_delta = yoffset

    def post_frame(self) -> None:
        """Clears single-frame impulse states at end of frame."""
        self.keys_pressed.clear()
        self.mouse_buttons_pressed.clear()
        self.delta_x = 0.0
        self.delta_y = 0.0
        self.scroll_delta = 0.0

    def is_key_down(self, key: int) -> bool:
        return key in self.keys_down

    def is_key_pressed(self, key: int) -> bool:
        return key in self.keys_pressed

    def is_mouse_down(self, button: int) -> bool:
        return button in self.mouse_buttons_down

    def is_mouse_pressed(self, button: int) -> bool:
        return button in self.mouse_buttons_pressed
