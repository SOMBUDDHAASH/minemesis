"""
Active Run Session State for Viewer V2.
Manages current database handle, filters, entity selections, and navigation history.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Optional

from viewer.core.bus import bus
from viewer.core.logging import log_error
from viewer.core.settings import settings
from viewer.data.database import RunDatabase


class RunSession:
    def __init__(self) -> None:
        self.db_path: Optional[Path] = None
        self.db: Optional[RunDatabase] = None

        # Filter state
        self.filters: dict[str, Any] = {
            "search": "",
            "era": None,          # tuple[int, int] or None
            "settlement": None,   # settlement_id or None
            "event_types": [],    # list[str]
            "major_only": False,
        }

        # Entity selection and web-like history
        self.selected_entity: Optional[tuple[str, str]] = None  # (entity_type, entity_id)
        self._history: list[tuple[str, str]] = []
        self._history_idx: int = -1

    @property
    def is_loaded(self) -> bool:
        return self.db is not None

    def load_file(self, file_path: str | Path) -> None:
        p = Path(file_path).resolve()
        if self.db:
            self.db.close()
            self.db = None

        try:
            self.db = RunDatabase(p)
            self.db_path = p
            settings.add_recent_file(str(p))

            # Reset state
            self.filters = {
                "search": "",
                "era": None,
                "settlement": None,
                "event_types": [],
                "major_only": False,
            }
            self.selected_entity = None
            self._history.clear()
            self._history_idx = -1

            bus.publish("session:loaded", path=str(p), meta=self.db.meta)
        except Exception as e:
            log_error(f"Failed to load run database {p}", e)
            raise

    def close(self) -> None:
        if self.db:
            self.db.close()
            self.db = None
            self.db_path = None
            bus.publish("session:closed")

    def select_entity(self, entity_type: str, entity_id: str, push_history: bool = True) -> None:
        """Selects an entity, updating detail panel and navigation history."""
        pair = (entity_type, entity_id)
        if self.selected_entity == pair and push_history:
            return

        self.selected_entity = pair
        if push_history:
            # Truncate forward history if navigating new branch
            if self._history_idx < len(self._history) - 1:
                self._history = self._history[: self._history_idx + 1]
            self._history.append(pair)
            self._history_idx = len(self._history) - 1

        bus.publish(
            "entity:selected",
            entity_type=entity_type,
            entity_id=entity_id,
            can_back=self.can_go_back(),
            can_forward=self.can_go_forward(),
        )

    def can_go_back(self) -> bool:
        return self._history_idx > 0

    def can_go_forward(self) -> bool:
        return 0 <= self._history_idx < len(self._history) - 1

    def go_back(self) -> Optional[tuple[str, str]]:
        if self.can_go_back():
            self._history_idx -= 1
            pair = self._history[self._history_idx]
            self.select_entity(pair[0], pair[1], push_history=False)
            return pair
        return None

    def go_forward(self) -> Optional[tuple[str, str]]:
        if self.can_go_forward():
            self._history_idx += 1
            pair = self._history[self._history_idx]
            self.select_entity(pair[0], pair[1], push_history=False)
            return pair
        return None

    def update_filters(self, **kwargs: Any) -> None:
        changed = False
        for k, v in kwargs.items():
            if k in self.filters and self.filters[k] != v:
                self.filters[k] = v
                changed = True
        if changed:
            bus.publish("filter:changed", filters=dict(self.filters))


session = RunSession()
