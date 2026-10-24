"""
Behavioral and Environmental Effects for the Standalone Religion Engine (Milestone R0).

Core Philosophy:
- Religions modify character and settlement behaviors based on active traits and personal devotion.
- Devotion scales the magnitude of character effects:
  * Devout believers experience the full behavioral pull of their faith.
  * Lukewarm adherents experience minimal modification.
"""

from __future__ import annotations
from typing import Mapping
from minemesis.religion.religion_models import CharacterFaith, Religion


def get_religion_aggregate_modifiers(religion: Religion | None) -> dict[str, float]:
    """
    Sums all raw trait modifiers for a religion.
    """
    if not religion:
        return {}

    totals: dict[str, float] = {}
    for trait in religion.traits.values():
        for mod_name, val in trait.modifiers.items():
            totals[mod_name] = totals.get(mod_name, 0.0) + val
    return totals


def get_character_effective_modifiers(
    faith: CharacterFaith | None,
    religion: Religion | None,
) -> dict[str, float]:
    """
    Calculates character-specific behavioral modifiers scaled by individual devotion.
    """
    if not faith or not religion:
        return {}

    base_mods = get_religion_aggregate_modifiers(religion)
    devotion_scale = max(0.1, min(1.0, faith.devotion))

    # Zealots receive an extra 20% intensity boost
    if faith.is_zealot:
        devotion_scale = min(1.2, devotion_scale * 1.2)

    return {k: round(v * devotion_scale, 4) for k, v in base_mods.items()}


def get_character_modifier(
    modifier_name: str,
    faith: CharacterFaith | None,
    religion: Religion | None,
    default: float = 0.0,
) -> float:
    """Returns a specific effective modifier for a character."""
    mods = get_character_effective_modifiers(faith, religion)
    return mods.get(modifier_name, default)


def get_settlement_consumption_multiplier(dominant_religion: Religion | None) -> float:
    """
    Returns a food consumption multiplier for the settlement (e.g. Asceticism/Fasting reduces consumption).
    Returns value centered around 1.0 (e.g. 0.85 for 15% reduction).
    """
    if not dominant_religion:
        return 1.0

    mods = get_religion_aggregate_modifiers(dominant_religion)
    consumption_mod = mods.get("consumption_modifier", 0.0)
    # Clamp effect between 0.70 (30% reduction) and 1.30 (30% increase)
    return round(max(0.70, min(1.30, 1.0 + consumption_mod)), 4)


def get_reconciliation_chance_delta(faith: CharacterFaith | None, religion: Religion | None) -> float:
    """Returns additive delta to reconciliation rolls."""
    return get_character_modifier("reconciliation_modifier", faith, religion, 0.0)


def get_revenge_probability_delta(faith: CharacterFaith | None, religion: Religion | None) -> float:
    """Returns additive delta to revenge probability rolls."""
    return get_character_modifier("revenge_modifier", faith, religion, 0.0)


def get_raid_inclination_delta(faith: CharacterFaith | None, religion: Religion | None) -> float:
    """Returns additive delta to raid inclination rolls."""
    return get_character_modifier("raid_modifier", faith, religion, 0.0)


def get_aid_probability_delta(faith: CharacterFaith | None, religion: Religion | None) -> float:
    """Returns additive delta to famine relief / charity aid rolls."""
    return get_character_modifier("aid_modifier", faith, religion, 0.0)


def get_grudge_persistence_multiplier(faith: CharacterFaith | None, religion: Religion | None) -> float:
    """Returns multiplier for emotional hatred decay (higher = holds grudges longer)."""
    delta = get_character_modifier("grudge_persistence_modifier", faith, religion, 0.0)
    return round(max(0.5, 1.0 + delta), 4)
