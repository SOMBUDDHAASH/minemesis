"""
Standalone Religion Engine Module for Project Minemesis (Milestone R0).

Exposes clean published interfaces for emergent religion generation, social diffusion,
theological evolution, schisms, and behavioral effects.
"""

from __future__ import annotations

from minemesis.religion.religion_config import ENABLE_RELIGION_ENGINE
from minemesis.religion.religion_engine import ReligionEngine
from minemesis.religion.religion_models import (
    CharacterFaith,
    HolySite,
    Religion,
    ReligionTrait,
    ReligiousRole,
    Saint,
    TraitCategory,
)
from minemesis.religion.religion_traits import (
    get_all_traits,
    get_trait,
    get_traits_by_category,
    is_trait_set_coherent,
)

__all__ = [
    "ENABLE_RELIGION_ENGINE",
    "ReligionEngine",
    "Religion",
    "CharacterFaith",
    "ReligionTrait",
    "TraitCategory",
    "ReligiousRole",
    "HolySite",
    "Saint",
    "get_all_traits",
    "get_trait",
    "get_traits_by_category",
    "is_trait_set_coherent",
]
