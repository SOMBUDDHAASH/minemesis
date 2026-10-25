"""
Religion Shapes Culture and Civilization System (Milestone R2 & R1.5).

Operationalizes:
1. R1.5.2 Regional Doctrine Profiles (Regional Drift).
2. R1.5.3 Folk Tradition Layer (Village Spirits, Sacred Trees, River Guardians, Ancestor Heroes).
3. R2.1 & R2.3 Cultural Profiles (Culture-Based Villages with multi-dimensional social values).
4. R2.4 Local Traditions & Seasonal Customs (Annual festivals and ceremonies).
5. R2.8 Cultural Pressure System (Social values shaping decisions).
6. R2.9 Cultural Mixing & Fluidity across trade routes and migrations.
"""

from __future__ import annotations
from typing import Any, Mapping, Optional, Sequence
from minemesis.core.rng import KeyedRNG
from minemesis.models.character import Character
from minemesis.models.settlement import Settlement
from minemesis.religion.religion_models import (
    CulturalProfile,
    CustomType,
    FolkTradition,
    FolkTraditionType,
    LocalCustom,
    RegionalDoctrineProfile,
    Religion,
)


DEFAULT_SETTLEMENT_FOLK_TRADITIONS = {
    "set_oakhaven": [
        ("The Elder Oak Spirit", FolkTraditionType.SACRED_TREE, "Ancient spirit guardian dwelling within the roots of the founding grove."),
        ("Ancestor Veneration of the Hearth", FolkTraditionType.ANCESTOR_HERO, "Traditional remembrance of the first settlers who built the hearth."),
    ],
    "set_riverbend": [
        ("The Whispering Current Guardian", FolkTraditionType.RIVER_GUARDIAN, "Protective river spirit that calms the spring floodwaters."),
        ("Water Sprite of the Shallows", FolkTraditionType.VILLAGE_SPIRIT, "Playful local spirit believed to guide fish to the nets."),
    ],
    "set_ironpeak": [
        ("The Mountain Sentinel of Granite", FolkTraditionType.MOUNTAIN_LEGEND, "Mythic giant spirit petrified into the high northern peak."),
        ("Spirits of the Deep Ore", FolkTraditionType.VILLAGE_SPIRIT, "Underground voices honoring courageous miners and warriors."),
    ],
}

DEFAULT_LOCAL_CUSTOMS = [
    ("Spring River Immersion", CustomType.RIVER_IMMERSION, 3, "Annual ritual ablutions at the thaw of the spring waters."),
    ("Midsummer Harvest Festival", CustomType.HARVEST_FESTIVAL, 6, "Communal feast of gratitude for earth's abundance and grain."),
    ("Autumn Ancestor Vigil", CustomType.ANCESTOR_CEREMONY, 9, "Evening vigil lighting torches to honor the spirits of deceased forebears."),
    ("Winter Hero Remembrance Day", CustomType.HERO_REMEMBRANCE, 12, "Solemn celebration recounting tales of fallen champions and founders."),
]


def initialize_settlement_culture(
    settlement_id: str,
    settlement_name: str,
    folk_counter: list[int],
    custom_counter: list[int],
    rng: KeyedRNG,
    settlement: Any = None,
) -> CulturalProfile:
    """Initializes a rich cultural profile derived from settlement economic endowment and rng."""
    ore = getattr(settlement, "ore_richness", 1.0) if settlement else 1.0
    farm = getattr(settlement, "farmland", 1.0) if settlement else 1.0
    defn = getattr(settlement, "defensibility", 1.0) if settlement else 1.0
    water = getattr(settlement, "water_access", 0.5) if settlement else 0.5
    forest = getattr(settlement, "forest", 1.0) if settlement else 1.0

    # Derive social values from economic & geographic profile
    if ore >= 1.25 or defn >= 1.20 or "iron" in settlement_id.lower() or "peak" in settlement_id.lower():
        social_values = {
            "family_loyalty": round(rng.uniform(0.70, 0.85), 2),
            "honor": round(rng.uniform(0.80, 0.95), 2),
            "discipline": round(rng.uniform(0.75, 0.90), 2),
            "compassion": round(rng.uniform(0.35, 0.55), 2),
            "warrior_tradition": round(rng.uniform(0.80, 0.95), 2),
            "collectivism": round(rng.uniform(0.60, 0.80), 2),
        }
    elif water >= 0.60 or "river" in settlement_id.lower() or "bend" in settlement_id.lower():
        social_values = {
            "family_loyalty": round(rng.uniform(0.65, 0.80), 2),
            "honor": round(rng.uniform(0.50, 0.70), 2),
            "discipline": round(rng.uniform(0.50, 0.70), 2),
            "compassion": round(rng.uniform(0.70, 0.90), 2),
            "pilgrimage_sanctity": round(rng.uniform(0.75, 0.95), 2),
            "collectivism": round(rng.uniform(0.70, 0.85), 2),
        }
    else:  # Agrarian / Woodland / Plain
        social_values = {
            "family_loyalty": round(rng.uniform(0.80, 0.95), 2),
            "honor": round(rng.uniform(0.60, 0.75), 2),
            "discipline": round(rng.uniform(0.60, 0.75), 2),
            "compassion": round(rng.uniform(0.65, 0.80), 2),
            "ancestor_veneration": round(rng.uniform(0.80, 0.95), 2),
            "collectivism": round(rng.uniform(0.75, 0.90), 2),
        }

    # Folk traditions dynamically generated from profile
    folk_list: list[FolkTradition] = []
    if ore >= 1.25 or defn >= 1.20:
        trad_templates = [
            (f"The Mountain Sentinel of {settlement_name}", FolkTraditionType.MOUNTAIN_LEGEND, f"Mythic guardian spirit petrified into the heights of {settlement_name}."),
            (f"Spirits of the Deep Ore", FolkTraditionType.VILLAGE_SPIRIT, "Underground voices honoring courageous miners and warriors."),
        ]
    elif water >= 0.60:
        trad_templates = [
            (f"The Current Guardian of {settlement_name}", FolkTraditionType.RIVER_GUARDIAN, f"Protective river spirit watching over the waters of {settlement_name}."),
            (f"Sprite of the Shallows", FolkTraditionType.VILLAGE_SPIRIT, "Playful local spirit believed to guide fish to the nets."),
        ]
    elif forest >= 1.20:
        trad_templates = [
            (f"The Sacred Tree Spirit of {settlement_name}", FolkTraditionType.SACRED_TREE, f"Ancient spirit guardian dwelling within the woods of {settlement_name}."),
            (f"Ancestor Veneration of the Hearth", FolkTraditionType.ANCESTOR_HERO, "Traditional remembrance of the first founders who cleared the hearth."),
        ]
    else:
        trad_templates = [
            (f"Guardian Spirit of {settlement_name}", FolkTraditionType.VILLAGE_SPIRIT, f"Generous village spirit watching over the homes of {settlement_name}."),
            (f"Ancestor Veneration of the Hearth", FolkTraditionType.ANCESTOR_HERO, "Traditional remembrance of the first forebears who built the village."),
        ]
    for name, f_type, desc in trad_templates:
        f_idx = folk_counter[0]
        folk_counter[0] += 1
        folk_list.append(FolkTradition(
            id=f"folk_{f_idx}",
            name=name,
            tradition_type=f_type,
            settlement_id=settlement_id,
            significance=desc,
        ))

    # Local customs
    custom_list: list[LocalCustom] = []
    for c_name, c_type, month, c_desc in DEFAULT_LOCAL_CUSTOMS:
        c_idx = custom_counter[0]
        custom_counter[0] += 1
        custom_list.append(LocalCustom(
            id=f"custom_{c_idx}",
            name=f"{settlement_name} {c_name}",
            custom_type=c_type,
            settlement_id=settlement_id,
            season_month=month,
            description=c_desc,
        ))

    return CulturalProfile(
        settlement_id=settlement_id,
        religious_composition={},
        social_values=social_values,
        historical_biases={},
        folk_traditions=folk_list,
        local_customs=custom_list,
    )


def absorb_folk_tradition_into_religion(
    religion: Religion,
    folk_tradition: FolkTradition,
    tick: int,
) -> dict[str, Any]:
    """
    R1.5.3: An organized religion absorbs an ancient local folk tradition / spirit guardian.
    """
    folk_tradition.is_absorbed_into_religion = True
    folk_tradition.absorbed_by_religion_id = religion.id
    if folk_tradition.id not in religion.absorbed_folk_traditions:
        religion.absorbed_folk_traditions.append(folk_tradition.id)

    return {
        "religion_id": religion.id,
        "religion_name": religion.name,
        "folk_tradition_id": folk_tradition.id,
        "folk_tradition_name": folk_tradition.name,
        "tradition_type": folk_tradition.tradition_type.value,
        "settlement_id": folk_tradition.settlement_id,
        "tick": tick,
    }


def celebrate_local_customs(
    settlement_id: str,
    culture: CulturalProfile,
    current_tick: int,
) -> list[dict[str, Any]]:
    """
    R2.4: Celebrates annual village customs.
    Directive 1: Routine annual celebrations update cultural state without logging events.
    Events are emitted ONLY on:
    1. First celebration of a custom (celebration_count == 0)
    2. Celebrations after an extended period of dormancy (>= 60 ticks / 5 years)
    """
    current_month = (current_tick % 12) + 1
    events: list[dict[str, Any]] = []

    for custom in culture.local_customs:
        if custom.season_month == current_month:
            is_first = (custom.celebration_count == 0)
            is_resumed = (
                custom.last_celebrated_tick is not None
                and (current_tick - custom.last_celebrated_tick) >= 60
            )

            custom.celebration_count += 1
            custom.last_celebrated_tick = current_tick

            # Only log event if first celebration or resumed after long dormancy
            if is_first or is_resumed:
                events.append({
                    "settlement_id": settlement_id,
                    "custom_id": custom.id,
                    "custom_name": custom.name,
                    "custom_type": custom.custom_type.value,
                    "description": custom.description,
                    "month": current_month,
                    "tick": current_tick,
                    "is_first_celebration": is_first,
                    "is_resumed": is_resumed,
                })

    return events


def process_cultural_mixing(
    settlements: Mapping[str, Settlement],
    active_trade_routes: Any,
    cultural_profiles: dict[str, CulturalProfile],
    mixing_rate: float = 0.05,
) -> list[dict[str, Any]]:
    """
    R2.9: Fluid cultural exchange across active trade corridors.
    Adjacent trading settlements gradually assimilate aspects of each other's social values.
    """
    exchanges: list[dict[str, Any]] = []
    if not active_trade_routes:
        return exchanges

    for (s_a, s_b), route in active_trade_routes.items():
        is_route_active = getattr(route, "active", getattr(route, "is_active", True))
        if is_route_active and s_a in cultural_profiles and s_b in cultural_profiles:
            cp_a = cultural_profiles[s_a]
            cp_b = cultural_profiles[s_b]

            # Exchange common social values
            for val_key in set(cp_a.social_values.keys()).intersection(cp_b.social_values.keys()):
                diff = cp_b.social_values[val_key] - cp_a.social_values[val_key]
                if abs(diff) > 0.02:
                    shift = round(diff * mixing_rate, 4)
                    cp_a.social_values[val_key] = round(cp_a.social_values[val_key] + shift, 3)
                    cp_b.social_values[val_key] = round(cp_b.social_values[val_key] - shift, 3)

            exchanges.append({
                "origin": s_a,
                "partner": s_b,
                "status": "Cultural values harmonized through active commerce.",
            })

    return exchanges


def get_cultural_behavioral_pressure(
    settlement_id: str,
    cultural_profiles: Mapping[str, CulturalProfile],
) -> dict[str, float]:
    """
    R2.8: Returns behavioral decision modifiers exerted by local settlement culture.
    """
    cp = cultural_profiles.get(settlement_id)
    if not cp:
        return {}

    vals = cp.social_values
    return {
        "grudge_retention_multiplier": 1.0 + (vals.get("family_loyalty", 0.5) * 0.4),
        "forgiveness_propensity_multiplier": 1.0 + (vals.get("compassion", 0.5) * 0.5),
        "raid_affinity_multiplier": 1.0 + (vals.get("warrior_tradition", 0.5) * 0.6),
        "aid_generosity_multiplier": 1.0 + (vals.get("compassion", 0.5) * 0.4),
    }
