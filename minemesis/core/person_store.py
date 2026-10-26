"""
PersonStore Protocol / Interface.
Enables Person retrieval and on-demand materialization, allowing Milestone 4
(Population Layering) to swap in layered demographic generation without rewriting kinship.
"""

from __future__ import annotations
from typing import Any, Optional, Protocol, runtime_checkable

from minemesis.models.character import Character


@runtime_checkable
class PersonStore(Protocol):
    """Abstract interface for accessing and materializing simulated persons."""

    def get_person(self, person_id: str) -> Optional[Character]:
        """Returns the Character object if loaded or living in store, else None."""
        ...

    def materialize_person(self, person_id: str) -> Optional[Character]:
        """Ensures the person is materialized into a full Character entity."""
        ...

    def is_alive(self, person_id: str) -> bool:
        """Returns True if the person is currently living."""
        ...

    def get_living_ids(self) -> list[str]:
        """Returns all currently living person IDs."""
        ...

    def get_settlement_living_ids(self, settlement_id: str) -> list[str]:
        """Returns all living person IDs residing in the given settlement."""
        ...
