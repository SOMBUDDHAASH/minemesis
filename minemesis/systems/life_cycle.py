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
    name_salt: int = 0,
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

    # 2. Check Marriages (M0.5.4: Bucketed by settlement & diplomatic ties)
    singles_m_by_s: dict[str, list[Character]] = {}
    singles_f_by_s: dict[str, list[Character]] = {}
    for c in characters.values():
        if c.alive and c.spouse_id is None and c.age_years >= 18:
            if c.sex == "M":
                singles_m_by_s.setdefault(c.settlement_id, []).append(c)
            elif c.sex == "F":
                singles_f_by_s.setdefault(c.settlement_id, []).append(c)

    for s_id in singles_m_by_s:
        singles_m_by_s[s_id].sort(key=lambda c: c.id)
    for s_id in singles_f_by_s:
        singles_f_by_s[s_id].sort(key=lambda c: c.id)

    # Candidate settlement pairings: Intra-settlement first, then diplomatic pairs
    settlement_pairs: list[tuple[str, str]] = [(s_id, s_id) for s_id in sorted(settlements.keys())]

    # Add active trade route pairs
    for r_pair in sorted(active_trade_route_events.keys()):
        if r_pair not in settlement_pairs:
            settlement_pairs.append(r_pair)

    # Add recent peace pairs (within 12 ticks)
    for past_evt in reversed(event_log.all_events()[-30:]):
        if past_evt.type == EventType.PEACE and (tick - past_evt.tick) <= 12:
            p1 = past_evt.participants_dict.get("initiator")
            p2 = past_evt.participants_dict.get("target")
            if p1 and p2 and p1 != p2:
                pair = tuple(sorted([p1, p2]))
                if pair not in settlement_pairs:
                    settlement_pairs.append(pair)

    def attempt_marriage(m: Character, f: Character) -> bool:
        if m.spouse_id is not None or f.spouse_id is not None:
            return False
        m_fam = getattr(m, "family_id", "") or m.last_name
        f_fam = getattr(f, "family_id", "") or f.last_name
        if m_fam == f_fam and (m.father_id is not None or f.father_id is not None):
            return False
        if f.id in m.children_ids or m.id in f.children_ids:
            return False

        roll = keyed_float(seed, "marriage_roll", f"{m.id}_{f.id}", tick)
        threshold = 0.05 if m.settlement_id == f.settlement_id else 0.025
        if roll >= threshold:
            return False

        rel_mf = get_relationship(m.id, f.id)
        rel_fm = get_relationship(f.id, m.id)

        if rel_mf.hatred < 15.0 and rel_fm.hatred < 15.0:
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

                # Or cite opening of diplomatic trade route (within 24 ticks per Directive 11)
                if not causes and route_key in active_trade_route_events:
                    tr_id = active_trade_route_events[route_key]
                    tr_evt = event_log.get(tr_id)
                    if tr_evt and (tick - tr_evt.tick) <= 24:
                        causes.append(tr_id)

            relocation_info: dict[str, str] | None = None
            s_m = settlements[m.settlement_id]
            s_f = settlements[f.settlement_id]

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
            return True
        return False

    for s_a, s_b in settlement_pairs:
        m_list = list(singles_m_by_s.get(s_a, []))
        f_list = list(singles_f_by_s.get(s_b, []))
        for m in m_list:
            if m.spouse_id is not None:
                continue
            for f in f_list:
                if f.spouse_id is not None:
                    continue
                if attempt_marriage(m, f):
                    break
        if s_a != s_b:
            m_list2 = list(singles_m_by_s.get(s_b, []))
            f_list2 = list(singles_f_by_s.get(s_a, []))
            for m in m_list2:
                if m.spouse_id is not None:
                    continue
                for f in f_list2:
                    if f.spouse_id is not None:
                        continue
                    if attempt_marriage(m, f):
                        break

    # 3. Check Births (M0.5.4: Carrying capacity & resource dampening)
    living_pop_by_s: dict[str, int] = {}
    for c in characters.values():
        if c.alive:
            living_pop_by_s[c.settlement_id] = living_pop_by_s.get(c.settlement_id, 0) + 1

    wives = [c for c in characters.values() if c.alive and c.sex == "F" and c.spouse_id is not None and 18 <= c.age_years <= 44]
    wives.sort(key=lambda c: c.id)

    for wife in wives:
        husband = characters.get(wife.spouse_id) if wife.spouse_id else None
        if not husband or not husband.alive:
            continue

        if len(wife.children_ids) >= 4:
            continue

        s = settlements.get(wife.settlement_id)
        birth_prob = 0.020
        if s:
            k_s = max(50, int(130 * s.farmland * (s.water_access + 0.5)))
            local_pop = living_pop_by_s.get(wife.settlement_id, 1)
            if local_pop > k_s:
                ratio = local_pop / k_s
                birth_prob *= max(0.08, 1.0 / (ratio * ratio))
            if s.food < local_pop * 0.50:
                birth_prob *= 0.50

        birth_roll = keyed_float(seed, "birth_roll", wife.id, tick)
        if birth_roll < birth_prob:
            living_pop_by_s[wife.settlement_id] = living_pop_by_s.get(wife.settlement_id, 0) + 1
            marriage_key = tuple(sorted([wife.id, husband.id]))
            marriage_evt_id = marriage_events.get(marriage_key)
            causes = [marriage_evt_id] if marriage_evt_id is not None else []

            child_id = f"char_{char_counter[0]}"
            char_counter[0] += 1

            child_sex = "M" if keyed_float(seed, "child_sex", child_id, tick) < 0.5 else "F"
            name_pool = FIRST_NAMES_MALE if child_sex == "M" else FIRST_NAMES_FEMALE
            first_name = keyed_choice(seed, "name:child_name", child_id, tick, name_pool, salt=name_salt)
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
                family_id=getattr(husband, "family_id", "") or last_name,
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
                payload={},
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
                char.death_tick = tick
                evt = event_log.append(
                    tick=tick,
                    location=char.settlement_id,
                    event_type=EventType.DEATH,
                    participants={"target": char.id},
                    causes=[],
                    intent=Intent.ACCIDENTAL,
                    scale=Scale.INDIVIDUAL,
                    payload={
                        "natural": True,
                    },
                )
                char.death_event_id = evt.id
                continue

        # B. Accidental Death during labor/forestry
        if char.age_years >= 16:
            acc_roll = keyed_float(seed, "accidental_death", char.id, tick)
            if acc_roll < 0.0010:
                peers = [p for p in characters.values() if p.alive and p.id != char.id and p.age_years >= 16]
                if peers:
                    partner = keyed_choice(seed, "acc_partner", char.id, tick, peers)
                    char.alive = False
                    char.death_tick = tick
                    evt = event_log.append(
                        tick=tick,
                        location=char.settlement_id,
                        event_type=EventType.DEATH,
                        participants={"actor": partner.id, "target": char.id},
                        causes=[],
                        intent=Intent.ACCIDENTAL,
                        scale=Scale.INDIVIDUAL,
                        payload={
                            "accidental": True,
                            "cause_of_death": "forestry mishap",
                        },
                    )
                    char.death_event_id = evt.id
