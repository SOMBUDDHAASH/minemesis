"""
Perception System for Milestone 0.5.4 (Epistemic Compaction & Bounded Witnesses).

Converts reality (Events in the EventLog) into observations:
1. Direct participants and immediate kin (Degree 1) form individual subjective Beliefs (capped at <= 10).
2. Cognitive bias & distortion apply to individual observers (Accidental -> False Intentional).
3. Background settlement residents do NOT allocate individual Belief objects.
   Instead, they update the CollectiveKnowledge engine (SettlementOpinion).
"""

from __future__ import annotations
from typing import Any, Callable, Optional, Sequence, Set
from minemesis.core.event_log import Event
from minemesis.core.rng import keyed_float
from minemesis.core.types import BeliefSource, Intent
from minemesis.models.belief import Belief
from minemesis.models.character import Character
from minemesis.models.relationship import Relationship


def perceive_event(
    event: Event,
    characters: dict[str, Character],
    get_relationship: Callable[[str, str], Relationship],
    seed: int,
    belief_counter: list[int],
    knowledge_engine: Optional[Any] = None,
    max_individual_witnesses: int = 10,
) -> list[Belief]:
    """
    Transforms an objective Event into individual subjective Beliefs for key witnesses,
    routing background community perception into CollectiveKnowledge.
    """
    witness_set: set[str] = set()
    actor_id = (
        event.participants_dict.get("actor")
        or event.participants_dict.get("instigator_char")
        or event.participants_dict.get("initiator")
        or event.participants_dict.get("instigator")
        or event.participants_dict.get("speaker")
        or event.participants_dict.get("spouse1")
    )
    target_id = (
        event.participants_dict.get("target")
        or event.participants_dict.get("defender")
        or event.participants_dict.get("victim")
        or event.participants_dict.get("deceased")
        or event.participants_dict.get("spouse2")
    )

    # 1. Direct Participants (always included if alive)
    for p_id in (actor_id, target_id):
        if p_id and p_id in characters and characters[p_id].alive:
            witness_set.add(p_id)

    # 2. Reaction fan-out (Milestone 1): Degree 1 & 2 kin, up to 3 friends, up to 2 rivals
    primary_participants = [p_id for p_id in (actor_id, target_id) if p_id and p_id in characters]
    for p_id in primary_participants:
        p_char = characters[p_id]

        # A. Degree 1 and Degree 2 kin
        from minemesis.core.kinship import get_kin_network
        kin_dict = get_kin_network(characters, p_id, max_degree=2) if hasattr(characters, "get_person") else {}
        if not kin_dict:
            # Fallback direct kin check if characters is raw dict
            deg1_cand = []
            if p_char.spouse_id:
                deg1_cand.append(p_char.spouse_id)
            if p_char.father_id:
                deg1_cand.append(p_char.father_id)
            if p_char.mother_id:
                deg1_cand.append(p_char.mother_id)
            deg1_cand.extend(p_char.children_ids)
            for k in deg1_cand:
                if k in characters and characters[k].alive:
                    witness_set.add(k)
        else:
            for k_id in kin_dict.keys():
                if k_id in characters and characters[k_id].alive:
                    witness_set.add(k_id)

        # B. Up to 3 friends and 2 rivals of the participant
        candidates = [c for c in characters.values() if c.alive and c.id != p_id and c.settlement_id == p_char.settlement_id]
        friends = []
        rivals = []
        for cand in candidates:
            rel = get_relationship(cand.id, p_id)
            if rel.trust >= 10.0 or rel.loyalty >= 10.0:
                friends.append((rel.trust + rel.loyalty, cand.id))
            elif rel.hatred >= 15.0:
                rivals.append((rel.hatred, cand.id))

        friends.sort(reverse=True)
        rivals.sort(reverse=True)
        for _, f_id in friends[:3]:
            witness_set.add(f_id)
        for _, r_id in rivals[:2]:
            witness_set.add(r_id)

    # 3. Sort deterministically and cap at max_individual_witnesses (default 10)
    sorted_witnesses = sorted(witness_set)
    if len(sorted_witnesses) > max_individual_witnesses:
        sorted_witnesses = sorted_witnesses[:max_individual_witnesses]

    beliefs: list[Belief] = []

    # 4. Allocate individual subjective Beliefs for key witnesses
    for observer_id in sorted_witnesses:
        observer = characters[observer_id]
        is_direct_participant = observer_id in (actor_id, target_id)

        # Base confidence
        base_confidence = 1.0 if is_direct_participant else 0.85

        believed_intent = event.intent
        believed_actor = actor_id
        believed_target = target_id

        # Cognitive Bias & Distortion check (agent.md lines 215-228)
        if event.intent == Intent.ACCIDENTAL and actor_id is not None and observer_id != actor_id:
            rel = get_relationship(observer_id, actor_id)

            roll = keyed_float(seed, "perception_bias", observer_id, event.tick, salt=event.id)
            distort_prob = 0.0
            if rel.hatred > 20.0 or rel.trust < -20.0:
                distort_prob = 0.85
            elif observer.suspicion >= 0.50:
                distort_prob = 0.40

            if roll < distort_prob:
                believed_intent = Intent.INTENTIONAL
                base_confidence = 0.80

        b_id = belief_counter[0]
        belief_counter[0] += 1

        belief = Belief(
            belief_id=b_id,
            believer_id=observer_id,
            event_ref=event.id,
            source=BeliefSource.WITNESSED,
            source_character_id=None,
            confidence=base_confidence,
            tick_acquired=event.tick,
            believed_type=event.type,
            believed_intent=believed_intent,
            believed_actor=believed_actor,
            believed_target=believed_target,
            believed_location=event.location,
            believed_payload=dict(event.payload),
        )
        beliefs.append(belief)

    # 5. Route background community perception into CollectiveKnowledge
    if knowledge_engine is not None and event.location:
        knowledge_engine.update_from_event(
            event=event,
            settlement_id=event.location,
            characters=characters,
            tick=event.tick,
        )

    return beliefs
