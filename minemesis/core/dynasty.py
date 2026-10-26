"""
Dynasty and Family Standing Analytics for Milestone 1.
Computes family lineages, prestige, living kin, and inherited grievance state.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from minemesis.core.person_store import PersonStore
from minemesis.models.character import Character


@dataclass
class FamilyStanding:
    family_id: str
    surname: str
    settlement_id: str
    living_count: int = 0
    total_born: int = 0
    prestige_score: float = 0.0
    active_feud_count: int = 0
    chief_count: int = 0
    book_count: int = 0
    head_of_house_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "surname": self.surname,
            "settlement_id": self.settlement_id,
            "living_count": self.living_count,
            "total_born": self.total_born,
            "prestige_score": round(self.prestige_score, 1),
            "active_feud_count": self.active_feud_count,
            "chief_count": self.chief_count,
            "book_count": self.book_count,
            "head_of_house_id": self.head_of_house_id,
        }


def compute_family_standings(
    store: PersonStore,
    characters: Mapping[str, Character],
    active_feuds: Sequence[Any],
    books: Sequence[Any] = (),
) -> dict[str, FamilyStanding]:
    """
    Derives family standing and prestige across all dynasties in the world.
    Prestige is driven by living size, authored books, settlement leaders, and honorable status.
    """
    standings: dict[str, FamilyStanding] = {}

    for c in characters.values():
        fam = getattr(c, "family_id", "") or c.last_name
        if not fam:
            continue

        if fam not in standings:
            standings[fam] = FamilyStanding(
                family_id=fam,
                surname=c.last_name,
                settlement_id=c.settlement_id,
            )

        f = standings[fam]
        f.total_born += 1
        if c.alive:
            f.living_count += 1
            if not f.head_of_house_id:
                f.head_of_house_id = c.id
            else:
                curr_head = store.get_person(f.head_of_house_id)
                if curr_head and c.age_ticks > curr_head.age_ticks:
                    f.head_of_house_id = c.id

    # Count authored books per family
    for b in books:
        auth_id = getattr(b, "author_id", None) or (b.get("author_id") if isinstance(b, dict) else None)
        if auth_id:
            auth = store.get_person(auth_id)
            if auth:
                fam = getattr(auth, "family_id", "") or auth.last_name
                if fam in standings:
                    standings[fam].book_count += 1

    # Count active feuds
    for feud in active_feuds:
        if getattr(feud, "active", True):
            inst = store.get_person(getattr(feud, "instigator_char_id", ""))
            if inst:
                fam = getattr(inst, "family_id", "") or inst.last_name
                if fam in standings:
                    standings[fam].active_feud_count += 1

    # Calculate prestige score
    for f in standings.values():
        score = (
            (f.living_count * 2.5)
            + (f.book_count * 8.0)
            + (f.chief_count * 15.0)
            - (f.active_feud_count * 3.0)
        )
        f.prestige_score = max(0.0, score)

    return standings
