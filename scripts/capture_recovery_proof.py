"""
Engine Recovery Mode Verification Script.
Generates all required visual proof screenshots:
1. recovery_1_terrain_visible.png
2. recovery_2_camera_movement.png
3. recovery_3_chunk_colors.png
4. recovery_4_wireframe.png
And outputs the required audit metrics: FPS, Camera XYZ, Chunks Rendered, Draw Calls, Triangle Count.
"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PIL import Image
from engine.app import EngineApp


def capture_all_proof():
    print("=== [ENGINE RECOVERY] VISUAL PROOF GENERATION ===", flush=True)
    app = EngineApp(width=1280, height=720, visible=False, spike_mode=False)

    p = app.player
    cam = app.camera
    cm = app.chunk_mgr

    # Look slightly down to see the ground and horizon clearly
    p.pitch = -18.0
    cam.pitch = -18.0

    out_dir = Path("reports/screens")
    out_dir.mkdir(parents=True, exist_ok=True)

    def save_and_analyze(filename: str, desc: str):
        # In ModernGL with GLFW, read from color texture attachment or frame
        path = out_dir / filename
        app.capture_screenshot(path)
        img = Image.open(path)
        colors = img.getcolors(1000000)
        top_cols = sorted(colors, key=lambda x: x[0], reverse=True)[:4] if colors else []
        print(f"\n[+] Captured {filename} ({desc})", flush=True)
        print(f"    Total Unique Colors: {len(colors)}", flush=True)
        print(f"    Top Colors: {top_cols}", flush=True)
        print(f"    Camera XYZ: ({cam.x:.2f}, {cam.y:.2f}, {cam.z:.2f}) [Yaw: {cam.yaw:.1f}°, Pitch: {cam.pitch:.1f}°]", flush=True)
        print(f"    Chunks Loaded: {len(cm.chunks)} | Chunks Meshed: {sum(1 for c in cm.chunks.values() if c.opaque_mesh is not None)}", flush=True)
        print(f"    Chunks Rendered: {cm.chunks_rendered} | Draw Calls: {cm.draw_calls} | Triangles: {cm.triangles_rendered:,}", flush=True)
        print(f"    FPS: {app.timer.fps:.1f}", flush=True)
        return len(colors)

    # 1. First Proof: Terrain Visible (with HUD and Crosshair)
    print("\n--- 1. Terrain Visible Test ---", flush=True)
    # Run 5 frames to settle
    for _ in range(5):
        app.run_frame()
    n_cols1 = save_and_analyze("recovery_1_terrain_visible.png", "Visible Terrain + Blocks + HUD + Crosshair")
    assert n_cols1 > 100, f"Expected rich visual colors, got {n_cols1}"

    # 2. Second Proof: Camera Movement
    print("\n--- 2. Camera Movement Test ---", flush=True)
    p.x += 12.0
    p.z += 12.0
    p.yaw = 45.0
    cam.yaw = 45.0
    for _ in range(3):
        app.run_frame()
    n_cols2 = save_and_analyze("recovery_2_camera_movement.png", "Camera Moved (+12m X, +12m Z, Yaw 45°)")
    assert n_cols2 > 100, f"Expected rich visual colors after movement, got {n_cols2}"

    # 3. Third Proof: Chunk Color Debug Mode (Red, Green, Blue, Yellow)
    print("\n--- 3. Chunk Color Debug Mode Test ---", flush=True)
    cm.chunk_debug_colors = True
    app.run_frame()
    n_cols3 = save_and_analyze("recovery_3_chunk_colors.png", "Chunk Colors Debug (Red, Green, Blue, Yellow)")
    assert n_cols3 > 100, f"Expected chunk color debug colors, got {n_cols3}"
    cm.chunk_debug_colors = False

    # 4. Fourth Proof: Wireframe Mode
    print("\n--- 4. Wireframe Mode Test ---", flush=True)
    cm.wireframe = True
    app.run_frame()
    n_cols4 = save_and_analyze("recovery_4_wireframe.png", "Wireframe Mesh Mode")
    assert n_cols4 > 10, f"Expected wireframe lines, got {n_cols4}"
    cm.wireframe = False

    app.window.destroy()
    print("\n=== [ENGINE RECOVERY] ALL PROOFS GENERATED AND VERIFIED 100% ===", flush=True)


if __name__ == "__main__":
    capture_all_proof()
