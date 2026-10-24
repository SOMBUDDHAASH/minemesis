"""
Hold-out B and Training Re-evaluation Runner for Milestone 0.5.1.
1. Re-runs the 50 training seeds (42 + 17*i) on m0.5.1 code via run_batch_analytics.
2. Runs Hold-out B (seeds 2000-2049) on m0.5.1 code via run_batch_analytics.
3. Identifies Median, Strongest, and Weakest runs from Hold-out B.
4. Generates formatted readable chronological histories in reports/history_seed_<N>.txt.
5. Exports Mermaid causal graph for the strongest seed.
"""

from __future__ import annotations
import json
import os
import sys

sys.path.insert(0, os.path.abspath("."))

from minemesis.analytics import run_batch_analytics
from minemesis.systems.simulation import Simulation
from minemesis.core.types import EventType
from minemesis.core.history_printer import (
    get_deepest_causal_chain_metrics,
    get_deepest_conflict_chain_metrics,
    get_longest_conflict_path,
    export_causal_graph_mermaid,
)


def is_non_routine(evt) -> bool:
    """
    Returns True if an event is non-routine:
    Conflict events (Feud, Raid, Revelation, Famine, SuccessionCrisis, Peace, SettlementCollapse, Migration)
    plus revenge Death or violent Death.
    Natural deaths (old age/illness with no causes), births, marriages without drama are routine.
    """
    if evt.type in {
        EventType.FEUD,
        EventType.RAID,
        EventType.REVELATION,
        EventType.FAMINE,
        EventType.SUCCESSION_CRISIS,
        EventType.PEACE,
        EventType.SETTLEMENT_COLLAPSE,
        EventType.MIGRATION,
    }:
        return True
    if evt.type == EventType.DEATH:
        if evt.payload.get("revenge") or evt.payload.get("cause_of_death") == "Revenge":
            return True
        if len(evt.causes) > 0:
            return True
    if evt.type == EventType.CHIEF_CHANGED and evt.causes:
        return True
    if evt.type == EventType.MARRIAGE and evt.causes:
        return True
    return False


def generate_readable_history(sim: Simulation) -> str:
    events = sim.event_log.all_events()
    lines = []
    
    # Track events by year
    events_by_year: dict[int, list] = {}
    for e in events:
        y = e.tick // 12 + 1
        events_by_year.setdefault(y, []).append(e)

    for y in range(1, 101):
        y_events = events_by_year.get(y, [])
        routine_births = 0
        routine_marriages = 0
        routine_deaths = 0
        dramatic_events = []

        for e in y_events:
            if e.type == EventType.BIRTH:
                routine_births += 1
            elif e.type == EventType.MARRIAGE and not e.causes:
                routine_marriages += 1
            elif e.type == EventType.DEATH and not e.causes and not e.payload.get("revenge"):
                routine_deaths += 1
            else:
                dramatic_events.append(e)

        # Yearly routine tally
        if routine_births > 0 or routine_marriages > 0 or routine_deaths > 0:
            lines.append(f"[Year {y:3d} Summary] Routine demographics: {routine_births} births, {routine_marriages} marriages, {routine_deaths} natural deaths.")

        for e in dramatic_events:
            m = e.tick % 12 + 1
            desc = e.payload.get("description", e.type.value)
            causes_str = f"Causes: [{', '.join('#' + str(c) for c in e.causes)}]" if e.causes else "Root Event"
            participants_str = ", ".join(f"{role}={name}" for role, name in e.participants) if e.participants else "None"
            lines.append(f"  [Year {y:3d} Month {m:2d}] #{e.id:4d} {e.type.value.upper()} @ {e.location} | {desc} | {causes_str} | Participants: ({participants_str})")

    return "\n".join(lines)


def main():
    print("=== Step 4: Re-evaluating Training Batch (m0.5.1) ===")
    training_seeds = [42 + i * 17 for i in range(50)]
    training_summary = run_batch_analytics(
        seeds=training_seeds,
        years=100,
        out_dir="reports",
        filename_prefix="training_m051",
    )
    print("Training batch re-evaluation complete.")

    print("\n=== Step 4: Executing Hold-out B (seeds 2000-2049) ===")
    holdout_b_seeds = list(range(2000, 2050))
    holdout_b_summary = run_batch_analytics(
        seeds=holdout_b_seeds,
        years=100,
        out_dir="reports",
        filename_prefix="holdout_B",
    )
    print("Hold-out B execution complete.")

    # Re-run the Hold-out B seeds to capture individual simulations for history analysis
    print("\nAnalyzing Hold-out B runs for Median, Strongest, and Weakest stories...")
    run_stats = []
    for seed in holdout_b_seeds:
        sim = Simulation(seed)
        sim.run_years(100)
        all_evts = sim.event_log.all_events()
        non_routine_count = sum(1 for e in all_evts if is_non_routine(e))
        feuds = [e for e in all_evts if e.type == EventType.FEUD]
        c_best_id, c_depth, c_types = get_deepest_conflict_chain_metrics(sim.event_log)
        run_stats.append({
            "seed": seed,
            "sim": sim,
            "total_events": len(all_evts),
            "non_routine": non_routine_count,
            "feuds": len(feuds),
            "conflict_depth": c_depth,
            "conflict_types": c_types,
            "c_best_id": c_best_id,
        })

    # Sort by non-routine count
    sorted_by_drama = sorted(run_stats, key=lambda x: (x["non_routine"], x["feuds"], x["conflict_depth"]))

    # Median: middle of sorted_by_drama
    median_item = sorted_by_drama[len(sorted_by_drama) // 2]

    # Strongest: highest feuds, then highest conflict depth, then non-routine
    strongest_candidates = sorted(run_stats, key=lambda x: (x["feuds"], x["conflict_depth"], x["non_routine"]), reverse=True)
    strongest_item = strongest_candidates[0]

    # Weakest: lowest feuds > 0, lowest conflict depth > 0, lowest non-routine
    non_zero_runs = [r for r in run_stats if r["feuds"] > 0]
    if non_zero_runs:
        weakest_candidates = sorted(non_zero_runs, key=lambda x: (x["feuds"], x["conflict_depth"], x["non_routine"]))
        weakest_item = weakest_candidates[0]
    else:
        weakest_item = sorted_by_drama[0]

    print("\n--- Selected Hold-out B Story Runs ---")
    print(f"Median Run: Seed {median_item['seed']} | Non-routine: {median_item['non_routine']} | Feuds: {median_item['feuds']} | Conflict Depth: {median_item['conflict_depth']}")
    print(f"Strongest Run: Seed {strongest_item['seed']} | Non-routine: {strongest_item['non_routine']} | Feuds: {strongest_item['feuds']} | Conflict Depth: {strongest_item['conflict_depth']}")
    print(f"Weakest Run: Seed {weakest_item['seed']} | Non-routine: {weakest_item['non_routine']} | Feuds: {weakest_item['feuds']} | Conflict Depth: {weakest_item['conflict_depth']}")

    # Export histories for all three
    selected_items = [
        ("median", median_item),
        ("strongest", strongest_item),
        ("weakest", weakest_item),
    ]

    for label, item in selected_items:
        sim = item["sim"]
        seed = item["seed"]
        history_text = generate_readable_history(sim)
        
        # Conflict chain details
        c_id = item["c_best_id"]
        c_path = get_longest_conflict_path(sim.event_log, c_id) if c_id != -1 else []
        conflict_chain_desc = []
        for e_id in c_path:
            e = sim.event_log.get(e_id)
            conflict_chain_desc.append(f"  #{e.id:4d} (Y{e.tick // 12 + 1} M{e.tick % 12 + 1}) {e.type.value} @ {e.location}: {e.payload.get('description', '')}")

        # Populations
        living = sim.living_characters
        pop_desc = []
        for s_id, s in sorted(sim.settlements.items()):
            c_count = sum(1 for c in living if c.settlement_id == s_id)
            pop_desc.append(f"  * {s.name:12s}: {c_count:2d} citizens | Food: {s.food:4d} | Wealth: {s.wealth:4d}")

        file_content = f"================================================================================\n"
        file_content += f"HOLD-OUT B CHRONOLOGICAL HISTORY: {label.upper()} RUN (SEED {seed})\n"
        file_content += f"================================================================================\n"
        file_content += f"Total Events: {item['total_events']} (Non-routine: {item['non_routine']})\n"
        file_content += f"Total Feuds: {item['feuds']}\n"
        file_content += f"Longest Conflict Path Depth: {item['conflict_depth']} (Distinct Types: {item['conflict_types']})\n\n"
        file_content += f"End-State Living Populations (Total: {len(living)}):\n"
        file_content += "\n".join(pop_desc) + "\n\n"
        file_content += f"Longest Conflict Chain (Ending at Event #{c_id}):\n"
        file_content += "\n".join(conflict_chain_desc) + "\n\n"
        file_content += f"--- Full Chronological History ---\n"
        file_content += history_text + "\n"

        out_path = f"reports/history_seed_{seed}.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(file_content)
        print(f"Exported history for Seed {seed} ({label}) to {out_path}")

    # Export Mermaid graph for Strongest run
    strongest_sim = strongest_item["sim"]
    strongest_id = strongest_item["c_best_id"]
    mermaid_path = "reports/strongest_story.mmd"
    with open(mermaid_path, "w", encoding="utf-8") as f:
        f.write(export_causal_graph_mermaid(strongest_sim.event_log, strongest_id))
    print(f"Exported Mermaid graph for Strongest seed ({strongest_item['seed']}) to {mermaid_path}")


if __name__ == "__main__":
    main()
