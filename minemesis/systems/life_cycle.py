"""
Life Cycle System: Birth, Death, Marriage, and Homesteading Migration.

Adheres strictly to agent.md and Milestone 0.5 (Sections 4.1 & 4.5):
- CAUSE_GRAMMAR compliant.
- Extinction protection:
  - If a settlement drops to <= 3 citizens, an unattached young adult from an overcrowded settlement (>= 15) migrates to homestead the available resources.
  - Inter-settlement marriages relocate to the smaller settlement if critical (<= 4).
"""

from __future__ import annotations
from typing import Callable, Mapping
from minemesis.core.event_log import EventLog
from minemesis.core.rng import keyed_choice, keyed_float, keyed_int
from minemesis.core.types import EventType, Intent, Scale
from minemesis.models.character import Character
from minemesis.models.relationship import Relationship
from minemesis.models.settlement import Settlement
from minemesis.systems.world_gen import FIRST_NAMES_FEMALE, FIRST_NAMES_MALE


def process_life_cycle(
    characters: dict[str, Character],
    settlements: dict[str, Settlement],
    event_log: EventLog,
    marriage_events: dict[tuple[str, str], int],
    active_trade_route_events: Mapping[tuple[str, str], int],
    get_relationship: Callable[[str, str], Relationship],
    tick: int,
    seed: int,
    char_counter: list[int],
) -> None:
    """
    Simulates monthly life cycle progressions:
    1. Aging
    2. Marriages & Homesteading Migration
    3. Births
    4. Natural and Accidental Deaths
    """
    living_chars = [c for c in characters.values() if c.alive]

    # 1. Age living characters
    for c_id in sorted(characters.keys()):
        char = characters[c_id]
        if char.alive:
            char.age_ticks += 1

    # 1b. Annual homesteading migration check (extinction protection, Section 4.5)
    # If any settlement drops to <= 4 citizens, a young adult from an overcrowded settlement migrates
    if tick % 12 == 0:
        for s_id, s in settlements.items():
            local_cnt = len([c for c in characters.values() if c.alive and c.settlement_id == s_id])
            if local_cnt <= 4:
                # Find most crowded settlement
                crowded = sorted(
                    [
                        other_s for other_id, other_s in settlements.items()
                        if other_id != s_id and len([c for c in characters.values() if c.alive and c.settlement_id == other_id]) >= 12
                    ],
                    key=lambda s_cand: len([c for c in characters.values() if c.alive and c.settlement_id == s_cand.id]),
                    reverse=True,
                )
                if crowded:
                    source_s = crowded[0]
                    candidates = [
                        c for c in characters.values()
                        if c.alive and c.settlement_id == source_s.id and c.spouse_id is None and 18 <= c.age_years <= 35
                    ]
                    if candidates:
                        migrant = keyed_choice(seed, "pioneer_migrant", f"{s_id}_{tick}", tick, candidates)
                        if migrant.id in source_s.member_ids:
                            source_s.member_ids.remove(migrant.id)
                        migrant.settlement_id = s_id
                        s.member_ids.append(migrant.id)

    # 2. Check Marriages
    singles_m = [c for c in characters.values() if c.alive and c.spouse_id is None and c.sex == "M" and c.age_years >= 18]
    singles_f = [c for c in characters.values() if c.alive and c.spouse_id is None and c.sex == "F" and c.age_years >= 18]

    singles_m.sort(key=lambda c: c.id)
    singles_f.sort(key=lambda c: c.id)

    for m in singles_m:
        if m.spouse_id is not None:
            continue
        for f in singles_f:
            if f.spouse_id is not None:
                continue
            if m.last_name == f.last_name and (m.father_id is not None or f.father_id is not None):
                continue
            if f.id in m.children_ids or m.id in f.children_ids:
                continue

            rel_mf = get_relationship(m.id, f.id)
            rel_fm = get_relationship(f.id, m.id)

            if rel_mf.hatred < 15.0 and rel_fm.hatred < 15.0:
                roll = keyed_float(seed, "marriage_roll", f"{m.id}_{f.id}", tick)
                threshold = 0.05 if m.settlement_id == f.settlement_id else 0.025
                if roll < threshold:
                    causes: list[int] = []
                    route_key = tuple(sorted([m.settlement_id, f.settlement_id]))
                    if m.settlement_id != f.settlement_id:
                        if route_key in active_trade_route_events:
                            causes.append(active_trade_route_events[route_key])
                        else:
                            for past_evt in reversed(event_log.all_events()):
                                if past_evt.type == EventType.PEACE:
                                    if m.settlement_id in past_evt.location or f.settlement_id in past_evt.location:
                                        causes.append(past_evt.id)
                                        break

                    evt = event_log.append(
                        tick=tick,
                        location=m.settlement_id,
                        event_type=EventType.MARRIAGE,
                        participants={"spouse1": m.id, "spouse2": f.id},
                        causes=causes,
                        intent=Intent.INTENTIONAL,
                        scale=Scale.INDIVIDUAL,
                        payload={
                            "description": f"Marriage of {m.full_name} and {f.full_name}",
                            "spouse1_name": m.full_name,
                            "spouse2_name": f.full_name,
                        },
                    )
                    m.spouse_id = f.id
                    f.spouse_id = m.id

                    s_m = settlements[m.settlement_id]
                    s_f = settlements[f.settlement_id]
                    if s_m.id != s_f.id:
                        m_pop = len([c for c in characters.values() if c.alive and c.settlement_id == s_m.id])
                        f_pop = len([c for c in characters.values() if c.alive and c.settlement_id == s_f.id])

                        # Young couple settles in the less populated settlement (homesteading opportunity)
                        if m_pop < f_pop:
                            chosen = s_m
                            leaving = s_f
                            moving_char = f
                        elif f_pop < m_pop:
                            chosen = s_f
                            leaving = s_m
                            moving_char = m
                        else:
                            if keyed_float(seed, "matrilocal_roll", f"{m.id}_{f.id}", tick) < 0.5:
                                chosen = s_m
                                leaving = s_f
                                moving_char = f
                            else:
                                chosen = s_f
                                leaving = s_m
                                moving_char = m

                        if moving_char.settlement_id != chosen.id:
                            if moving_char.id in leaving.member_ids:
                                leaving.member_ids.remove(moving_char.id)
                            moving_char.settlement_id = chosen.id
                            chosen.member_ids.append(moving_char.id)

                    marriage_key = tuple(sorted([m.id, f.id]))
                    marriage_events[marriage_key] = evt.id
                    break

    # 3. Check Births
    wives = [c for c in characters.values() if c.alive and c.sex == "F" and c.spouse_id is not None and 18 <= c.age_years <= 44]
    wives.sort(key=lambda c: c.id)

    for wife in wives:
        husband = characters.get(wife.spouse_id) if wife.spouse_id else None
        if not husband or not husband.alive:
            continue

        if len(wife.children_ids) >= 4:
            continue

        birth_roll = keyed_float(seed, "birth_roll", wife.id, tick)
        if birth_roll < 0.020:
            marriage_key = tuple(sorted([wife.id, husband.id]))
            marriage_evt_id = marriage_events.get(marriage_key)
            causes = [marriage_evt_id] if marriage_evt_id is not None else []

            child_id = f"char_{char_counter[0]}"
            char_counter[0] += 1

            child_sex = "M" if keyed_float(seed, "child_sex", child_id, tick) < 0.5 else "F"
            name_pool = FIRST_NAMES_MALE if child_sex == "M" else FIRST_NAMES_FEMALE
            first_name = keyed_choice(seed, "child_name", child_id, tick, name_pool)
            last_name = husband.last_name

            child = Character(
                id=child_id,
                first_name=first_name,
                last_name=last_name,
                settlement_id=wife.settlement_id,
                age_ticks=0,
                sex=child_sex,
                father_id=husband.id,
                mother_id=wife.id,
                suspicion=0.45,
                forgiveness=0.55,
            )
            characters[child_id] = child
            settlements[wife.settlement_id].member_ids.append(child_id)
            wife.children_ids.append(child_id)
            husband.children_ids.append(child_id)

            event_log.append(
                tick=tick,
                location=wife.settlement_id,
                event_type=EventType.BIRTH,
                participants={"child": child_id, "mother": wife.id, "father": husband.id},
                causes=causes,
                intent=Intent.INTENTIONAL,
                scale=Scale.INDIVIDUAL,
                payload={
                    "description": f"Birth of {child.full_name} to {husband.full_name} and {wife.full_name}",
                    "child_name": child.full_name,
                },
            )

    # 4. Check Deaths (Natural & Accidental)
    living_chars = [c for c in characters.values() if c.alive]
    living_chars.sort(key=lambda c: c.id)

    for char in living_chars:
        # A. Old Age / Natural death
        if char.age_years >= 60:
            death_prob = 0.006 + 0.0025 * (char.age_years - 60)
            roll = keyed_float(seed, "natural_death", char.id, tick)
            if roll < death_prob:
                char.alive = False
                event_log.append(
                    tick=tick,
                    location=char.settlement_id,
                    event_type=EventType.DEATH,
                    participants={"target": char.id},
                    causes=[],
                    intent=Intent.ACCIDENTAL,
                    scale=Scale.INDIVIDUAL,
                    payload={
                        "description": f"{char.full_name} passed away of old age at {char.age_years} years",
                        "victim_name": char.full_name,
                        "natural": True,
                    },
                )
                continue

        # B. Accidental Death during labor/forestry
        if char.age_years >= 16:
            acc_roll = keyed_float(seed, "accidental_death", char.id, tick)
            if acc_roll < 0.0010:
                peers = [p for p in living_chars if p.id != char.id and p.age_years >= 16]
                if peers:
                    partner = keyed_choice(seed, "acc_partner", char.id, tick, peers)
                    char.alive = False

                    event_log.append(
                        tick=tick,
                        location=char.settlement_id,
                        event_type=EventType.DEATH,
                        participants={"actor": partner.id, "target": char.id},
                        causes=[],
                        intent=Intent.ACCIDENTAL,
                        scale=Scale.INDIVIDUAL,
                        payload={
                            "description": f"{char.full_name} died accidentally in a forestry mishap with {partner.full_name}",
                            "victim_name": char.full_name,
                            "actor_name": partner.full_name,
                            "accidental": True,
                        },
                    )
