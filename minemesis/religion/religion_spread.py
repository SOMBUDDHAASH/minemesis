"""
Religious Spread and Conversion Mechanics for the Standalone Religion Engine (Milestone R0 & R1).

Core Philosophy:
- Faith spreads through social, familial, economic, and geographic channels.
- Religion is independent of political borders; a settlement can have religious minorities,
  inter-faith households, or shift dominant religions over centuries.
- R1.9 Dynamic Spread Mechanisms:
  1. Family Lineage
  2. Interfaith Marriage
  3. Trade Route Evangelism
  4. Clergy & Missionary Preaching
  5. Pilgrimage Journeys
  6. Religious Refugee Flight
  7. Holy War / Conquest Conversion
  8. Saint Cult Devotion
"""

from __future__ import annotations
from typing import Any, Mapping, Optional, Sequence
from minemesis.core.rng import KeyedRNG
from minemesis.models.character import Character
from minemesis.models.settlement import Settlement
from minemesis.religion.religion_config import (
    CHILD_INHERITANCE_CHANCE,
    MARRIAGE_CONVERSION_CHANCE,
    MISSIONARY_PROSELYTIZE_CHANCE,
    PILGRIMAGE_CHANCE,
    REFUGEE_FLIGHT_TENSION_THRESHOLD,
    SAINT_CULT_CONVERSION_CHANCE,
    TRADE_ROUTE_SPREAD_CHANCE,
)
from minemesis.religion.religion_models import (
    CharacterFaith,
    HolySite,
    Religion,
    ReligiousRole,
)


def process_family_faith_inheritance(
    child_id: str,
    father_faith: CharacterFaith | None,
    mother_faith: CharacterFaith | None,
    settlement_dominant_rel_id: str | None,
    rng: KeyedRNG,
    tick: int,
) -> CharacterFaith | None:
    """Assigns religious affiliation to a newborn child based on parents' faith."""
    if father_faith and mother_faith and father_faith.religion_id == mother_faith.religion_id:
        devotion = round(rng.uniform(0.7, 0.9), 3)
        return CharacterFaith(
            character_id=child_id,
            religion_id=father_faith.religion_id,
            devotion=devotion,
            religious_standing=50.0,
            conversion_tick=tick,
            role=ReligiousRole.LAITY,
        )

    if father_faith and mother_faith:
        chosen = father_faith if father_faith.devotion > mother_faith.devotion else mother_faith
        if father_faith.devotion == mother_faith.devotion:
            chosen = father_faith if rng.random() < 0.5 else mother_faith
        devotion = round(rng.uniform(0.5, 0.75), 3)
        return CharacterFaith(
            character_id=child_id,
            religion_id=chosen.religion_id,
            devotion=devotion,
            religious_standing=50.0,
            conversion_tick=tick,
            role=ReligiousRole.LAITY,
        )

    parent = father_faith or mother_faith
    if parent and rng.random() < CHILD_INHERITANCE_CHANCE:
        devotion = round(rng.uniform(0.6, 0.8), 3)
        return CharacterFaith(
            character_id=child_id,
            religion_id=parent.religion_id,
            devotion=devotion,
            religious_standing=50.0,
            conversion_tick=tick,
            role=ReligiousRole.LAITY,
        )

    if settlement_dominant_rel_id:
        return CharacterFaith(
            character_id=child_id,
            religion_id=settlement_dominant_rel_id,
            devotion=round(rng.uniform(0.4, 0.65), 3),
            religious_standing=50.0,
            conversion_tick=tick,
            role=ReligiousRole.LAITY,
        )

    return None


def process_marriage_conversion(
    spouse1_faith: CharacterFaith,
    spouse2_faith: CharacterFaith,
    rng: KeyedRNG,
    tick: int,
) -> tuple[str, str, str] | None:
    """Evaluates whether an inter-faith marriage leads to conversion of the less devout spouse."""
    if spouse1_faith.religion_id == spouse2_faith.religion_id:
        return None

    diff = abs(spouse1_faith.devotion - spouse2_faith.devotion)
    chance = MARRIAGE_CONVERSION_CHANCE + (diff * 0.1)

    if rng.random() < chance:
        if spouse1_faith.devotion > spouse2_faith.devotion:
            old_rel = spouse2_faith.religion_id
            spouse2_faith.former_religion_ids.append(old_rel)
            spouse2_faith.religion_id = spouse1_faith.religion_id
            spouse2_faith.devotion = round(spouse1_faith.devotion * 0.8, 3)
            spouse2_faith.conversion_tick = tick
            return (spouse2_faith.character_id, old_rel, spouse1_faith.religion_id)
        else:
            old_rel = spouse1_faith.religion_id
            spouse1_faith.former_religion_ids.append(old_rel)
            spouse1_faith.religion_id = spouse2_faith.religion_id
            spouse1_faith.devotion = round(spouse2_faith.devotion * 0.8, 3)
            spouse1_faith.conversion_tick = tick
            return (spouse1_faith.character_id, old_rel, spouse2_faith.religion_id)

    return None


def process_trade_route_evangelism(
    characters_in_town: Sequence[Any],
    faiths: dict[str, CharacterFaith],
    foreign_dominant_rel_id: str,
    rng: KeyedRNG,
    tick: int,
) -> tuple[str, str, str] | None:
    """Active trade corridors expose locals to foreign faith ideas."""
    if not characters_in_town:
        return None

    candidates = [
        c for c in characters_in_town
        if c.alive and faiths.get(c.id) and faiths[c.id].religion_id != foreign_dominant_rel_id
    ]
    if not candidates:
        return None

    target = rng.choice(candidates)
    c_faith = faiths[target.id]

    conversion_prob = TRADE_ROUTE_SPREAD_CHANCE * (1.0 - c_faith.devotion)
    if rng.random() < conversion_prob:
        old_rel = c_faith.religion_id
        c_faith.former_religion_ids.append(old_rel)
        c_faith.religion_id = foreign_dominant_rel_id
        c_faith.devotion = round(rng.uniform(0.35, 0.55), 3)
        c_faith.conversion_tick = tick
        return (target.id, old_rel, foreign_dominant_rel_id)

    return None


def process_clergy_missionary_work(
    clergy_char_id: str,
    settlement_characters: Sequence[Any],
    faiths: dict[str, CharacterFaith],
    rng: KeyedRNG,
    tick: int,
) -> tuple[str, str, str] | None:
    """Clergy (Priests, Prophets, Monks, Shamans) actively preach to citizens in their settlement."""
    clergy_faith = faiths.get(clergy_char_id)
    if not clergy_faith:
        return None

    potential_converts = [
        c for c in settlement_characters
        if c.alive and c.id != clergy_char_id and faiths.get(c.id) and faiths[c.id].religion_id != clergy_faith.religion_id
    ]

    if potential_converts and rng.random() < MISSIONARY_PROSELYTIZE_CHANCE:
        target = rng.choice(potential_converts)
        t_faith = faiths[target.id]
        if rng.random() < (clergy_faith.devotion * (1.0 - t_faith.devotion)):
            old_rel = t_faith.religion_id
            t_faith.former_religion_ids.append(old_rel)
            t_faith.religion_id = clergy_faith.religion_id
            t_faith.devotion = round(rng.uniform(0.4, 0.7), 3)
            t_faith.conversion_tick = tick
            return (target.id, old_rel, clergy_faith.religion_id)

    return None


def process_religious_refugee_migration(
    settlement_id: str,
    settlement_tension: float,
    settlement_characters: Sequence[Character],
    settlements: Mapping[str, Settlement],
    faiths: dict[str, CharacterFaith],
    dominant_by_settlement: Mapping[str, str],
    rng: KeyedRNG,
    tick: int,
) -> Optional[tuple[Character, str, str, str]]:
    """
    R1.9: Minority adherents fleeing severe sectarian tension migrate to a settlement
    where their religion is dominant or safe.
    Returns (refugee_character, old_settlement_id, new_settlement_id, religion_id)
    """
    if settlement_tension < REFUGEE_FLIGHT_TENSION_THRESHOLD:
        return None

    dom_rel = dominant_by_settlement.get(settlement_id)
    minority_adherents = [
        c for c in settlement_characters
        if c.alive and c.settlement_id == settlement_id and c.id in faiths and faiths[c.id].religion_id != dom_rel
    ]
    if not minority_adherents:
        return None

    refugee = rng.choice(minority_adherents)
    r_faith = faiths[refugee.id]

    # Find candidate sanctuary settlements where their faith is dominant or present
    candidate_sanctuaries = [
        s_id for s_id, d_rel in dominant_by_settlement.items()
        if s_id != settlement_id and d_rel == r_faith.religion_id
    ]
    if not candidate_sanctuaries:
        # Fallback to any other settlement
        other_settlements = [s_id for s_id in settlements.keys() if s_id != settlement_id]
        if other_settlements:
            candidate_sanctuaries = other_settlements

    if candidate_sanctuaries:
        target_settlement = rng.choice(candidate_sanctuaries)
        old_settlement = refugee.settlement_id
        # Religious asylum/sanctuary sought in destination settlement
        return (refugee, old_settlement, target_settlement, r_faith.religion_id)

    return None


def process_conquest_conversion(
    conquering_settlement_id: str,
    target_settlement_id: str,
    living_target_chars: Sequence[Character],
    faiths: dict[str, CharacterFaith],
    dominant_by_settlement: Mapping[str, str],
    religions: Mapping[str, Religion],
    rng: KeyedRNG,
    tick: int,
) -> list[tuple[str, str, str]]:
    """
    R1.9: Holy War conquest / raid imposes faith on defeated survivors.
    """
    conqueror_rel_id = dominant_by_settlement.get(conquering_settlement_id)
    if not conqueror_rel_id or conqueror_rel_id not in religions:
        return []

    conqueror_rel = religions[conqueror_rel_id]
    if "holy_war" not in conqueror_rel.traits and "warrior_tradition" not in conqueror_rel.traits:
        return []

    converts: list[tuple[str, str, str]] = []
    candidates = [
        c for c in living_target_chars
        if c.alive and c.settlement_id == target_settlement_id and c.id in faiths and faiths[c.id].religion_id != conqueror_rel_id
    ]

    for victim in candidates:
        v_faith = faiths[victim.id]
        # Low devotion or fear leads to forced conversion
        if rng.random() < 0.40 * (1.0 - v_faith.devotion):
            old_rel = v_faith.religion_id
            v_faith.former_religion_ids.append(old_rel)
            v_faith.religion_id = conqueror_rel_id
            v_faith.devotion = round(rng.uniform(0.3, 0.5), 3)
            v_faith.conversion_tick = tick
            converts.append((victim.id, old_rel, conqueror_rel_id))

    return converts


def process_saint_cult_conversions(
    religion: Religion,
    settlement_characters: Sequence[Character],
    faiths: dict[str, CharacterFaith],
    rng: KeyedRNG,
    tick: int,
) -> list[tuple[str, str, str]]:
    """
    R1.9: Local veneration of a deceased saint/martyr inspires conversions among neighboring folk.
    """
    if not religion.saints:
        return []

    converts: list[tuple[str, str, str]] = []
    candidates = [
        c for c in settlement_characters
        if c.alive and c.id in faiths and faiths[c.id].religion_id != religion.id and faiths[c.id].devotion < 0.5
    ]

    if candidates and rng.random() < SAINT_CULT_CONVERSION_CHANCE:
        chosen = rng.choice(candidates)
        c_faith = faiths[chosen.id]
        old_rel = c_faith.religion_id
        c_faith.former_religion_ids.append(old_rel)
        c_faith.religion_id = religion.id
        c_faith.devotion = round(rng.uniform(0.45, 0.70), 3)
        c_faith.conversion_tick = tick
        converts.append((chosen.id, old_rel, religion.id))

    return converts


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
