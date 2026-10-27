"""
Minemesis Standalone Game Engine Executable Entrypoint.
"""

from __future__ import annotations
import argparse
import os
from pathlib import Path
import sys
import time

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine import __version__
from engine.app import EngineApp


def main() -> int:
    parser = argparse.ArgumentParser(description="Minemesis Standalone 3D Voxel Civilization Game")
    parser.add_argument("--version", action="store_true", help="Print engine version and exit")
    parser.add_argument("--spike", action="store_true", help="Run Stage E0 spinning cube bootstrap spike")
    parser.add_argument("--benchmark", type=int, default=0, help="Run for N frames, measure FPS & RAM, save screenshot, then exit")
    parser.add_argument("--headless", action="store_true", help="Run with hidden window")
    parser.add_argument("--screenshot", type=str, default=None, help="Save screenshot to path on exit")

    args = parser.parse_args()

    if args.version:
        print(f"Minemesis Engine v{__version__} [Standalone OpenGL 3.3 Core]")
        return 0

    visible = not args.headless
    app = EngineApp(width=1280, height=720, visible=visible)

    if args.benchmark > 0:
        print(f"[*] Running Minemesis Benchmark for {args.benchmark} frames...")
        t0 = time.perf_counter()
        app.run(max_frames=args.benchmark)
        total_time = time.perf_counter() - t0
        avg_fps = args.benchmark / total_time if total_time > 0 else 60.0

        print(f"[OK] Benchmark Complete:")
        print(f"     Total Frames: {args.benchmark}")
        print(f"     Total Time:   {total_time:.3f} s")
        print(f"     Average FPS:  {avg_fps:.1f} FPS")
        print(f"     Peak RAM:     {app.peak_rss_mb:.1f} MB")

        shot_path = args.screenshot or "reports/screens/benchmark.png"
        app.capture_screenshot(shot_path)
        print(f"     Screenshot:   {shot_path}")
        return 0

    # Normal interactive execution
    app.run()
    if args.screenshot:
        app.capture_screenshot(args.screenshot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
