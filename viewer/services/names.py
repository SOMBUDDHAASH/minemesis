"""
Name Resolution Service for Viewer V2.
Queries DB for display_name; renders missing names with a visible [?] tag in red.
"""

from __future__ import annotations
from typing import Optional

from viewer.core.session import session


class NameResolver:
    """Caches and resolves entity names from the active run database."""

    def __init__(self) -> None:
        self._char_cache: dict[str, str] = {}
        self._settle_cache: dict[str, str] = {}
        self._rel_cache: dict[str, str] = {}

    def clear(self) -> None:
        self._char_cache.clear()
        self._settle_cache.clear()
        self._rel_cache.clear()

    def resolve_character(self, character_id: str) -> tuple[str, bool]:
        """
        Returns (display_name, is_valid).
        If character is missing from DB, returns ('[? ' + id + ']', False).
        """
        if not character_id or character_id in ("None", "Unknown", "unknown", "Someone", "someone"):
            return ("[? Unidentified]", False)

        if character_id in self._char_cache:
            return (self._char_cache[character_id], True)

        if session.db:
            name = session.db.get_character_name(character_id)
            if name:
                self._char_cache[character_id] = name
                return (name, True)

        # Regressed or missing name
        fallback = f"[? {character_id}]"
        return (fallback, False)

    def resolve_settlement(self, settlement_id: str) -> str:
        if not settlement_id:
            return "World"
        if settlement_id in self._settle_cache:
            return self._settle_cache[settlement_id]

        if session.db:
            s = session.db.get_settlement(settlement_id)
            if s and s.get("name"):
                name = s["name"]
                self._settle_cache[settlement_id] = name
                return name

        # Syllable/id fallback
        clean = settlement_id.replace("set_", "").capitalize()
        self._settle_cache[settlement_id] = clean
        return clean

    def resolve_religion(self, religion_id: str) -> str:
        if not religion_id:
            return "Faith"
        if religion_id in self._rel_cache:
            return self._rel_cache[religion_id]

        if session.db:
            r = session.db.get_religion(religion_id)
            if r and r.get("name"):
                name = r["name"]
                self._rel_cache[religion_id] = name
                return name

        clean = religion_id.replace("rel_", "Faith ")
        return clean


name_resolver = NameResolver()
