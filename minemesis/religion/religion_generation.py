"""
Procedural Religion Generation for the Standalone Religion Engine (Milestone R0).

Core Philosophy:
- Generates emergent, coherent religions by combining traits from the religious trait library.
- Ensures no two worlds produce the exact same theology while maintaining internal ideological coherence.
- Generates unique liturgical names, scriptures, and holy sites.
"""

from __future__ import annotations
from typing import Mapping, Sequence
from minemesis.core.rng import KeyedRNG
from minemesis.religion.religion_models import HolySite, Religion, TraitCategory
from minemesis.religion.religion_traits import (
    get_all_traits,
    get_traits_by_category,
    is_trait_set_coherent,
)


_NAME_TEMPLATES = [
    "Faith of the {adj} {elem}",
    "Children of the {adj} {celestial}",
    "Order of the {virtue} {symbol}",
    "Way of the {adj} {geo}",
    "Covenant of the {adj} {concept}",
    "Circle of the {symbol} and {elem}",
    "Followers of the {adj} {authority}",
]

_ADJECTIVES = [
    "Eternal", "Sacred", "Radiant", "Harmonious", "Unseen", "Silent",
    "Ancient", "Hallowed", "Pure", "Undying", "Celestial", "Golden",
    "Iron", "Living", "Mystic", "Sovereign", "Boundless", "Venerable",
]

_ELEMENTS = [
    "River", "Flame", "Grove", "Mountain", "Stone", "Wind",
    "Earth", "Waters", "Dawn", "Thunder", "Tree of Life", "Sun",
]

_CELESTIALS = [
    "Sun", "Moon", "Stars", "Sky Flame", "Cosmic Wheel", "Heavenly Light",
]

_VIRTUES = [
    "Merciful", "Steadfast", "Righteous", "Ascetic", "Honorable", "Forgiving",
    "Humble", "Valiant", "Wise", "Peaceful",
]

_SYMBOLS = [
    "Pillar", "Root", "Chalice", "Torch", "Spire", "Eye",
    "Crossroads", "Lotus", "Crescent", "Shield", "Crown",
]

_GEOGRAPHY = [
    "Valley", "Peak", "Waters", "Forest", "Cavern", "Highlands", "Shores",
]

_CONCEPTS = [
    "Path", "Truth", "Breath", "Dreaming", "Covenant", "Void", "Presence",
]

_AUTHORITIES = [
    "Ancestors", "Prophets", "Shades", "Watchers", "Elders", "Immortals",
]

_SCRIPTURE_TEMPLATES = [
    "The Book of {title}",
    "The Tablets of the {adj} {elem}",
    "The Verses of {title}",
    "The Chronicles of the {authority}",
    "The Songs of the {adj} {concept}",
]


def generate_religion_name(rng: KeyedRNG) -> str:
    template = rng.choice(_NAME_TEMPLATES)
    return template.format(
        adj=rng.choice(_ADJECTIVES),
        elem=rng.choice(_ELEMENTS),
        celestial=rng.choice(_CELESTIALS),
        virtue=rng.choice(_VIRTUES),
        symbol=rng.choice(_SYMBOLS),
        geo=rng.choice(_GEOGRAPHY),
        concept=rng.choice(_CONCEPTS),
        authority=rng.choice(_AUTHORITIES),
    )


def generate_scripture_name(rng: KeyedRNG, religion_name: str) -> str:
    template = rng.choice(_SCRIPTURE_TEMPLATES)
    return template.format(
        title=religion_name.replace("Faith of the ", "").replace("Children of the ", ""),
        adj=rng.choice(_ADJECTIVES),
        elem=rng.choice(_ELEMENTS),
        authority=rng.choice(_AUTHORITIES),
        concept=rng.choice(_CONCEPTS),
    )


def generate_coherent_traits(rng: KeyedRNG, min_traits: int = 4, max_traits: int = 6) -> dict[str, Any]:
    """
    Selects a coherent set of compatible traits spanning core theological categories.
    """
    target_count = rng.randint(min_traits, max_traits)
    
    # Required core categories
    primary_categories = [
        TraitCategory.COSMOLOGY,
        TraitCategory.VIRTUES,
        TraitCategory.TABOOS,
        TraitCategory.WARFARE_VIEWS,
    ]
    
    # Secondary optional categories
    secondary_categories = [
        TraitCategory.SOCIAL_STRUCTURES,
        TraitCategory.SACRED_GEOGRAPHY,
        TraitCategory.AFTERLIFE_CONCEPTS,
        TraitCategory.FAMILY_BELIEFS,
        TraitCategory.RITUALS,
    ]

    selected_traits = []
    
    # Pick one from each primary category first
    for cat in primary_categories:
        candidates = get_traits_by_category(cat)
        rng.shuffle(candidates)
        for cand in candidates:
            if is_trait_set_coherent(selected_traits + [cand]):
                selected_traits.append(cand)
                break

    # Fill remaining slots from secondary categories
    rng.shuffle(secondary_categories)
    for cat in secondary_categories:
        if len(selected_traits) >= target_count:
            break
        candidates = get_traits_by_category(cat)
        rng.shuffle(candidates)
        for cand in candidates:
            if is_trait_set_coherent(selected_traits + [cand]):
                selected_traits.append(cand)
                break

    return {t.id: t for t in selected_traits}


def generate_world_religions(
    seed: int,
    num_religions: int = 2,
    settlement_ids: Sequence[str] = (),
) -> dict[str, Religion]:
    """
    Deterministically generates initial religions for a newly generated world.
    """
    rng = KeyedRNG(seed + 9999, stream="religion_generation")
    religions: dict[str, Religion] = {}

    settlement_list = list(settlement_ids) if settlement_ids else ["set_oakhaven", "set_riverbend", "set_ironpeak"]

    for i in range(1, num_religions + 1):
        rel_id = f"rel_{i}"
        name = generate_religion_name(rng)
        traits = generate_coherent_traits(rng)
        scripture = generate_scripture_name(rng, name)

        # Create primary holy site
        home_settlement = settlement_list[(i - 1) % len(settlement_list)]
        holy_site_types = ["Sacred River Temple", "High Mountain Altar", "Ancient Forest Grove", "Hallowed Megalith"]
        holy_site = HolySite(
            id=f"site_{i}",
            name=f"{name.split(' of the ')[-1] if ' of the ' in name else name} Sanctuary",
            settlement_id=home_settlement,
            site_type=rng.choice(holy_site_types),
            significance="Original founding sanctuary and locus of divine communion.",
            founded_tick=0,
        )

        religion = Religion(
            id=rel_id,
            name=name,
            parent_religion_id=None,
            founded_tick=0,
            founded_year=1,
            traits=traits,
            adherents=set(),
            dominant_settlements=set([home_settlement]),
            schisms=[],
            holy_sites=[holy_site],
            saints=[],
            scripture_name=scripture,
            reformation_level=0,
        )
        religions[rel_id] = religion

    return religions
