"""
Smoke Runner for Big Build Milestones.
Runs a 100-year simulation in a fresh process, measures peak RSS and elapsed runtime,
and appends a standardized entry to reports/ram_log.md.
Supports --profile to inspect object counts and memory distribution.
"""

from __future__ import annotations
import argparse
from collections import Counter
import gc
import os
from pathlib import Path
import sys
import time
import tracemalloc

import psutil

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from minemesis.core.seed import SeedPair
from minemesis.export.writer import RunDBWriter
from minemesis.systems.simulation import Simulation


def format_size(bytes_val: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:3.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"


def run_smoke(
    milestone: str,
    years: int = 100,
    world_seed: int = 42,
    history_seed: int = 1337,
    profile: bool = False,
    out_db: str = "smoke_run.minemesis",
) -> int:
    process = psutil.Process(os.getpid())
    peak_rss = 0.0

    if profile:
        tracemalloc.start()

    seed_pair = SeedPair(world=world_seed, history=history_seed)
    db_path = Path(out_db).resolve()
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass

    writer = RunDBWriter(db_path)

    print(f"============================================================")
    print(f" SMOKE RUN: {milestone} ({years} Years, Seed {world_seed}:{history_seed}) ")
    print(f"============================================================")

    t0 = time.perf_counter()

    sim = Simulation(
        seed=seed_pair,
        export_sink=writer,
        enable_religion=True,
        enable_lore=True,
    )

    total_ticks = years * 12
    for tick_idx in range(total_ticks):
        sim.step_month()

        # Check RSS every year
        if (tick_idx + 1) % 12 == 0:
            current_rss = process.memory_info().rss / (1024 * 1024)
            if current_rss > peak_rss:
                peak_rss = current_rss

            if current_rss > 800.0:
                print(f"[WARN] Year {(tick_idx+1)//12}: RSS {current_rss:.1f}MB exceeds 80% budget (800MB). Running aggressive compaction...")
                sim.compact_history()
                current_rss = process.memory_info().rss / (1024 * 1024)
                if current_rss > 1000.0:
                    type_counts = Counter(type(obj).__name__ for obj in gc.get_objects())
                    top_objs = type_counts.most_common(10)
                    raise MemoryError(
                        f"[FATAL] RSS {current_rss:.1f}MB exceeded 1.0GB budget! Top objects: {top_objs}"
                    )

    sim.finalize_export()
    t_elapsed = time.perf_counter() - t0

    current_rss = process.memory_info().rss / (1024 * 1024)
    if current_rss > peak_rss:
        peak_rss = current_rss

    living_pop = len(sim.living_characters)
    total_events = len(sim.event_log)

    status = "PASS" if peak_rss <= 1000.0 else "FAIL"

    print(f"[RESULT] Milestone: {milestone}")
    print(f"  Runtime:    {t_elapsed:.2f}s")
    print(f"  Peak RSS:   {peak_rss:.1f} MB (Budget <= 1000.0 MB) -> {status}")
    print(f"  Living Pop: {living_pop}")
    print(f"  Events:     {total_events}")

    if profile:
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")
        print("\n[PROFILE] Top 10 Memory Allocations by Line:")
        for stat in top_stats[:10]:
            print(f"  {stat}")

        type_counts = Counter(type(obj).__name__ for obj in gc.get_objects())
        print("\n[PROFILE] Top 10 Python Object Counts in Heap:")
        for name, count in type_counts.most_common(10):
            print(f"  {name}: {count:,}")

    # Append to reports/ram_log.md
    log_file = ROOT_DIR / "reports" / "ram_log.md"
    entry = f"| {milestone} | {years} | {total_ticks} | {living_pop} | {total_events} | {peak_rss:.1f} | {t_elapsed:.2f} | {status} |\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(entry)

    # Clean up test db file
    try:
        db_path.unlink(missing_ok=True)
    except Exception:
        pass

    return 0 if status == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Milestone Smoke Runner")
    parser.add_argument("--milestone", type=str, required=True, help="Milestone name (e.g. M1, M4, M2, M3, M5, M6)")
    parser.add_argument("--years", type=int, default=100, help="Years to simulate")
    parser.add_argument("--world-seed", type=int, default=42, help="World Seed")
    parser.add_argument("--history-seed", type=int, default=1337, help="History Seed")
    parser.add_argument("--profile", action="store_true", help="Print memory profile & object breakdown")
    parser.add_argument("--out", type=str, default="smoke_run.minemesis", help="Output database path")

    args = parser.parse_args()
    return run_smoke(
        milestone=args.milestone,
        years=args.years,
        world_seed=args.world_seed,
        history_seed=args.history_seed,
        profile=args.profile,
        out_db=args.out,
    )


if __name__ == "__main__":
    sys.exit(main())
