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
from minemesis.religion.religion_culture import (
    absorb_folk_tradition_into_religion,
    celebrate_local_customs,
    get_cultural_behavioral_pressure,
    initialize_settlement_culture,
    process_cultural_mixing,
)
from minemesis.religion.religion_engine import ReligionEngine
from minemesis.religion.religion_figures import determine_hero_archetype
from minemesis.religion.religion_geography import check_and_elevate_holy_site
from minemesis.religion.religion_interpretation import apply_religious_interpretation_filter
from minemesis.religion.religion_models import (
    CharacterFaith,
    CulturalProfile,
    CustomType,
    FolkTradition,
    FolkTraditionType,
    HeroArchetype,
    HolySite,
    HolySiteType,
    LocalCustom,
    LoreStage,
    RegionalDoctrineProfile,
    Religion,
    ReligionTrait,
    ReligiousFigure,
    ReligiousFigureType,
    ReligiousIdentityStrength,
    ReligiousMyth,
    ReligiousRelationshipType,
    ReligiousRole,
    Saint,
    SiteTier,
    TraitCategory,
)
from minemesis.religion.religion_myths import exchange_myths_across_trade_routes
from minemesis.religion.religion_syncretism import (
    calculate_jaccard_similarity,
    evaluate_doctrinal_borrowing,
    evaluate_syncretic_fusion,
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
    "SiteTier",
    "ReligiousIdentityStrength",
    "HeroArchetype",
    "FolkTraditionType",
    "CustomType",
    "FolkTradition",
    "LocalCustom",
    "RegionalDoctrineProfile",
    "CulturalProfile",
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
    "calculate_jaccard_similarity",
    "evaluate_doctrinal_borrowing",
    "evaluate_syncretic_fusion",
    "initialize_settlement_culture",
    "absorb_folk_tradition_into_religion",
    "celebrate_local_customs",
    "process_cultural_mixing",
    "get_cultural_behavioral_pressure",
    "check_and_elevate_holy_site",
    "determine_hero_archetype",
    "exchange_myths_across_trade_routes",
]
