"""
High-Precision Frame Timer and Profiling Metrics for Minemesis Engine.
"""

from __future__ import annotations
import collections
import time
from typing import Deque


class FrameTimer:
    """Measures delta time (dt), frames per second (FPS), and frame time distribution."""

    def __init__(self, fps_smoothing_window: int = 60) -> None:
        self.last_time = time.perf_counter()
        self.dt: float = 0.016
        self.elapsed: float = 0.0
        self.frame_count: int = 0
        self.fps: float = 60.0
        self._history: Deque[float] = collections.deque(maxlen=fps_smoothing_window)

    def tick(self) -> float:
        now = time.perf_counter()
        self.dt = now - self.last_time
        self.last_time = now

        # Prevent physics explosion on window drag/freeze
        if self.dt > 0.1:
            self.dt = 0.1

        self.elapsed += self.dt
        self.frame_count += 1
        self._history.append(self.dt)

        if self._history:
            avg_dt = sum(self._history) / len(self._history)
            if avg_dt > 0.00001:
                self.fps = 1.0 / avg_dt

        return self.dt
