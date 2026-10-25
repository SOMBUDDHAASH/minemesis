"""
Deterministic World & Cast Generation for Minemesis.

Milestone 0.5.3: Randomized Worlds and Casts (Seed Split).

Replaces hard-coded settlements and fixed character rosters with:
- WorldSpec generated exclusively from WorldSeed via WorldProvider.
- Cast generated exclusively from ChronicleSeed + WorldSpec via CastGenerator.
- Designates an initial chief per settlement.
- Zero hard-coded rosters or settlement names in code.
"""

from __future__ import annotations
from typing import Mapping, Optional

from minemesis.core.seed import SeedPair
from minemesis.models.character import Character
from minemesis.models.settlement import Settlement
from minemesis.systems.world_spec import WorldSpec, SettlementSite, WorldProvider
from minemesis.systems.world_gen_v0 import V0WorldGenerator
from minemesis.systems.cast_gen import (
    CastGenerator,
    GIVEN_NAMES_MALE as FIRST_NAMES_MALE,
    GIVEN_NAMES_FEMALE as FIRST_NAMES_FEMALE,
)


def generate_world(
    seed_or_pair: SeedPair | int = 42,
    world_provider: Optional[WorldProvider] = None,
    name_salt: int = 0,
) -> tuple[dict[str, Settlement], dict[str, Character], WorldSpec]:
    """
    Generates a complete world (settlements, characters, and WorldSpec)
    from a SeedPair or legacy integer seed.
    Names are isolated in their own domain and can be re-salted independently via name_salt.
    """
    if isinstance(seed_or_pair, int):
        pair = SeedPair.from_legacy(seed_or_pair)
    elif isinstance(seed_or_pair, SeedPair):
        pair = seed_or_pair
    else:
        raise TypeError(f"Expected SeedPair or int, got {type(seed_or_pair)}")

    # 1. World Generation (from world_seed only)
    provider = world_provider or V0WorldGenerator()
    world_spec = provider.generate(pair.world, name_salt=name_salt)

    # 2. Construct Settlements
    settlements: dict[str, Settlement] = {}
    for site in world_spec.settlements:
        settlement = Settlement(
            id=site.id,
            name=site.name,
            x=site.x,
            y=site.y,
            food=site.base_food,
            wood=site.base_wood,
            ore=site.base_ore,
            wealth=site.base_wealth,
            farmland=site.farmland,
            forest=site.forest,
            ore_richness=site.ore_richness,
            defensibility=site.defensibility,
            water_access=site.water_access,
            stability=1.0,
        )
        settlements[site.id] = settlement

    # 3. Cast Generation (from history_seed + world_spec)
    cast_gen = CastGenerator(history_seed=pair.history, world_spec=world_spec, name_salt=name_salt)
    characters = cast_gen.generate_cast()

    # 4. Associate characters with settlements and assign initial chiefs
    for site in world_spec.settlements:
        settlement = settlements[site.id]
        member_ids = [c_id for c_id, c in characters.items() if c.settlement_id == site.id]
        settlement.member_ids = member_ids

        # Select initial chief: prefer respected elder or senior prime adult
        adult_members = [
            characters[c_id] for c_id in member_ids
            if characters[c_id].age_years >= 25
        ]
        if adult_members:
            # Sort deterministically: elders first, then highest forgiveness / lowest suspicion
            adult_members.sort(key=lambda c: (-c.age_years, c.suspicion, c.id))
            chief = adult_members[0]
            settlement.leader_id = chief.id
        elif member_ids:
            settlement.leader_id = member_ids[0]

    return settlements, characters, world_spec
