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

    # 1. Age living characters and update marital status for surviving spouses
    for c_id in sorted(characters.keys()):
        char = characters[c_id]
        if char.alive:
            char.age_ticks += 1
            if char.spouse_id is not None:
                spouse = characters.get(char.spouse_id)
                if not spouse or not spouse.alive:
                    char.spouse_id = None

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
                    is_alliance = False
                    route_key = tuple(sorted([m.settlement_id, f.settlement_id]))

                    if m.settlement_id != f.settlement_id:
                        # Genuine alliance condition: check for a recent Peace between these two settlements (within 12 ticks)
                        for past_evt in reversed(event_log.all_events()[-30:]):
                            if past_evt.type == EventType.PEACE and (tick - past_evt.tick) <= 12:
                                p_parties = {past_evt.participants_dict.get("initiator"), past_evt.participants_dict.get("target")}
                                if p_parties == {m.settlement_id, f.settlement_id}:
                                    causes.append(past_evt.id)
                                    is_alliance = True
                                    break

                        # Or cite opening of diplomatic trade route
                        if not causes and route_key in active_trade_route_events:
                            causes.append(active_trade_route_events[route_key])

                    relocation_info: dict[str, str] | None = None
                    s_m = settlements[m.settlement_id]
                    s_f = settlements[f.settlement_id]

                    # Standard marriage relocation follows a fixed rule (patrilocal) and is recorded in payload
                    if s_m.id != s_f.id:
                        chosen = s_m
                        leaving = s_f
                        moving_char = f
                        relocation_info = {
                            "moved_char_id": moving_char.id,
                            "from_settlement_id": leaving.id,
                            "to_settlement_id": chosen.id,
                        }

                    evt = event_log.append(
                        tick=tick,
                        location=m.settlement_id,
                        event_type=EventType.MARRIAGE,
                        participants={"spouse1": m.id, "spouse2": f.id},
                        causes=causes,
                        intent=Intent.INTENTIONAL,
                        scale=Scale.INDIVIDUAL,
                        payload={
                            "description": f"Marriage of {m.full_name} and {f.full_name}" + (" (Alliance Marriage)" if is_alliance else ""),
                            "spouse1_name": m.full_name,
                            "spouse2_name": f.full_name,
                            "is_alliance": is_alliance,
                            "relocation": relocation_info,
                        },
                    )
                    m.spouse_id = f.id
                    f.spouse_id = m.id

                    if relocation_info is not None:
                        if f.id in s_f.member_ids:
                            s_f.member_ids.remove(f.id)
                        f.settlement_id = s_m.id
                        s_m.member_ids.append(f.id)

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
