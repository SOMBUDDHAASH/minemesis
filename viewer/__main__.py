"""
Minemesis Viewer V2 Entrypoint.
Handles CLI flags:
  --version
  --simulate --world-seed <W> --history-seed <H> --years <Y> --out <file.minemesis>
  <file.minemesis> (open archive in GUI)
"""

from __future__ import annotations
import argparse
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from minemesis.core.seed import SeedPair
from minemesis.export.schema import BUILD_ID, CURRENT_SCHEMA_VERSION
from minemesis.export.writer import RunDBWriter
from minemesis.systems.simulation import Simulation


def run_simulation_cli(args: argparse.Namespace) -> int:
    world_seed = args.world_seed
    history_seed = args.history_seed
    years = args.years
    out_path = Path(args.out).resolve()

    print(f"[*] Starting Minemesis Simulation: World {world_seed}, History {history_seed}, {years} Years...")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    seed_pair = SeedPair(world=world_seed, history=history_seed)
    writer = RunDBWriter(out_path)

    sim = Simulation(
        seed=seed_pair,
        export_sink=writer,
        enable_religion=True,
        enable_lore=True,
    )

    print(f"[*] Simulating {years} years ({years * 12} ticks)...")
    sim.run_years(years)

    print("[*] Finalizing run database and executing Name Integrity Audit...")
    sim.finalize_export()

    print(f"[OK] Simulation complete! Exported to: {out_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Minemesis Historical Archive Viewer V2")
    parser.add_argument("file", nargs="?", default=None, help="Path to .minemesis database file to open")
    parser.add_argument("--version", action="store_true", help="Show viewer version and exit")
    parser.add_argument("--voxel", action="store_true", help="Launch directly into 3D Voxel Sandbox mode")
    parser.add_argument("--simulate", action="store_true", help="Run simulation headlessly and export to .minemesis")
    parser.add_argument("--world-seed", type=int, default=42, help="World Seed for simulation")
    parser.add_argument("--history-seed", type=int, default=1337, help="History Seed for simulation")
    parser.add_argument("--years", type=int, default=30, help="Years to simulate")
    parser.add_argument("--out", type=str, default="output.minemesis", help="Output .minemesis file path")

    args = parser.parse_args()

    if args.version:
        print(f"Minemesis Viewer {BUILD_ID} (Schema Version {CURRENT_SCHEMA_VERSION})")
        return 0

    if args.simulate:
        return run_simulation_cli(args)

    # Launch GUI
    from viewer.app import StoryViewerApp

    app = StoryViewerApp(initial_file=args.file)
    if args.voxel:
        app.after(200, lambda: app._launch_voxel_world())
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
