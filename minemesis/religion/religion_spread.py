"""
Religious Spread and Conversion Mechanics for the Standalone Religion Engine (Milestone R0).

Core Philosophy:
- Faith spreads through social, familial, economic, and geographic channels.
- Religion is independent of political borders; a settlement can have religious minorities,
  inter-faith households, or shift dominant religions over centuries.
"""

from __future__ import annotations
import random
from typing import Any, Mapping, Sequence
from minemesis.religion.religion_config import (
    CHILD_INHERITANCE_CHANCE,
    MARRIAGE_CONVERSION_CHANCE,
    MISSIONARY_PROSELYTIZE_CHANCE,
    PILGRIMAGE_CHANCE,
    TRADE_ROUTE_SPREAD_CHANCE,
)
from minemesis.religion.religion_models import CharacterFaith, Religion, ReligiousRole


def process_family_faith_inheritance(
    child_id: str,
    father_faith: CharacterFaith | None,
    mother_faith: CharacterFaith | None,
    settlement_dominant_rel_id: str | None,
    rng: random.Random,
    tick: int,
) -> CharacterFaith | None:
    """
    Assigns religious affiliation to a newborn child based on parents' faith.
    """
    if father_faith and mother_faith and father_faith.religion_id == mother_faith.religion_id:
        # Both parents share faith: strong socialization
        devotion = round(rng.uniform(0.7, 0.9), 3)
        return CharacterFaith(
            character_id=child_id,
            religion_id=father_faith.religion_id,
            devotion=devotion,
            conversion_tick=tick,
            role=ReligiousRole.LAITY,
        )

    if father_faith and mother_faith:
        # Interfaith parents: choose based on higher devotion or coin flip
        chosen = father_faith if father_faith.devotion > mother_faith.devotion else mother_faith
        if father_faith.devotion == mother_faith.devotion:
            chosen = father_faith if rng.random() < 0.5 else mother_faith
        devotion = round(rng.uniform(0.5, 0.75), 3)
        return CharacterFaith(
            character_id=child_id,
            religion_id=chosen.religion_id,
            devotion=devotion,
            conversion_tick=tick,
            role=ReligiousRole.LAITY,
        )

    # Single parent or local dominant faith fallback
    parent = father_faith or mother_faith
    if parent and rng.random() < CHILD_INHERITANCE_CHANCE:
        devotion = round(rng.uniform(0.6, 0.8), 3)
        return CharacterFaith(
            character_id=child_id,
            religion_id=parent.religion_id,
            devotion=devotion,
            conversion_tick=tick,
            role=ReligiousRole.LAITY,
        )

    if settlement_dominant_rel_id:
        return CharacterFaith(
            character_id=child_id,
            religion_id=settlement_dominant_rel_id,
            devotion=round(rng.uniform(0.4, 0.65), 3),
            conversion_tick=tick,
            role=ReligiousRole.LAITY,
        )

    return None


def process_marriage_conversion(
    spouse1_faith: CharacterFaith,
    spouse2_faith: CharacterFaith,
    rng: random.Random,
    tick: int,
) -> tuple[str, str, str] | None:
    """
    Evaluates whether an inter-faith marriage leads to conversion of the less devout spouse.
    Returns (converting_char_id, old_rel_id, new_rel_id) if conversion occurs, else None.
    """
    if spouse1_faith.religion_id == spouse2_faith.religion_id:
        return None

    # Determine who is more devout
    diff = abs(spouse1_faith.devotion - spouse2_faith.devotion)
    chance = MARRIAGE_CONVERSION_CHANCE + (diff * 0.1)

    if rng.random() < chance:
        if spouse1_faith.devotion > spouse2_faith.devotion:
            # Spouse 2 converts to Spouse 1's faith
            old_rel = spouse2_faith.religion_id
            spouse2_faith.religion_id = spouse1_faith.religion_id
            spouse2_faith.devotion = round(spouse1_faith.devotion * 0.8, 3)
            spouse2_faith.conversion_tick = tick
            return (spouse2_faith.character_id, old_rel, spouse1_faith.religion_id)
        else:
            # Spouse 1 converts to Spouse 2's faith
            old_rel = spouse1_faith.religion_id
            spouse1_faith.religion_id = spouse2_faith.religion_id
            spouse1_faith.devotion = round(spouse2_faith.devotion * 0.8, 3)
            spouse1_faith.conversion_tick = tick
            return (spouse1_faith.character_id, old_rel, spouse2_faith.religion_id)

    return None


def process_trade_route_evangelism(
    characters_in_town: Sequence[Any],
    faiths: dict[str, CharacterFaith],
    foreign_dominant_rel_id: str,
    rng: random.Random,
    tick: int,
) -> tuple[str, str, str] | None:
    """
    Active trade corridors expose locals to foreign faith ideas.
    A local character with low devotion may convert.
    """
    if not characters_in_town:
        return None

    # Filter candidates who do not already follow the foreign faith
    candidates = [c for c in characters_in_town if c.alive and faiths.get(c.id) and faiths[c.id].religion_id != foreign_dominant_rel_id]
    if not candidates:
        return None

    target = rng.choice(candidates)
    c_faith = faiths[target.id]

    # Lower devotion means easier persuasion
    conversion_prob = TRADE_ROUTE_SPREAD_CHANCE * (1.0 - c_faith.devotion)
    if rng.random() < conversion_prob:
        old_rel = c_faith.religion_id
        c_faith.religion_id = foreign_dominant_rel_id
        c_faith.devotion = round(rng.uniform(0.35, 0.55), 3)
        c_faith.conversion_tick = tick
        return (target.id, old_rel, foreign_dominant_rel_id)

    return None


def process_clergy_missionary_work(
    clergy_char_id: str,
    settlement_characters: Sequence[Any],
    faiths: dict[str, CharacterFaith],
    rng: random.Random,
    tick: int,
) -> tuple[str, str, str] | None:
    """
    Clergy (Priests, Prophets, Monks, Shamans) actively preach to citizens in their settlement.
    """
    clergy_faith = faiths.get(clergy_char_id)
    if not clergy_faith:
        return None

    # Look for living citizens who follow another faith or are lukewarm
    potential_converts = [
        c for c in settlement_characters
        if c.alive and c.id != clergy_char_id and faiths.get(c.id) and faiths[c.id].religion_id != clergy_faith.religion_id
    ]

    if potential_converts and rng.random() < MISSIONARY_PROSELYTIZE_CHANCE:
        target = rng.choice(potential_converts)
        t_faith = faiths[target.id]
        if rng.random() < (clergy_faith.devotion * (1.0 - t_faith.devotion)):
            old_rel = t_faith.religion_id
            t_faith.religion_id = clergy_faith.religion_id
            t_faith.devotion = round(rng.uniform(0.4, 0.7), 3)
            t_faith.conversion_tick = tick
            return (target.id, old_rel, clergy_faith.religion_id)

    return None


def update_settlement_dominant_religions(
    settlements: Mapping[str, Any],
    living_characters: Sequence[Any],
    faiths: Mapping[str, CharacterFaith],
    religions: dict[str, Religion],
) -> dict[str, str]:
    """
    Recalculates the dominant religion for each settlement and updates Religion.dominant_settlements.
    Returns mapping {settlement_id: dominant_religion_id}.
    """
    settlement_counts: dict[str, dict[str, int]] = {s_id: {} for s_id in settlements.keys()}
    
    # Reset adherents on religions
    for r in religions.values():
        r.adherents.clear()
        r.dominant_settlements.clear()

    for c in living_characters:
        if not c.alive:
            continue
        c_faith = faiths.get(c.id)
        if not c_faith:
            continue
        rel = religions.get(c_faith.religion_id)
        if rel:
            rel.adherents.add(c.id)
            if c.settlement_id in settlement_counts:
                counts = settlement_counts[c.settlement_id]
                counts[rel.id] = counts.get(rel.id, 0) + 1

    dominant_by_settlement: dict[str, str] = {}
    for s_id, counts in settlement_counts.items():
        if counts:
            best_rel_id = max(counts.items(), key=lambda x: x[1])[0]
            dominant_by_settlement[s_id] = best_rel_id
            if best_rel_id in religions:
                religions[best_rel_id].dominant_settlements.add(s_id)

    # Check for religious extinction
    for r in religions.values():
        if len(r.adherents) == 0:
            r.is_extinct = True

    return dominant_by_settlement
