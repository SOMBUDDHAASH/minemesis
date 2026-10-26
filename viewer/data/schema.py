"""
Data schema definitions and compatibility checking for Viewer V2.
"""

from __future__ import annotations

SUPPORTED_SCHEMA_VERSION = 1


class IncompatibleSchemaError(Exception):
    """Raised when the database schema version is newer than supported."""
    pass


TABLE_NAMES = [
    "meta",
    "settlements",
    "census",
    "events",
    "event_participants",
    "event_causes",
    "characters",
    "epistemic_ledger",
    "books",
    "religions",
    "holy_sites",
    "myths",
    "threads",
    "name_audit",
    "geography",
]
