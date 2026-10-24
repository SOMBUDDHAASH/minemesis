"""
Religious Evolution, Schisms, and Canonization for the Standalone Religion Engine (Milestone R0).

Core Philosophy:
- Religions evolve through historical pressure.
- Famous deaths create saints; crises inspire reformations; ideological tensions trigger schisms.
- All sects track their ancestry via parent_religion_id.
"""

from __future__ import annotations
from typing import Any, Mapping, Sequence
from minemesis.core.rng import KeyedRNG
from minemesis.religion.religion_models import (
    CharacterFaith,
    HolySite,
    Religion,
    ReligiousRole,
    Saint,
    TraitCategory,
)
from minemesis.religion.religion_traits import (
    get_all_traits,
    get_traits_by_category,
    is_trait_set_coherent,
)


_SAINT_TITLES = [
    "The Martyr", "The Steadfast", "The Merciful", "The Unyielding",
    "The Compassionate", "The Seer", "The Pure", "The Peacemaker",
    "The Ascetic", "The Righteous", "The Anchor of Faith",
]

_SECT_PREFIXES = [
    "Reformed", "Orthodox", "True", "Ascetic", "Eternal", "Covenant of the",
    "New Dawn of the", "Disciples of the",
]


def check_and_canonize_saint(
    deceased_char: Any,
    deceased_faith: CharacterFaith | None,
    religion: Religion | None,
    cause_of_death: str,
    tick: int,
    rng: KeyedRNG,
) -> tuple[Saint, Religion] | None:
    """
    Evaluates whether a deceased devout character is canonized as a Saint.
    """
    if not deceased_faith or not religion:
        return None

    if deceased_faith.devotion < 0.80:
        return None

    # Martyrdom or holy defense increases saint probability
    is_violent = cause_of_death in ("Raid", "MilitaryAction", "Revenge", "Starvation")
    base_chance = 0.4 if is_violent else 0.15

    if religion.has_trait("martyrdom_glory"):
        base_chance += 0.35

    if rng.random() < base_chance:
        title = rng.choice(_SAINT_TITLES)
        deed = f"Slain in {cause_of_death} during service to {religion.name}" if is_violent else f"Departed in pious devotion to {religion.name}"
        saint = Saint(
            character_id=deceased_char.id,
            character_name=deceased_char.name,
            title=title,
            canonized_tick=tick,
            deed=deed,
        )
        religion.saints.append(saint)
        return saint, religion

    return None


def trigger_religious_reformation(
    religion: Religion,
    trigger_cause: str,
    tick: int,
    rng: KeyedRNG,
) -> tuple[str, str] | None:
    """
    Mutates a religion by acquiring a new theological trait in response to historical crises.
    Returns (added_trait_id, description) if mutation succeeds.
    """
    all_traits = get_all_traits()
    rng.shuffle(all_traits)

    # Find a candidate trait that is not already present and is coherent with current traits
    for cand in all_traits:
        if cand.id not in religion.traits:
            current_traits = list(religion.traits.values())
            if is_trait_set_coherent(current_traits + [cand]):
                religion.add_trait(cand)
                religion.reformation_level += 1
                desc = f"{religion.name} adopted trait '{cand.name}' following {trigger_cause} (Reformation #{religion.reformation_level})"
                return cand.id, desc

    return None


def trigger_religious_schism(
    parent_religion: Religion,
    schism_settlement_id: str,
    instigator_character_id: str,
    living_characters: Sequence[Any],
    faiths: dict[str, CharacterFaith],
    new_rel_counter: int,
    tick: int,
    rng: KeyedRNG,
) -> tuple[Religion, list[str]] | None:
    """
    Spawns a new sect / daughter religion from an existing faith.
    Returns (new_religion, list_of_converted_character_ids).
    """
    child_id = f"rel_{new_rel_counter}"
    
    # Form sect name
    prefix = rng.choice(_SECT_PREFIXES)
    if prefix.endswith("of the"):
        child_name = f"{prefix} {parent_religion.name.replace('Faith of the ', '').replace('Children of the ', '')}"
    else:
        child_name = f"{prefix} {parent_religion.name}"

    # Inherit parent traits
    inherited_traits = dict(parent_religion.traits)

    # Drop 1 trait if large, and add 1 new distinct trait
    if len(inherited_traits) >= 5:
        drop_id = rng.choice(list(inherited_traits.keys()))
        del inherited_traits[drop_id]

    # Find a distinct candidate trait
    all_traits = get_all_traits()
    rng.shuffle(all_traits)
    for cand in all_traits:
        if cand.id not in inherited_traits:
            if is_trait_set_coherent(list(inherited_traits.values()) + [cand]):
                inherited_traits[cand.id] = cand
                break

    # Build new daughter religion
    child_religion = Religion(
        id=child_id,
        name=child_name,
        parent_religion_id=parent_religion.id,
        founded_tick=tick,
        founded_year=(tick // 12) + 1,
        traits=inherited_traits,
        adherents=set(),
        dominant_settlements=set(),
        schisms=[],
        holy_sites=[],
        saints=list(parent_religion.saints),  # shares ancestral saints
        scripture_name=f"The Revised {parent_religion.scripture_name or 'Book'}",
        reformation_level=parent_religion.reformation_level + 1,
    )

    parent_religion.schisms.append(child_id)

    # Convert instigator and a faction of adherents in the schism settlement
    converted_ids = []
    instigator_faith = faiths.get(instigator_character_id)
    if instigator_faith:
        instigator_faith.religion_id = child_id
        instigator_faith.devotion = 0.95
        instigator_faith.role = ReligiousRole.PROPHET
        instigator_faith.conversion_tick = tick
        converted_ids.append(instigator_character_id)

    # Convert others in the settlement who followed the parent religion
    for c in living_characters:
        if c.id == instigator_character_id:
            continue
        c_faith = faiths.get(c.id)
        if c_faith and c_faith.religion_id == parent_religion.id and c.settlement_id == schism_settlement_id:
            if rng.random() < 0.65:  # high local conversion in dissident town
                c_faith.religion_id = child_id
                c_faith.devotion = round(rng.uniform(0.6, 0.85), 3)
                c_faith.conversion_tick = tick
                converted_ids.append(c.id)

    return child_religion, converted_ids
