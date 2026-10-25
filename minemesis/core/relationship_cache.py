"""
Relationship Cache for Milestone 0.5.4.

Solves the primary CPU bottleneck:
Replaces repeated expensive scans of character memory lists with O(1) cached views.
Invalidated lazily via TTL or event-driven triggers (new memory or truth revelation).
"""

from __future__ import annotations
from typing import Optional, Tuple
from minemesis.models.relationship import Relationship


class RelationshipCache:
    """
    O(1) Interpersonal Relationship Cache.
    """
    def __init__(self, default_ttl_ticks: int = 12) -> None:
        self.default_ttl = default_ttl_ticks
        # Key: (source_id, target_id) -> (Relationship, expiry_tick)
        self._cache: dict[tuple[str, str], tuple[Relationship, int]] = {}

    def get(self, source_id: str, target_id: str, current_tick: int) -> Optional[Relationship]:
        entry = self._cache.get((source_id, target_id))
        if entry is not None and entry[1] >= current_tick:
            return entry[0]
        return None

    def put(
        self,
        source_id: str,
        target_id: str,
        relationship: Relationship,
        current_tick: int,
        ttl_ticks: Optional[int] = None,
    ) -> None:
        ttl = ttl_ticks if ttl_ticks is not None else self.default_ttl
        self._cache[(source_id, target_id)] = (relationship, current_tick + ttl)

    def invalidate_character(self, character_id: str) -> None:
        """
        Invalidates cached relationships involving character_id.
        Called when a character forms a new emotional memory or supersedes a belief.
        """
        to_del = [k for k in self._cache if k[0] == character_id or k[1] == character_id]
        for k in to_del:
            del self._cache[k]

    def invalidate_pair(self, char_a: str, char_b: str) -> None:
        self._cache.pop((char_a, char_b), None)
        self._cache.pop((char_b, char_a), None)

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)
