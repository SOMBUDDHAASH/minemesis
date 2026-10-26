"""
Generates 6 Sample Continental Map Renders for Milestone T0.

Exports high-resolution PNG renders directly to reports/maps/
using pure standard library (zlib, struct) with zero external dependencies.
"""

from __future__ import annotations
import math
import os
from pathlib import Path
import struct
import sys
import time
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from minemesis.terrain.terrain_engine import (
    generate_terrain,
    TerrainGrid,
    BIOME_NAMES,
    BIOME_OCEAN,
    BIOME_BEACH,
    BIOME_GRASSLAND,
    BIOME_FOREST,
    BIOME_TAIGA,
    BIOME_SNOW,
    BIOME_DESERT,
    BIOME_SWAMP,
    BIOME_HILLS,
    BIOME_MOUNTAIN,
    SEA_LEVEL,
)
from minemesis.terrain.catchment import place_settlements
from minemesis.terrain.roads import generate_road_network


BIOME_PALETTE = {
    BIOME_OCEAN: (26, 62, 118),
    BIOME_BEACH: (226, 206, 142),
    BIOME_GRASSLAND: (94, 178, 76),
    BIOME_FOREST: (36, 120, 54),
    BIOME_TAIGA: (44, 92, 74),
    BIOME_SNOW: (232, 244, 254),
    BIOME_DESERT: (228, 188, 110),
    BIOME_SWAMP: (70, 90, 60),
    BIOME_HILLS: (140, 150, 120),
    BIOME_MOUNTAIN: (116, 116, 124),
}


def write_png_rgb(filepath: Path, width: int, height: int, rgb_bytes: bytes) -> None:
    """Writes raw RGB buffer to standard PNG file."""
    def make_chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)

    raw_scanlines = bytearray()
    row_stride = width * 3
    for y in range(height):
        raw_scanlines.append(0)  # filter type 0: None
        raw_scanlines.extend(rgb_bytes[y * row_stride : (y + 1) * row_stride])

    png_data = bytearray(b"\x89PNG\r\n\x1a\n")
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png_data.extend(make_chunk(b"IHDR", ihdr))
    png_data.extend(make_chunk(b"IDAT", zlib.compress(bytes(raw_scanlines), 9)))
    png_data.extend(make_chunk(b"IEND", b""))

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(png_data)


def render_map_for_seed(world_seed: int, scale: int = 2) -> tuple[Path, dict]:
    """Generates world terrain, settlements, and roads, then renders to PNG."""
    t0 = time.perf_counter()
    w, h = 300, 300
    grid = generate_terrain(world_seed=world_seed, width=w, height=h)
    settlements = place_settlements(grid=grid, world_seed=world_seed, settlement_count=10, min_spacing=28)
    roads = generate_road_network(grid=grid, settlements=settlements)

    # Calculate statistics
    land_tiles = sum(1 for i in range(grid.size) if grid.elevation[i] > SEA_LEVEL)
    land_pct = (land_tiles / grid.size) * 100.0

    biome_counts: dict[str, int] = {}
    for i in range(grid.size):
        b_name = BIOME_NAMES[grid.biome[i]]
        biome_counts[b_name] = biome_counts.get(b_name, 0) + 1

    # Base 300x300 RGB buffer
    base_rgb = bytearray(w * h * 3)

    for y in range(h):
        row_offset = y * w * 3
        grid_row = y * w
        for x in range(w):
            idx = grid_row + x
            elev = grid.elevation[idx]
            biome = grid.biome[idx]
            has_river = (grid.river_flow[idx] > 0)
            is_lake = bool(grid.lake_flag[idx])

            if has_river and elev > SEA_LEVEL:
                r, g, b = (35, 128, 225)
            elif is_lake:
                r, g, b = (25, 85, 155)
            else:
                r, g, b = BIOME_PALETTE.get(biome, (100, 100, 100))

            # Elevation shading
            if biome not in (BIOME_OCEAN, BIOME_BEACH) and not has_river and not is_lake:
                shade = 0.82 + (elev / 255.0) * 0.36
                r = min(255, int(r * shade))
                g = min(255, int(g * shade))
                b = min(255, int(b * shade))

            px = row_offset + x * 3
            base_rgb[px] = r
            base_rgb[px + 1] = g
            base_rgb[px + 2] = b

    # Burn Roads into RGB (amber gold: 245, 158, 11)
    road_tiles = set()
    for road in roads:
        r_path = road.get("path", []) if isinstance(road, dict) else getattr(road, "path", [])
        for rx, ry in r_path:
            road_tiles.add((rx, ry))

    for rx, ry in road_tiles:
        if 0 <= rx < w and 0 <= ry < h:
            px = (ry * w + rx) * 3
            base_rgb[px] = 245
            base_rgb[px + 1] = 158
            base_rgb[px + 2] = 11

    # Scale image up by `scale` factor (e.g. 2x -> 600x600)
    out_w = w * scale
    out_h = h * scale
    scaled_rgb = bytearray(out_w * out_h * 3)

    for y in range(out_h):
        src_y = y // scale
        src_row = src_y * w * 3
        out_row = y * out_w * 3
        for x in range(out_w):
            src_x = x // scale
            src_px = src_row + src_x * 3
            out_px = out_row + x * 3
            scaled_rgb[out_px] = base_rgb[src_px]
            scaled_rgb[out_px + 1] = base_rgb[src_px + 1]
            scaled_rgb[out_px + 2] = base_rgb[src_px + 2]

    # Draw Settlements with distinct 7x7 red/gold badge with black outline
    for s in settlements:
        cx = s.x * scale + scale // 2
        cy = s.y * scale + scale // 2
        radius = max(3, 2 * scale)

        for dy in range(-radius - 1, radius + 2):
            for dx in range(-radius - 1, radius + 2):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < out_w and 0 <= ny < out_h:
                    d_sq = dx * dx + dy * dy
                    px = (ny * out_w + nx) * 3
                    if d_sq <= radius * radius:
                        # Inner red
                        scaled_rgb[px] = 239
                        scaled_rgb[px + 1] = 68
                        scaled_rgb[px + 2] = 68
                    elif d_sq <= (radius + 1) * (radius + 1):
                        # Black outline
                        scaled_rgb[px] = 0
                        scaled_rgb[px + 1] = 0
                        scaled_rgb[px + 2] = 0

    out_file = Path("reports") / "maps" / f"map_seed_{world_seed}.png"
    write_png_rgb(out_file, out_w, out_h, bytes(scaled_rgb))
    elapsed = time.perf_counter() - t0

    stats = {
        "world_seed": world_seed,
        "width": w,
        "height": h,
        "land_fraction_pct": round(land_pct, 1),
        "settlements": [s.name for s in settlements],
        "roads_count": len(roads),
        "render_time_sec": round(elapsed, 3),
        "file_size_kb": round(out_file.stat().st_size / 1024, 1),
        "biomes": {k: round((v / grid.size) * 100, 1) for k, v in sorted(biome_counts.items())},
    }
    return out_file, stats


def main() -> None:
    seeds = [42, 100, 777, 1337, 2024, 9999]
    print(f"Generating {len(seeds)} map renders to reports/maps/...")

    all_stats = []
    for s in seeds:
        path, stats = render_map_for_seed(s, scale=2)
        all_stats.append(stats)
        print(f" -> Seed {s:5d}: Land {stats['land_fraction_pct']}% | Settlements: {len(stats['settlements'])} | Roads: {stats['roads_count']} | Time: {stats['render_time_sec']}s | File: {path.name} ({stats['file_size_kb']} KB)")

    print("\nAll 6 map renders successfully generated!")


if __name__ == "__main__":
    main()
