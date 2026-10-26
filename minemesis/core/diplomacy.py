"""
Settlement Politics and Warfare System for Milestone 2.

Manages inter-settlement diplomatic stances (Alliance, Friendly, Neutral, Suspicious, Hostile, War),
formal treaties, war declarations, and aggregated war campaigns that track casualties
and skirmishes without creating unbound event log spam.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence, Set

from minemesis.core.event_log import EventLog
from minemesis.core.rng import keyed_float, keyed_choice
from minemesis.core.types import DiplomaticStance, EventType, Intent, Scale
from minemesis.models.settlement import Settlement, TradeRoute


@dataclass
class WarCampaign:
    id: int
    initiator_id: str
    target_id: str
    war_event_id: int
    start_tick: int
    active: bool = True
    total_skirmishes: int = 0
    initiator_casualties: int = 0
    target_casualties: int = 0
    plundered_food: int = 0
    last_action_tick: int = -100


class DiplomacyManager:
    """
    Simulates inter-settlement geopolitics, treaty alliances, and campaign-level warfare.
    """

    def __init__(self) -> None:
        # Key: (min(s1, s2), max(s1, s2)) -> DiplomaticStance
        self.stances: dict[tuple[str, str], DiplomaticStance] = {}
        self.stance_scores: dict[tuple[str, str], float] = {}
        self.active_campaigns: list[WarCampaign] = []
        self.last_stance_event_id: dict[tuple[str, str], int] = {}
        self._next_campaign_id = 1

    def get_pair_key(self, s1: str, s2: str) -> tuple[str, str]:
        return (min(s1, s2), max(s1, s2))

    def get_stance(self, s1: str, s2: str) -> DiplomaticStance:
        if s1 == s2:
            return DiplomaticStance.ALLIANCE
        return self.stances.get(self.get_pair_key(s1, s2), DiplomaticStance.NEUTRAL)

    def get_diplomacy_matrix(self) -> dict[tuple[str, str], dict[str, Any]]:
        res = {}
        for pair, stance in self.stances.items():
            res[pair] = {
                "settlement_a": pair[0],
                "settlement_b": pair[1],
                "stance": stance.value,
                "score": round(self.stance_scores.get(pair, 0.0), 1),
            }
        return res

    def compute_pair_score(
        self,
        s1: str,
        s2: str,
        settlements: Mapping[str, Settlement],
        trade_routes: Mapping[tuple[str, str], TradeRoute],
        active_feuds: Sequence[Any],
        marriage_events: Mapping[tuple[str, str], int],
        recent_raids: Sequence[Any],
    ) -> float:
        pair_key = self.get_pair_key(s1, s2)
        score = 0.0

        # 1. Trade ties (+30)
        route = trade_routes.get(pair_key)
        if route and route.active:
            score += 30.0

        # 2. Inter-settlement marriages (+15 per marriage, max +45)
        for (m_s1, m_s2) in marriage_events.keys():
            if self.get_pair_key(m_s1, m_s2) == pair_key:
                score += 15.0

        # 3. Active feuds (-40 per feud)
        for feud in active_feuds:
            if getattr(feud, "active", True):
                f_s1 = getattr(feud, "instigator_settlement_id", "")
                f_s2 = getattr(feud, "target_settlement_id", "")
                if self.get_pair_key(f_s1, f_s2) == pair_key:
                    score -= 40.0

        # 4. Recent raids in past 5 years (-20 per raid)
        for r in recent_raids:
            r_s1 = r.get("initiator") or r.get("settlement1", "")
            r_s2 = r.get("target") or r.get("settlement2", "")
            if self.get_pair_key(r_s1, r_s2) == pair_key:
                score -= 20.0

        # 5. Settlement wealth & stability disparity
        set1 = settlements.get(s1)
        set2 = settlements.get(s2)
        if set1 and set2:
            if set1.stability < 0.5 or set2.stability < 0.5:
                score -= 10.0
            if (set1.food < 15 and set2.food > 100) or (set2.food < 15 and set1.food > 100):
                score -= 15.0  # Desperation envy

        return max(-100.0, min(100.0, score))

    def step_diplomacy(
        self,
        settlements: Mapping[str, Settlement],
        trade_routes: Mapping[tuple[str, str], TradeRoute],
        active_feuds: Sequence[Any],
        marriage_events: Mapping[tuple[str, str], int],
        event_log: EventLog,
        tick: int,
        seed: int,
    ) -> None:
        """
        Evaluates inter-settlement geopolitics and steps active war campaigns.
        """
        settlement_ids = sorted(settlements.keys())

        # Collect recent raids (last 60 ticks)
        recent_raids = []
        for past_e in reversed(event_log.all_events()[-80:]):
            if past_e.type == EventType.RAID and (tick - past_e.tick) <= 60:
                recent_raids.append(past_e.participants_dict)

        # 1. Update scores and evaluate transitions
        for i in range(len(settlement_ids)):
            for j in range(i + 1, len(settlement_ids)):
                s1 = settlement_ids[i]
                s2 = settlement_ids[j]
                pair_key = (s1, s2)

                score = self.compute_pair_score(
                    s1, s2, settlements, trade_routes, active_feuds, marriage_events, recent_raids
                )
                self.stance_scores[pair_key] = score
                old_stance = self.stances.get(pair_key, DiplomaticStance.NEUTRAL)

                # Map score to target stance
                if score >= 50.0:
                    new_stance = DiplomaticStance.ALLIANCE
                elif score >= 20.0:
                    new_stance = DiplomaticStance.FRIENDLY
                elif score >= -10.0:
                    new_stance = DiplomaticStance.NEUTRAL
                elif score >= -35.0:
                    new_stance = DiplomaticStance.SUSPICIOUS
                elif score >= -65.0:
                    new_stance = DiplomaticStance.HOSTILE
                else:
                    new_stance = DiplomaticStance.WAR

                # Evaluate Stance Transitions
                if new_stance != old_stance:
                    # Transition: Form Alliance
                    if new_stance == DiplomaticStance.ALLIANCE and old_stance != DiplomaticStance.ALLIANCE:
                        cause_id = None
                        route = trade_routes.get(pair_key)
                        if route and route.active:
                            cause_id = getattr(route, "event_id", None)
                        causes = [cause_id] if cause_id is not None else []
                        evt = event_log.append(
                            tick=tick,
                            location=s1,
                            event_type=EventType.ALLIANCE_FORMED,
                            participants={"settlement1": s1, "settlement2": s2},
                            causes=causes,
                            intent=Intent.INTENTIONAL,
                            scale=Scale.AGGREGATE,
                            payload={"score": score},
                        )
                        self.last_stance_event_id[pair_key] = evt.id

                    # Transition: Declare War
                    elif new_stance == DiplomaticStance.WAR and old_stance != DiplomaticStance.WAR:
                        # Find root cause event (active feud or raid)
                        cause_id = None
                        for feud in active_feuds:
                            if getattr(feud, "active", True):
                                f_pair = self.get_pair_key(
                                    getattr(feud, "instigator_settlement_id", ""),
                                    getattr(feud, "target_settlement_id", "")
                                )
                                if f_pair == pair_key:
                                    cause_id = getattr(feud, "id", None)
                                    break
                        if cause_id is None:
                            for past_e in reversed(event_log.all_events()[-50:]):
                                if past_e.type in (EventType.RAID, EventType.FEUD, EventType.TRADE_ROUTE_BROKEN):
                                    cause_id = past_e.id
                                    break

                        if cause_id is not None:
                            evt = event_log.append(
                                tick=tick,
                                location=s1,
                                event_type=EventType.WAR_DECLARED,
                                participants={"aggressor": s1, "defender": s2},
                                causes=[cause_id],
                                intent=Intent.MILITARY_ACTION,
                                scale=Scale.AGGREGATE,
                                payload={"score": score},
                            )
                            self.last_stance_event_id[pair_key] = evt.id
                            campaign = WarCampaign(
                                id=self._next_campaign_id,
                                initiator_id=s1,
                                target_id=s2,
                                war_event_id=evt.id,
                                start_tick=tick,
                            )
                            self._next_campaign_id += 1
                            self.active_campaigns.append(campaign)

                    # Transition: Sign Treaty
                    elif old_stance in (DiplomaticStance.WAR, DiplomaticStance.HOSTILE) and new_stance in (DiplomaticStance.NEUTRAL, DiplomaticStance.FRIENDLY):
                        war_cause = None
                        for c in self.active_campaigns:
                            if self.get_pair_key(c.initiator_id, c.target_id) == pair_key and c.war_event_id:
                                war_cause = c.war_event_id
                                break

                        if war_cause is None:
                            for past_e in reversed(event_log.all_events()[-50:]):
                                if past_e.type in (EventType.WAR_DECLARED, EventType.RAID, EventType.FEUD, EventType.PEACE, EventType.FAMINE):
                                    war_cause = past_e.id
                                    break

                        if war_cause is not None:
                            evt = event_log.append(
                                tick=tick,
                                location=s1,
                                event_type=EventType.TREATY_SIGNED,
                                participants={"party1": s1, "party2": s2},
                                causes=[war_cause],
                                intent=Intent.INTENTIONAL,
                                scale=Scale.AGGREGATE,
                                payload={"score": score},
                            )
                            self.last_stance_event_id[pair_key] = evt.id
                            for c in self.active_campaigns:
                                if self.get_pair_key(c.initiator_id, c.target_id) == pair_key:
                                    c.active = False

                    self.stances[pair_key] = new_stance

        # 2. Step Active War Campaigns (Campaign-level casualty tracking)
        for camp in self.active_campaigns:
            if not camp.active:
                continue
            pair_key = self.get_pair_key(camp.initiator_id, camp.target_id)
            if self.stances.get(pair_key) != DiplomaticStance.WAR:
                camp.active = False
                continue

            camp_duration = tick - camp.start_tick
            if camp_duration > 36 and (tick - camp.last_action_tick) > 12:
                # War fatigue treaty
                evt = event_log.append(
                    tick=tick,
                    location=camp.initiator_id,
                    event_type=EventType.TREATY_SIGNED,
                    participants={"party1": camp.initiator_id, "party2": camp.target_id},
                    causes=[camp.war_event_id],
                    intent=Intent.INTENTIONAL,
                    scale=Scale.AGGREGATE,
                    payload={"reason": "War Exhaustion", "skirmishes": camp.total_skirmishes},
                )
                self.last_stance_event_id[pair_key] = evt.id
                camp.active = False
                self.stances[pair_key] = DiplomaticStance.SUSPICIOUS
                continue

            # Monthly Skirmish Check
            skirmish_roll = keyed_float(seed, "campaign_skirmish", str(camp.id), tick)
            if skirmish_roll < 0.25:
                camp.total_skirmishes += 1
                camp.last_action_tick = tick
                # Minor skirmish increments casualty counts without polluting the EventLog
                camp.target_casualties += 1
                if skirmish_roll < 0.08:
                    camp.initiator_casualties += 1
