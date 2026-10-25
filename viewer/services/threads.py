"""
Thread and Storyline Service for Viewer V2.
"""

from __future__ import annotations
from typing import Any, Optional

from viewer.core.session import session


class ThreadService:
    def get_all_threads(self) -> list[dict[str, Any]]:
        if not session.db:
            return []
        return session.db.get_threads()

    def get_thread(self, thread_id: str) -> Optional[dict[str, Any]]:
        if not session.db:
            return None
        return session.db.get_thread(thread_id)

    def get_thread_events(self, thread_id: str) -> list[dict[str, Any]]:
        if not session.db:
            return []
        return session.db.get_thread_events(thread_id)


thread_service = ThreadService()
