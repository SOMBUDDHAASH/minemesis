"""
Standalone Religion Engine Module for Project Minemesis (Milestone R0 & R1: Religion Becomes History).

Exposes clean published interfaces for emergent religion generation, social diffusion,
theological evolution, schisms, sacred geography, myth making, and behavioral effects.
"""

from __future__ import annotations

from minemesis.religion.religion_analytics import (
    ReligiousAnalyticsReport,
    format_religion_family_tree,
    format_religious_analytics_summary,
    generate_religious_analytics,
)
from minemesis.religion.religion_config import ENABLE_RELIGION_ENGINE
from minemesis.religion.religion_engine import ReligionEngine
from minemesis.religion.religion_interpretation import apply_religious_interpretation_filter
from minemesis.religion.religion_models import (
    CharacterFaith,
    HolySite,
    HolySiteType,
    LoreStage,
    Religion,
    ReligionTrait,
    ReligiousFigure,
    ReligiousFigureType,
    ReligiousMyth,
    ReligiousRelationshipType,
    ReligiousRole,
    Saint,
    TraitCategory,
)
from minemesis.religion.religion_tensions import (
    calculate_religious_relationship_modifier,
    calculate_settlement_religious_tension,
    get_religious_relationship,
)
from minemesis.religion.religion_traits import (
    get_all_traits,
    get_trait,
    get_traits_by_category,
    is_trait_set_coherent,
)
from minemesis.religion.religion_virtues import evaluate_action_against_virtues

__all__ = [
    "ENABLE_RELIGION_ENGINE",
    "ReligionEngine",
    "Religion",
    "CharacterFaith",
    "ReligionTrait",
    "TraitCategory",
    "ReligiousRole",
    "ReligiousRelationshipType",
    "ReligiousFigure",
    "ReligiousFigureType",
    "HolySite",
    "HolySiteType",
    "Saint",
    "LoreStage",
    "ReligiousMyth",
    "ReligiousAnalyticsReport",
    "get_all_traits",
    "get_trait",
    "get_traits_by_category",
    "is_trait_set_coherent",
    "apply_religious_interpretation_filter",
    "get_religious_relationship",
    "calculate_religious_relationship_modifier",
    "calculate_settlement_religious_tension",
    "evaluate_action_against_virtues",
    "generate_religious_analytics",
    "format_religious_analytics_summary",
    "format_religion_family_tree",
]
