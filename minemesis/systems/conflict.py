"""
Conflict, Economy, and Historical Pressure Systems.

Adheres strictly to agent.md and Milestone 0.5 (Sections 4.1 - 4.5):
- CAUSE_GRAMMAR enforced for all emitted events.
- Demotes routine trade to continuous TradeRoute state; emits TradeRouteFounded/Broken.
- Truth Revelation pipeline with belief supersession and memory re-appraisal.
- Raid cooldowns: Prevents raid spam and continuous unmitigated pillaging.
- Extinction protection: Guarantees zero extinct settlements across all seeds.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence, Set, Optional
from minemesis.core.event_log import EventLog
from minemesis.core.rng import keyed_choice, keyed_float, keyed_int, keyed_sample
from minemesis.core.types import BeliefSource, Emotion, EventType, Intent, Scale
from minemesis.models.belief import Belief
from minemesis.models.character import Character
from minemesis.models.memory import Memory
from minemesis.models.relationship import Relationship
from minemesis.models.settlement import Settlement, TradeRoute
from minemesis.core.kinship import get_kin_network, kin_degree, get_kin_relation


class _DictStore:
    def __init__(self, chars: dict[str, Character]):
        self.chars = chars

    def get_person(self, person_id: str) -> Optional[Character]:
        return self.chars.get(person_id)


@dataclass
class ActiveFeud:
    id: int  # Feud Event ID
    instigator_char_id: str
    target_char_id: str
    instigator_settlement_id: str
    target_settlement_id: str
    root_cause_event_id: int
    is_wrongful: bool
    start_tick: int
    active: bool = True
    last_revenge_tick: int = -100
    revenge_count: int = 0
    minor_raids: int = 0
    raid_count: int = 0
    primary_avenger_id: Optional[str] = None
    secondary_avenger_id: Optional[str] = None


def select_feud_avengers(
    feud: ActiveFeud,
    characters: dict[str, Character],
    get_relationship: Callable[[str, str], Relationship],
    tick: int,
) -> tuple[Optional[str], Optional[str]]:
    """
    Gender-neutral avenger selection across adult living degree 1 and 2 kin.
    Motivation score: (hatred / 100.0) * 0.5 + (0.5 if age >= 18 else 0.1) * 0.3 + suspicion * 0.2 - forgiveness * 0.2.
    One primary avenger per feud; plus at most one secondary avenger only if feud duration > 24 ticks.
    """
    store = characters if hasattr(characters, "get_person") else _DictStore(characters)
    
    # Pool candidate kin from instigator
    candidate_ids: set[str] = set()
    candidate_ids.add(feud.instigator_char_id)
    kin_net = get_kin_network(store, feud.instigator_char_id, max_degree=2)
    candidate_ids.update(kin_net.keys())

    scored_candidates: list[tuple[float, str]] = []
    for cid in candidate_ids:
        c = store.get_person(cid)
        if not c or not c.alive:
            continue
        rel = get_relationship(c.id, feud.target_char_id)
        hatred = rel.hatred
        age_score = 0.5 if c.age_years >= 18 else 0.1
        susp = c.suspicion
        forg = c.forgiveness
        motivation = (hatred / 100.0) * 0.5 + age_score * 0.3 + susp * 0.2 - forg * 0.2
        scored_candidates.append((motivation, c.id))

    if not scored_candidates:
        return None, None

    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    primary = scored_candidates[0][1]

    secondary = None
    elapsed = tick - feud.start_tick
    if elapsed > 24 and len(scored_candidates) > 1 and scored_candidates[1][0] > 0.1:
        secondary = scored_candidates[1][1]

    return primary, secondary


def process_conflicts_and_economy(
    characters: dict[str, Character],
    settlements: dict[str, Settlement],
    trade_routes: dict[tuple[str, str], TradeRoute],
    active_trade_route_events: dict[tuple[str, str], int],
    last_raid_ticks: dict[tuple[str, str], int],
    collapsed_settlements: Set[str],
    beliefs_by_character: dict[str, dict[int, Belief]],
    memories: list[Memory],
    superseded_memory_ids: Set[int],
    event_log: EventLog,
    active_feuds: list[ActiveFeud],
    get_relationship: Callable[[str, str], Relationship],
    tick: int,
    seed: int,
    belief_counter: list[int],
    memory_counter: list[int],
    resolved_grievance_event_ids: Set[int] | None = None,
) -> None:
    """
    Simulates monthly economic production, leadership, conflicts, and reconciliation.
    """
    if resolved_grievance_event_ids is None:
        resolved_grievance_event_ids = set()
    living_chars = [c for c in characters.values() if c.alive]
    sorted_chars = sorted(living_chars, key=lambda c: c.id)
    settlement_keys = sorted(settlements.keys())

    # =========================================================================
    # 1. SCARCITY, FAMINE & WEALTH ECONOMICS (Milestone 0.5.1 Section 3c)
    # =========================================================================
    month_of_year = (tick % 12) + 1
    if month_of_year in (12, 1, 2):
        season_mult = 0.40  # Winter dormancy
    elif month_of_year in (9, 10, 11):
        season_mult = 1.45  # Harvest Autumn
    else:
        season_mult = 1.15  # Spring / Summer

    active_feud_pairs = {
        tuple(sorted([f.instigator_settlement_id, f.target_settlement_id]))
        for f in active_feuds if f.active
    }

    for s_id in settlement_keys:
        s = settlements[s_id]
        local_living = [c for c in living_chars if c.settlement_id == s_id]
        pop = len(local_living)
        if pop == 0:
            continue

        # Carrying capacity & land saturation (Milestone 0.5.4)
        k_settlement = max(50, int(130 * s.farmland * (s.water_access + 0.5)))
        if pop > k_settlement:
            saturation = k_settlement / (k_settlement + (pop - k_settlement) * 1.05)
        else:
            saturation = 1.0

        effective_farmland = s.farmland * saturation
        noise = 0.90 + 0.20 * keyed_float(seed, "food_noise", s_id, tick)
        food_produced = int(pop * effective_farmland * season_mult * 1.08 * noise)
        s.food += food_produced

        food_consumed = max(1, int(pop * 1.0))
        s.food -= food_consumed

        # Wealth production from mining & timber resources (Section 2d fix)
        workers = max(1, len([c for c in local_living if 16 <= c.age_years <= 60]))
        wealth_produced = int(workers * s.ore_richness * 0.35) + int(workers * s.forest * 0.15)
        s.wealth += wealth_produced

        # Storage cap & spoilage (M0.5.4: realistic 14-month historical granary capacity)
        storage_cap = pop * 14 + 100
        if s.food > storage_cap:
            excess = s.food - storage_cap
            spoilage = int(excess * 0.20)
            s.food -= spoilage

        critical_food_threshold = max(5, int(pop * 0.50))
        if s.food <= critical_food_threshold:
            s.consecutive_starvation_ticks += 1
            if s.food < 0:
                s.food = 0
        elif s.food >= max(10, int(pop * 1.50)):
            s.consecutive_starvation_ticks = max(0, s.consecutive_starvation_ticks - 1)

        # Directive 9: Wealth sink (maintenance costs & municipal upkeep)
        maintenance = max(1, int(pop * 0.15 + (s.wealth * 0.01)))
        s.wealth = max(0, s.wealth - maintenance)

        # Directive 9: Emergency food purchases for wealthy starving settlements
        if s.food < max(15, int(pop * 0.35)) and s.wealth >= 10:
            for other_id in settlement_keys:
                if other_id == s_id or other_id in collapsed_settlements:
                    continue
                # Cannot purchase emergency grain from settlements in active feud
                if tuple(sorted([s_id, other_id])) in active_feud_pairs:
                    continue
                other_s = settlements[other_id]
                other_pop = len([c for c in living_chars if c.settlement_id == other_id])
                surplus = max(0, other_s.food - max(15, other_pop * 2))
                if surplus > 0:
                    needed = min(max(20, int(pop * 0.50)), surplus, s.wealth // 3)
                    if needed > 0:
                        cost = needed * 3
                        s.wealth -= cost
                        other_s.wealth += cost
                        s.food += needed
                        other_s.food -= needed
                        if s.food >= max(20, int(pop * 0.50)):
                            break

        # Directive 8: Famine Consolidation (historical spell, not bi-monthly pulse)
        if s.food >= max(20, pop * 2):
            s.adequate_food_ticks += 1
            if s.active_famine_event_id is not None and s.adequate_food_ticks >= 6:
                # Famine spell resolved through sustained recovery
                s.active_famine_event_id = None
                s.active_famine_start_tick = None
                s.last_famine_end_tick = tick
        else:
            s.adequate_food_ticks = 0

        # Trigger new Famine spell ONLY if no active famine and adequate recovery (>= 12 months since last famine)
        if s.active_famine_event_id is None:
            if s.consecutive_starvation_ticks >= 2 and (tick - s.last_famine_end_tick >= 12):
                famine_roll = keyed_float(seed, "famine_event", s_id, tick)
                causes: list[int] = []
                for past_evt in reversed(event_log.all_events()[-25:]):
                    if past_evt.type == EventType.RAID and past_evt.location == s.id:
                        causes.append(past_evt.id)
                        break

                threshold = 0.50 if causes else 0.30
                if famine_roll < threshold:
                    famine_evt = event_log.append(
                        tick=tick,
                        location=s.id,
                        event_type=EventType.FAMINE,
                        participants={"settlement": s.id},
                        causes=causes,
                        intent=Intent.ACCIDENTAL,
                        scale=Scale.AGGREGATE,
                        payload={
                            "settlement": s.id,
                            "active_spell": True,
                        },
                    )
                    s.active_famine_event_id = famine_evt.id
                    s.active_famine_start_tick = tick
                    s.adequate_food_ticks = 0
                    s.consecutive_starvation_ticks = 0

        # While famine spell is active, starvation deaths cite the active famine
        if s.active_famine_event_id is not None and s.consecutive_starvation_ticks >= 1:
            if len(local_living) > 4:
                starve_roll = keyed_float(seed, "starve_roll", f"{s_id}_{s.active_famine_event_id}", tick)
                if starve_roll < 0.25:
                    vulnerable = [c for c in local_living if c.age_years >= 60 or c.age_years <= 12]
                    starve_victim = keyed_choice(seed, "starve_victim", s_id, tick, vulnerable or local_living)
                    starve_victim.alive = False
                    starve_victim.death_tick = tick
                    evt = event_log.append(
                        tick=tick,
                        location=s.id,
                        event_type=EventType.DEATH,
                        participants={"target": starve_victim.id},
                        causes=[s.active_famine_event_id],
                        intent=Intent.ACCIDENTAL,
                        scale=Scale.INDIVIDUAL,
                        payload={
                            "cause": "Starvation",
                            "famine_id": s.active_famine_event_id,
                        },
                    )
                    starve_victim.death_event_id = evt.id

            # Desperate food raid during active famine
            current_living = [c for c in characters.values() if c.alive and c.settlement_id == s_id and c.age_years >= 16]
            food_rich = [other_id for other_id in settlement_keys if settlements[other_id].food > 40 and other_id not in collapsed_settlements]
            if food_rich and len(current_living) >= 4:
                target_s = keyed_choice(seed, "famine_target", s_id, tick, food_rich)
                action_roll = keyed_float(seed, "famine_action", s_id, tick)
                if action_roll < 0.20:
                    leader_c = characters[s.leader_id] if s.leader_id and s.leader_id in characters and characters[s.leader_id].alive else current_living[0]
                    if leader_c and leader_c.alive:
                        event_log.append(
                            tick=tick,
                            location=target_s,
                            event_type=EventType.RAID,
                            participants={"initiator": s.id, "target": target_s, "instigator_char": leader_c.id},
                            causes=[s.active_famine_event_id],
                            intent=Intent.MILITARY_ACTION,
                            scale=Scale.AGGREGATE,
                            payload={
                                "feud_id": None,
                                "famine_id": s.active_famine_event_id,
                            },
                        )
                        settlements[target_s].food -= min(15, settlements[target_s].food // 3)
                        s.food += 12

    # =========================================================================
    # 2. TRADE ROUTES (Continuous State & Historical Events, Section 4.2)
    # =========================================================================
    active_feud_by_settlements = {
        tuple(sorted([f.instigator_settlement_id, f.target_settlement_id])): f
        for f in active_feuds if f.active
    }

    for i, s1_id in enumerate(settlement_keys):
        for s2_id in settlement_keys[i + 1 :]:
            route_key = tuple(sorted([s1_id, s2_id]))
            route = trade_routes.get(route_key)
            if not route:
                route = TradeRoute(settlement_a=s1_id, settlement_b=s2_id, active=False)
                trade_routes[route_key] = route

            feud_causing = active_feud_by_settlements.get(route_key)
            has_feud = feud_causing is not None

            s1 = settlements[s1_id]
            s2 = settlements[s2_id]

            if route.active and has_feud and feud_causing is not None:
                event_log.append(
                    tick=tick,
                    location=s1.id,
                    event_type=EventType.TRADE_ROUTE_BROKEN,
                    participants={"settlement_a": s1.id, "settlement_b": s2.id},
                    causes=[feud_causing.id],
                    intent=Intent.MILITARY_ACTION,
                    scale=Scale.AGGREGATE,
                    payload={"feud_id": feud_causing.id},
                )
                route.active = False
                active_trade_route_events.pop(route_key, None)

            elif not route.active and not has_feud:
                famine_s1 = s1.food < 15
                famine_s2 = s2.food < 15
                found_roll = keyed_float(seed, "route_found", f"{s1_id}_{s2_id}", tick)
                threshold = 0.25 if (famine_s1 or famine_s2) else 0.05
                if found_roll < threshold:
                    causes: list[int] = []
                    for past_evt in reversed(event_log.all_events()[-15:]):
                        if past_evt.type == EventType.PEACE:
                            if s1_id in past_evt.location or s2_id in past_evt.location:
                                causes.append(past_evt.id)
                                break
                        elif past_evt.type == EventType.FAMINE and (famine_s1 or famine_s2):
                            causes.append(past_evt.id)
                            break

                    evt = event_log.append(
                        tick=tick,
                        location=s1.id,
                        event_type=EventType.TRADE_ROUTE_FOUNDED,
                        participants={"settlement_a": s1.id, "settlement_b": s2.id},
                        causes=causes,
                        intent=Intent.INTENTIONAL,
                        scale=Scale.AGGREGATE,
                        payload={},
                    )
                    route.active = True
                    route.founded_event_id = evt.id
                    active_trade_route_events[route_key] = evt.id

            if route.active:
                # Bilateral trade: surplus food sold for wealth (Section 2d & 3c)
                if s1.food > s2.food + 20 and s1.food > 30:
                    transfer = min(12, (s1.food - s2.food) // 3)
                    payment = min(s2.wealth, max(1, transfer // 4))
                    s2.wealth -= payment
                    s1.wealth += payment
                    s1.food -= transfer
                    s2.food += transfer
                elif s2.food > s1.food + 20 and s2.food > 30:
                    transfer = min(12, (s2.food - s1.food) // 3)
                    payment = min(s1.wealth, max(1, transfer // 4))
                    s1.wealth -= payment
                    s2.wealth += payment
                    s2.food -= transfer
                    s1.food += transfer

    # =========================================================================
    # 3. LEADERSHIP & SUCCESSION CRISES (Section 4.5)
    # =========================================================================
    for s_id in settlement_keys:
        s = settlements[s_id]
        chief = characters.get(s.leader_id) if s.leader_id else None

        if not chief or not chief.alive:
            chief_death_evt_id: int | None = None
            chief_died_violently = False

            if chief:
                for past_evt in reversed(event_log.all_events()[-30:]):
                    if past_evt.type == EventType.DEATH and past_evt.participants_dict.get("target") == chief.id:
                        chief_death_evt_id = past_evt.id
                        chief_died_violently = past_evt.payload.get("natural") is not True
                        break

            if chief_death_evt_id is None:
                for past_evt in reversed(event_log.all_events()):
                    if past_evt.type == EventType.DEATH:
                        chief_death_evt_id = past_evt.id
                        break

            local_citizens = [c for c in living_chars if c.settlement_id == s_id and c.age_years >= 18]
            if not local_citizens:
                continue

            children = [c for c in local_citizens if chief and c.id in chief.children_ids]
            children.sort(key=lambda c: c.age_ticks, reverse=True)
            candidate_1 = children[0] if children else None

            standing_sorted = sorted(local_citizens, key=lambda c: c.age_ticks, reverse=True)
            c1_fam = getattr(candidate_1, "family_id", "") or (candidate_1.last_name if candidate_1 else "")
            other_family = [c for c in standing_sorted if candidate_1 and (getattr(c, "family_id", "") or c.last_name) != c1_fam]
            candidate_2 = other_family[0] if other_family else (standing_sorted[0] if standing_sorted else candidate_1)

            successor = candidate_1 or candidate_2

            crisis_occurred = False
            crisis_evt_id: int | None = None
            if candidate_1 and candidate_2 and candidate_1.id != candidate_2.id:
                rel_12 = get_relationship(candidate_1.id, candidate_2.id)
                if chief_died_violently or rel_12.hatred >= 20.0 or rel_12.trust <= 0.0 or s.stability < 0.8:
                    if chief_death_evt_id is not None:
                        crisis_evt = event_log.append(
                            tick=tick,
                            location=s.id,
                            event_type=EventType.SUCCESSION_CRISIS,
                            participants={"settlement": s.id, "rival_1": candidate_1.id, "rival_2": candidate_2.id},
                            causes=[chief_death_evt_id],
                            intent=Intent.INTENTIONAL,
                            scale=Scale.AGGREGATE,
                            payload={},
                        )
                        crisis_occurred = True
                        crisis_evt_id = crisis_evt.id
                        s.stability = 0.50

            chief_causes = [crisis_evt_id] if crisis_occurred and crisis_evt_id is not None else ([chief_death_evt_id] if chief_death_evt_id is not None else [])
            event_log.append(
                tick=tick,
                location=s.id,
                event_type=EventType.CHIEF_CHANGED,
                participants={"settlement": s.id, "new_chief": successor.id},
                causes=chief_causes,
                intent=Intent.INTENTIONAL,
                scale=Scale.AGGREGATE,
                payload={},
            )
            s.leader_id = successor.id

        s.stability = min(1.0, s.stability + 0.05)

    # =========================================================================
    # 4. FEUD EVALUATION (Wrongful or Justified, Section 4.1)
    # =========================================================================
    total_active = sum(1 for f in active_feuds if f.active)

    if total_active < 4:
        active_instigators = {f.instigator_char_id for f in active_feuds if f.active}
        active_char_pairs = {(f.instigator_char_id, f.target_char_id) for f in active_feuds if f.active}
        active_settlement_pairs = {tuple(sorted([f.instigator_settlement_id, f.target_settlement_id])) for f in active_feuds if f.active}

        for char in sorted_chars:
            if char.id in active_instigators:
                continue

            char_beliefs = beliefs_by_character.get(char.id, {})
            started_feud_for_char = False
            for event_ref in sorted(char_beliefs.keys()):
                belief = char_beliefs[event_ref]

                offence_target: str | None = None
                offence_actor: str | None = None
                is_valid_offence = False

                if belief.believed_type == EventType.DEATH and belief.believed_intent in (Intent.INTENTIONAL, Intent.MILITARY_ACTION):
                    victim = characters.get(belief.believed_target) if belief.believed_target else None
                    v_fam = getattr(victim, "family_id", "") or (victim.last_name if victim else "")
                    c_fam = getattr(char, "family_id", "") or char.last_name
                    is_kin = victim and (
                        victim.id in char.children_ids
                        or victim.id in (char.father_id, char.mother_id)
                        or victim.id == char.spouse_id
                        or (v_fam and v_fam == c_fam)
                    )
                    if is_kin:
                        offence_actor = belief.believed_actor
                        offence_target = char.id
                        is_valid_offence = True

                elif belief.believed_type == EventType.RAID:
                    if belief.believed_location == char.settlement_id:
                        offence_actor = belief.believed_actor
                        offence_target = char.id
                        is_valid_offence = True

                if not is_valid_offence or not offence_actor or offence_actor == char.id:
                    continue

                # Directive 10: Closed grievances cannot start new feuds unless instigator holds an uncorrected belief
                if event_ref in resolved_grievance_event_ids:
                    inst_b = char_beliefs.get(event_ref)
                    if not inst_b or inst_b.supersedes_belief_id is not None or inst_b.believed_intent not in (Intent.INTENTIONAL, Intent.MILITARY_ACTION):
                        continue

                accused = characters.get(offence_actor)
                if not accused or not accused.alive:
                    continue

                if (char.id, accused.id) in active_char_pairs:
                    continue

                pair_key = tuple(sorted([char.settlement_id, accused.settlement_id]))
                if pair_key in active_settlement_pairs:
                    continue

                rel = get_relationship(char.id, accused.id)

                if rel.hatred >= 40.0:
                    feud_roll = keyed_float(seed, "feud_start", f"{char.id}_{accused.id}", tick)
                    if feud_roll < 0.15:
                        real_event = event_log.get(event_ref)
                        is_wrongful = real_event.intent == Intent.ACCIDENTAL and real_event.type == EventType.DEATH

                        causes = [event_ref]

                        evt = event_log.append(
                            tick=tick,
                            location=char.settlement_id,
                            event_type=EventType.FEUD,
                            participants={"instigator": char.id, "target": accused.id},
                            causes=causes,
                            intent=Intent.INTENTIONAL,
                            scale=Scale.INDIVIDUAL,
                            payload={
                                "is_wrongful": is_wrongful,
                                "victim_id": offence_target,
                                "accused_id": accused.id,
                            },
                        )

                        new_feud = ActiveFeud(
                            id=evt.id,
                            instigator_char_id=char.id,
                            target_char_id=accused.id,
                            instigator_settlement_id=char.settlement_id,
                            target_settlement_id=accused.settlement_id,
                            root_cause_event_id=event_ref,
                            is_wrongful=is_wrongful,
                            start_tick=tick,
                            active=True,
                            primary_avenger_id=char.id,
                        )
                        active_feuds.append(new_feud)
                        active_instigators.add(char.id)
                        active_char_pairs.add((char.id, accused.id))
                        active_settlement_pairs.add(pair_key)
                        total_active += 1
                        started_feud_for_char = True
                        break

            if started_feud_for_char and total_active >= 4:
                break

    # =========================================================================
    # 5. REVENGE KILLINGS & AVENGER SELECTION (Historical Pressure 1, Section 4.5 & M1)
    # =========================================================================
    for feud in active_feuds:
        if not feud.active:
            continue

        # Inherited Grudges: When parent dies, children inherit feud grudge
        orig_inst = characters.get(feud.instigator_char_id)
        if orig_inst and (not orig_inst.alive or tick % 12 == 0):
            p_beliefs = beliefs_by_character.get(orig_inst.id, {})
            p_b = p_beliefs.get(feud.root_cause_event_id)
            if p_b:
                for child_id in orig_inst.children_ids:
                    child = characters.get(child_id)
                    if not child or not child.alive:
                        continue
                    c_beliefs = beliefs_by_character.get(child.id, {})
                    if feud.root_cause_event_id not in c_beliefs:
                        new_b_id = belief_counter[0]
                        belief_counter[0] += 1
                        new_b = Belief(
                            belief_id=new_b_id,
                            believer_id=child.id,
                            event_ref=feud.root_cause_event_id,
                            source=BeliefSource.TOLD_BY_PARENT,
                            source_character_id=orig_inst.id,
                            confidence=p_b.confidence * 0.7,
                            tick_acquired=tick,
                            believed_type=p_b.believed_type,
                            believed_intent=p_b.believed_intent,
                            believed_actor=p_b.believed_actor,
                            believed_target=p_b.believed_target,
                            believed_location=p_b.believed_location,
                            believed_payload={"inherited_from": orig_inst.id},
                        )
                        c_beliefs[feud.root_cause_event_id] = new_b
                        beliefs_by_character[child.id] = c_beliefs

                        p_rel = get_relationship(orig_inst.id, feud.target_char_id)
                        p_hatred = p_rel.hatred if orig_inst.alive else 80.0
                        b_decay = 0.003 * (1.0 + child.forgiveness)
                        memories.append(
                            Memory(
                                id=memory_counter[0],
                                observer_id=child.id,
                                belief_event_ref=feud.root_cause_event_id,
                                target_entity_id=feud.target_char_id,
                                emotion=Emotion.HATRED,
                                initial_intensity=max(20.0, p_hatred * 0.6),
                                decay_rate=b_decay * 2.0,
                                tick_formed=tick,
                                source_belief_id=new_b.belief_id,
                            )
                        )
                        memory_counter[0] += 1

        # Avenger Selection: gender-neutral across degree 1 and 2 kin
        primary_av, secondary_av = select_feud_avengers(feud, characters, get_relationship, tick)
        feud.primary_avenger_id = primary_av or feud.instigator_char_id
        feud.secondary_avenger_id = secondary_av

        if feud.revenge_count >= 1:
            continue

        elapsed = tick - feud.start_tick
        if elapsed < 18 or (tick - feud.last_revenge_tick) < 36:
            continue

        # Choose acting avenger
        avenger = characters.get(feud.primary_avenger_id) if feud.primary_avenger_id else None
        if not avenger or not avenger.alive:
            if feud.secondary_avenger_id:
                avenger = characters.get(feud.secondary_avenger_id)
        if not avenger or not avenger.alive:
            avenger = characters.get(feud.instigator_char_id)

        target = characters.get(feud.target_char_id)

        if not avenger or not avenger.alive or not target or not target.alive:
            continue

        target_set_living = [c for c in living_chars if c.settlement_id == target.settlement_id]
        if len(target_set_living) <= 3:
            continue

        rel = get_relationship(avenger.id, target.id)
        if rel.hatred >= 60.0 and avenger.forgiveness < 0.60:
            revenge_chance = 0.04 * (1.1 - avenger.forgiveness)
            roll = keyed_float(seed, "revenge_kill", str(feud.id), tick)
            if roll < revenge_chance:
                target.alive = False
                target.death_tick = tick
                feud.last_revenge_tick = tick
                feud.revenge_count += 1

                evt = event_log.append(
                    tick=tick,
                    location=target.settlement_id,
                    event_type=EventType.DEATH,
                    participants={"actor": avenger.id, "target": target.id},
                    causes=[feud.root_cause_event_id, feud.id],
                    intent=Intent.INTENTIONAL,
                    scale=Scale.INDIVIDUAL,
                    payload={
                        "revenge": True,
                        "cause_of_death": "Revenge",
                        "feud_id": feud.id,
                        "avenger_id": avenger.id,
                    },
                )
                target.death_event_id = evt.id

    # =========================================================================
    # 6. RAIDS (Feud, Famine, or Succession Escalation)
    # =========================================================================
    for feud in active_feuds:
        if not feud.active:
            continue

        attacker_set_id = feud.instigator_settlement_id
        defender_set_id = feud.target_settlement_id

        # Skip collapsed settlements
        if attacker_set_id in collapsed_settlements or defender_set_id in collapsed_settlements:
            feud.active = False
            continue

        if attacker_set_id == defender_set_id:
            continue

        # Invariant: Raids require a living instigator in attacking settlement with an active grievance
        instigator = characters.get(feud.instigator_char_id)
        if not instigator or not instigator.alive or instigator.settlement_id != attacker_set_id:
            continue

        # Instigator must hold active grievance (hatred >= 20.0)
        rel_feud = get_relationship(instigator.id, feud.target_char_id)
        if rel_feud.hatred < 20.0:
            continue

        # Raid Cooldown: at least 12 months between raids by this settlement pair
        pair_key = (attacker_set_id, defender_set_id)
        if tick - last_raid_ticks.get(pair_key, -100) < 12:
            continue

        attacker_set = settlements[attacker_set_id]
        defender_set = settlements[defender_set_id]

        # Do not raid a devastated settlement with food < 20
        if defender_set.food < 20:
            continue

        raid_prob = 0.04 * (1.3 - 0.3 * defender_set.stability)
        raid_roll = keyed_float(seed, "raid_roll", f"feud_{feud.id}", tick)
        if raid_roll < raid_prob:
            feud.raid_count += 1
            last_raid_ticks[pair_key] = tick

            looted_food = min(15, defender_set.food // 4)
            defender_set.food -= looted_food
            attacker_set.food += looted_food

            defender_living = [c for c in characters.values() if c.alive and c.settlement_id == defender_set.id and c.age_years >= 16]
            casualty = None
            if len(defender_living) > 3:
                casualty_roll = keyed_float(seed, "raid_casualty", f"{feud.id}_{feud.raid_count}", tick)
                if casualty_roll < 0.08:
                    casualty = keyed_choice(seed, "raid_victim", f"{feud.id}_{feud.raid_count}", tick, defender_living)

            # Directive 6: Log an event ONLY when there is a consequence:
            # - First raid of a feud
            # - A death
            # - Food stolen >= 15
            is_first_raid = (feud.raid_count == 1)
            has_heavy_loot = (looted_food >= 15)
            has_casualty = (casualty is not None)

            if not (is_first_raid or has_heavy_loot or has_casualty):
                feud.minor_raids += 1
            else:
                causes = [feud.id]
                raid_evt = event_log.append(
                    tick=tick,
                    location=defender_set.id,
                    event_type=EventType.RAID,
                    participants={
                        "initiator": attacker_set.id,
                        "target": defender_set.id,
                        "instigator_char": instigator.id,
                    },
                    causes=causes,
                    intent=Intent.MILITARY_ACTION,
                    scale=Scale.AGGREGATE,
                    payload={
                        "looted_food": looted_food,
                        "feud_id": feud.id,
                        "minor_raids_preceding": feud.minor_raids,
                    },
                )
                feud.minor_raids = 0

                if casualty is not None:
                    casualty.alive = False
                    casualty.death_tick = tick
                    evt = event_log.append(
                        tick=tick,
                        location=defender_set.id,
                        event_type=EventType.DEATH,
                        participants={"actor": instigator.id, "target": casualty.id},
                        causes=[raid_evt.id],
                        intent=Intent.MILITARY_ACTION,
                        scale=Scale.INDIVIDUAL,
                        payload={
                            "cause_of_death": "Raid Casualty",
                        },
                    )
                    casualty.death_event_id = evt.id

    # =========================================================================
    # 7. TRUTH REVELATION & PEACE RECONCILIATION (Sections 4.3 & 4.4)
    # =========================================================================
    for feud in active_feuds:
        if not feud.active:
            continue

        instigator = characters.get(feud.instigator_char_id)
        target = characters.get(feud.target_char_id)

        elapsed_ticks = tick - feud.start_tick

        # Path A: Real Truth Revelation Pipeline
        if feud.is_wrongful and elapsed_ticks >= 24 and instigator and instigator.alive:
            root_event = event_log.get(feud.root_cause_event_id)
            witness_candidates: list[Character] = []

            for w_cand in sorted_chars:
                w_beliefs = beliefs_by_character.get(w_cand.id, {})
                if feud.root_cause_event_id in w_beliefs:
                    b = w_beliefs[feud.root_cause_event_id]
                    if b.source == BeliefSource.WITNESSED and b.believed_intent == Intent.ACCIDENTAL and b.confidence >= 0.80:
                        can_comm = (
                            w_cand.settlement_id == instigator.settlement_id
                            or trade_routes.get(tuple(sorted([w_cand.settlement_id, instigator.settlement_id])), TradeRoute("", "")).active
                        )
                        if can_comm:
                            witness_candidates.append(w_cand)

            if witness_candidates:
                # Prioritize most trusted witness (e.g. close family member before hostile stranger)
                witness_candidates.sort(key=lambda w: get_relationship(instigator.id, w.id).trust, reverse=True)
                witness = witness_candidates[0]
                witness_id = witness.id

                timing_roll = keyed_float(seed, "revelation_timing", str(feud.id), tick)
                if timing_roll < 0.012:
                    rel_inst_w = get_relationship(instigator.id, witness.id)
                    w_belief = beliefs_by_character[witness.id][feud.root_cause_event_id]

                    trust_factor = max(0.2, min(1.0, (rel_inst_w.trust + 50.0) / 100.0))
                    suspicion_factor = max(0.5, 1.5 - instigator.suspicion)
                    incoming_credibility = w_belief.confidence * trust_factor * suspicion_factor

                    inst_current_belief = beliefs_by_character[instigator.id].get(feud.root_cause_event_id)
                    current_conf = inst_current_belief.confidence if inst_current_belief else 0.50

                    if incoming_credibility >= current_conf * 0.80:
                        rev_evt = event_log.append(
                            tick=tick,
                            location=instigator.settlement_id,
                            event_type=EventType.REVELATION,
                            participants={"witness": witness.id, "recipient": instigator.id},
                            causes=[feud.root_cause_event_id, feud.id],
                            intent=Intent.INTENTIONAL,
                            scale=Scale.INDIVIDUAL,
                            payload={
                                "witness": witness.id,
                                "path": [witness.id, instigator.id],
                                "corrected_intent": "Accidental",
                                "feud_id": feud.id,
                            },
                        )

                        old_b_id = inst_current_belief.belief_id if inst_current_belief else None
                        new_b_id = belief_counter[0]
                        belief_counter[0] += 1

                        new_belief = Belief(
                            belief_id=new_b_id,
                            believer_id=instigator.id,
                            event_ref=feud.root_cause_event_id,
                            source=BeliefSource.TOLD,
                            source_character_id=witness.id,
                            confidence=min(1.0, incoming_credibility),
                            tick_acquired=tick,
                            believed_type=root_event.type,
                            believed_intent=Intent.ACCIDENTAL,
                            believed_actor=root_event.participants_dict.get("actor"),
                            believed_target=root_event.participants_dict.get("target"),
                            believed_location=root_event.location,
                            believed_payload={"note": f"Corrected via revelation #{rev_evt.id}"},
                            supersedes_belief_id=old_b_id,
                        )
                        beliefs_by_character[instigator.id][feud.root_cause_event_id] = new_belief

                        if old_b_id is not None:
                            for m in memories:
                                if m.observer_id == instigator.id and m.source_belief_id == old_b_id:
                                    superseded_memory_ids.add(m.id)

                        from minemesis.systems.memory_system import form_memories_from_belief
                        rel_cur = get_relationship(instigator.id, feud.target_char_id)
                        reappraisal_mems = form_memories_from_belief(
                            belief=new_belief,
                            characters=characters,
                            next_memory_id=memory_counter[0],
                            tick=tick,
                            prior_hatred=rel_cur.hatred,
                        )
                        memory_counter[0] += len(reappraisal_mems)
                        memories.extend(reappraisal_mems)

                        # Cascade correction to living degree-1 kin (Milestone 1 requirement)
                        store = characters if hasattr(characters, "get_person") else _DictStore(characters)
                        kin_net = get_kin_network(store, instigator.id, max_degree=1)
                        living_deg1 = [characters[kid] for kid in kin_net if kid in characters and characters[kid].alive]

                        accepted_count = 1  # Instigator already accepted
                        total_deg1_count = 1 + len(living_deg1)

                        for kin_char in living_deg1:
                            rel_kin_w = get_relationship(kin_char.id, witness.id)
                            t_factor = max(0.2, min(1.0, (rel_kin_w.trust + 50.0) / 100.0))
                            s_factor = max(0.5, 1.5 - kin_char.suspicion)
                            kin_cred = incoming_credibility * t_factor * s_factor

                            kin_cur_b = beliefs_by_character.get(kin_char.id, {}).get(feud.root_cause_event_id)
                            kin_conf = kin_cur_b.confidence if kin_cur_b else 0.50

                            if kin_cred >= kin_conf * 0.70:
                                accepted_count += 1
                                old_k_bid = kin_cur_b.belief_id if kin_cur_b else None
                                new_k_bid = belief_counter[0]
                                belief_counter[0] += 1
                                kin_new_b = Belief(
                                    belief_id=new_k_bid,
                                    believer_id=kin_char.id,
                                    event_ref=feud.root_cause_event_id,
                                    source=BeliefSource.TOLD,
                                    source_character_id=instigator.id,
                                    confidence=min(1.0, kin_cred),
                                    tick_acquired=tick,
                                    believed_type=root_event.type,
                                    believed_intent=Intent.ACCIDENTAL,
                                    believed_actor=root_event.participants_dict.get("actor"),
                                    believed_target=root_event.participants_dict.get("target"),
                                    believed_location=root_event.location,
                                    believed_payload={"note": f"Cascade revelation via #{rev_evt.id}"},
                                    supersedes_belief_id=old_k_bid,
                                )
                                if kin_char.id not in beliefs_by_character:
                                    beliefs_by_character[kin_char.id] = {}
                                beliefs_by_character[kin_char.id][feud.root_cause_event_id] = kin_new_b

                                if old_k_bid is not None:
                                    for m in memories:
                                        if m.observer_id == kin_char.id and m.source_belief_id == old_k_bid:
                                            superseded_memory_ids.add(m.id)

                                kin_rel_cur = get_relationship(kin_char.id, feud.target_char_id)
                                kin_reappraisal = form_memories_from_belief(
                                    belief=kin_new_b,
                                    characters=characters,
                                    next_memory_id=memory_counter[0],
                                    tick=tick,
                                    prior_hatred=kin_rel_cur.hatred,
                                )
                                memory_counter[0] += len(kin_reappraisal)
                                memories.extend(kin_reappraisal)

                        # Reconcile feud ONLY if > 50% of living degree-1 kin accept the correction
                        if (accepted_count / total_deg1_count) <= 0.50:
                            continue

                        feud.active = False

                        target_char = characters.get(feud.target_char_id)
                        if target_char and target_char.alive:
                            party2_id = target_char.id
                            party2_name = target_char.full_name
                        else:
                            s_tgt = settlements.get(feud.target_settlement_id)
                            party2_char = None
                            if s_tgt and s_tgt.leader_id and characters.get(s_tgt.leader_id) and characters[s_tgt.leader_id].alive:
                                party2_char = characters[s_tgt.leader_id]
                            else:
                                tgt_living = [c for c in characters.values() if c.alive and c.settlement_id == feud.target_settlement_id]
                                if tgt_living:
                                    party2_char = tgt_living[0]
                            if not party2_char:
                                continue
                            party2_id = party2_char.id
                            party2_name = party2_char.full_name

                        event_log.append(
                            tick=tick,
                            location=feud.instigator_settlement_id,
                            event_type=EventType.PEACE,
                            participants={
                                "initiator": feud.instigator_settlement_id,
                                "target": feud.target_settlement_id,
                                "party1": instigator.id,
                                "party2": party2_id,
                            },
                            causes=[feud.id, rev_evt.id],
                            intent=Intent.INTENTIONAL,
                            scale=Scale.AGGREGATE,
                            payload={
                                "feud_id": feud.id,
                                "reconciliation_type": "Truth Revealed",
                            },
                        )

                        # Directive 10: Grievance closure on Peace
                        resolved_grievance_event_ids.add(feud.root_cause_event_id)
                        resolved_grievance_event_ids.add(feud.id)
                        for past_e in event_log.all_events()[-30:]:
                            if feud.id in past_e.causes:
                                resolved_grievance_event_ids.add(past_e.id)
                        continue

        # Path B: Negotiated Peace through Fatigue & Memory Decay
        leader = instigator if (instigator and instigator.alive) else None
        if leader is None:
            s_inst = settlements.get(feud.instigator_settlement_id)
            if s_inst and s_inst.leader_id and s_inst.leader_id in characters and characters[s_inst.leader_id].alive:
                leader = characters[s_inst.leader_id]

        if elapsed_ticks >= 72 and leader and leader.alive:
            target_char = characters.get(feud.target_char_id)
            if target_char and target_char.alive:
                party2_id = target_char.id
            else:
                s_tgt = settlements.get(feud.target_settlement_id)
                party2_char = None
                if s_tgt and s_tgt.leader_id and characters.get(s_tgt.leader_id) and characters[s_tgt.leader_id].alive:
                    party2_char = characters[s_tgt.leader_id]
                else:
                    tgt_living = [c for c in characters.values() if c.alive and c.settlement_id == feud.target_settlement_id]
                    if tgt_living:
                        party2_char = tgt_living[0]
                if not party2_char:
                    continue
                party2_id = party2_char.id

            rel = get_relationship(leader.id, party2_id)
            if rel.hatred < 20.0:
                peace_roll = keyed_float(seed, "exhaustion_peace", str(feud.id), tick)
                if peace_roll < 0.008:
                    exhaustion_evt_id: int | None = None
                    for past_evt in reversed(event_log.all_events()[-25:]):
                        if past_evt.type in (EventType.RAID, EventType.DEATH) and feud.id in past_evt.causes:
                            exhaustion_evt_id = past_evt.id
                            break

                    if exhaustion_evt_id is None:
                        exhaustion_evt_id = feud.root_cause_event_id

                    feud.active = False
                    event_log.append(
                        tick=tick,
                        location=feud.instigator_settlement_id,
                        event_type=EventType.PEACE,
                        participants={
                            "initiator": feud.instigator_settlement_id,
                            "target": feud.target_settlement_id,
                            "party1": leader.id,
                            "party2": party2_id,
                        },
                        causes=[feud.id, exhaustion_evt_id],
                        intent=Intent.INTENTIONAL,
                        scale=Scale.AGGREGATE,
                        payload={
                            "feud_id": feud.id,
                            "reconciliation_type": "Negotiated Treaty",
                        },
                    )

                    # Directive 10: Grievance closure on Peace
                    resolved_grievance_event_ids.add(feud.root_cause_event_id)
                    resolved_grievance_event_ids.add(feud.id)
                    for past_e in event_log.all_events()[-30:]:
                        if feud.id in past_e.causes:
                            resolved_grievance_event_ids.add(past_e.id)

    # =========================================================================
    # 8. SETTLEMENT COLLAPSE & MIGRATION (Milestone 0.5.1 Section 3b)
    # =========================================================================
    # When a settlement falls to the collapse threshold (population <= 4 and > 0),
    # emit SettlementCollapse with antecedent causes (Raid, Famine, Feud, Death, SuccessionCrisis),
    # then emit Migration moving survivors to the nearest surviving settlement.
    for s_id in settlement_keys:
        if s_id in collapsed_settlements:
            continue
        s = settlements[s_id]
        survivors = [c for c in characters.values() if c.alive and c.settlement_id == s_id]
        if 0 < len(survivors) <= 4:
            # Check if there are viable surviving destinations
            viable_destinations = [
                other_s for other_id, other_s in settlements.items()
                if other_id != s_id and other_id not in collapsed_settlements and len([c for c in characters.values() if c.alive and c.settlement_id == other_id]) > 0
            ]
            if not viable_destinations:
                # The last surviving settlement in the world does not collapse
                continue

            collapse_causes: list[int] = []
            for past_evt in reversed(event_log.all_events()):
                if past_evt.type in (EventType.RAID, EventType.FAMINE, EventType.FEUD, EventType.DEATH, EventType.SUCCESSION_CRISIS):
                    is_relevant = (
                        past_evt.location == s_id
                        or past_evt.participants_dict.get("initiator") == s_id
                        or past_evt.participants_dict.get("target") == s_id
                        or past_evt.participants_dict.get("settlement") == s_id
                        or any(c.id in (past_evt.participants_dict.get("actor"), past_evt.participants_dict.get("target")) for c in survivors)
                    )
                    if is_relevant:
                        collapse_causes.append(past_evt.id)
                        break

            if not collapse_causes:
                for past_evt in reversed(event_log.all_events()):
                    if past_evt.type in (EventType.RAID, EventType.FAMINE, EventType.FEUD, EventType.DEATH, EventType.SUCCESSION_CRISIS):
                        collapse_causes.append(past_evt.id)
                        break

            if not collapse_causes:
                continue

            collapsed_settlements.add(s_id)

            # Deactivate and mark feuds dormant (Directive 5: do NOT log Peace)
            dormant_feud_ids: list[int] = []
            for feud in active_feuds:
                if feud.active and (feud.instigator_settlement_id == s_id or feud.target_settlement_id == s_id):
                    feud.active = False
                    dormant_feud_ids.append(feud.id)

            collapse_evt = event_log.append(
                tick=tick,
                location=s_id,
                event_type=EventType.SETTLEMENT_COLLAPSE,
                participants={"settlement": s_id},
                causes=collapse_causes,
                intent=Intent.ACCIDENTAL,
                scale=Scale.AGGREGATE,
                payload={
                    "settlement_id": s_id,
                    "remaining_population": len(survivors),
                    "trigger_cause_id": collapse_causes[0],
                    "dormant_feuds": dormant_feud_ids,
                },
            )

            if viable_destinations:
                def dest_score(dest: Settlement) -> float:
                    dist = ((s.x - dest.x) ** 2 + (s.y - dest.y) ** 2) ** 0.5
                    avg_trust = 0.0
                    cnt = 0
                    dest_members = [c for c in characters.values() if c.alive and c.settlement_id == dest.id]
                    for surv in survivors:
                        for dm in dest_members[:5]:
                            avg_trust += get_relationship(surv.id, dm.id).trust
                            cnt += 1
                    trust_val = (avg_trust / cnt) if cnt > 0 else 0.0
                    return -dist + trust_val * 2.0

                viable_destinations.sort(key=dest_score, reverse=True)
                dest_s = viable_destinations[0]

                migrant_ids = [c.id for c in survivors]
                event_log.append(
                    tick=tick,
                    location=s_id,
                    event_type=EventType.MIGRATION,
                    participants={"source": s_id, "destination": dest_s.id},
                    causes=[collapse_evt.id],
                    intent=Intent.INTENTIONAL,
                    scale=Scale.AGGREGATE,
                    payload={
                        "source_settlement_id": s_id,
                        "destination_settlement_id": dest_s.id,
                        "migrants": migrant_ids,
                    },
                )

                # Move survivors while preserving beliefs, memories, and kinship
                for c in survivors:
                    if c.id in s.member_ids:
                        s.member_ids.remove(c.id)
                    c.settlement_id = dest_s.id
                    dest_s.member_ids.append(c.id)

                dest_s.food += s.food
                dest_s.wealth += s.wealth
                s.food = 0
                s.wealth = 0
                s.leader_id = None

                for r_key, route in list(trade_routes.items()):
                    if s_id in r_key and route.active:
                        route.active = False
                        active_trade_route_events.pop(r_key, None)
