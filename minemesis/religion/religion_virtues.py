"""
Religious Virtue and Moral Standing System (Milestone R1.8).

Transforms theological traits into actionable moral and virtue expectations:
- Charity, Honor, Forgiveness, Discipline, Ancestor Loyalty, Purity, Wisdom.
- Characters earn or lose religious standing based on how their actions align with faith virtues:
  Faith values forgiveness + Character seeks revenge -> Religious standing drops.
  Faith values warrior honor + Character avenges kin -> Religious standing increases.
"""

from __future__ import annotations
from typing import Any, Mapping, Optional
from minemesis.core.types import EventType
from minemesis.models.character import Character
from minemesis.religion.religion_models import (
    CharacterFaith,
    Religion,
    ReligiousRole,
)


def _has_any(traits: Mapping[str, Any], *keys: str) -> bool:
    return any(k in traits for k in keys)


def evaluate_action_against_virtues(
    character: Character,
    faith: CharacterFaith,
    religion: Religion,
    action_type: EventType,
    action_role: str,
    action_payload: Mapping[str, Any],
) -> tuple[float, str]:
    """
    Evaluates a character's action against the virtues and moral codes of their faith.
    Returns (standing_delta, justification).
    """
    traits = religion.traits
    delta = 0.0
    reasons = []

    # 1. Peace / Reconciliation
    if action_type == EventType.PEACE:
        if _has_any(traits, "forgiveness", "forgiveness_doctrine"):
            delta += 20.0
            reasons.append("Fulfilled virtue of holy forgiveness and ended bloodshed")
        elif _has_any(traits, "pacifism", "strict_pacifism"):
            delta += 15.0
            reasons.append("Restored sacred non-violence and harmony")
        elif _has_any(traits, "warrior_tradition", "warrior_honor"):
            delta -= 8.0
            reasons.append("Yielded to peace without claiming total martial victory")

    # 2. Feuds & Raids
    elif action_type in (EventType.FEUD, EventType.RAID):
        is_instigator = action_role in ("actor", "initiator", "instigator", "attacker")
        if is_instigator:
            if _has_any(traits, "pacifism", "strict_pacifism", "forgiveness", "forgiveness_doctrine"):
                delta -= 25.0
                reasons.append("Violated fundamental mandate of peace and non-aggression")
            elif _has_any(traits, "holy_war", "holy_war_zeal"):
                delta += 15.0
                reasons.append("Righteously waged sanctified conflict against rivals")
            elif _has_any(traits, "honor", "warrior_honor", "warrior_tradition"):
                delta += 10.0
                reasons.append("Defended village and family honor through valor")

    # 3. Death & Retaliation
    elif action_type == EventType.DEATH:
        if action_payload.get("revenge_for_death_id") is not None:
            if _has_any(traits, "forgiveness", "forgiveness_doctrine"):
                delta -= 25.0
                reasons.append("Slew an adversary in vengeance, defying the call for forgiveness")
            elif _has_any(traits, "honor", "warrior_honor", "warrior_tradition"):
                delta += 15.0
                reasons.append("Redeemed the blood debt of fallen kin with honorable retribution")

    # 4. Family & Marriage
    elif action_type == EventType.MARRIAGE:
        if _has_any(traits, "family_loyalty", "family_loyalty_piety", "ancestor_worship", "ancestral_veneration"):
            delta += 12.0
            reasons.append("Sanctified ancestral bloodlines through lawful matrimony")

    # 5. Pilgrimage & Sacred Acts
    elif action_type == EventType.PILGRIMAGE:
        if _has_any(traits, "discipline", "ascetic_discipline", "pilgrimage_sites"):
            delta += 18.0
            reasons.append("Completed arduous sacred pilgrimage in pious discipline")
        else:
            delta += 8.0
            reasons.append("Undertook spiritual journey to a holy site")

    # Apply delta
    old_standing = faith.religious_standing
    faith.religious_standing = max(0.0, min(100.0, old_standing + delta))

    # Social/Role repercussions
    if faith.religious_standing >= 85.0 and faith.role == ReligiousRole.LAITY and faith.devotion >= 0.75:
        # Eligible for promotion to Elder/Monk
        faith.role = ReligiousRole.ELDER
        reasons.append("Elevated to Elder due to exemplary moral standing")
    elif faith.religious_standing <= 15.0 and faith.role in (ReligiousRole.PRIEST, ReligiousRole.ELDER):
        # Demoted due to scandal / sin
        faith.role = ReligiousRole.LAITY
        reasons.append("Stripped of clerical title due to moral transgression")

    justification = "; ".join(reasons) if reasons else "Routine adherence"
    return delta, justification
