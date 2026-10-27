"""
Game Settings Provider for Minemesis Engine:
Mouse sensitivity, camera smoothing, FOV, invert Y, and fly mode.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
import json
from pathlib import Path


@dataclass
class GameSettings:
    mouse_sensitivity: float = 0.12     # Range 0.02 to 0.40
    camera_smoothing: bool = True
    smoothing_factor: float = 0.5       # Lerp factor (0.1 = heavy, 0.9 = sharp)
    fov: float = 75.0                   # 60.0 to 100.0 degrees
    invert_y: bool = False
    fly_mode: bool = False              # Strictly False by default (Player Bound by Gravity)

    def cycle_sensitivity(self) -> float:
        presets = [0.05, 0.08, 0.12, 0.16, 0.22, 0.30]
        for p in presets:
            if p > self.mouse_sensitivity + 0.01:
                self.mouse_sensitivity = p
                return self.mouse_sensitivity
        self.mouse_sensitivity = presets[0]
        return self.mouse_sensitivity

    def toggle_smoothing(self) -> bool:
        self.camera_smoothing = not self.camera_smoothing
        return self.camera_smoothing

    def cycle_fov(self) -> float:
        presets = [65.0, 75.0, 85.0, 95.0]
        for p in presets:
            if p > self.fov + 1.0:
                self.fov = p
                return self.fov
        self.fov = presets[0]
        return self.fov

    def toggle_invert_y(self) -> bool:
        self.invert_y = not self.invert_y
        return self.invert_y

    def toggle_fly_mode(self) -> bool:
        self.fly_mode = not self.fly_mode
        return self.fly_mode

    def save(self, path: Path | str = "settings.json") -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2)
        except Exception:
            pass

    @classmethod
    def load(cls, path: Path | str = "settings.json") -> GameSettings:
        p = Path(path)
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(**data)
            except Exception:
                pass
        return cls()
