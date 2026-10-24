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
    """
    believer = characters.get(belief.believer_id)
    if not believer or not believer.alive:
        return []

    memories: list[Memory] = []
    mem_id = next_memory_id

    b_type = belief.believed_type
    b_intent = belief.believed_intent
    actor_id = belief.believed_actor
    target_id = belief.believed_target

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
                    decay_rate=0.005,
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
                    decay_rate=0.01,
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
                    decay_rate=0.008,
                    tick_formed=tick,
                    source_belief_id=belief.belief_id,
                )
            )
            mem_id += 1
        return memories

    # 2. Standard belief reactions
    if b_type == EventType.DEATH:
        victim = characters.get(target_id) if target_id else None
        
        is_child = victim and victim.id in believer.children_ids
        is_parent = victim and victim.id in (believer.father_id, believer.mother_id)
        is_spouse = victim and victim.id == believer.spouse_id
        is_kin = is_child or is_parent or is_spouse or (victim and victim.last_name == believer.last_name)

        if is_kin:
            memories.append(
                Memory(
                    id=mem_id,
                    observer_id=believer.id,
                    belief_event_ref=belief.event_ref,
                    target_entity_id=target_id,
                    emotion=Emotion.GRIEF,
                    initial_intensity=90.0,
                    decay_rate=0.005,
                    tick_formed=tick,
                    source_belief_id=belief.belief_id,
                )
            )
            mem_id += 1

            if b_intent == Intent.INTENTIONAL and actor_id and actor_id != believer.id:
                memories.append(
                    Memory(
                        id=mem_id,
                        observer_id=believer.id,
                        belief_event_ref=belief.event_ref,
                        target_entity_id=actor_id,
                        emotion=Emotion.HATRED,
                        initial_intensity=95.0,
                        decay_rate=0.003,
                        tick_formed=tick,
                        source_belief_id=belief.belief_id,
                    )
                )
                mem_id += 1
            elif b_intent == Intent.ACCIDENTAL and actor_id and actor_id != believer.id:
                memories.append(
                    Memory(
                        id=mem_id,
                        observer_id=believer.id,
                        belief_event_ref=belief.event_ref,
                        target_entity_id=actor_id,
                        emotion=Emotion.GRIEF,
                        initial_intensity=20.0,
                        decay_rate=0.02,
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
        if target_id == believer.id or (target_id and characters.get(target_id, Character("", "", "", "", 0, "")).last_name == believer.last_name):
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

    return memories
