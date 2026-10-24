"""
Religious Tension and Inter-Faith Relationship System (Milestone R1.2).

Models sectarian dynamics, doctrinal hostility, and inter-religious affinity:
- SharedFaith: Co-religionists share sacred bonds (trust boost).
- SimilarFaith: Unrelated or harmonized faiths coexist peacefully.
- DivergentSect: Schismatic offshoots of the same root tree ("narcissism of small differences").
  Historically, rival sects of the same parent faith often clash with greater theological fury
  than completely unrelated traditions!
- HostileDoctrine: Diametrically opposed theological or warfare mandates (e.g., Holy War vs Pacifism).
"""

from __future__ import annotations
from typing import Mapping, Optional, Sequence
from minemesis.models.character import Character
from minemesis.religion.religion_models import (
    CharacterFaith,
    Religion,
    ReligiousRelationshipType,
)


def get_religious_relationship(
    rel_a: Optional[Religion],
    rel_b: Optional[Religion],
    all_religions: Mapping[str, Religion],
) -> ReligiousRelationshipType:
    """
    Classifies the doctrinal relationship between two emergent religions.
    """
    if rel_a is None or rel_b is None:
        return ReligiousRelationshipType.SIMILAR_FAITH

    if rel_a.id == rel_b.id:
        return ReligiousRelationshipType.SHARED_FAITH

    # Check for Divergent Sect: Common root ancestry in the religion family tree
    root_a = rel_a.get_root_ancestor_id(all_religions)
    root_b = rel_b.get_root_ancestor_id(all_religions)
    if root_a == root_b or rel_a.is_descendant_of(rel_b.id, all_religions) or rel_b.is_descendant_of(rel_a.id, all_religions):
        return ReligiousRelationshipType.DIVERGENT_SECT

    # Check for Hostile Doctrine: Mutually exclusive core warfare / cosmological traits
    traits_a = set(rel_a.traits.keys())
    traits_b = set(rel_b.traits.keys())

    # Check direct trait incompatibilities
    for t_id, t in rel_a.traits.items():
        for incomp in t.incompatibilities:
            if incomp in traits_b:
                return ReligiousRelationshipType.HOSTILE_DOCTRINE

    for t_id, t in rel_b.traits.items():
        for incomp in t.incompatibilities:
            if incomp in traits_a:
                return ReligiousRelationshipType.HOSTILE_DOCTRINE

    # Explicit doctrinal warfare clash
    if ("holy_war" in traits_a and "pacifism" in traits_b) or ("holy_war" in traits_b and "pacifism" in traits_a):
        return ReligiousRelationshipType.HOSTILE_DOCTRINE

    # If significant trait overlap, similar faith
    overlap = len(traits_a.intersection(traits_b))
    union = len(traits_a.union(traits_b))
    jaccard = (overlap / union) if union > 0 else 0.0

    if jaccard >= 0.35:
        return ReligiousRelationshipType.SIMILAR_FAITH

    return ReligiousRelationshipType.SIMILAR_FAITH


def calculate_religious_relationship_modifier(
    faith_a: Optional[CharacterFaith],
    faith_b: Optional[CharacterFaith],
    rel_a: Optional[Religion],
    rel_b: Optional[Religion],
    all_religions: Mapping[str, Religion],
) -> tuple[float, float, float, ReligiousRelationshipType]:
    """
    Computes (trust_offset, hatred_offset, fear_offset, relationship_type)
    for two characters based on their religious affiliations and personal devotion.
    """
    if faith_a is None or faith_b is None or rel_a is None or rel_b is None:
        return 0.0, 0.0, 0.0, ReligiousRelationshipType.SIMILAR_FAITH

    rel_type = get_religious_relationship(rel_a, rel_b, all_religions)
    dev_a = faith_a.devotion
    dev_b = faith_b.devotion
    combined_dev = (dev_a + dev_b) / 2.0

    trust_offset = 0.0
    hatred_offset = 0.0
    fear_offset = 0.0

    if rel_type == ReligiousRelationshipType.SHARED_FAITH:
        trust_offset = 15.0 * combined_dev
        hatred_offset = -10.0 * combined_dev
    elif rel_type == ReligiousRelationshipType.DIVERGENT_SECT:
        # Sectarian bitterness: apostasy is viewed more harshly than unfamiliar heathenism
        trust_offset = -20.0 * combined_dev
        hatred_offset = 18.0 * combined_dev
        fear_offset = 6.0 * combined_dev
    elif rel_type == ReligiousRelationshipType.HOSTILE_DOCTRINE:
        trust_offset = -22.0 * combined_dev
        hatred_offset = 22.0 * combined_dev
        fear_offset = 12.0 * combined_dev
    elif rel_type == ReligiousRelationshipType.SIMILAR_FAITH:
        trust_offset = 4.0 * combined_dev

    return trust_offset, hatred_offset, fear_offset, rel_type


def calculate_settlement_religious_tension(
    settlement_id: str,
    settlement_characters: Sequence[Character],
    faiths: Mapping[str, CharacterFaith],
    religions: Mapping[str, Religion],
) -> float:
    """
    Calculates the internal sectarian tension index [0.0, 100.0] of a settlement.
    Higher tension occurs when divergent sects or hostile doctrines inhabit the same community.
    """
    chars = [c for c in settlement_characters if c.alive and c.settlement_id == settlement_id]
    if len(chars) < 2:
        return 0.0

    religion_counts: dict[str, int] = {}
    for c in chars:
        f = faiths.get(c.id)
        if f:
            religion_counts[f.religion_id] = religion_counts.get(f.religion_id, 0) + 1

    if len(religion_counts) <= 1:
        return 0.0

    total_tension = 0.0
    comparisons = 0
    rel_ids = sorted(religion_counts.keys())

    for i in range(len(rel_ids)):
        for j in range(i + 1, len(rel_ids)):
            r_a = religions.get(rel_ids[i])
            r_b = religions.get(rel_ids[j])
            if r_a and r_b:
                rel_type = get_religious_relationship(r_a, r_b, religions)
                weight = (religion_counts[r_a.id] * religion_counts[r_b.id]) / (len(chars) ** 2)
                if rel_type == ReligiousRelationshipType.DIVERGENT_SECT:
                    total_tension += 80.0 * weight
                elif rel_type == ReligiousRelationshipType.HOSTILE_DOCTRINE:
                    total_tension += 100.0 * weight
                elif rel_type == ReligiousRelationshipType.SIMILAR_FAITH:
                    total_tension += 15.0 * weight
                comparisons += 1

    return min(100.0, total_tension * 4.0)
