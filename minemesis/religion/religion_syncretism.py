"""
Religious Syncretism & Doctrinal Evolution Engine (Milestone R1.5).

Operationalizes living religious evolution:
1. R1.5.1 Religious Syncretism Engine: Merging faiths (Faith A + Faith B -> Faith C).
   Example: River Cult + Mountain Ancestor Faith -> River Ancestor Faith.
2. R1.5.4 Religious Trait Exchange: Doctrinal borrowing between faiths without conversion.
3. R1.5.5 Faith Convergence: Long-term mutual assimilation between cohabiting faiths.
"""

from __future__ import annotations
from typing import Any, Mapping, Optional, Sequence
from minemesis.core.rng import KeyedRNG
from minemesis.models.character import Character
from minemesis.religion.religion_models import (
    CharacterFaith,
    Religion,
    ReligionTrait,
    ReligiousRole,
)


def calculate_jaccard_similarity(rel_a: Religion, rel_b: Religion) -> float:
    """Calculates Jaccard trait similarity index between two religions."""
    set_a = set(rel_a.traits.keys())
    set_b = set(rel_b.traits.keys())
    union = set_a.union(set_b)
    if not union:
        return 0.0
    return len(set_a.intersection(set_b)) / len(union)


def evaluate_doctrinal_borrowing(
    donor_rel: Religion,
    recipient_rel: Religion,
    all_traits: Mapping[str, ReligionTrait],
    tick: int,
    rng: KeyedRNG,
) -> Optional[dict[str, Any]]:
    """
    R1.5.4: Recipient faith adopts an idea / trait from donor faith without converting.
    """
    if donor_rel.id == recipient_rel.id:
        return None

    # Find candidate traits present in donor but not recipient
    candidates = []
    recipient_traits = set(recipient_rel.traits.keys())

    for t_id, trait in sorted(donor_rel.traits.items()):
        if t_id not in recipient_traits:
            # Check incompatibility with recipient's existing traits
            has_incompatibility = any(
                incomp in recipient_traits or t_id in recipient_rel.traits[rt_id].incompatibilities
                for incomp in trait.incompatibilities
                for rt_id in recipient_traits
            )
            if not has_incompatibility:
                candidates.append(trait)

    if not candidates:
        return None

    borrowed_trait = rng.choice(candidates)
    recipient_rel.add_trait(borrowed_trait)
    recipient_rel.borrowed_traits[borrowed_trait.id] = donor_rel.id

    return {
        "recipient_religion_id": recipient_rel.id,
        "recipient_religion_name": recipient_rel.name,
        "donor_religion_id": donor_rel.id,
        "donor_religion_name": donor_rel.name,
        "borrowed_trait_id": borrowed_trait.id,
        "borrowed_trait_name": borrowed_trait.name,
        "tick": tick,
    }


def evaluate_syncretic_fusion(
    rel_a: Religion,
    rel_b: Religion,
    settlement_id: str,
    settlement_characters: Sequence[Character],
    faiths: dict[str, CharacterFaith],
    all_traits: Mapping[str, ReligionTrait],
    rel_counter: list[int],
    tick: int,
    rng: KeyedRNG,
) -> Optional[tuple[Religion, dict[str, Any]]]:
    """
    R1.5.1: Merges two cohabiting religions in a settlement into a novel syncretic faith.
    Faith A + Faith B -> Faith C.
    """
    if rel_a.id == rel_b.id:
        return None

    # Check local adherents of both in the settlement
    adherents_a = [
        c.id for c in settlement_characters
        if c.alive and c.settlement_id == settlement_id and c.id in faiths and faiths[c.id].religion_id == rel_a.id
    ]
    adherents_b = [
        c.id for c in settlement_characters
        if c.alive and c.settlement_id == settlement_id and c.id in faiths and faiths[c.id].religion_id == rel_b.id
    ]

    if len(adherents_a) < 2 or len(adherents_b) < 2:
        return None

    # Combine non-conflicting traits
    merged_traits: dict[str, ReligionTrait] = {}
    combined_trait_pool = list(rel_a.traits.values()) + list(rel_b.traits.values())
    combined_trait_pool.sort(key=lambda t: t.id)

    for t in combined_trait_pool:
        # Check incompatibility with already added traits
        conflict = any(
            incomp in merged_traits or t.id in merged_traits[mt_id].incompatibilities
            for incomp in t.incompatibilities
            for mt_id in merged_traits
        )
        if not conflict:
            merged_traits[t.id] = t

    if len(merged_traits) < 3:
        return None

    r_idx = rel_counter[0]
    rel_counter[0] += 1
    syncretic_id = f"rel_syncretic_{r_idx}"

    # Procedural Syncretic Name synthesis
    prefixes = ["United", "Harmonious", "Syncretic", "Eternal Way of", "Sacred Union of"]
    prefix = rng.choice(prefixes)
    short_a = rel_a.name.split()[-1]
    short_b = rel_b.name.split()[-1]
    syncretic_name = f"{prefix} {short_a} and {short_b}"

    # Converts in settlement
    all_converts = sorted(list(set(adherents_a + adherents_b)))

    # Dedup objects by ID
    seen_sites: set[str] = set()
    combined_sites = []
    for s in rel_a.holy_sites + rel_b.holy_sites:
        if s.id not in seen_sites:
            seen_sites.add(s.id)
            combined_sites.append(s)

    seen_saints: set[str] = set()
    combined_saints = []
    for st in rel_a.saints + rel_b.saints:
        if st.character_id not in seen_saints:
            seen_saints.add(st.character_id)
            combined_saints.append(st)

    seen_figs: set[str] = set()
    combined_figs = []
    for fg in rel_a.figures + rel_b.figures:
        if fg.id not in seen_figs:
            seen_figs.add(fg.id)
            combined_figs.append(fg)

    seen_myths: set[str] = set()
    combined_myths = []
    for my in rel_a.myths + rel_b.myths:
        if my.myth_id not in seen_myths:
            seen_myths.add(my.myth_id)
            combined_myths.append(my)

    syncretic_religion = Religion(
        id=syncretic_id,
        name=syncretic_name,
        parent_religion_id=rel_a.id,
        child_religion_ids=[],
        syncretic_parents=[rel_a.id, rel_b.id],
        borrowed_traits={},
        absorbed_folk_traditions=sorted(list(set(rel_a.absorbed_folk_traditions + rel_b.absorbed_folk_traditions))),
        regional_profiles={},
        cultural_traditions=sorted(list(set(rel_a.cultural_traditions + rel_b.cultural_traditions))),
        founded_tick=tick,
        founded_year=(tick // 12) + 1,
        traits=merged_traits,
        adherents=set(all_converts),
        dominant_settlements=set(),
        schisms=[],
        reforms=[],
        generation=max(rel_a.generation, rel_b.generation) + 1,
        holy_sites=combined_sites,
        saints=combined_saints,
        figures=combined_figs,
        myths=combined_myths,
        scripture_name=f"The Sacred Synthesis of {rel_a.name} and {rel_b.name}",
        reformation_level=0,
    )

    # Register child pointers on parents
    rel_a.child_religion_ids.append(syncretic_religion.id)
    rel_b.child_religion_ids.append(syncretic_religion.id)

    # Convert characters
    for c_id in all_converts:
        f = faiths[c_id]
        f.former_religion_ids.append(f.religion_id)
        f.religion_id = syncretic_religion.id
        f.conversion_tick = tick
        f.devotion = min(1.0, round(f.devotion + 0.1, 3))

    event_payload = {
        "syncretic_religion_id": syncretic_religion.id,
        "syncretic_religion_name": syncretic_religion.name,
        "parent_rel_a_id": rel_a.id,
        "parent_rel_a_name": rel_a.name,
        "parent_rel_b_id": rel_b.id,
        "parent_rel_b_name": rel_b.name,
        "settlement_id": settlement_id,
        "convert_count": len(all_converts),
        "traits": [t.name for t in merged_traits.values()],
    }

    return syncretic_religion, event_payload
