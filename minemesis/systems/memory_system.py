"""
Memory Formation System.

Adheres strictly to agent.md (lines 270-331) and Milestone 0.5 (Section 4.4):
- Memories are formed in response to BELIEFS, never directly from raw events.
- Tracks source_belief_id for memory indexing.
- Supports memory re-appraisal (Regret, Relief, Respect) when beliefs are superseded.
"""

from __future__ import annotations
from typing import Callable, Optional
from minemesis.core.types import Emotion, EventType, Intent
from minemesis.models.belief import Belief
from minemesis.models.character import Character
from minemesis.models.memory import Memory
from minemesis.models.relationship import Relationship
from minemesis.core.kinship import get_full_siblings, get_half_siblings, kin_degree, get_kin_relation


class _DictStoreAdapter:
    def __init__(self, chars: dict[str, Character]):
        self.chars = chars

    def get_person(self, person_id: str) -> Optional[Character]:
        return self.chars.get(person_id)


def form_memories_from_belief(
    belief: Belief,
    characters: dict[str, Character],
    next_memory_id: int,
    tick: int,
    prior_hatred: float = 0.0,
) -> list[Memory]:
    """
    Evaluates a subjective belief from the perspective of the believer and generates emotional memories.
    If belief supersedes an earlier belief, forms re-appraisal memories scaled by prior_hatred.
    Modulates intensity and decay by character traits (suspicion, forgiveness).
    """
    store = characters if hasattr(characters, "get_person") else _DictStoreAdapter(characters)
    believer = store.get_person(belief.believer_id)
    if not believer or not believer.alive:
        return []

    memories: list[Memory] = []
    mem_id = next_memory_id

    b_type = belief.believed_type
    b_intent = belief.believed_intent
    actor_id = belief.believed_actor
    target_id = belief.believed_target

    # Personality modulation factors
    susp = believer.suspicion
    forg = believer.forgiveness

    # 1. Re-appraisal when an earlier false belief is superseded (Section 4.4)
    if belief.supersedes_belief_id is not None and b_intent == Intent.ACCIDENTAL:
        accused_id = actor_id
        if accused_id and accused_id != believer.id:
            regret_intensity = min(100.0, max(40.0, prior_hatred * 0.95))
            memories.append(
                Memory(
                    id=mem_id,
                    observer_id=believer.id,
                    belief_event_ref=belief.event_ref,
                    target_entity_id=accused_id,
                    emotion=Emotion.REGRET,
                    initial_intensity=regret_intensity,
                    decay_rate=0.005 * (1.0 + forg),
                    tick_formed=tick,
                    source_belief_id=belief.belief_id,
                )
            )
            mem_id += 1
            memories.append(
                Memory(
                    id=mem_id,
                    observer_id=believer.id,
                    belief_event_ref=belief.event_ref,
                    target_entity_id=accused_id,
                    emotion=Emotion.RELIEF,
                    initial_intensity=70.0,
                    decay_rate=0.01 * (1.0 + forg),
                    tick_formed=tick,
                    source_belief_id=belief.belief_id,
                )
            )
            mem_id += 1
            memories.append(
                Memory(
                    id=mem_id,
                    observer_id=believer.id,
                    belief_event_ref=belief.event_ref,
                    target_entity_id=accused_id,
                    emotion=Emotion.RESPECT,
                    initial_intensity=45.0,
                    decay_rate=0.008 * (1.0 + forg),
                    tick_formed=tick,
                    source_belief_id=belief.belief_id,
                )
            )
            mem_id += 1
        return memories

    # 2. Standard belief reactions
    if b_type == EventType.DEATH:
        victim = store.get_person(target_id) if target_id else None

        # Check Rival reaction: relief on death of rival
        if prior_hatred >= 40.0:
            memories.append(
                Memory(
                    id=mem_id,
                    observer_id=believer.id,
                    belief_event_ref=belief.event_ref,
                    target_entity_id=target_id,
                    emotion=Emotion.RELIEF,
                    initial_intensity=65.0,
                    decay_rate=0.01 * (1.0 + forg),
                    tick_formed=tick,
                    source_belief_id=belief.belief_id,
                )
            )
            mem_id += 1

        if victim:
            # Kinship evaluation
            rel_label = get_kin_relation(store, believer.id, victim.id)
            deg = kin_degree(store, believer.id, victim.id)

            is_spouse = (rel_label == "Spouse")
            is_child = (rel_label == "Parent")  # believer is child of victim
            is_parent = (rel_label == "Child")  # believer is parent of victim
            is_sibling = (rel_label in ("Sibling", "Half-Sibling"))
            v_fam = getattr(victim, "family_id", "") or victim.last_name
            b_fam = getattr(believer, "family_id", "") or believer.last_name
            same_clan = bool(v_fam) and (v_fam == b_fam)

            # A. Grief memory formation
            grief_intensity = 0.0
            grief_decay = 0.005 * (1.0 + forg)

            if is_spouse:
                grief_intensity = 95.0
                grief_decay = 0.004 * (1.0 + forg * 0.8)
            elif is_child or is_parent:
                grief_intensity = 90.0
                grief_decay = 0.005 * (1.0 + forg)
            elif is_sibling:
                grief_intensity = 85.0
                grief_decay = 0.006 * (1.0 + forg)
            elif deg == 2:
                grief_intensity = 60.0
                grief_decay = 0.008 * (1.0 + forg)
            elif same_clan:
                grief_intensity = 40.0
                grief_decay = 0.010 * (1.0 + forg)

            if grief_intensity > 0.0:
                memories.append(
                    Memory(
                        id=mem_id,
                        observer_id=believer.id,
                        belief_event_ref=belief.event_ref,
                        target_entity_id=target_id,
                        emotion=Emotion.GRIEF,
                        initial_intensity=grief_intensity,
                        decay_rate=grief_decay,
                        tick_formed=tick,
                        source_belief_id=belief.belief_id,
                    )
                )
                mem_id += 1

            # B. Grievance memory towards killer (intentional death)
            if b_intent in (Intent.INTENTIONAL, Intent.MILITARY_ACTION) and actor_id and actor_id != believer.id:
                decay_mod = max(0.001, 0.003 * (1.0 + forg - susp * 0.4))

                if is_child:
                    # Child: anger (intensity 90.0 towards actor) and hatred
                    anger_int = min(100.0, 90.0 * (0.8 + 0.4 * susp))
                    memories.append(
                        Memory(
                            id=mem_id,
                            observer_id=believer.id,
                            belief_event_ref=belief.event_ref,
                            target_entity_id=actor_id,
                            emotion=Emotion.ANGER,
                            initial_intensity=anger_int,
                            decay_rate=decay_mod * 1.5,
                            tick_formed=tick,
                            source_belief_id=belief.belief_id,
                        )
                    )
                    mem_id += 1
                    hatred_int = min(100.0, 90.0 * (0.8 + 0.4 * susp))
                    memories.append(
                        Memory(
                            id=mem_id,
                            observer_id=believer.id,
                            belief_event_ref=belief.event_ref,
                            target_entity_id=actor_id,
                            emotion=Emotion.HATRED,
                            initial_intensity=hatred_int,
                            decay_rate=decay_mod,
                            tick_formed=tick,
                            source_belief_id=belief.belief_id,
                        )
                    )
                    mem_id += 1
                elif is_sibling:
                    # Sibling: hatred (intensity 95.0 towards actor)
                    hatred_int = min(100.0, 95.0 * (0.8 + 0.4 * susp))
                    memories.append(
                        Memory(
                            id=mem_id,
                            observer_id=believer.id,
                            belief_event_ref=belief.event_ref,
                            target_entity_id=actor_id,
                            emotion=Emotion.HATRED,
                            initial_intensity=hatred_int,
                            decay_rate=decay_mod,
                            tick_formed=tick,
                            source_belief_id=belief.belief_id,
                        )
                    )
                    mem_id += 1
                elif is_spouse or is_parent:
                    hatred_int = min(100.0, 95.0 * (0.8 + 0.4 * susp))
                    memories.append(
                        Memory(
                            id=mem_id,
                            observer_id=believer.id,
                            belief_event_ref=belief.event_ref,
                            target_entity_id=actor_id,
                            emotion=Emotion.HATRED,
                            initial_intensity=hatred_int,
                            decay_rate=decay_mod,
                            tick_formed=tick,
                            source_belief_id=belief.belief_id,
                        )
                    )
                    mem_id += 1
                elif deg == 2 or same_clan:
                    base_h = 70.0 if deg == 2 else 50.0
                    hatred_int = min(100.0, base_h * (0.8 + 0.4 * susp))
                    memories.append(
                        Memory(
                            id=mem_id,
                            observer_id=believer.id,
                            belief_event_ref=belief.event_ref,
                            target_entity_id=actor_id,
                            emotion=Emotion.HATRED,
                            initial_intensity=hatred_int,
                            decay_rate=decay_mod * 1.5,
                            tick_formed=tick,
                            source_belief_id=belief.belief_id,
                        )
                    )
                    mem_id += 1

            elif b_intent == Intent.ACCIDENTAL and actor_id and actor_id != believer.id and (deg in (1, 2) or same_clan):
                memories.append(
                    Memory(
                        id=mem_id,
                        observer_id=believer.id,
                        belief_event_ref=belief.event_ref,
                        target_entity_id=actor_id,
                        emotion=Emotion.GRIEF,
                        initial_intensity=20.0,
                        decay_rate=0.02 * (1.0 + forg),
                        tick_formed=tick,
                        source_belief_id=belief.belief_id,
                    )
                )
                mem_id += 1

    elif b_type == EventType.RAID:
        if belief.believed_location == believer.settlement_id:
            if actor_id:
                memories.append(
                    Memory(
                        id=mem_id,
                        observer_id=believer.id,
                        belief_event_ref=belief.event_ref,
                        target_entity_id=actor_id,
                        emotion=Emotion.HATRED,
                        initial_intensity=75.0,
                        decay_rate=0.008,
                        tick_formed=tick,
                        source_belief_id=belief.belief_id,
                    )
                )
                mem_id += 1
                memories.append(
                    Memory(
                        id=mem_id,
                        observer_id=believer.id,
                        belief_event_ref=belief.event_ref,
                        target_entity_id=actor_id,
                        emotion=Emotion.FEAR,
                        initial_intensity=50.0,
                        decay_rate=0.015,
                        tick_formed=tick,
                        source_belief_id=belief.belief_id,
                    )
                )
                mem_id += 1

    elif b_type == EventType.FEUD:
        target_char = characters.get(target_id) if target_id else None
        t_fam = getattr(target_char, "family_id", "") or (target_char.last_name if target_char else "")
        b_fam = getattr(believer, "family_id", "") or believer.last_name
        if target_id == believer.id or (bool(t_fam) and t_fam == b_fam):
            if actor_id:
                memories.append(
                    Memory(
                        id=mem_id,
                        observer_id=believer.id,
                        belief_event_ref=belief.event_ref,
                        target_entity_id=actor_id,
                        emotion=Emotion.ANGER,
                        initial_intensity=70.0,
                        decay_rate=0.008,
                        tick_formed=tick,
                        source_belief_id=belief.belief_id,
                    )
                )
                mem_id += 1

    elif b_type == EventType.PEACE:
        partner_id = actor_id if actor_id != believer.id else target_id
        if partner_id:
            memories.append(
                Memory(
                    id=mem_id,
                    observer_id=believer.id,
                    belief_event_ref=belief.event_ref,
                    target_entity_id=partner_id,
                    emotion=Emotion.RELIEF,
                    initial_intensity=60.0,
                    decay_rate=0.01,
                    tick_formed=tick,
                    source_belief_id=belief.belief_id,
                )
            )
            mem_id += 1

    elif b_type == EventType.MARRIAGE:
        spouse_partner = actor_id if actor_id != believer.id else target_id
        if spouse_partner:
            memories.append(
                Memory(
                    id=mem_id,
                    observer_id=believer.id,
                    belief_event_ref=belief.event_ref,
                    target_entity_id=spouse_partner,
                    emotion=Emotion.AFFECTION,
                    initial_intensity=80.0,
                    decay_rate=0.003,
                    tick_formed=tick,
                    source_belief_id=belief.belief_id,
                )
            )
            mem_id += 1

    elif b_type == EventType.TRADE_ROUTE_FOUNDED:
        partner_id = actor_id if actor_id != believer.id else target_id
        if partner_id:
            memories.append(
                Memory(
                    id=mem_id,
                    observer_id=believer.id,
                    belief_event_ref=belief.event_ref,
                    target_entity_id=partner_id,
                    emotion=Emotion.GRATITUDE,
                    initial_intensity=40.0,
                    decay_rate=0.01,
                    tick_formed=tick,
                    source_belief_id=belief.belief_id,
                )
            )
            mem_id += 1

    elif b_type == EventType.SUCCESSION_CRISIS:
        memories.append(
            Memory(
                id=mem_id,
                observer_id=believer.id,
                belief_event_ref=belief.event_ref,
                target_entity_id=actor_id,
                emotion=Emotion.FEAR,
                initial_intensity=45.0,
                decay_rate=0.02,
                tick_formed=tick,
                source_belief_id=belief.belief_id,
            )
        )
        mem_id += 1

    elif b_type == EventType.BOOK_WRITTEN:
        if actor_id and actor_id != believer.id:
            memories.append(
                Memory(
                    id=mem_id,
                    observer_id=believer.id,
                    belief_event_ref=belief.event_ref,
                    target_entity_id=actor_id,
                    emotion=Emotion.RESPECT,
                    initial_intensity=40.0,
                    decay_rate=0.01,
                    tick_formed=tick,
                    source_belief_id=belief.belief_id,
                )
            )
            mem_id += 1

    elif b_type == EventType.ARCHIVE_DAMAGED:
        # Directive 7: Only scholars, librarians, elders (age >= 50), or culturally invested
        # characters form grief memories for destroyed manuscripts, not every resident.
        if believer.age_years >= 50 or believer.suspicion < 0.25:
            memories.append(
                Memory(
                    id=mem_id,
                    observer_id=believer.id,
                    belief_event_ref=belief.event_ref,
                    target_entity_id=believer.settlement_id,
                    emotion=Emotion.GRIEF,
                    initial_intensity=40.0,
                    decay_rate=0.02,
                    tick_formed=tick,
                    source_belief_id=belief.belief_id,
                )
            )
            mem_id += 1

    return memories
