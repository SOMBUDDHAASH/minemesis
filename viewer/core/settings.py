"""
Settings management for Minemesis Viewer V2.
Persists configuration to %APPDATA%/MinemesisViewer/settings.json.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Optional


def get_appdata_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        base = Path(appdata) / "MinemesisViewer"
    else:
        base = Path.home() / ".minemesis_viewer"
    base.mkdir(parents=True, exist_ok=True)
    return base


class Settings:
    DEFAULT_SETTINGS = {
        "theme": "dark",
        "font_size": 10,
        "recent_files": [],
        "window_width": 1280,
        "window_height": 820,
        "detail_panel_visible": True,
        "major_events_only": False,
    }

    def __init__(self) -> None:
        self.settings_dir = get_appdata_dir()
        self.settings_path = self.settings_dir / "settings.json"
        self._data = dict(self.DEFAULT_SETTINGS)
        self.load()

    def load(self) -> None:
        if self.settings_path.exists():
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self._data.update(loaded)
            except Exception:
                pass

    def save(self) -> None:
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def add_recent_file(self, path_str: str) -> None:
        recents: list[str] = self._data.get("recent_files", [])
        if path_str in recents:
            recents.remove(path_str)
        recents.insert(0, path_str)
        self._data["recent_files"] = recents[:10]
        self.save()


settings = Settings()
