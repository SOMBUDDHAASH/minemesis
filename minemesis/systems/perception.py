"""
Perception System.

Converts reality (Events in the EventLog) into observations (Beliefs).
Adheres strictly to agent.md (lines 166-229) and Milestone 0.5:
- Uncertainty is NOT distortion: Low visibility reduces confidence, does not invent facts.
- Distortion arises from Bias, Pre-existing Relationships, and Suspicion.
- Accidental harm + negative bias/suspicion -> False belief of Intentional murder.
"""

from __future__ import annotations
from typing import Callable, Sequence
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
) -> list[Belief]:
    """
    Transforms an objective Event into individual subjective Beliefs for witnesses.
    Assigns sequential belief_id.
    """
    witnesses: list[str] = []
    actor_id = event.participants_dict.get("actor") or event.participants_dict.get("instigator_char") or event.participants_dict.get("initiator") or event.participants_dict.get("instigator")
    target_id = event.participants_dict.get("target") or event.participants_dict.get("defender")

    # Determine witnesses: living characters at the location or involved
    for char_id in sorted(characters.keys()):
        char = characters[char_id]
        if not char.alive:
            continue
        if char.settlement_id == event.location or char.id in (actor_id, target_id):
            witnesses.append(char.id)

    beliefs: list[Belief] = []

    for observer_id in witnesses:
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

    return beliefs
