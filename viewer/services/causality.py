"""
Causality & Why-Graph Service for Viewer V2.
Traverses causal DAG backwards (causes) and forwards (consequences).
"""

from __future__ import annotations
from typing import Any, Optional

from viewer.core.session import session


class CausalityService:
    def get_causes(self, event_id: int) -> list[dict[str, Any]]:
        """Returns direct causes of an event."""
        if not session.db:
            return []
        cause_ids = session.db.get_event_causes(event_id)
        results = []
        for cid in cause_ids:
            evt = session.db.get_event(cid)
            if evt:
                results.append(evt)
        return results

    def get_consequences(self, event_id: int) -> list[dict[str, Any]]:
        """Returns direct consequences of an event."""
        if not session.db:
            return []
        conseq_ids = session.db.get_event_consequences(event_id)
        results = []
        for cid in conseq_ids:
            evt = session.db.get_event(cid)
            if evt:
                results.append(evt)
        return results

    def get_causal_chain(self, event_id: int, max_depth: int = 5) -> list[dict[str, Any]]:
        """Recursively walks ancestral causes backwards in time."""
        if not session.db:
            return []

        visited: set[int] = set()
        chain: list[dict[str, Any]] = []

        def walk(eid: int, depth: int):
            if depth > max_depth or eid in visited:
                return
            visited.add(eid)
            evt = session.db.get_event(eid)
            if not evt:
                return
            chain.append(evt)
            for cid in evt.get("causes", []):
                walk(cid, depth + 1)

        walk(event_id, 0)
        return sorted(chain, key=lambda e: e.get("event_id", 0))


causality_service = CausalityService()
