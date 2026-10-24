"""
Sacred Geography & Pilgrimage Infrastructure System (Milestone R1.6).

Connects emergent religions to physical and spiritual geography:
- Sacred Mountains, Sacred Forests, Sacred Rivers, Sacred Trees, Temples, Shrines.
- Mystics, Pilgrims, and Elders discover and consecrate sacred spaces.
- Pilgrimages along sacred routes stimulate trade connections and settlement prosperity:
  Holy Site Discovered -> Pilgrimage Route Created -> Trade Route Grows -> Settlement Prosperity
"""

from __future__ import annotations
from typing import Any, Mapping, Optional, Sequence
from minemesis.core.rng import KeyedRNG
from minemesis.models.character import Character
from minemesis.models.settlement import Settlement
from minemesis.religion.religion_models import (
    HolySite,
    HolySiteType,
    Religion,
    ReligiousFigure,
    ReligiousRole,
    SiteTier,
)


SITE_NAME_TEMPLATES = {
    HolySiteType.SACRED_MOUNTAIN: ["Mount {prefix}", "The {prefix} Peak", "Crest of {prefix}"],
    HolySiteType.SACRED_FOREST: ["The {prefix} Grove", "Forest of {prefix}", "The Whispering Glade of {prefix}"],
    HolySiteType.SACRED_RIVER: ["The {prefix} Waters", "River of {prefix}", "Sacred Stream of {prefix}"],
    HolySiteType.SACRED_TREE: ["The Great {prefix} Tree", "World-Root of {prefix}", "The Elder Arbor of {prefix}"],
    HolySiteType.TEMPLE: ["The Grand Temple of {prefix}", "House of {prefix}", "High Sanctum of {prefix}"],
    HolySiteType.SHRINE: ["Shrine of the {prefix}", "Waystone of {prefix}", "Altar of {prefix}"],
}

PREFIXES = ["Dawn", "Ancestors", "Eternal Fire", "Serpent", "Pure Spirit", "Silence", "Heaven", "Sacred Spring", "Celestial"]


def generate_holy_site(
    religion: Religion,
    settlement_id: str,
    site_type: HolySiteType,
    tick: int,
    site_counter: list[int],
    rng: KeyedRNG,
    discoverer: Optional[Character] = None,
) -> tuple[HolySite, dict[str, Any]]:
    """
    Creates a new Holy Site attached to a settlement location.
    """
    s_idx = site_counter[0]
    site_counter[0] += 1
    site_id = f"holy_site_{s_idx}"

    templates = SITE_NAME_TEMPLATES.get(site_type, ["Sacred Ground of {prefix}"])
    template = rng.choice(templates)
    prefix = rng.choice(PREFIXES)
    site_name = template.format(prefix=prefix)

    desc = f"Consecrated by {religion.name} at tick {tick}"
    if discoverer:
        desc += f", revealed through the visions of {discoverer.name}"

    site = HolySite(
        id=site_id,
        name=site_name,
        settlement_id=settlement_id,
        site_type=site_type.value,
        significance=desc,
        founded_tick=tick,
    )
    religion.holy_sites.append(site)

    event_payload = {
        "site_id": site.id,
        "site_name": site.name,
        "site_type": site.site_type,
        "settlement_id": settlement_id,
        "religion_id": religion.id,
        "religion_name": religion.name,
        "discoverer_id": discoverer.id if discoverer else None,
        "discoverer_name": discoverer.name if discoverer else None,
        "tick": tick,
    }

    return site, event_payload


def evaluate_holy_site_discovery_or_construction(
    religion: Religion,
    settlements: Mapping[str, Settlement],
    living_characters: Sequence[Character],
    tick: int,
    rng: KeyedRNG,
    site_counter: list[int],
) -> Optional[tuple[HolySite, dict[str, Any]]]:
    """
    Checks if a mystic discovers a natural site or if a devout settlement constructs a Temple/Shrine.
    """
    # Prefer settlements where religion is dominant or present
    valid_settlements = sorted(list(settlements.keys()))
    if not valid_settlements:
        return None

    target_settlement_id = rng.choice(valid_settlements)

    # Check for living mystic or oracle
    mystics = [
        c for c in living_characters
        if c.alive and c.settlement_id == target_settlement_id
    ]
    discoverer = rng.choice(mystics) if mystics else None

    # Roll site type
    site_types = [
        HolySiteType.SACRED_MOUNTAIN,
        HolySiteType.SACRED_FOREST,
        HolySiteType.SACRED_RIVER,
        HolySiteType.SACRED_TREE,
        HolySiteType.TEMPLE,
        HolySiteType.SHRINE,
    ]
    chosen_type = rng.choice(site_types)

    return generate_holy_site(
        religion=religion,
        settlement_id=target_settlement_id,
        site_type=chosen_type,
        tick=tick,
        site_counter=site_counter,
        rng=rng,
        discoverer=discoverer,
    )


def process_pilgrimage_economic_benefit(
    pilgrim_home_id: str,
    holy_site_settlement_id: str,
    active_trade_routes: Any,
    rng: KeyedRNG,
) -> Optional[dict[str, Any]]:
    """
    Simulates economic prosperity boost and commercial route seeding from pilgrims.
    """
    if pilgrim_home_id == holy_site_settlement_id:
        return None

    # Route key check
    route_key = tuple(sorted([pilgrim_home_id, holy_site_settlement_id]))
    if active_trade_routes and route_key in active_trade_routes:
        # Boost existing route
        return {
            "origin": pilgrim_home_id,
            "destination": holy_site_settlement_id,
            "impact": "Trade route traffic stimulated by religious pilgrims.",
            "prosperity_bonus": 0.15,
        }

    return {
        "origin": pilgrim_home_id,
        "destination": holy_site_settlement_id,
        "impact": "Pilgrimage route established between settlements.",
        "prosperity_bonus": 0.10,
    }


def check_and_elevate_holy_site(
    site: HolySite,
    religion: Religion,
    tick: int,
    rng: Optional[KeyedRNG] = None,
) -> Optional[dict[str, Any]]:
    """
    R2.7: Sacred Geography Evolution.
    Evolves holy sites as pilgrimage traffic grows:
    NaturalSanctuary -> LocalShrine -> Temple -> RegionalPilgrimageSite -> HolyCapital.
    """
    tier_transitions = {
        SiteTier.NATURAL_SANCTUARY: (5, SiteTier.LOCAL_SHRINE),
        SiteTier.LOCAL_SHRINE: (15, SiteTier.TEMPLE),
        SiteTier.TEMPLE: (30, SiteTier.REGIONAL_PILGRIMAGE_SITE),
        SiteTier.REGIONAL_PILGRIMAGE_SITE: (60, SiteTier.HOLY_CAPITAL),
    }

    if site.tier in tier_transitions:
        threshold, next_tier = tier_transitions[site.tier]
        if site.pilgrims_visited >= threshold:
            old_tier = site.tier
            site.tier = next_tier
            return {
                "site_id": site.id,
                "site_name": site.name,
                "religion_id": religion.id,
                "religion_name": religion.name,
                "old_tier": old_tier.value,
                "new_tier": next_tier.value,
                "pilgrims_visited": site.pilgrims_visited,
                "settlement_id": site.settlement_id,
                "tick": tick,
            }

    return None
