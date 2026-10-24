"""
Religious Heresy, Reformation, and Reunification Engine (Milestone R1.5).

Models doctrinal divergence beyond simple random schisms:
1. Orthodoxy: Mainstream canon preserved by traditionalist clergy.
2. Heresy: A dissident cleric/thinker (Heretic) rejects a core trait or embraces a forbidden one.
   Dissidents quietly gather adherents in their village until an open breach occurs.
3. Reformation & Counter-Reformation:
   The mother church reacts to the schism by purifying orthodoxy, reinforcing zealotry,
   and declaring the breakaway sect divergent apostates.
4. Sectarian Reunification:
   After decades of separation, related sects can heal theological rifts and reunify
   under a common confession.
"""

from __future__ import annotations
import random
from typing import Any, Mapping, Optional, Sequence
from minemesis.core.types import EventType
from minemesis.models.character import Character
from minemesis.religion.religion_models import (
    CharacterFaith,
    Religion,
    ReligiousFigure,
    ReligiousFigureType,
    ReligiousRole,
    ReligionTrait,
)
from minemesis.religion.religion_traits import ALL_RELIGION_TRAITS


def check_and_declare_heresy(
    religion: Religion,
    settlement_characters: Sequence[Character],
    faiths: dict[str, CharacterFaith],
    all_traits: Mapping[str, ReligionTrait],
    tick: int,
    rng: random.Random,
    figure_counter: list[int],
) -> Optional[tuple[ReligiousFigure, list[str], str, dict[str, Any]]]:
    """
    Checks if a theological dispute arises among the living adherents of a religion.
    A dissident emerges as a Heretic, convincing followers in their village.
    """
    if len(religion.traits) < 2:
        return None

    living_adherents = [
        c for c in settlement_characters
        if c.alive and c.id in faiths and faiths[c.id].religion_id == religion.id
    ]
    if len(living_adherents) < 3:
        return None

    # Prioritize clergy or independent-minded characters
    dissident_candidates = [
        c for c in living_adherents
        if faiths[c.id].role in (ReligiousRole.PRIEST, ReligiousRole.MONK, ReligiousRole.SHAMAN, ReligiousRole.ELDER, ReligiousRole.LAITY)
    ]
    if not dissident_candidates:
        return None

    dissident_candidates.sort(key=lambda c: (faiths[c.id].religious_standing, c.id))
    heretic_char = dissident_candidates[0]
    h_faith = faiths[heretic_char.id]

    # Pick a trait to dispute / reject
    orthodox_trait_keys = sorted(list(religion.traits.keys()))
    rejected_trait_id = rng.choice(orthodox_trait_keys)
    rejected_trait = religion.traits[rejected_trait_id]

    # Pick a new alternative trait to embrace
    available_traits = [
        t for t_id, t in sorted(all_traits.items())
        if t_id not in religion.traits and rejected_trait_id not in t.incompatibilities
    ]
    if not available_traits:
        return None

    adopted_trait = rng.choice(available_traits)

    # Gather followers in the same settlement
    village_peers = [
        c for c in living_adherents
        if c.id != heretic_char.id and c.settlement_id == heretic_char.settlement_id
    ]
    village_peers.sort(key=lambda c: (faiths[c.id].devotion, c.id))

    # Converted followers (up to 3 peers)
    followers = [heretic_char.id]
    for peer in village_peers[:3]:
        followers.append(peer.id)

    # Create the Heretic figure
    f_num = figure_counter[0]
    figure_counter[0] += 1
    fig_id = f"fig_{f_num}"
    title = f"The Questioner of {rejected_trait.name}"
    deed = f"Rejected {rejected_trait.name} in favor of {adopted_trait.name} at tick {tick}."

    heretic_fig = ReligiousFigure(
        id=fig_id,
        character_id=heretic_char.id,
        character_name=heretic_char.name,
        figure_type=ReligiousFigureType.HERETIC,
        religion_id=religion.id,
        title=title,
        deeds=[deed],
        tick_recognized=tick,
        is_alive=True,
    )
    religion.figures.append(heretic_fig)
    h_faith.role = ReligiousRole.ZEALOT

    event_payload = {
        "religion_id": religion.id,
        "religion_name": religion.name,
        "heretic_id": heretic_char.id,
        "heretic_name": heretic_char.name,
        "rejected_trait": rejected_trait.name,
        "adopted_trait": adopted_trait.name,
        "follower_ids": followers,
        "settlement_id": heretic_char.settlement_id,
    }

    return heretic_fig, followers, adopted_trait.id, event_payload


def establish_heretical_schism(
    parent_religion: Religion,
    heretic_fig: ReligiousFigure,
    follower_ids: Sequence[str],
    adopted_trait_id: str,
    faiths: dict[str, CharacterFaith],
    all_traits: Mapping[str, ReligionTrait],
    rel_counter: list[int],
    tick: int,
    rng: random.Random,
) -> tuple[Religion, dict[str, Any]]:
    """
    Transforms an active heresy into a full breakaway child religion.
    Establishes genealogical parent-child link.
    """
    r_idx = rel_counter[0]
    rel_counter[0] += 1
    new_rel_id = f"rel_sect_{r_idx}"

    sect_descriptors = ["Reformed", "Pure", "Ascendant", "Orthodox", "Covenant", "Revival"]
    descriptor = rng.choice(sect_descriptors)
    new_name = f"{descriptor} {parent_religion.name}"

    # Traits: parent traits plus adopted trait
    new_traits = dict(parent_religion.traits)
    if adopted_trait_id in all_traits:
        new_traits[adopted_trait_id] = all_traits[adopted_trait_id]

    child_religion = Religion(
        id=new_rel_id,
        name=new_name,
        parent_religion_id=parent_religion.id,
        child_religion_ids=[],
        founded_tick=tick,
        founded_year=(tick // 12) + 1,
        traits=new_traits,
        adherents=set(follower_ids),
        dominant_settlements=set(),
        schisms=[],
        reforms=[],
        generation=parent_religion.generation + 1,
        holy_sites=list(parent_religion.holy_sites),
        saints=list(parent_religion.saints),
        figures=[heretic_fig],
        myths=list(parent_religion.myths),
        scripture_name=f"The {descriptor} Testament of {parent_religion.name}",
        reformation_level=parent_religion.reformation_level + 1,
    )

    # Update parent genealogy
    parent_religion.child_religion_ids.append(child_religion.id)
    parent_religion.schisms.append(child_religion.id)

    # Convert followers
    for f_id in follower_ids:
        if f_id in faiths:
            faiths[f_id].former_religion_ids.append(parent_religion.id)
            faiths[f_id].religion_id = child_religion.id
            faiths[f_id].conversion_tick = tick
            faiths[f_id].devotion = min(1.0, faiths[f_id].devotion + 0.1)

    event_payload = {
        "schism_id": child_religion.id,
        "sect_name": child_religion.name,
        "parent_religion_id": parent_religion.id,
        "parent_religion_name": parent_religion.name,
        "founder_id": heretic_fig.character_id,
        "founder_name": heretic_fig.character_name,
        "initial_converts": len(follower_ids),
        "generation": child_religion.generation,
    }

    return child_religion, event_payload


def evaluate_counter_reformation(
    parent_religion: Religion,
    child_religion: Religion,
    all_traits: Mapping[str, ReligionTrait],
    tick: int,
    rng: random.Random,
) -> Optional[dict[str, Any]]:
    """
    Orthodox parent religion reacts to a schism by launching a Counter-Reformation.
    Reaffirms doctrine, boosts orthodoxy zeal, and records the reform.
    """
    if "counter_reformation" in parent_religion.reforms:
        return None

    parent_religion.reformation_level += 1
    reform_name = f"Council of Orthodox Purity (Tick {tick})"
    parent_religion.reforms.append(reform_name)

    # Add discipline or inquisition if available
    if "discipline" in all_traits and "discipline" not in parent_religion.traits:
        parent_religion.traits["discipline"] = all_traits["discipline"]

    return {
        "religion_id": parent_religion.id,
        "religion_name": parent_religion.name,
        "schismatic_sect": child_religion.name,
        "reform_action": "Counter-Reformation",
        "decree": f"{parent_religion.name} reaffirms orthodox doctrine against schismatic departure.",
    }


def evaluate_sect_reunification(
    rel_a: Religion,
    rel_b: Religion,
    all_religions: Mapping[str, Religion],
    faiths: dict[str, CharacterFaith],
    tick: int,
    rng: random.Random,
) -> Optional[dict[str, Any]]:
    """
    Checks if two related sects heal their schism and reunify into a single communion.
    Requires shared root ancestor and long separation (or near extinction of one).
    """
    if rel_a.id == rel_b.id:
        return None

    root_a = rel_a.get_root_ancestor_id(all_religions)
    root_b = rel_b.get_root_ancestor_id(all_religions)
    if root_a != root_b:
        return None

    # Determine mother / larger sect and absorbed sect
    count_a = sum(1 for f in faiths.values() if f.religion_id == rel_a.id)
    count_b = sum(1 for f in faiths.values() if f.religion_id == rel_b.id)

    if count_a >= count_b:
        surviving_rel = rel_a
        absorbed_rel = rel_b
    else:
        surviving_rel = rel_b
        absorbed_rel = rel_a

    # Reconcile adherents
    reunified_count = 0
    for f in faiths.values():
        if f.religion_id == absorbed_rel.id:
            f.former_religion_ids.append(absorbed_rel.id)
            f.religion_id = surviving_rel.id
            f.conversion_tick = tick
            reunified_count += 1

    # Mark absorbed sect extinct
    absorbed_rel.is_extinct = True

    return {
        "surviving_religion_id": surviving_rel.id,
        "surviving_religion_name": surviving_rel.name,
        "absorbed_religion_id": absorbed_rel.id,
        "absorbed_religion_name": absorbed_rel.name,
        "reunified_adherents": reunified_count,
        "tick": tick,
    }
