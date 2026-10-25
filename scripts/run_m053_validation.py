"""
Milestone 0.5.3 200-Pair Validation Script.

Executes:
- 100 Training Pairs (World Seeds 5000..5099, paired Chronicle Seeds)
- 100 Hold-out D Pairs (World Seeds 7000..7099, paired Chronicle Seeds)

Verifies:
1. Exact demographic conservation (living = initial + births - deaths).
2. World survival rate (target >= 80%).
3. Stratified distributions by settlement count (3, 4, 5, 6, 7 sites).
4. Causal depth and conflict chain distributions.
5. Exports 5 showcase readable histories across settlement counts (3..7).
6. Exports reports/m053_validation_summary.json.
"""

from __future__ import annotations
import json
import math
import os
import sys
from collections import Counter, defaultdict
from typing import Any

# Ensure workspace root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from minemesis.core.seed import SeedPair
from minemesis.core.rng import keyed_hash_int
from minemesis.systems.simulation import Simulation
from minemesis.core.types import EventType
from minemesis.core.history_printer import (
    get_deepest_conflict_chain_metrics,
    get_longest_conflict_path,
    get_deepest_causal_chain_metrics,
    export_causal_graph_mermaid,
)
from viewer.export import export_story_to_text


def percentile(data: list[float], pct: float) -> float:
    """Computes percentile from sorted list."""
    if not data:
        return 0.0
    k = (len(data) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(data[int(k)])
    d0 = data[int(f)] * (c - k)
    d1 = data[int(c)] * (k - f)
    return round(float(d0 + d1), 2)


def compute_distribution(vals: list[float | int]) -> dict[str, float]:
    """Computes mean, median, p10, p90, min, max."""
    if not vals:
        return {"mean": 0.0, "median": 0.0, "p10": 0.0, "p90": 0.0, "min": 0.0, "max": 0.0}
    sorted_vals = sorted(float(v) for v in vals)
    mean_val = round(sum(sorted_vals) / len(sorted_vals), 2)
    med_val = percentile(sorted_vals, 50)
    p10 = percentile(sorted_vals, 10)
    p90 = percentile(sorted_vals, 90)
    return {
        "mean": mean_val,
        "median": med_val,
        "p10": p10,
        "p90": p90,
        "min": sorted_vals[0],
        "max": sorted_vals[-1],
    }


def audit_pair(pair: SeedPair, years: int = 100) -> dict[str, Any]:
    sim = Simulation(seed=pair, enable_religion=True, enable_lore=True)
    initial_living = len(sim.living_characters)
    settlement_count = len(sim.settlements)

    for _ in range(years * 12):
        if len(sim.living_characters) == 0:
            break
        sim.step_month()

    all_events = sim.event_log.all_events()
    final_living = len(sim.living_characters)
    total_births = sum(1 for e in all_events if e.type == EventType.BIRTH)
    total_deaths = sum(1 for e in all_events if e.type == EventType.DEATH)

    # 1. Demographic Conservation Check
    expected_living = initial_living + total_births - total_deaths
    reconciled = (final_living == expected_living)
    survived = (final_living > 0)

    # 2. Drama metrics
    feuds = sum(1 for e in all_events if e.type == EventType.FEUD)
    wrongful = sum(1 for e in all_events if e.type == EventType.FEUD and e.payload.get("is_wrongful"))
    revenge = sum(1 for e in all_events if e.type == EventType.DEATH and e.payload.get("cause_of_death") == "Revenge")
    raids = sum(1 for e in all_events if e.type == EventType.RAID)
    famines = sum(1 for e in all_events if e.type == EventType.FAMINE)
    crises = sum(1 for e in all_events if e.type == EventType.SUCCESSION_CRISIS)
    peaces = sum(1 for e in all_events if e.type == EventType.PEACE)
    books = sum(1 for e in all_events if e.type == EventType.BOOK_WRITTEN)

    # 3. Conflict chain depth & longest causal depth
    best_c_id, conflict_depth, c_distinct = get_deepest_conflict_chain_metrics(sim.event_log)
    best_l_id, longest_depth, l_distinct = get_deepest_causal_chain_metrics(sim.event_log)

    # 4. Event shares
    event_counts = Counter(e.type.value for e in all_events)
    total_evts = len(all_events) or 1
    event_shares = {k: round((v / total_evts) * 100, 2) for k, v in event_counts.items()}

    return {
        "world_seed": pair.world,
        "history_seed": pair.history,
        "chronicle_seed": pair.chronicle,  # backward compatibility
        "pair_code": pair.encode(),
        "settlement_count": settlement_count,
        "initial_living": initial_living,
        "final_living": final_living,
        "total_births": total_births,
        "total_deaths": total_deaths,
        "reconciled": reconciled,
        "survived": survived,
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
        "event_shares": event_shares,
        "sim_instance": sim,
    }


def run_cohort(pairs: list[SeedPair], label: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    print(f"\n--- Running {label} ({len(pairs)} pairs) ---")
    results = []
    for idx, pair in enumerate(pairs, 1):
        r = audit_pair(pair)
        results.append(r)
        if idx % 20 == 0 or idx == len(pairs):
            reconciled_so_far = sum(1 for item in results if item["reconciled"])
            survived_so_far = sum(1 for item in results if item["survived"])
            print(f"  Processed {idx:3d}/{len(pairs)} pairs | Reconciled: {reconciled_so_far}/{idx} | Survived: {survived_so_far}/{idx}")

    # Aggregate metrics
    total_reconciled = sum(1 for r in results if r["reconciled"])
    total_survived = sum(1 for r in results if r["survived"])
    c_depths = [r["conflict_causal_depth"] for r in results]
    l_depths = [r["longest_causal_depth"] for r in results]
    feuds = [r["feuds"] for r in results]
    revenge = [r["revenge_killings"] for r in results]
    raids = [r["raids"] for r in results]
    famines = [r["famines"] for r in results]
    crises = [r["succession_crises"] for r in results]
    peaces = [r["peaces"] for r in results]
    pop_final = [r["final_living"] for r in results]

    # Global event share across cohort
    cohort_counts = Counter()
    for r in results:
        for et, cnt in Counter(e.type.value for e in r["sim_instance"].event_log.all_events()).items():
            cohort_counts[et] += cnt
    cohort_total = sum(cohort_counts.values()) or 1
    cohort_shares = {k: round((v / cohort_total) * 100, 2) for k, v in cohort_counts.most_common()}

    summary = {
        "cohort": label,
        "pairs_tested": len(pairs),
        "reconciliation_rate": round(total_reconciled / len(pairs), 4),
        "world_survival_rate": round(total_survived / len(pairs), 4),
        "conflict_causal_depth": compute_distribution(c_depths),
        "longest_causal_depth": compute_distribution(l_depths),
        "feuds": compute_distribution(feuds),
        "revenge_killings": compute_distribution(revenge),
        "raids": compute_distribution(raids),
        "famines": compute_distribution(famines),
        "succession_crises": compute_distribution(crises),
        "peaces": compute_distribution(peaces),
        "final_population": compute_distribution(pop_final),
        "event_shares": cohort_shares,
    }

    return results, summary


def main():
    os.makedirs("reports", exist_ok=True)
    print("=================================================================")
    print(" MINEMESIS MILESTONE 0.5.3: 200-PAIR VALIDATION SUITE")
    print("=================================================================")

    # 1. Generate 100 Training Pairs
    training_pairs = []
    for i in range(100):
        w = 5000 + i
        c = keyed_hash_int(w, "training_chronicle", i, 0)
        training_pairs.append(SeedPair(world=w, chronicle=c))

    # 2. Generate 100 Hold-out D Pairs
    holdout_d_pairs = []
    for i in range(100):
        w = 7000 + i
        c = keyed_hash_int(w, "holdout_d_chronicle", i, 0)
        holdout_d_pairs.append(SeedPair(world=w, chronicle=c))

    # Run Training Cohort
    train_results, train_summary = run_cohort(training_pairs, "Training Cohort (100 pairs)")

    # Run Hold-out D Cohort
    holdout_results, holdout_summary = run_cohort(holdout_d_pairs, "Hold-out D Cohort (100 pairs)")

    # 3. Stratification of Hold-out D by Settlement Count (3..7)
    stratified: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in holdout_results:
        stratified[r["settlement_count"]].append(r)

    stratified_metrics = {}
    print("\n=================================================================")
    print(" HOLD-OUT D STRATIFICATION BY SETTLEMENT COUNT")
    print("=================================================================")
    print(" Sites | Runs | Surv% | Mean Pop (Init -> End) | Med Feuds | Med Raids | Med Famines | Med C-Depth")
    print("-------+------+-------+------------------------+-----------+-----------+-------------+------------")

    for s_count in sorted(stratified.keys()):
        cohort_s = stratified[s_count]
        n_runs = len(cohort_s)
        surv_cnt = sum(1 for r in cohort_s if r["survived"])
        surv_pct = round(surv_cnt / n_runs * 100, 1)

        init_pops = [r["initial_living"] for r in cohort_s]
        end_pops = [r["final_living"] for r in cohort_s]
        feuds = [r["feuds"] for r in cohort_s]
        raids = [r["raids"] for r in cohort_s]
        famines = [r["famines"] for r in cohort_s]
        c_depths = [r["conflict_causal_depth"] for r in cohort_s]

        m_init = round(sum(init_pops) / n_runs, 1)
        m_end = round(sum(end_pops) / n_runs, 1)

        f_dist = compute_distribution(feuds)
        r_dist = compute_distribution(raids)
        fam_dist = compute_distribution(famines)
        c_dist = compute_distribution(c_depths)

        stratified_metrics[str(s_count)] = {
            "runs": n_runs,
            "survival_rate": surv_pct,
            "initial_population": compute_distribution(init_pops),
            "final_population": compute_distribution(end_pops),
            "feuds": f_dist,
            "raids": r_dist,
            "famines": fam_dist,
            "conflict_causal_depth": c_dist,
        }

        print(f"   {s_count:2d}  | {n_runs:4d} | {surv_pct:4.1f}% | {m_init:5.1f} -> {m_end:5.1f}        | {f_dist['median']:9.1f} | {r_dist['median']:9.1f} | {fam_dist['median']:11.1f} | {c_dist['median']:10.1f}")

    # 4. Export 5 Showcase Histories across settlement counts (3, 4, 5, 6, 7)
    showcase_runs: dict[int, dict[str, Any]] = {}
    for s_count in [3, 4, 5, 6, 7]:
        candidates = stratified.get(s_count, [])
        if candidates:
            # Pick run with highest conflict causal depth
            candidates.sort(key=lambda r: (-r["conflict_causal_depth"], -r["feuds"]))
            showcase_runs[s_count] = candidates[0]

    for s_count, run in showcase_runs.items():
        filename = f"reports/m053_showcase_{s_count}sets.txt"
        sim = run["sim_instance"]
        txt = export_story_to_text(
            events=sim.event_log.all_events(),
            event_log=sim.event_log,
            characters=sim.characters,
            settlements=sim.settlements,
            title=f"Minemesis World History - {s_count} Settlements (World: {run['world_seed']}, History: {run['history_seed']})",
            include_causes=True,
        )
        with open(filename, "w", encoding="utf-8") as f:
            f.write(txt)
        print(f"Exported {s_count}-settlement showcase chronicle to: {filename}")

    # Export Mermaid diagram for highest depth showcase
    all_showcase = list(showcase_runs.values())
    all_showcase.sort(key=lambda r: -r["conflict_causal_depth"])
    best_showcase = all_showcase[0]
    best_sim = best_showcase["sim_instance"]
    mermaid_path = "reports/m053_showcase_deepest_dag.mmd"
    best_evt_id, _, _ = get_deepest_conflict_chain_metrics(best_sim.event_log)
    with open(mermaid_path, "w", encoding="utf-8") as f:
        f.write(export_causal_graph_mermaid(best_sim.event_log, best_evt_id))
    print(f"Exported deepest conflict DAG to: {mermaid_path}")

    # 5. Write full JSON validation summary
    validation_summary = {
        "milestone": "0.5.3",
        "training": train_summary,
        "holdout_d": holdout_summary,
        "holdout_d_stratified": stratified_metrics,
        "showcase_runs": {
            str(k): {
                "world_seed": v["world_seed"],
                "history_seed": v["history_seed"],
                "chronicle_seed": v["chronicle_seed"],
                "pair_code": v["pair_code"],
                "settlement_count": v["settlement_count"],
                "conflict_causal_depth": v["conflict_causal_depth"],
                "feuds": v["feuds"],
                "raids": v["raids"],
                "famines": v["famines"],
                "total_events": v["total_events"],
            }
            for k, v in showcase_runs.items()
        },
    }

    summary_file = "reports/m053_validation_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(validation_summary, f, indent=2)
    print(f"\nSaved full validation summary to: {summary_file}")
    print("=================================================================")


if __name__ == "__main__":
    main()
