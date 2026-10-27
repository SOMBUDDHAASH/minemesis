"""
Verification script for Stage E2: People, Places, Schedules, and Books.
Captures screenshots of NPCs, Book Reader, and NPC Interaction Menu.
"""

import math
from pathlib import Path
from engine.app import EngineApp
from engine.entities.book_reader import BookReader


def test_stage_e2():
    print("[*] Launching Engine for Stage E2 Verification...")
    app = EngineApp(width=1280, height=720, visible=False, spike_mode=False)

    p = app.player
    print(f"[*] Player spawned at ({p.x:.1f}, {p.y:.1f}, {p.z:.1f})")
    print(f"[*] Total NPCs spawned: {len(app.npcs)}")

    # Move player close to the first NPC (Chief) and face them
    if app.npcs:
        target_npc = app.npcs[0]
        p.x = target_npc.x - 2.5
        p.z = target_npc.z - 2.5
        p.y = target_npc.y
        # Face target
        dx = target_npc.x - p.x
        dz = target_npc.z - p.z
        p.yaw = math.degrees(math.atan2(-dx, dz))
        p.pitch = -5.0
        print(f"[*] Target NPC: {target_npc.name} ({target_npc.profession}) at ({target_npc.x:.1f}, {target_npc.y:.1f}, {target_npc.z:.1f})")

    # Run 10 frames to mesh and settle
    for _ in range(10):
        app.run_frame()

    # Capture 1: NPCs in 3D
    Path("reports/screens").mkdir(parents=True, exist_ok=True)
    app.capture_screenshot("reports/screens/stage_e2_npcs.png")
    print("[+] Captured reports/screens/stage_e2_npcs.png")

    # Capture 2: NPC Interaction Menu
    if app.npcs:
        app.interaction.open_interaction(app.npcs[0])
        app.interaction.execute_action("talk", p)
        app.run_frame()
        app.capture_screenshot("reports/screens/stage_e2_interaction.png")
        print("[+] Captured reports/screens/stage_e2_interaction.png")
        app.interaction.close_interaction()

    # Capture 3: Book Reader
    book_data = BookReader.load_random_book_from_disk()
    app.book_reader.open_book(book_data)
    app.run_frame()
    app.capture_screenshot("reports/screens/stage_e2_book_reader.png")
    print("[+] Captured reports/screens/stage_e2_book_reader.png")
    app.book_reader.close_book()

    app.window.destroy()
    print("[OK] Stage E2 Verification complete!")


if __name__ == "__main__":
    test_stage_e2()
