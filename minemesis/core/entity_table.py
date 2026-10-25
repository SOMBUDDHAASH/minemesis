"""
Entity Lexicon and String Intern Table (M0.5.4 Lore Compression).

Provides O(1) string deduplication via sys.intern and integer-indexed entity registries.
Ensures that recurring names (villagers, settlements, families, holy sites) occupy
exactly one string instance on the heap regardless of how many thousands of times
they are referenced.
"""

from __future__ import annotations
import sys
from typing import Mapping, Optional


class EntityTable:
    """
    Centralized string intern pool for Minemesis.
    """
    @staticmethod
    def intern(s: str) -> str:
        """Interns a string so identical strings share a single heap address."""
        if not s or not isinstance(s, str):
            return s
        return sys.intern(s)

    @staticmethod
    def intern_dict(d: dict[str, str]) -> dict[str, str]:
        """Interns both keys and string values of a dictionary."""
        return {sys.intern(str(k)): sys.intern(str(v)) if isinstance(v, str) else v for k, v in d.items()}
