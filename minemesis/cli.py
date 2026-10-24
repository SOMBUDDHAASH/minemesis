"""
Command Line Interface for Minemesis Headless Simulation.
Supports single-run simulations and 50-seed batch analytics.
"""

from __future__ import annotations
import argparse
import hashlib
import os
import sys
from minemesis.analytics import run_batch_analytics
from minemesis.core.history_printer import (
    export_causal_graph_dot,
    export_causal_graph_mermaid,
    format_causal_chain,
    format_linear_history,
    get_deepest_causal_chain_metrics,
    get_deepest_conflict_chain_metrics,
)
from minemesis.core.types import EventType
from minemesis.systems.simulation import Simulation


def run_single(args: argparse.Namespace) -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print(f"=== Minemesis Simulation (Milestone 0.5) ===")
    print(f"Seed: {args.seed} | Duration: {args.years} Simulated Years ({args.years * 12} Ticks)")

    if args.check_determinism:
        print("\n--- Running Determinism Verification ---")
        sim_a = Simulation(args.seed)
        sim_a.run_years(args.years)
        json_a = sim_a.event_log.to_json(indent=None)
        hash_a = hashlib.sha256(json_a.encode("utf-8")).hexdigest()

        sim_b = Simulation(args.seed)
        sim_b.run_years(args.years)
        json_b = sim_b.event_log.to_json(indent=None)
        hash_b = hashlib.sha256(json_b.encode("utf-8")).hexdigest()

        if hash_a == hash_b and json_a == json_b:
            print(f"[PASS] Determinism Check: Byte-identical event logs! SHA256: {hash_a}")
        else:
            print(f"[FAIL] Determinism mismatch! Hash A: {hash_a} != Hash B: {hash_b}")
            sys.exit(1)

    sim = Simulation(args.seed)
    sim.run_years(args.years)

    events = sim.event_log.all_events()
    print(f"\n--- Simulation Completed: {args.years} Years ({sim.tick} Ticks) ---")
    print(f"Total Objective Events: {len(events)}")

    # Breakdown by event type
    type_counts: dict[str, int] = {}
    for e in events:
        type_counts[e.type.value] = type_counts.get(e.type.value, 0) + 1

    for e_type in EventType:
        count = type_counts.get(e_type.value, 0)
        if count > 0:
            print(f"  * {e_type.value:20s}: {count:4d}")

    # Demographics
    living = sim.living_characters
    print(f"\nPopulation: {len(living)} living characters (started with {len(sim.settlements) * 10})")
    for s_id, s in sorted(sim.settlements.items()):
        s_living = [c for c in living if c.settlement_id == s_id]
        print(f"  * {s.name:10s} (pos: {s.x}, {s.y}): {len(s_living)} citizens | Wealth: {s.wealth} | Food: {s.food}")

    # Drama metrics
    feuds = [e for e in events if e.type == EventType.FEUD]
    wrongful = [e for e in feuds if e.payload.get("is_wrongful")]
    revenge = [e for e in events if e.type == EventType.DEATH and e.payload.get("revenge")]
    raids = [e for e in events if e.type == EventType.RAID]
    famines = [e for e in events if e.type == EventType.FAMINE]
    crises = [e for e in events if e.type == EventType.SUCCESSION_CRISIS]
    peaces = [e for e in events if e.type == EventType.PEACE]

    print(f"\nHistorical Drama Metrics:")
    print(f"  * Feuds Declared       : {len(feuds)}")
    print(f"  * Wrongful Grudges     : {len(wrongful)} (emerged from false belief over accidental death)")
    print(f"  * Revenge Killings     : {len(revenge)}")
    print(f"  * Raids Conducted      : {len(raids)}")
    print(f"  * Famines Endured      : {len(famines)}")
    print(f"  * Succession Crises    : {len(crises)}")
    print(f"  * Peace / Reconciled   : {len(peaces)}")

    # Causal chain demonstration
    best_id, depth, distinct_types = get_deepest_causal_chain_metrics(sim.event_log)
    c_best_id, c_depth, c_distinct_types = get_deepest_conflict_chain_metrics(sim.event_log)
    target_id = args.event_id if args.event_id is not None else best_id

    print(f"\n--- Deepest Causal Story Analysis (Event #{target_id}) ---")
    print(f"Longest Causal Depth: {depth} | Distinct Event Types on Path: {distinct_types}")
    print(f"Conflict Causal Depth: {c_depth} | Distinct Conflict Event Types on Path: {c_distinct_types}")
    print(format_causal_chain(sim.event_log, target_id))

    if args.export_dot:
        os.makedirs(os.path.dirname(os.path.abspath(args.export_dot)), exist_ok=True)
        with open(args.export_dot, "w", encoding="utf-8") as f:
            f.write(export_causal_graph_dot(sim.event_log, target_id))
        print(f"\nCausal story DOT exported to {args.export_dot}")

    if args.export_mermaid:
        os.makedirs(os.path.dirname(os.path.abspath(args.export_mermaid)), exist_ok=True)
        with open(args.export_mermaid, "w", encoding="utf-8") as f:
            f.write(export_causal_graph_mermaid(sim.event_log, target_id))
        print(f"\nCausal story Mermaid exported to {args.export_mermaid}")

    if args.output_json:
        os.makedirs(os.path.dirname(os.path.abspath(args.output_json)), exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            f.write(sim.event_log.to_json(indent=2))
        print(f"\nEvent log written to {args.output_json}")


def run_batch(args: argparse.Namespace) -> None:
    print(f"=== Minemesis Batch Analytics (Milestone 0.5.1) ===")
    print(f"Evaluating {args.seeds} seeds over {args.years} simulated years...")
    seed_list = [42 + i * 17 for i in range(args.seeds)]
    summary = run_batch_analytics(seeds=seed_list, years=args.years, out_dir=args.out, filename_prefix="milestone_0_5")
    print(f"\nBatch completed. Summary written to {args.out}/milestone_0_5_summary.md")
    print(f"Runs CSV written to {args.out}/milestone_0_5_runs.csv")
    print(f"Full metrics JSON written to {args.out}/milestone_0_5_metrics.json")
    print("\n--- Summary Snippet ---")
    print(f"World Extinctions: {summary['world_extinctions']}")
    print(f"Settlement Collapses: {summary['total_settlement_collapses']}")
    print(f"Zero Feud Share: {summary['zero_feud_share']:.1%}")
    print(f"Active Feud at Year 100 Share: {summary['active_feud_at_end_share']:.1%}")
    print(f"Routine Share (Mean): {summary['routine_share']['mean']:.1%}")
    print(f"Median Feuds: {summary['feuds']['median']} (Mean {summary['feuds']['mean']})")
    print(f"Median Conflict Chain Depth: {summary['conflict_causal_depth']['median']} (Distinct Types: {summary['distinct_types_on_conflict_path']['median']})")
    print(f"Median Longest Chain Depth: {summary['max_causal_depth']['median']} (Distinct Types: {summary['distinct_types_on_deepest_path']['median']})")


def run_cli() -> None:
    parser = argparse.ArgumentParser(description="Minemesis Headless Simulation Runner")
    subparsers = parser.add_subparsers(dest="subcommand")

    batch_parser = subparsers.add_parser("batch", help="Run multi-seed batch analytics")
    batch_parser.add_argument("--seeds", type=int, default=50, help="Number of seeds (default: 50)")
    batch_parser.add_argument("--years", type=int, default=100, help="Simulated years (default: 100)")
    batch_parser.add_argument("--out", type=str, default="reports", help="Output directory (default: reports)")

    run_parser = subparsers.add_parser("run", help="Run a single simulation")
    run_parser.add_argument("--seed", type=int, default=42, help="World generation seed (default: 42)")
    run_parser.add_argument("--years", type=int, default=100, help="Simulated years to run (default: 100)")
    run_parser.add_argument("--check-determinism", action="store_true", help="Run twice and verify byte-identical output")
    run_parser.add_argument("--event-id", type=int, default=None, help="Trace causal chain for a specific event ID")
    run_parser.add_argument("--output-json", type=str, default=None, help="Save event log to JSON file")
    run_parser.add_argument("--export-dot", type=str, default=None, help="Export causal story as Graphviz DOT file")
    run_parser.add_argument("--export-mermaid", type=str, default=None, help="Export causal story as Mermaid file")

    parser.add_argument("--seed", type=int, default=42, help="World generation seed")
    parser.add_argument("--years", type=int, default=100, help="Simulated years")
    parser.add_argument("--check-determinism", action="store_true")
    parser.add_argument("--event-id", type=int, default=None)
    parser.add_argument("--output-json", type=str, default=None)
    parser.add_argument("--export-dot", type=str, default=None)
    parser.add_argument("--export-mermaid", type=str, default=None)

    args = parser.parse_args()

    if args.subcommand == "batch":
        run_batch(args)
    else:
        run_single(args)


if __name__ == "__main__":
    run_cli()
