"""
Generates 6 Visual Verification Screenshots for Stage E1:
1. mountain.png
2. river.png
3. forest.png
4. coast.png
5. village.png
6. underground.png
Also computes distinct block counts used per biome and in total.
"""

from __future__ import annotations
import json
import math
from pathlib import Path
import sys
import time

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.app import EngineApp
from engine.world.block_registry import registry
from minemesis.terrain.world_provider_t0 import T0WorldProvider


def main():
    print("=====================================================")
    print(" Minemesis Stage E1 Visual Screenshot Generator     ")
    print("=====================================================")

    prov = T0WorldProvider()
    spec = prov.generate(42)

    screens_dir = _ROOT / "reports" / "screens"
    screens_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initialize Headless Engine App with 1280x720
    app = EngineApp(width=1280, height=720, visible=False, world_spec=spec, view_distance=8)
    gen = app.chunk_mgr.generator

    # 2. Block Palette Audit: Count distinct blocks in data/blocks.json and per biome
    with open(_ROOT / "data" / "blocks.json", "r", encoding="utf-8") as f:
        blocks_data = json.load(f)
    total_blocks = blocks_data.get("total_blocks", len(blocks_data.get("blocks", [])))

    with open(_ROOT / "data" / "biome_palettes.json", "r", encoding="utf-8") as f:
        biomes_data = json.load(f).get("biomes", {})

    print(f"\n[AUDIT] Total Distinct Registered Block Types: {total_blocks}")
    print("\n[AUDIT] Distinct Blocks Configured Per Biome:")
    for b_name, b_info in biomes_data.items():
        used_blocks = set()
        if b_info.get("surface_block"): used_blocks.add(b_info["surface_block"])
        if b_info.get("subsurface_block"): used_blocks.add(b_info["subsurface_block"])
        if b_info.get("stone_base"): used_blocks.add(b_info["stone_base"])
        if b_info.get("deep_stone"): used_blocks.add(b_info["deep_stone"])
        if b_info.get("fluid_block"): used_blocks.add(b_info["fluid_block"])
        if b_info.get("ground_cover"): used_blocks.add(b_info["ground_cover"])
        for flora_entry in b_info.get("flora_mix", []):
            used_blocks.add(flora_entry[0])
        print(f"  • {b_name:12}: {len(used_blocks):2} distinct materials ({', '.join(list(used_blocks)[:4])}...)")

    # 3. Define the 6 Camera Locations
    # 3a. Village (Settlement 0)
    s0 = spec.settlements[0]
    vil_x = float(s0.x * 8 + 4)
    vil_z = float(s0.y * 8 + 4)
    vil_y = float(gen.get_interpolated_height(int(vil_x), int(vil_z)) + 4)

    # 3b. Mountain (Search high elevation)
    mtn_x, mtn_z, mtn_y = 1200.0, 1200.0, 140.0
    for tz in range(50, 250, 20):
        for tx in range(50, 250, 20):
            idx = gen.grid.index(tx, tz)
            if gen.grid.elevation[idx] > 180:
                mtn_x = float(tx * 8 + 4)
                mtn_z = float(tz * 8 + 4)
                mtn_y = float(gen.get_interpolated_height(int(mtn_x), int(mtn_z)) + 4)
                break

    # 3c. River (Search river tile)
    riv_x, riv_z, riv_y = 1200.0, 1200.0, 65.0
    for tz in range(50, 250, 10):
        for tx in range(50, 250, 10):
            idx = gen.grid.index(tx, tz)
            if gen.grid.river_flow[idx] > 0 and gen.grid.elevation[idx] > 64:
                riv_x = float(tx * 8 + 4)
                riv_z = float(tz * 8 + 4)
                riv_y = float(gen.get_interpolated_height(int(riv_x), int(riv_z)) + 3)
                break

    # 3d. Forest
    for_x, for_z, for_y = 1200.0, 1200.0, 75.0
    for tz in range(50, 250, 10):
        for tx in range(50, 250, 10):
            idx = gen.grid.index(tx, tz)
            if gen.grid.biome[idx] == 3:  # Forest
                for_x = float(tx * 8 + 4)
                for_z = float(tz * 8 + 4)
                for_y = float(gen.get_interpolated_height(int(for_x), int(for_z)) + 3)
                break

    # 3e. Coast / Beach
    cst_x, cst_z, cst_y = 1200.0, 1200.0, 64.0
    for tz in range(30, 270, 10):
        for tx in range(30, 270, 10):
            idx = gen.grid.index(tx, tz)
            if gen.grid.biome[idx] == 1:  # Beach
                cst_x = float(tx * 8 + 4)
                cst_z = float(tz * 8 + 4)
                cst_y = float(gen.get_interpolated_height(int(cst_x), int(cst_z)) + 3)
                break

    # 3f. Underground
    ug_x = vil_x + 12.0
    ug_z = vil_z + 12.0
    ug_y = 28.0  # Deep subterranean strata

    shots = [
        ("village.png", vil_x, vil_y, vil_z, 45.0, -15.0, "Settlement architecture, longhouse & well"),
        ("mountain.png", mtn_x, mtn_y, mtn_z, 120.0, -10.0, "High alpine peaks, granite scree & snow"),
        ("river.png", riv_x, riv_y, riv_z, 210.0, -12.0, "Carved river gorge with fresh water flow"),
        ("forest.png", for_x, for_y, for_z, 90.0, -8.0, "Dense woodland canopy, ferns & soil"),
        ("coast.png", cst_x, cst_y, cst_z, 300.0, -10.0, "Coastal dunes, sand & ocean waves"),
        ("underground.png", ug_x, ug_y, ug_z, 180.0, 5.0, "Deep subterranean basalt, ores & caves"),
    ]

    print("\n[RENDER] Capturing 6 Required Screenshots for Stage E1...")
    for filename, x, y, z, yaw, pitch, desc in shots:
        app.player.x = x
        app.player.y = y
        app.player.z = z
        app.player.yaw = yaw
        app.player.pitch = pitch

        # Update streaming and run 3 frames to settle
        app.chunk_mgr.update_player_position(x, z)
        for _ in range(4):
            app.run_frame()

        out_path = screens_dir / filename
        app.capture_screenshot(out_path)
        print(f"  [OK] Saved {filename:16} ({desc}) -> {out_path.name}")

    app.window.destroy()
    print("\n[SUCCESS] All 6 Stage E1 Screenshots Generated Successfully!")


if __name__ == "__main__":
    main()
