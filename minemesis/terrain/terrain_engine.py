"""
Terrain and Geography Engine for Milestone T0.

Generates a complete 300x300 tile continent with platform-independent integer hash noise:
- Elevation (0-255, sea level = 64)
- Temperature (0-255)
- Moisture (0-255)
- 10 Discrete Biomes (Ocean, Beach, Grassland, Forest, Taiga, Snow, Desert, Swamp, Hills, Mountain)
- Downhill River Routing and Lake Accumulation
- Economic Endowments (Fertility, Forest Density, Ore Richness, Fish, Stone)
- Travel Cost Surface for A* Road Finding
- Encoded as contiguous bytearrays for minimal RAM footprint (~1.2 MB total for 300x300).
"""

from __future__ import annotations
import math
from typing import Any, Sequence

from minemesis.terrain.noise import fbm_noise_2d, int_hash_2d


BIOME_OCEAN = 0
BIOME_BEACH = 1
BIOME_GRASSLAND = 2
BIOME_FOREST = 3
BIOME_TAIGA = 4
BIOME_SNOW = 5
BIOME_DESERT = 6
BIOME_SWAMP = 7
BIOME_HILLS = 8
BIOME_MOUNTAIN = 9

BIOME_NAMES = [
    "Ocean", "Beach", "Grassland", "Forest", "Taiga",
    "Snow", "Desert", "Swamp", "Hills", "Mountain"
]

SEA_LEVEL = 64


class TerrainGrid:
    """
    Compact RAM-efficient container for 300x300 world geography.
    Uses contiguous bytearrays (1 byte per tile) instead of individual Python objects.
    """

    def __init__(self, width: int = 300, height: int = 300) -> None:
        self.width = width
        self.height = height
        self.size = width * height

        self.elevation = bytearray(self.size)
        self.temperature = bytearray(self.size)
        self.moisture = bytearray(self.size)
        self.biome = bytearray(self.size)
        self.river_flow = bytearray(self.size)
        self.river_width = bytearray(self.size)
        self.lake_flag = bytearray(self.size)

        self.fertility = bytearray(self.size)
        self.forest_density = bytearray(self.size)
        self.ore_richness = bytearray(self.size)
        self.fish_potential = bytearray(self.size)
        self.stone = bytearray(self.size)
        self.travel_cost = bytearray(self.size)  # 1 to 255

    def index(self, x: int, y: int) -> int:
        return y * self.width + x

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height


def generate_terrain(
    world_seed: int,
    width: int = 300,
    height: int = 300,
) -> TerrainGrid:
    """
    Generates a full 300x300 continental terrain grid from the world_seed.
    """
    grid = TerrainGrid(width=width, height=height)

    # 1. Continent Elevation with Ocean Border Falloff
    center_x = width / 2.0
    center_y = height / 2.0
    max_dist = math.sqrt(center_x * center_x + center_y * center_y)

    for y in range(height):
        row_idx = y * width
        for x in range(width):
            idx = row_idx + x

            # Distance from ocean borders (first 18 tiles border is ocean)
            dist_border = min(x, y, width - 1 - x, height - 1 - y)
            border_factor = min(1.0, dist_border / 18.0)

            # Center island falloff (finite continent)
            dx = (x - center_x) / center_x
            dy = (y - center_y) / center_y
            rad_dist = math.sqrt(dx * dx + dy * dy)
            continent_shape = max(0.0, 1.0 - rad_dist * 0.75)

            # Multi-octave elevation noise
            nx = x / 75.0
            ny = y / 75.0
            raw_elev = fbm_noise_2d(world_seed, nx, ny, octaves=5, persistence=0.52, salt=11)
            raw_mountains = fbm_noise_2d(world_seed, nx * 2.2, ny * 2.2, octaves=3, persistence=0.5, salt=23)

            # Combine continent falloff with mountain peaks
            elev_val = ((raw_elev * 0.65 + raw_mountains * 0.35) * 1.18) * continent_shape * border_factor
            
            # Map to 0-255 scale
            elev_byte = int(elev_val * 255)
            grid.elevation[idx] = max(0, min(255, elev_byte))

            # Temperature: north is colder + elevation lapse rate (altitude = colder)
            temp_noise = fbm_noise_2d(world_seed, x / 110.0, y / 110.0, octaves=3, salt=41)
            base_temp = 0.85 - (y / height) * 0.50  # South is warmer
            lapse_rate = (elev_byte / 255.0) * 0.45
            temp_val = max(0.0, min(1.0, base_temp + (temp_noise - 0.5) * 0.25 - lapse_rate))
            grid.temperature[idx] = int(temp_val * 255)

            # Moisture: rainfall noise + proximity to water
            moist_noise = fbm_noise_2d(world_seed, x / 95.0, y / 95.0, octaves=4, salt=57)
            moist_val = max(0.0, min(1.0, moist_noise * 0.80 + 0.10))
            grid.moisture[idx] = int(moist_val * 255)

    # 2. Downhill River Carving
    # Seed river heads in mountain highlands (elevation > 140)
    river_heads = []
    for y in range(15, height - 15, 6):
        for x in range(15, width - 15, 6):
            idx = grid.index(x, y)
            elev = grid.elevation[idx]
            moist = grid.moisture[idx]
            if elev > 135 and moist > 110:
                h = int_hash_2d(world_seed, x, y, salt=71)
                if (h % 100) < 30:
                    river_heads.append((x, y))

    for rx, ry in river_heads:
        curr_x, curr_y = rx, ry
        flow = 6
        visited = set()

        for _ in range(350):  # Maximum river path steps
            if (curr_x, curr_y) in visited:
                break
            visited.add((curr_x, curr_y))

            c_idx = grid.index(curr_x, curr_y)
            curr_elev = grid.elevation[c_idx]

            # Reached ocean
            if curr_elev <= SEA_LEVEL:
                grid.river_flow[c_idx] = min(255, grid.river_flow[c_idx] + flow)
                break

            grid.river_flow[c_idx] = min(255, grid.river_flow[c_idx] + flow)
            flow += 1
            w = 1 if flow < 20 else (2 if flow < 50 else 3)
            grid.river_width[c_idx] = max(grid.river_width[c_idx], w)

            # Find lowest neighbor (steepest downhill descent)
            best_nb = None
            min_e = curr_elev

            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
                nx, ny = curr_x + dx, curr_y + dy
                if grid.in_bounds(nx, ny) and (nx, ny) not in visited:
                    n_e = grid.elevation[grid.index(nx, ny)]
                    if n_e < min_e:
                        min_e = n_e
                        best_nb = (nx, ny)

            if best_nb is None:
                # Local depression: forms a lake
                grid.lake_flag[c_idx] = 1
                grid.elevation[c_idx] = SEA_LEVEL
                break

            curr_x, curr_y = best_nb

    # 3. Biomes and Economic Endowments
    for y in range(height):
        row_idx = y * width
        for x in range(width):
            idx = row_idx + x
            elev = grid.elevation[idx]
            temp = grid.temperature[idx] / 255.0
            moist = grid.moisture[idx] / 255.0
            has_river = (grid.river_flow[idx] > 0)
            is_lake = bool(grid.lake_flag[idx])

            # Classify Biome
            if elev <= SEA_LEVEL or is_lake:
                b = BIOME_OCEAN
            elif elev <= SEA_LEVEL + 4:
                b = BIOME_BEACH
            elif elev > 175:
                b = BIOME_SNOW if (temp < 0.35 or elev > 200) else BIOME_MOUNTAIN
            elif elev > 125:
                b = BIOME_HILLS if temp > 0.30 else BIOME_TAIGA
            else:
                # Lowlands classification
                if temp < 0.28:
                    b = BIOME_SNOW if moist < 0.40 else BIOME_TAIGA
                elif temp > 0.65 and moist < 0.28:
                    b = BIOME_DESERT
                elif moist > 0.68 and elev <= SEA_LEVEL + 10:
                    b = BIOME_SWAMP
                elif moist > 0.45:
                    b = BIOME_FOREST
                else:
                    b = BIOME_GRASSLAND

            grid.biome[idx] = b

            # Compute Endowments
            # Fertility: high in grasslands, river valleys, forests
            if b in (BIOME_OCEAN, BIOME_SNOW, BIOME_DESERT):
                fert = 10 if b == BIOME_DESERT else 0
            elif b == BIOME_GRASSLAND:
                fert = 180 + (25 if has_river else 0)
            elif b == BIOME_FOREST:
                fert = 150 + (20 if has_river else 0)
            elif b == BIOME_SWAMP:
                fert = 130
            elif b == BIOME_HILLS:
                fert = 80
            else:
                fert = 40
            grid.fertility[idx] = min(255, fert)

            # Forest Density
            if b == BIOME_FOREST:
                f_dens = 210
            elif b == BIOME_TAIGA:
                f_dens = 190
            elif b == BIOME_SWAMP:
                f_dens = 120
            elif b == BIOME_GRASSLAND:
                f_dens = 40
            elif b == BIOME_HILLS:
                f_dens = 70
            else:
                f_dens = 0
            grid.forest_density[idx] = min(255, f_dens)

            # Ore Richness: highest in mountains and hills
            if b == BIOME_MOUNTAIN:
                ore = 220
            elif b == BIOME_HILLS:
                ore = 170
            elif b == BIOME_DESERT:
                ore = 90
            elif b == BIOME_TAIGA:
                ore = 110
            elif b in (BIOME_GRASSLAND, BIOME_FOREST):
                ore = 50
            else:
                ore = 10
            grid.ore_richness[idx] = min(255, ore)

            # Fish Potential: coastlines, ocean, lakes, and rivers
            if b == BIOME_OCEAN or is_lake:
                fish = 220
            elif b == BIOME_BEACH or has_river:
                fish = 180
            elif b == BIOME_SWAMP:
                fish = 120
            else:
                fish = 10
            grid.fish_potential[idx] = min(255, fish)

            # Stone
            if b == BIOME_MOUNTAIN:
                stone = 230
            elif b == BIOME_HILLS:
                stone = 180
            elif b in (BIOME_GRASSLAND, BIOME_FOREST):
                stone = 70
            else:
                stone = 30
            grid.stone[idx] = min(255, stone)

            # Travel Cost
            if b == BIOME_OCEAN:
                cost = 80  # Requires boats
            elif b == BIOME_MOUNTAIN:
                cost = 90  # Extremely steep
            elif b == BIOME_SNOW:
                cost = 65
            elif b == BIOME_SWAMP:
                cost = 55
            elif b == BIOME_HILLS:
                cost = 35
            elif b == BIOME_FOREST:
                cost = 25
            elif b == BIOME_TAIGA:
                cost = 28
            elif b == BIOME_DESERT:
                cost = 20
            elif b == BIOME_BEACH:
                cost = 14
            else:  # Grassland
                cost = 10
            if has_river and b != BIOME_OCEAN:
                cost = max(8, cost - 4)  # River valley ease of travel

            grid.travel_cost[idx] = min(255, cost)

    return grid
