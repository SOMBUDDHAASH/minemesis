"""
Settlement Catchment Evaluation and Placement for Milestone T0.

Rules:
- Evaluates candidate tiles for settlement viability (fertility, water, defense, diversity).
- Places configured number of settlements (default 10) with minimum spatial spacing.
- Derives each settlement's economic profile (farmland, forest, ore, fish, stone, defensibility)
  from its surrounding 12-tile catchment radius.
- Generates descriptive place names derived from local terrain features.
"""

from __future__ import annotations
import math
from typing import Sequence

from minemesis.core.rng import keyed_choice, keyed_int
from minemesis.models.settlement import Settlement
from minemesis.systems.world_spec import SettlementSite
from minemesis.terrain.terrain_engine import (
    BIOME_BEACH,
    BIOME_DESERT,
    BIOME_FOREST,
    BIOME_GRASSLAND,
    BIOME_HILLS,
    BIOME_MOUNTAIN,
    BIOME_NAMES,
    BIOME_OCEAN,
    BIOME_SNOW,
    BIOME_SWAMP,
    BIOME_TAIGA,
    SEA_LEVEL,
    TerrainGrid,
)


def score_tile_for_settlement(grid: TerrainGrid, x: int, y: int) -> float:
    """
    Evaluates settlement suitability score for a tile based on survival essentials.
    """
    idx = grid.index(x, y)
    elev = grid.elevation[idx]
    if elev <= SEA_LEVEL or grid.biome[idx] in (BIOME_OCEAN, BIOME_SNOW, BIOME_MOUNTAIN):
        return -1000.0  # Uninhabitable

    score = 0.0

    # 1. Fertility (vital for sustenance)
    fert = grid.fertility[idx] / 255.0
    score += fert * 50.0

    # 2. Water Access (freshwater river or coastal port)
    has_river = (grid.river_flow[idx] > 0)
    is_lake = bool(grid.lake_flag[idx])
    is_coast = False

    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nx, ny = x + dx, y + dy
        if grid.in_bounds(nx, ny):
            n_idx = grid.index(nx, ny)
            if grid.elevation[n_idx] <= SEA_LEVEL:
                is_coast = True
                break

    if has_river:
        score += 35.0
    elif is_coast:
        score += 25.0
    elif is_lake:
        score += 20.0
    else:
        score -= 15.0  # Arid inland penalty

    # 3. Defensibility (elevation bonus, but avoid extreme mountain heights)
    if 75 <= elev <= 140:
        score += 20.0
    elif elev > 170:
        score -= 25.0

    # 4. Resource Diversity in immediate radius (5 tiles)
    biomes_seen = set()
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            nx, ny = x + dx, y + dy
            if grid.in_bounds(nx, ny):
                biomes_seen.add(grid.biome[grid.index(nx, ny)])
    score += len(biomes_seen) * 5.0

    return score


def analyze_catchment(
    grid: TerrainGrid,
    site_x: int,
    site_y: int,
    radius: int = 12,
) -> dict[str, float]:
    """
    Aggregates economic endowments within catchment radius of a settlement.
    """
    fert_sum = 0.0
    forest_sum = 0.0
    ore_sum = 0.0
    fish_sum = 0.0
    stone_sum = 0.0
    count = 0
    water_count = 0

    site_idx = grid.index(site_x, site_y)
    site_elev = grid.elevation[site_idx]

    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy <= radius * radius:
                nx, ny = site_x + dx, site_y + dy
                if grid.in_bounds(nx, ny):
                    idx = grid.index(nx, ny)
                    count += 1
                    fert_sum += grid.fertility[idx] / 255.0
                    forest_sum += grid.forest_density[idx] / 255.0
                    ore_sum += grid.ore_richness[idx] / 255.0
                    fish_sum += grid.fish_potential[idx] / 255.0
                    stone_sum += grid.stone[idx] / 255.0
                    if grid.elevation[idx] <= SEA_LEVEL or grid.river_flow[idx] > 0:
                        water_count += 1

    if count == 0:
        count = 1

    avg_fert = fert_sum / count
    avg_forest = forest_sum / count
    avg_ore = ore_sum / count
    avg_fish = fish_sum / count
    avg_stone = stone_sum / count
    water_ratio = water_count / count

    # Compute scaled profile in [0.50, 2.50]
    farmland = round(max(0.50, min(2.50, 0.40 + avg_fert * 2.2)), 2)
    forest = round(max(0.50, min(2.50, 0.40 + avg_forest * 2.2)), 2)
    ore = round(max(0.50, min(2.50, 0.40 + avg_ore * 2.2)), 2)
    fish = round(max(0.50, min(2.50, 0.30 + avg_fish * 2.4)), 2)
    stone = round(max(0.50, min(2.50, 0.40 + avg_stone * 2.1)), 2)
    water_acc = round(max(0.10, min(1.0, water_ratio * 3.0)), 2)

    # Defensibility calculation
    defens = round(max(0.60, min(2.50, 0.50 + (site_elev / 255.0) * 1.8 + (1.0 - water_ratio) * 0.4)), 2)

    return {
        "farmland": farmland,
        "forest": forest,
        "ore_richness": ore,
        "fish_potential": fish,
        "stone": stone,
        "water_access": water_acc,
        "defensibility": defens,
    }


def generate_place_name(
    site_type: str,
    biome: int,
    has_river: bool,
    is_coast: bool,
    seed: int,
    settlement_id: str,
) -> str:
    """
    Generates culturally authentic place name derived from local geographic features.
    """
    prefixes_river = ["River", "Clear", "Brook", "Silver", "Cold", "Swift", "Broad", "Deep", "Otter", "Reed"]
    suffixes_river = ["ford", "bridge", "dale", "mouth", "bank", "wash", "mere", "wick"]

    prefixes_coast = ["Port", "Fair", "Sea", "Bay", "Anchor", "Gull", "Wave", "Harbor", "Cape", "North"]
    suffixes_coast = ["haven", "port", "mouth", "vik", "bay", "cove", "strand", "reach"]

    prefixes_mountain = ["High", "Stone", "Iron", "Crag", "Eagle", "Falcon", "Hawk", "Peak", "Frost", "Cloud"]
    suffixes_mountain = ["peak", "crag", "crest", "ridge", "mount", "horn", "spire", "berg"]

    prefixes_forest = ["Oak", "Pine", "Shadow", "Green", "Timber", "Birch", "Elm", "Thorn", "Moss", "Ash"]
    suffixes_forest = ["wood", "wold", "grove", "forest", "hurst", "shade", "holt", "glade"]

    prefixes_plain = ["Golden", "Sun", "Meadow", "Wind", "Amber", "Fair", "Grass", "Wheat", "Plains", "Broad"]
    suffixes_plain = ["stead", "ton", "field", "vale", "dale", "croft", "bury", "land"]

    if has_river:
        pfx_list, sfx_list = prefixes_river, suffixes_river
    elif is_coast:
        pfx_list, sfx_list = prefixes_coast, suffixes_coast
    elif biome in (BIOME_MOUNTAIN, BIOME_HILLS):
        pfx_list, sfx_list = prefixes_mountain, suffixes_mountain
    elif biome in (BIOME_FOREST, BIOME_TAIGA):
        pfx_list, sfx_list = prefixes_forest, suffixes_forest
    else:
        pfx_list, sfx_list = prefixes_plain, suffixes_plain

    pfx = keyed_choice(seed, "pfx", settlement_id, 0, pfx_list)
    sfx = keyed_choice(seed, "sfx", settlement_id, 0, sfx_list)
    return f"{pfx}{sfx}"


def place_settlements(
    grid: TerrainGrid,
    world_seed: int,
    settlement_count: int = 10,
    min_spacing: int = 32,
) -> list[SettlementSite]:
    """
    Identifies optimal, viable settlement sites across the continental landmass.
    Guarantees configured number of settlements through deterministic spacing relaxation if needed.
    """
    candidates = []

    # Score all valid land tiles
    for y in range(25, grid.height - 25, 2):
        for x in range(25, grid.width - 25, 2):
            score = score_tile_for_settlement(grid, x, y)
            if score > 0:
                candidates.append((score, x, y))

    # Sort descending by suitability score
    candidates.sort(key=lambda item: item[0], reverse=True)

    placed_sites: list[SettlementSite] = []
    current_spacing = min_spacing

    for attempt in range(5):
        placed_coords: list[tuple[int, int]] = []
        placed_sites.clear()

        for score, cx, cy in candidates:
            # Check spacing against already placed settlements
            too_close = False
            for px, py in placed_coords:
                dist = math.sqrt((cx - px) ** 2 + (cy - py) ** 2)
                if dist < current_spacing:
                    too_close = True
                    break

            if not too_close:
                sid = f"set_{len(placed_sites)}"
                profile = analyze_catchment(grid, cx, cy, radius=12)

                idx = grid.index(cx, cy)
                has_river = (grid.river_flow[idx] > 0)
                is_coast = False
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    if grid.in_bounds(cx + dx, cy + dy) and grid.elevation[grid.index(cx + dx, cy + dy)] <= SEA_LEVEL:
                        is_coast = True
                        break

                biome_id = grid.biome[idx]
                biome_name = BIOME_NAMES[biome_id]
                site_name = generate_place_name(
                    site_type=biome_name.lower(),
                    biome=biome_id,
                    has_river=has_river,
                    is_coast=is_coast,
                    seed=world_seed,
                    settlement_id=sid,
                )

                site = SettlementSite(
                    id=sid,
                    name=site_name,
                    x=cx,
                    y=cy,
                    farmland=profile["farmland"],
                    forest=profile["forest"],
                    ore_richness=profile["ore_richness"],
                    defensibility=profile["defensibility"],
                    water_access=profile["water_access"],
                    site_type="river" if has_river else ("coast" if is_coast else "plain"),
                    base_food=int(120 * profile["farmland"]),
                    base_wood=int(100 * profile["forest"]),
                    base_ore=int(50 * profile["ore_richness"]),
                    base_wealth=int(60 + 40 * profile["water_access"]),
                )
                placed_sites.append(site)
                placed_coords.append((cx, cy))

                if len(placed_sites) >= settlement_count:
                    break

        if len(placed_sites) >= settlement_count:
            break

        # Relax spacing by 15% on retry if continent density requires it
        current_spacing = int(current_spacing * 0.85)

    return placed_sites
