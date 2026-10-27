"""
Rendering Audit & Diagnostic Script for Minemesis Engine.
Inspects camera, matrices, chunk generation, meshing, GPU buffers, and draw calls.
"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
from engine.app import EngineApp
from engine.world.block_registry import registry


def run_audit():
    print("=== [ENGINE RECOVERY] 1. RENDERING AUDIT ===", flush=True)

    # Initialize Engine (headless or hidden)
    app = EngineApp(width=1280, height=720, visible=False, spike_mode=False)
    p = app.player
    cam = app.camera
    cm = app.chunk_mgr

    print(f"\n[1] Camera & Player State:", flush=True)
    print(f"  Player Pos: ({p.x}, {p.y}, {p.z})", flush=True)
    print(f"  Player Yaw/Pitch: ({p.yaw}, {p.pitch})", flush=True)
    print(f"  Eye Pos: {p.get_eye_position()}", flush=True)
    print(f"  Camera Pos: ({cam.x}, {cam.y}, {cam.z})", flush=True)
    print(f"  Camera Forward: {cam.get_forward_vector()}", flush=True)

    # Check spawn chunk
    cx = int(p.x) // 16
    cz = int(p.z) // 16
    print(f"\n[2] Spawn Chunk Coordinates: cx={cx}, cz={cz}", flush=True)

    chunk = cm.get_chunk(cx, cz)
    block_counts = {}
    for y in range(256):
        for z in range(16):
            for x in range(16):
                bid = chunk.get_block(x, y, z)
                if bid != 0:
                    block_counts[bid] = block_counts.get(bid, 0) + 1

    total_blocks = sum(block_counts.values())
    print(f"  Total solid blocks in chunk ({cx}, {cz}): {total_blocks}", flush=True)
    print(f"  Block types in chunk: {block_counts}", flush=True)

    # Check terrain height at player position
    ground_y = cm.generator.get_interpolated_height(int(p.x), int(p.z))
    print(f"  Interpolated Terrain Height at player (x={int(p.x)}, z={int(p.z)}): {ground_y}", flush=True)
    print(f"  Player y={p.y:.1f} vs Ground y={ground_y:.1f} (Diff: {p.y - ground_y:.1f}m)", flush=True)

    # Check Meshing
    print(f"\n[3] Chunk Mesh State:", flush=True)
    print(f"  Opaque Mesh: {chunk.opaque_mesh}", flush=True)
    print(f"  Transparent Mesh: {chunk.transparent_mesh}", flush=True)
    if chunk.opaque_mesh:
        vao, vcount = chunk.opaque_mesh
        print(f"  Opaque Vertex Count: {vcount} vertices ({vcount // 3} triangles)", flush=True)

    # Check Matrices
    print(f"\n[4] Matrix Mathematics:", flush=True)
    proj = cam.projection_matrix
    view = cam.get_view_matrix()
    print("  Projection Matrix:\n", proj, flush=True)
    print("  View Matrix:\n", view, flush=True)

    # Test coordinate transformation of a block in front of camera
    test_pt = np.array([p.x, ground_y, p.z + 5.0, 1.0], dtype=np.float32)
    view_pt = np.dot(view, test_pt)
    clip_pt = np.dot(proj, view_pt)
    ndc_pt = clip_pt[:3] / clip_pt[3] if clip_pt[3] != 0 else clip_pt[:3]
    print(f"  Test Point (World): {test_pt[:3]}", flush=True)
    print(f"  Test Point (View):  {view_pt[:3]}", flush=True)
    print(f"  Test Point (Clip):  {clip_pt}", flush=True)
    print(f"  Test Point (NDC):   {ndc_pt}", flush=True)
    is_in_ndc = (-1.0 <= ndc_pt[0] <= 1.0) and (-1.0 <= ndc_pt[1] <= 1.0) and (-1.0 <= ndc_pt[2] <= 1.0)
    print(f"  Is Point inside Frustum? {is_in_ndc}", flush=True)

    # Check Shader Uniforms
    print(f"\n[5] Shader Program Uniforms:", flush=True)
    for u_name in ["u_proj", "u_view", "u_model", "u_texture", "u_light_dir", "u_fog_end"]:
        if u_name in app.shader.program:
            val = app.shader.program[u_name]
            print(f"  Uniform '{u_name}': {val}", flush=True)

    # Render a frame and check draw calls
    print(f"\n[6] Rendering Test Frame...", flush=True)
    app.run_frame()
    print(f"  Rendered frame successfully. FPS: {app.timer.fps:.1f}", flush=True)
    print(f"  Total Chunks Loaded: {len(cm.chunks)}", flush=True)

    # Capture diagnostic screenshot
    Path("reports/screens").mkdir(parents=True, exist_ok=True)
    diag_path = "reports/screens/diag_render.png"
    app.capture_screenshot(diag_path)
    print(f"  Saved diagnostic screenshot to {diag_path}", flush=True)

    # Analyze screenshot pixel colors
    from PIL import Image
    img = Image.open(diag_path)
    colors = img.getcolors(maxcolors=1000000)
    print(f"  Total Unique Colors in Screenshot: {len(colors)}", flush=True)
    if colors:
        sorted_cols = sorted(colors, key=lambda x: x[0], reverse=True)[:5]
        print(f"  Top 5 Colors (count, RGB): {sorted_cols}", flush=True)

    app.window.destroy()
    print("\n=== AUDIT COMPLETE ===", flush=True)


if __name__ == "__main__":
    run_audit()
