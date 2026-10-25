"""
Collective Knowledge Engine for Milestone 0.5.4.

Solves the primary historical retention bottleneck:
Transitions epistemology from:
    Event -> 725 identical Belief objects stored forever in RAM
To:
    Event -> <= 10 personal beliefs (direct kin/witnesses)
          -> CollectiveKnowledge (Settlement / Family / Religion opinion vectors)
          -> Historical summary

Supports:
- SettlementOpinion
- FamilyOpinion
- ReligionOpinion
- FactionOpinion
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional, Sequence, Set

from minemesis.core.types import EventType, Intent


class KnowledgeOwnerType(str, Enum):
    SETTLEMENT = "Settlement"
    FAMILY = "Family"
    RELIGION = "Religion"
    FACTION = "Faction"


class KnowledgeTargetType(str, Enum):
    CHARACTER = "Character"
    FAMILY = "Family"
    SETTLEMENT = "Settlement"


@dataclass
class CollectiveKnowledge:
    """
    Compact community consensus / opinion vector.
    Replaces hundreds of thousands of redundant individual Belief objects.
    """
    owner_type: KnowledgeOwnerType
    owner_id: str                      # e.g., "set_0", "Ironwood", "rel_0"
    target_type: KnowledgeTargetType
    target_id: str                     # e.g., "char_12", "Blackwood", "set_1"
    reputation: float = 0.0            # [-100.0, 100.0]
    trust: float = 0.0                 # [-100.0, 100.0]
    hatred: float = 0.0                # [0.0, 100.0]
    dominant_grievance_id: Optional[int] = None
    last_updated_tick: int = 0

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.owner_type.value, self.owner_id, self.target_type.value, self.target_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner_type": self.owner_type.value,
            "owner_id": self.owner_id,
            "target_type": self.target_type.value,
            "target_id": self.target_id,
            "reputation": round(self.reputation, 2),
            "trust": round(self.trust, 2),
            "hatred": round(self.hatred, 2),
            "dominant_grievance_id": self.dominant_grievance_id,
            "last_updated_tick": self.last_updated_tick,
        }


class KnowledgeEngine:
    """
    Manages collective social knowledge, village consensus, and inter-group reputation.
    """
    def __init__(self) -> None:
        # Key: (owner_type, owner_id, target_type, target_id) -> CollectiveKnowledge
        self._records: dict[tuple[str, str, str, str], CollectiveKnowledge] = {}
        # Settlement public event registry: settlement_id -> set of notable Event IDs
        self._settlement_public_events: dict[str, set[int]] = {}

    def get_knowledge(
        self,
        owner_type: KnowledgeOwnerType | str,
        owner_id: str,
        target_type: KnowledgeTargetType | str,
        target_id: str,
    ) -> Optional[CollectiveKnowledge]:
        o_t = owner_type.value if isinstance(owner_type, KnowledgeOwnerType) else str(owner_type)
        t_t = target_type.value if isinstance(target_type, KnowledgeTargetType) else str(target_type)
        return self._records.get((o_t, owner_id, t_t, target_id))

    def ensure_knowledge(
        self,
        owner_type: KnowledgeOwnerType | str,
        owner_id: str,
        target_type: KnowledgeTargetType | str,
        target_id: str,
        tick: int = 0,
    ) -> CollectiveKnowledge:
        o_t = KnowledgeOwnerType(owner_type) if not isinstance(owner_type, KnowledgeOwnerType) else owner_type
        t_t = KnowledgeTargetType(target_type) if not isinstance(target_type, KnowledgeTargetType) else target_type
        key = (o_t.value, owner_id, t_t.value, target_id)
        if key not in self._records:
            self._records[key] = CollectiveKnowledge(
                owner_type=o_t,
                owner_id=owner_id,
                target_type=t_t,
                target_id=target_id,
                last_updated_tick=tick,
            )
        return self._records[key]

    def record_public_event(self, settlement_id: str, event_id: int) -> None:
        self._settlement_public_events.setdefault(settlement_id, set()).add(event_id)

    def is_publicly_known(self, settlement_id: str, event_id: int) -> bool:
        return event_id in self._settlement_public_events.get(settlement_id, set())

    def update_from_event(
        self,
        event: Any,
        settlement_id: str,
        characters: Mapping[str, Any],
        tick: int,
    ) -> None:
        """
        Updates settlement and family collective knowledge from an objective event.
        Replaces individual belief creation for the background community.
        """
        self.record_public_event(settlement_id, event.id)
        actor_id = event.participants_dict.get("actor") or event.participants_dict.get("instigator") or event.participants_dict.get("initiator")
        target_id = event.participants_dict.get("target") or event.participants_dict.get("victim")
        
        actor = characters.get(actor_id) if actor_id else None
        target = characters.get(target_id) if target_id else None

        actor_fam = getattr(actor, "family_id", "") or (actor.last_name if actor else "")
        target_fam = getattr(target, "family_id", "") or (target.last_name if target else "")

        # 1. Homicides / Deaths
        if event.type == EventType.DEATH:
            cause_of_death = event.payload.get("cause_of_death") or event.payload.get("cause")
            if event.intent in (Intent.INTENTIONAL, Intent.MILITARY_ACTION) or cause_of_death == "Revenge":
                if actor and target:
                    # Settlement Opinion against actor and actor's family
                    ck_char = self.ensure_knowledge(KnowledgeOwnerType.SETTLEMENT, settlement_id, KnowledgeTargetType.CHARACTER, actor.id, tick)
                    ck_char.reputation = max(-100.0, ck_char.reputation - 45.0)
                    ck_char.trust = max(-100.0, ck_char.trust - 50.0)
                    ck_char.hatred = min(100.0, ck_char.hatred + 60.0)
                    ck_char.dominant_grievance_id = event.id
                    ck_char.last_updated_tick = tick

                    if actor_fam:
                        ck_fam = self.ensure_knowledge(KnowledgeOwnerType.SETTLEMENT, settlement_id, KnowledgeTargetType.FAMILY, actor_fam, tick)
                        ck_fam.reputation = max(-100.0, ck_fam.reputation - 25.0)
                        ck_fam.trust = max(-100.0, ck_fam.trust - 30.0)
                        ck_fam.dominant_grievance_id = event.id
                        ck_fam.last_updated_tick = tick

                    # Victim's Family Opinion against Killer's Family
                    if target_fam and actor_fam and target_fam != actor_fam:
                        ck_fam_rel = self.ensure_knowledge(KnowledgeOwnerType.FAMILY, target_fam, KnowledgeTargetType.FAMILY, actor_fam, tick)
                        ck_fam_rel.hatred = min(100.0, ck_fam_rel.hatred + 70.0)
                        ck_fam_rel.trust = max(-100.0, ck_fam_rel.trust - 60.0)
                        ck_fam_rel.dominant_grievance_id = event.id
                        ck_fam_rel.last_updated_tick = tick

        # 2. Raids
        elif event.type == EventType.RAID:
            invader_settlement = event.participants_dict.get("initiator")
            if invader_settlement and settlement_id:
                ck_set = self.ensure_knowledge(KnowledgeOwnerType.SETTLEMENT, settlement_id, KnowledgeTargetType.SETTLEMENT, invader_settlement, tick)
                ck_set.trust = max(-100.0, ck_set.trust - 60.0)
                ck_set.hatred = min(100.0, ck_set.hatred + 50.0)
                ck_set.dominant_grievance_id = event.id
                ck_set.last_updated_tick = tick

        # 3. Peace / Truth Revelation Reconciliation
        elif event.type in (EventType.PEACE, EventType.REVELATION):
            # Expunge hatred and resolve dominant grievance across settlement and families
            for key, ck in list(self._records.items()):
                if ck.dominant_grievance_id and ck.dominant_grievance_id in event.causes:
                    ck.dominant_grievance_id = None
                    ck.hatred = max(0.0, ck.hatred * 0.20)  # 80% reduction
                    ck.trust = min(50.0, ck.trust + 40.0)
                    ck.reputation = min(50.0, ck.reputation + 30.0)
                    ck.last_updated_tick = tick

        # 4. Books and Cultural Achievements
        elif event.type == EventType.BOOK_WRITTEN:
            if actor:
                ck_char = self.ensure_knowledge(KnowledgeOwnerType.SETTLEMENT, settlement_id, KnowledgeTargetType.CHARACTER, actor.id, tick)
                ck_char.reputation = min(100.0, ck_char.reputation + 20.0)
                ck_char.last_updated_tick = tick
                if actor_fam:
                    ck_fam = self.ensure_knowledge(KnowledgeOwnerType.SETTLEMENT, settlement_id, KnowledgeTargetType.FAMILY, actor_fam, tick)
                    ck_fam.reputation = min(100.0, ck_fam.reputation + 10.0)
                    ck_fam.last_updated_tick = tick

    def get_reputation_offset(
        self,
        observer_settlement_id: str,
        observer_family_id: str,
        target_char_id: str,
        target_family_id: str,
        target_settlement_id: str,
    ) -> tuple[float, float, float]:
        """
        Returns (trust_offset, hatred_offset, respect_offset) from collective knowledge.
        Provides O(1) community consensus modifier.
        """
        t_off = 0.0
        h_off = 0.0
        r_off = 0.0

        # Check Family-on-Family knowledge first
        if observer_family_id and target_family_id and observer_family_id != target_family_id:
            ck_ff = self.get_knowledge(KnowledgeOwnerType.FAMILY, observer_family_id, KnowledgeTargetType.FAMILY, target_family_id)
            if ck_ff:
                t_off += ck_ff.trust * 0.40
                h_off += ck_ff.hatred * 0.40
                r_off += ck_ff.reputation * 0.30

        # Check Settlement-on-Character knowledge
        if observer_settlement_id and target_char_id:
            ck_sc = self.get_knowledge(KnowledgeOwnerType.SETTLEMENT, observer_settlement_id, KnowledgeTargetType.CHARACTER, target_char_id)
            if ck_sc:
                t_off += ck_sc.trust * 0.30
                h_off += ck_sc.hatred * 0.30
                r_off += ck_sc.reputation * 0.30

        # Check Settlement-on-Settlement knowledge
        if observer_settlement_id and target_settlement_id and observer_settlement_id != target_settlement_id:
            ck_ss = self.get_knowledge(KnowledgeOwnerType.SETTLEMENT, observer_settlement_id, KnowledgeTargetType.SETTLEMENT, target_settlement_id)
            if ck_ss:
                t_off += ck_ss.trust * 0.30
                h_off += ck_ss.hatred * 0.30

        return max(-50.0, min(50.0, t_off)), max(0.0, min(50.0, h_off)), max(-50.0, min(50.0, r_off))
