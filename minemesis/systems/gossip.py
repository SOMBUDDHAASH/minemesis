"""
Knowledge Propagation System (Gossip & Rumors).

Adheres strictly to agent.md (lines 355-380) and Milestone 0.5:
- Spreads information gradually between characters.
- Confidence is attenuated by listener's trust in speaker.
- Assigns sequential belief_ids.
"""

from __future__ import annotations
from typing import Callable
from minemesis.core.rng import keyed_float, keyed_int, keyed_sample
from minemesis.core.types import BeliefSource, Intent
from minemesis.models.belief import Belief
from minemesis.models.character import Character
from minemesis.models.relationship import Relationship


def propagate_gossip(
    characters: dict[str, Character],
    beliefs_by_character: dict[str, dict[int, Belief]],
    get_relationship: Callable[[str, str], Relationship],
    tick: int,
    seed: int,
    belief_counter: list[int],
) -> list[Belief]:
    """
    Simulates monthly intra- and inter-settlement conversations.
    Generates new secondary (TOLD) beliefs.
    """
    new_beliefs: list[Belief] = []
    living_chars = [c for c in characters.values() if c.alive]
    sorted_chars = sorted(living_chars, key=lambda c: c.id)

    by_settlement: dict[str, list[Character]] = {}
    for c in sorted_chars:
        by_settlement.setdefault(c.settlement_id, []).append(c)

    # 1. Intra-settlement gossip
    for s_id in sorted(by_settlement.keys()):
        residents = by_settlement[s_id]
        if len(residents) < 2:
            continue

        pair_roll = keyed_float(seed, "gossip_intra", s_id, tick)
        if pair_roll > 0.40:
            pair = keyed_sample(seed, "gossip_pair", s_id, tick, residents, 2)
            speaker, listener = pair[0], pair[1]
            speaker_beliefs = beliefs_by_character.get(speaker.id, {})
            listener_beliefs = beliefs_by_character.get(listener.id, {})

            notable = [b for b in speaker_beliefs.values() if b.event_ref not in listener_beliefs]
            if notable:
                pick_idx = keyed_int(seed, "gossip_pick", speaker.id, tick, 0, len(notable) - 1)
                shared = notable[pick_idx]

                rel = get_relationship(listener.id, speaker.id)
                speaker_rel_actor = (
                    get_relationship(speaker.id, shared.believed_actor)
                    if shared.believed_actor
                    else Relationship(speaker.id, "", 0, 0, 0, 0, 0)
                )

                trust_factor = max(0.3, min(1.0, (rel.trust + 50.0) / 100.0))
                new_conf = round(shared.confidence * trust_factor, 3)

                believed_intent = shared.believed_intent
                if speaker_rel_actor.hatred > 25.0 and shared.believed_intent == Intent.ACCIDENTAL:
                    believed_intent = Intent.INTENTIONAL

                b_id = belief_counter[0]
                belief_counter[0] += 1

                b = Belief(
                    belief_id=b_id,
                    believer_id=listener.id,
                    event_ref=shared.event_ref,
                    source=BeliefSource.TOLD,
                    source_character_id=speaker.id,
                    confidence=new_conf,
                    tick_acquired=tick,
                    believed_type=shared.believed_type,
                    believed_intent=believed_intent,
                    believed_actor=shared.believed_actor,
                    believed_target=shared.believed_target,
                    believed_location=shared.believed_location,
                    believed_payload=dict(shared.believed_payload),
                )
                new_beliefs.append(b)

    # 2. Inter-settlement travelers (15% chance per tick)
    inter_roll = keyed_float(seed, "gossip_inter", "world", tick)
    if inter_roll < 0.20 and len(by_settlement) >= 2:
        s_keys = sorted(by_settlement.keys())
        s1 = keyed_sample(seed, "inter_s1", "world", tick, s_keys, 2)
        from_set, to_set = s1[0], s1[1]

        if by_settlement.get(from_set) and by_settlement.get(to_set):
            traveler = keyed_sample(seed, "inter_traveler", from_set, tick, by_settlement[from_set], 1)[0]
            local = keyed_sample(seed, "inter_local", to_set, tick, by_settlement[to_set], 1)[0]

            traveler_beliefs = beliefs_by_character.get(traveler.id, {})
            local_beliefs = beliefs_by_character.get(local.id, {})

            notable = [b for b in traveler_beliefs.values() if b.event_ref not in local_beliefs]
            if notable:
                pick_idx = keyed_int(seed, "inter_pick", traveler.id, tick, 0, len(notable) - 1)
                shared = notable[pick_idx]
                
                b_id = belief_counter[0]
                belief_counter[0] += 1

                b = Belief(
                    belief_id=b_id,
                    believer_id=local.id,
                    event_ref=shared.event_ref,
                    source=BeliefSource.TOLD,
                    source_character_id=traveler.id,
                    confidence=round(shared.confidence * 0.70, 3),
                    tick_acquired=tick,
                    believed_type=shared.believed_type,
                    believed_intent=shared.believed_intent,
                    believed_actor=shared.believed_actor,
                    believed_target=shared.believed_target,
                    believed_location=shared.believed_location,
                    believed_payload=dict(shared.believed_payload),
                )
                new_beliefs.append(b)

    return new_beliefs
