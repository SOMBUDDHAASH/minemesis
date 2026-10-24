"""
Milestone 0.5.2 100-Seed Validation Script.

Runs:
- 50 Training Seeds (0 to 49)
- 50 Hold-out C Seeds (3000 to 3049)

Verifies:
1. Exact demographic conservation (living = initial + births - deaths).
2. World survival rate (target >= 80%).
3. Marriage & birth funnels (identifying any stall of >= 10 years without births).
4. Causal depth and conflict chain analysis.
5. Event type share distribution (auditing demoted routine spam).
6. Exports 3 readable histories (highest, median, lowest) and Mermaid DAG for highest.
"""

from __future__ import annotations
import json
import os
import sys
from collections import Counter
from typing import Any

# Ensure workspace root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from minemesis.systems.simulation import Simulation
from minemesis.core.types import EventType
from minemesis.core.history_printer import (
    get_deepest_conflict_chain_metrics,
    get_longest_conflict_path,
    get_causal_depth,
    export_causal_graph_mermaid,
)
from viewer.formatter import format_event_sentence, format_because_clause
from viewer.export import export_story_to_text


TRAINING_SEEDS = list(range(50))
HOLDOUT_C_SEEDS = [3000 + i for i in range(50)]


def audit_single_seed(seed: int, years: int = 100) -> dict[str, Any]:
    sim = Simulation(seed=seed, enable_religion=True, enable_lore=True)
    initial_living = len(sim.living_characters)
    
    # Yearly tracking for birth stalls
    yearly_births: list[int] = [0] * (years + 1)
    yearly_living: list[int] = [0] * (years + 1)

    for y in range(1, years + 1):
        # Step 12 months
        for _ in range(12):
            if len(sim.living_characters) == 0:
                break
            sim.step_month()
        yearly_living[y] = len(sim.living_characters)
        # Count births in this year
        y_births = sum(1 for e in sim.event_log.all_events() if e.type == EventType.BIRTH and (e.tick // 12) + 1 == y)
        yearly_births[y] = y_births

    all_events = sim.event_log.all_events()
    final_living = len(sim.living_characters)
    total_births = sum(1 for e in all_events if e.type == EventType.BIRTH)
    total_deaths = sum(1 for e in all_events if e.type == EventType.DEATH)

    # 1. Demographic Conservation Check
    expected_living = initial_living + total_births - total_deaths
    reconciled = (final_living == expected_living)

    # 2. Survival Check
    survived = (final_living > 0)

    # 3. Birth Stall Check (>=10 consecutive years with 0 births while living >= 10)
    max_birth_stall = 0
    current_stall = 0
    stall_occurred = False
    for y in range(1, years + 1):
        if yearly_living[y] >= 10 and yearly_births[y] == 0:
            current_stall += 1
            if current_stall >= 10:
                stall_occurred = True
            max_birth_stall = max(max_birth_stall, current_stall)
        else:
            current_stall = 0

    # 4. Longest Conflict Path & Causal Depth
    best_id, longest_depth, distinct_types = get_deepest_conflict_chain_metrics(sim.event_log)
    longest_path = get_longest_conflict_path(sim.event_log, best_id) if best_id != -1 else []

    # 5. Event Counts
    event_counts = Counter(e.type.value for e in all_events)

    return {
        "seed": seed,
        "survived": survived,
        "initial_living": initial_living,
        "final_living": final_living,
        "total_births": total_births,
        "total_deaths": total_deaths,
        "expected_living": expected_living,
        "reconciled": reconciled,
        "max_birth_stall": max_birth_stall,
        "stall_occurred": stall_occurred,
        "longest_conflict_depth": longest_depth,
        "longest_path_ids": longest_path,
        "total_events": len(all_events),
        "event_counts": dict(event_counts),
        "sim_instance": sim,
    }


def run_batch(seeds: list[int], label: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    print(f"\n--- Running {label} ({len(seeds)} Seeds) ---")
    results = []
    reconciled_count = 0
    survived_count = 0
    stall_count = 0
    depths = []
    all_event_counts = Counter()

    for idx, s in enumerate(seeds, 1):
        res = audit_single_seed(s, years=100)
        results.append(res)
        if res["reconciled"]:
            reconciled_count += 1
        if res["survived"]:
            survived_count += 1
        if res["stall_occurred"]:
            stall_count += 1
        depths.append(res["longest_conflict_depth"])
        all_event_counts.update(res["event_counts"])

        if idx % 10 == 0 or idx == len(seeds):
            print(f"  Processed {idx}/{len(seeds)} seeds...")

    total_events = sum(all_event_counts.values()) or 1
    event_shares = {k: round((v / total_events) * 100, 2) for k, v in all_event_counts.most_common()}

    depths.sort()
    med_depth = depths[len(depths) // 2]
    avg_depth = sum(depths) / len(depths)

    summary = {
        "total_seeds": len(seeds),
        "reconciled_rate": (reconciled_count / len(seeds)) * 100,
        "survival_rate": (survived_count / len(seeds)) * 100,
        "stall_rate": (stall_count / len(seeds)) * 100,
        "min_depth": depths[0],
        "max_depth": depths[-1],
        "median_depth": med_depth,
        "mean_depth": round(avg_depth, 2),
        "total_events": total_events,
        "event_shares": event_shares,
    }

    return results, summary


def main():
    os.makedirs("reports", exist_ok=True)

    print("=======================================================")
    print(" Milestone 0.5.2 Validation Pass (100 Seeds)")
    print("=======================================================")

    # 1. Training Set (0 to 49)
    train_results, train_summary = run_batch(TRAINING_SEEDS, "Training Set (Seeds 0-49)")

    # 2. Hold-out C Set (3000 to 3049)
    holdout_results, holdout_summary = run_batch(HOLDOUT_C_SEEDS, "Hold-out C Set (Seeds 3000-3049)")

    # Combine for global analytics
    all_results = train_results + holdout_results
    total_reconciled = sum(1 for r in all_results if r["reconciled"])
    total_survived = sum(1 for r in all_results if r["survived"])
    total_stalls = sum(1 for r in all_results if r["stall_occurred"])
    all_depths = [r["longest_conflict_depth"] for r in all_results]
    all_depths.sort()

    print("\n=======================================================")
    print(" 100-SEED AGGREGATE RESULTS SUMMARY")
    print("=======================================================")
    print(f"Demographic Reconciliation: {total_reconciled}/100 ({total_reconciled}%) [Target: 100%]")
    print(f"World Survival Rate       : {total_survived}/100 ({total_survived}%) [Target: >= 80%]")
    print(f"Birth Stall Rate (>=10 yr): {total_stalls}/100 ({total_stalls}%)")
    print(f"Conflict Causal Depth     : Min={all_depths[0]}, Median={all_depths[len(all_depths)//2]}, Max={all_depths[-1]}")
    print("\nTraining Set Shares:")
    for k, v in list(train_summary["event_shares"].items())[:8]:
        print(f"  {k:24s}: {v}%")
    print("\nHold-out C Set Shares:")
    for k, v in list(holdout_summary["event_shares"].items())[:8]:
        print(f"  {k:24s}: {v}%")

    # Select 3 Runs from Hold-out C: Highest, Median, Lowest
    sorted_holdout = sorted(holdout_results, key=lambda r: r["longest_conflict_depth"])
    lowest_run = sorted_holdout[0]
    median_run = sorted_holdout[len(sorted_holdout) // 2]
    highest_run = sorted_holdout[-1]

    print(f"\nSelected Benchmark Runs from Hold-out C:")
    print(f"  Highest Causal Depth: Seed {highest_run['seed']} (Depth: {highest_run['longest_conflict_depth']})")
    print(f"  Median Causal Depth : Seed {median_run['seed']} (Depth: {median_run['longest_conflict_depth']})")
    print(f"  Lowest Causal Depth : Seed {lowest_run['seed']} (Depth: {lowest_run['longest_conflict_depth']})")

    # Export histories
    def export_run_history(run: dict[str, Any], filepath: str, title: str):
        sim = run["sim_instance"]
        txt = export_story_to_text(
            events=sim.event_log.all_events(),
            event_log=sim.event_log,
            characters=sim.characters,
            settlements=sim.settlements,
            title=title,
            include_causes=True,
        )
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(txt)
        print(f"  Exported history to: {filepath}")

    export_run_history(
        highest_run,
        "reports/m052_history_highest.txt",
        f"Minemesis Chronicle - Highest Causal Depth (Seed {highest_run['seed']}, Depth {highest_run['longest_conflict_depth']})",
    )
    export_run_history(
        median_run,
        "reports/m052_history_median.txt",
        f"Minemesis Chronicle - Median Causal Depth (Seed {median_run['seed']}, Depth {median_run['longest_conflict_depth']})",
    )
    export_run_history(
        lowest_run,
        "reports/m052_history_lowest.txt",
        f"Minemesis Chronicle - Lowest Causal Depth (Seed {lowest_run['seed']}, Depth {lowest_run['longest_conflict_depth']})",
    )

    # Export Mermaid diagram for Highest
    high_sim = highest_run["sim_instance"]
    mermaid_path = "reports/m052_causal_dag_highest.mmd"
    high_best_id, _, _ = get_deepest_conflict_chain_metrics(high_sim.event_log)
    mermaid_text = export_causal_graph_mermaid(high_sim.event_log, high_best_id)
    with open(mermaid_path, "w", encoding="utf-8") as f:
        f.write(mermaid_text)
    print(f"  Exported Mermaid causal graph to: {mermaid_path}")

    # Save summary report JSON
    full_report = {
        "training": train_summary,
        "holdout_c": holdout_summary,
        "aggregate": {
            "reconciliation_rate": total_reconciled,
            "survival_rate": total_survived,
            "stall_rate": total_stalls,
            "min_depth": all_depths[0],
            "median_depth": all_depths[len(all_depths)//2],
            "max_depth": all_depths[-1],
        },
        "selected_runs": {
            "highest": {"seed": highest_run["seed"], "depth": highest_run["longest_conflict_depth"]},
            "median": {"seed": median_run["seed"], "depth": median_run["longest_conflict_depth"]},
            "lowest": {"seed": lowest_run["seed"], "depth": lowest_run["longest_conflict_depth"]},
        }
    }
    with open("reports/m052_validation_summary.json", "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)
    print(f"  Saved validation metrics to: reports/m052_validation_summary.json")


if __name__ == "__main__":
    main()
