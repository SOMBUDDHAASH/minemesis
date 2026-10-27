"""
Day & Night Cycle and Atmospheric Sky Lighting.
"""

from __future__ import annotations
import math
from typing import Tuple


class SkyLighting:
    """Computes dynamic time-of-day, sun/moon positions, and ambient light colors."""

    def __init__(self, day_duration_seconds: float = 1200.0) -> None:
        self.day_duration = day_duration_seconds
        self.time_of_day: float = 300.0  # Seconds into day (default mid-morning)

    def tick(self, dt: float) -> None:
        self.time_of_day = (self.time_of_day + dt) % self.day_duration

    @property
    def progress(self) -> float:
        """Normalized day progress: 0.0 to 1.0 (0.25 = sunrise, 0.5 = noon, 0.75 = sunset, 0.0 = midnight)."""
        return self.time_of_day / self.day_duration

    def get_sun_direction(self) -> Tuple[float, float, float]:
        sun_rad = self.progress * 2.0 * math.pi - math.pi * 0.5
        sx = math.cos(sun_rad)
        sy = -math.sin(sun_rad)
        sz = 0.35
        length = math.sqrt(sx * sx + sy * sy + sz * sz)
        return sx / length, sy / length, sz / length

    def get_sun_color(self) -> Tuple[float, float, float]:
        sun_dir = self.get_sun_direction()
        elevation = -sun_dir[1]  # positive when sun is high
        if elevation > 0.2:
            return (1.0, 0.96, 0.88)
        elif elevation > -0.05:
            # Sunset / Sunrise golden glow
            t = (elevation + 0.05) / 0.25
            r = 1.0
            g = 0.55 + 0.41 * t
            b = 0.25 + 0.63 * t
            return (r, g, b)
        else:
            # Faint moonlight
            return (0.15, 0.20, 0.35)

    def get_ambient_sky_color(self) -> Tuple[float, float, float]:
        sun_dir = self.get_sun_direction()
        elevation = -sun_dir[1]
        if elevation > 0.2:
            return (0.48, 0.72, 0.98)
        elif elevation > -0.05:
            t = (elevation + 0.05) / 0.25
            r = 0.15 + 0.65 * (1.0 - t)
            g = 0.18 + 0.40 * t
            b = 0.30 + 0.60 * t
            return (r, g, b)
        else:
            # Deep starry night
            return (0.04, 0.06, 0.14)
