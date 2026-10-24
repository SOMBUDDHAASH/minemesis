"""
Religious Interpretation Layer (Milestone R1.1).

Converts objective Event perception into subjective religious belief:
Event -> Perception -> Religion Filter -> Belief

Characters adhering to different faiths perceive the exact same objective reality
through radically different theological lenses:
- Ancestor-oriented faith: "Ancestors angry."
- Reincarnation-oriented faith: "Natural cycle."
- Divine Judgment faith: "Punishment from the gods."
- Martyrdom-oriented faith: "Sacred sacrifice."
"""

from __future__ import annotations
import random
from typing import Any, Mapping, Optional, Tuple
from minemesis.core.types import EventType, Intent
from minemesis.models.belief import Belief
from minemesis.models.character import Character
from minemesis.religion.religion_models import CharacterFaith, Religion


def _has_any(traits: Mapping[str, Any], *keys: str) -> bool:
    return any(k in traits for k in keys)


def apply_religious_interpretation_filter(
    belief: Belief,
    observer: Character,
    faith: Optional[CharacterFaith],
    religion: Optional[Religion],
    event_intent: Intent,
    rng: Optional[random.Random] = None,
) -> Belief:
    """
    Filters a raw perceptual belief through the observer's religious framework.
    Adds 'theological_framing', 'theological_narrative', and emotional offsets to believed_payload.
    """
    if faith is None or religion is None or not religion.traits:
        # Lay/unaligned interpretation
        return belief

    traits = religion.traits
    evt_type = belief.believed_type
    devotion = faith.devotion

    framing = "MORTAL_OCCURRENCE"
    narrative = f"{religion.name} observes the worldly event."
    grief_mult = 1.0
    fear_mult = 1.0
    anger_mult = 1.0
    respect_bonus = 0.0

    # 1. Death Interpretation
    if evt_type == EventType.DEATH:
        if _has_any(traits, "martyrdom_glory", "sacred_martyrdom") or (_has_any(traits, "warrior_tradition", "warrior_honor") and event_intent == Intent.MILITARY_ACTION):
            framing = "SACRED_SACRIFICE"
            narrative = f"A glorious passing in holy duty, celebrated in the halls of {religion.name}."
            grief_mult = max(0.2, 1.0 - (0.6 * devotion))
            respect_bonus = 25.0 * devotion
        elif _has_any(traits, "ancestor_worship", "ancestral_veneration", "ancestral_spirit_communion"):
            framing = "ANCESTOR_WRATH"
            narrative = f"The ancestral spirits have withdrawn their favor, claiming this soul in stern judgment."
            fear_mult = 1.0 + (0.5 * devotion)
        elif _has_any(traits, "reincarnation", "karmic_transmigration", "cycle_of_ages"):
            framing = "NATURAL_CYCLE"
            narrative = f"The wheel of rebirth turns; the soul sheds its temporary vessel into karmic renewal."
            grief_mult = max(0.3, 1.0 - (0.5 * devotion))
        elif _has_any(traits, "divine_judgment", "apocalyptic_judgment", "monotheism"):
            framing = "DIVINE_PUNISHMENT"
            narrative = f"The supreme divine will has rendered judgment upon the fallen."
            fear_mult = 1.0 + (0.4 * devotion)
        elif _has_any(traits, "animism", "animism_cosmology"):
            framing = "SPIRIT_RETURN"
            narrative = f"The spirit re-enters the sacred rivers, winds, and stone of the earth."
            grief_mult = max(0.5, 1.0 - (0.3 * devotion))
        else:
            framing = "MORTAL_PASSING"
            narrative = f"A soul has concluded their mortal pilgrimage under {religion.name}."

    # 2. Raid / Feud Interpretation
    elif evt_type in (EventType.RAID, EventType.FEUD):
        if _has_any(traits, "holy_war", "holy_war_zeal"):
            framing = "RIGHTEOUS_STRUGGLE"
            narrative = f"Sanctified conflict against the faithless, ordained by divine necessity."
            anger_mult = 1.0 + (0.5 * devotion)
        elif _has_any(traits, "pacifism", "strict_pacifism", "forgiveness", "forgiveness_doctrine"):
            framing = "SACRILEGIOUS_VIOLENCE"
            narrative = f"A grievous spiritual transgression rupturing cosmic balance and moral purity."
            fear_mult = 1.0 + (0.3 * devotion)
            anger_mult = 1.0 + (0.6 * devotion)
        elif _has_any(traits, "honor", "warrior_honor", "warrior_tradition"):
            framing = "HONOR_RECTIFICATION"
            narrative = f"Blood demands balance; honor commands that the covenant be defended."
        else:
            framing = "WORLDLY_STRIFE"
            narrative = f"Mortal discord disturbing the followers of {religion.name}."

    # 3. Famine Interpretation
    elif evt_type == EventType.FAMINE:
        if _has_any(traits, "divine_judgment", "apocalyptic_judgment", "taboo_food_restrictions"):
            framing = "DIVINE_CHASTISEMENT"
            narrative = f"The earth is barren because the people have transgressed holy taboos."
            fear_mult = 1.0 + (0.6 * devotion)
        elif _has_any(traits, "animism", "animism_cosmology"):
            framing = "EARTH_DROUGHT_TRIAL"
            narrative = f"The earth spirits are deep in slumber; offerings and endurance are required."
        else:
            framing = "TEST_OF_VIRTUE"
            narrative = f"A season of trial calling for charity, fasting, and spiritual resilience."

    # 4. Peace / Marriage Interpretation
    elif evt_type in (EventType.PEACE, EventType.MARRIAGE):
        if _has_any(traits, "forgiveness", "forgiveness_doctrine", "charity_obligation"):
            framing = "DIVINE_HARMONY"
            narrative = f"Cosmic reconciliation blessed by the heavens of {religion.name}."
            respect_bonus = 20.0 * devotion
        elif _has_any(traits, "family_loyalty_piety", "ancestor_worship", "bloodline_sanctity"):
            framing = "SACRED_KINSHIP_BOND"
            narrative = f"A bloodline covenant woven under the gaze of the ancestors."
            respect_bonus = 15.0 * devotion
        else:
            framing = "BLESSED_ACCORD"
            narrative = f"Harmony established among mortals."

    # 5. Religious Event Interpretation
    elif evt_type in (EventType.CONVERSION, EventType.RELIGIOUS_REFORM, EventType.RELIGIOUS_SCHISM, EventType.SAINT_CANONIZED):
        framing = "SPIRITUAL_WATERSHED"
        narrative = f"The divine dispensation unfolds through {evt_type.value}."

    # Build updated payload
    updated_payload = dict(belief.believed_payload)
    updated_payload["theological_framing"] = framing
    updated_payload["theological_narrative"] = narrative
    updated_payload["emotional_modifiers"] = {
        "grief_mult": round(grief_mult, 3),
        "fear_mult": round(fear_mult, 3),
        "anger_mult": round(anger_mult, 3),
        "respect_bonus": round(respect_bonus, 2),
    }

    # Return new immutable belief with enhanced religious interpretation
    return Belief(
        belief_id=belief.belief_id,
        believer_id=belief.believer_id,
        event_ref=belief.event_ref,
        source=belief.source,
        source_character_id=belief.source_character_id,
        confidence=belief.confidence,
        tick_acquired=belief.tick_acquired,
        believed_type=belief.believed_type,
        believed_intent=belief.believed_intent,
        believed_actor=belief.believed_actor,
        believed_target=belief.believed_target,
        believed_location=belief.believed_location,
        believed_payload=updated_payload,
        supersedes_belief_id=belief.supersedes_belief_id,
    )
