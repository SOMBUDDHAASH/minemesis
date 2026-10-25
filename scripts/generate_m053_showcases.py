"""
Generates the 5 stratified showcase histories across settlement counts 3..7
and exports reports/m053_validation_summary.json and DAG mermaid chart.
Fast execution without launching a 200-pair suite.
"""

from __future__ import annotations
import json
import os
import sys

# Ensure workspace root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from minemesis.core.seed import SeedPair
from minemesis.core.rng import keyed_hash_int
from minemesis.systems.simulation import Simulation
from minemesis.core.types import EventType
from minemesis.core.history_printer import (
    get_deepest_conflict_chain_metrics,
    get_deepest_causal_chain_metrics,
    export_causal_graph_mermaid,
)
from viewer.export import export_story_to_text


SEEDS_BY_SETTLEMENT = {
    3: 1002,
    4: 1020,
    5: 1000,
    6: 1003,
    7: 1005,
}


def run_showcases():
    os.makedirs("reports", exist_ok=True)
    showcase_runs = {}

    print("=== Generating Milestone 0.5.3 Stratified Showcases (3..7 Sites) ===")

    for s_count, w_seed in sorted(SEEDS_BY_SETTLEMENT.items()):
        h_seed = keyed_hash_int(w_seed, "showcase_history", s_count, 0)
        pair = SeedPair(world=w_seed, history=h_seed)

        print(f"\nSimulating {s_count} Settlements (World: {w_seed}, History: {h_seed}, Code: {pair.encode()})...")
        sim = Simulation(seed=pair, enable_religion=True, enable_lore=True)
        init_living = len(sim.living_characters)

        sim.run_years(100)
        all_events = sim.event_log.all_events()
        final_living = len(sim.living_characters)
        total_births = sum(1 for e in all_events if e.type == EventType.BIRTH)
        total_deaths = sum(1 for e in all_events if e.type == EventType.DEATH)

        # Demographic Conservation Check
        expected = init_living + total_births - total_deaths
        reconciled = (final_living == expected)
        assert reconciled, f"Demographic leak: {final_living} != {expected}"
        print(f"  [OK] Conservation verified: {init_living} + {total_births} births - {total_deaths} deaths = {final_living} living")

        feuds = sum(1 for e in all_events if e.type == EventType.FEUD)
        wrongful = sum(1 for e in all_events if e.type == EventType.FEUD and e.payload.get("is_wrongful"))
        revenge = sum(1 for e in all_events if e.type == EventType.DEATH and e.payload.get("cause_of_death") == "Revenge")
        raids = sum(1 for e in all_events if e.type == EventType.RAID)
        famines = sum(1 for e in all_events if e.type == EventType.FAMINE)
        crises = sum(1 for e in all_events if e.type == EventType.SUCCESSION_CRISIS)
        peaces = sum(1 for e in all_events if e.type == EventType.PEACE)
        books = sum(1 for e in all_events if e.type == EventType.BOOK_WRITTEN)

        best_c_id, conflict_depth, c_distinct = get_deepest_conflict_chain_metrics(sim.event_log)
        best_l_id, longest_depth, l_distinct = get_deepest_causal_chain_metrics(sim.event_log)

        run_info = {
            "world_seed": w_seed,
            "history_seed": h_seed,
            "chronicle_seed": h_seed,
            "pair_code": pair.encode(),
            "settlement_count": len(sim.settlements),
            "initial_living": init_living,
            "final_living": final_living,
            "total_births": total_births,
            "total_deaths": total_deaths,
            "reconciled": reconciled,
            "survived": final_living > 0,
            "total_events": len(all_events),
            "feuds": feuds,
            "wrongful_grudges": wrongful,
            "revenge_killings": revenge,
            "raids": raids,
            "famines": famines,
            "succession_crises": crises,
            "peaces": peaces,
            "books": books,
            "conflict_causal_depth": conflict_depth,
            "conflict_distinct_types": c_distinct,
            "longest_causal_depth": longest_depth,
            "longest_distinct_types": l_distinct,
            "sim_instance": sim,
            "best_conflict_event_id": best_c_id,
        }
        showcase_runs[s_count] = run_info

        # Export readable showcase text
        txt_file = f"reports/m053_showcase_{s_count}sets.txt"
        txt = export_story_to_text(
            events=all_events,
            event_log=sim.event_log,
            characters=sim.characters,
            settlements=sim.settlements,
            title=f"Minemesis World History - {s_count} Settlements (World: {w_seed}, History: {h_seed})",
            include_causes=True,
        )
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(txt)
        print(f"  Exported history to: {txt_file} ({len(all_events)} events, {len(sim.characters)} characters)")

    # Export deepest conflict DAG
    all_runs = list(showcase_runs.values())
    all_runs.sort(key=lambda r: -r["conflict_causal_depth"])
    best_run = all_runs[0]
    best_sim = best_run["sim_instance"]
    mermaid_path = "reports/m053_showcase_deepest_dag.mmd"
    with open(mermaid_path, "w", encoding="utf-8") as f:
        f.write(export_causal_graph_mermaid(best_sim.event_log, best_run["best_conflict_event_id"]))
    print(f"\nExported deepest conflict DAG to: {mermaid_path}")

    # Export JSON validation summary
    validation_summary = {
        "milestone": "0.5.3",
        "description": "Stratified showcase verification across 3..7 settlements with demographic conservation and DAG export.",
        "showcase_runs": {
            str(k): {
                "world_seed": v["world_seed"],
                "history_seed": v["history_seed"],
                "chronicle_seed": v["chronicle_seed"],
                "pair_code": v["pair_code"],
                "settlement_count": v["settlement_count"],
                "initial_living": v["initial_living"],
                "final_living": v["final_living"],
                "total_births": v["total_births"],
                "total_deaths": v["total_deaths"],
                "reconciled": v["reconciled"],
                "survived": v["survived"],
                "total_events": v["total_events"],
                "feuds": v["feuds"],
                "wrongful_grudges": v["wrongful_grudges"],
                "revenge_killings": v["revenge_killings"],
                "raids": v["raids"],
                "famines": v["famines"],
                "succession_crises": v["succession_crises"],
                "peaces": v["peaces"],
                "books": v["books"],
                "conflict_causal_depth": v["conflict_causal_depth"],
                "longest_causal_depth": v["longest_causal_depth"],
            }
            for k, v in showcase_runs.items()
        },
    }

    summary_file = "reports/m053_validation_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(validation_summary, f, indent=2)
    print(f"Saved validation summary to: {summary_file}")
    print("\nAll 5 showcase histories successfully generated and reconciled.")


if __name__ == "__main__":
    run_showcases()
