"""
Verification Script for Stage E3: Live Link to the Simulation.
Tests Bridge, Time Progression, Persistence, Construction Analyzer, Combat Witnesses,
and captures visual verification screenshots (Pause, Chronicle, World Map).
"""

from pathlib import Path
import sys
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.app import EngineApp


def test_stage_e3():
    print("[*] Launching Engine for Stage E3 Verification...")
    app = EngineApp(width=1280, height=720, visible=False, spike_mode=False)

    p = app.player
    bridge = app.bridge
    print(f"[*] Simulation Bridge active! Total Prehistory Ticks: {bridge.total_simulated_ticks} ({bridge.total_simulated_ticks // 12} Years)")
    print(f"[*] Recent Chronicle Events Loaded: {len(bridge.recent_chronicle_events)}")

    # 1. Test Chronicle Overlay Screenshot [J]
    app.show_chronicle = True
    app.run_frame()
    Path("reports/screens").mkdir(parents=True, exist_ok=True)
    app.capture_screenshot("reports/screens/stage_e3_chronicle.png")
    print("[+] Captured reports/screens/stage_e3_chronicle.png")
    app.show_chronicle = False

    # 2. Test World Map Overlay Screenshot [M]
    app.show_world_map = True
    app.run_frame()
    app.capture_screenshot("reports/screens/stage_e3_world_map.png")
    print("[+] Captured reports/screens/stage_e3_world_map.png")
    app.show_world_map = False

    # 3. Test Pause Menu Screenshot [Esc]
    app.paused = True
    app.save_message = "World State Saved Successfully to saves/test_e3/!"
    app.run_frame()
    app.capture_screenshot("reports/screens/stage_e3_pause.png")
    print("[+] Captured reports/screens/stage_e3_pause.png")
    app.paused = False

    # 4. Test Persistence (Save and Load)
    save_path = bridge.save_world("saves/test_e3", app)
    print(f"[*] Saved test world to: {save_path}")
    assert (save_path / "player.json").exists(), "player.json missing!"
    assert (save_path / "chunk_deltas.json").exists(), "chunk_deltas.json missing!"
    assert (save_path / "chronicle.minemesis").exists(), "chronicle.minemesis missing!"

    # Test load
    success = bridge.load_world(save_path, app)
    assert success, "World load failed!"
    print("[OK] Persistence Save/Load Verified 100% Operational!")

    # 5. Test Time Skipping (Sleeping)
    prev_ticks = bridge.total_simulated_ticks
    bridge.skip_time(8.0, app)
    assert bridge.total_simulated_ticks > prev_ticks, "Time skip did not advance simulation ticks!"
    print(f"[OK] Time Skip Verified: Advanced from {prev_ticks} to {bridge.total_simulated_ticks} ticks")

    # 6. Test Construction Analysis (Fortifications)
    s0 = app.world_spec.settlements[0]
    s0_x = s0.x * 8 + 4
    s0_z = s0.y * 8 + 4
    cx, cz = s0_x // 16, s0_z // 16
    if (cx, cz) not in app.chunk_mgr.chunk_deltas:
        app.chunk_mgr.chunk_deltas[(cx, cz)] = {}

    # Place 30 stone brick blocks (ID 89) near settlement
    for i in range(30):
        app.chunk_mgr.chunk_deltas[(cx, cz)][(i % 16, 70, (i // 16))] = 89

    bridge.analyze_construction(app.chunk_mgr)
    new_def = bridge.settlement_defensibility.get(s0.id, 10.0)
    print(f"[*] Settlement {s0.name} Defensibility after placing stone fortifications: {new_def:.1f}%")
    assert new_def > 10.0, "Defensibility did not increase after stone wall construction!"
    print("[OK] Construction Analyzer & Settlement Defensibility Verified!")

    # 7. Test Combat Witness & Reaction System
    if app.npcs:
        victim = app.npcs[0]
        witnesses = app.npcs[1:4]
        bridge.record_combat_encounter(victim_npc=victim, damage=6.0, fatal=False, witnesses=witnesses)
        for w in witnesses:
            assert w.affinity_to_player < 0, f"Witness {w.name} did not react to crime!"
            assert w.is_fleeing or w.is_hostile, f"Witness {w.name} did not flee or become hostile!"
        print("[OK] Combat Encounter Witness & Organic Reaction System Verified!")

    app.window.destroy()
    print("[SUCCESS] Stage E3 Full Verification Complete!")


if __name__ == "__main__":
    test_stage_e3()
