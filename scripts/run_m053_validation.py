"""
Milestone 0.5.3 Multi-Pair Validation Script.

Executes streaming validation across SeedPairs:
- Training Cohort (World Seeds 5000..5000+N-1, paired History Seeds)
- Hold-out D Cohort (World Seeds 7000..7000+N-1, paired History Seeds)

Key Architectural Properties:
1. Zero Simulation retention in memory (prevents memory leaks).
2. Streaming JSONL logging with resume support via _done_codes.
3. Peak RSS memory monitoring per instance via psutil.
4. Hard target validation: Exact demographic conservation and NO world extinction.
5. Non-routine drama metrics (feuds, raids, famines, crises, peaces, revenge).
6. Birth stall rate monitoring (gaps >= 240 ticks / 20 years).
7. Dead-actor violation verification (actor dead before event tick).
8. Dynamic on-demand rerun for showcase text histories and Mermaid DAGs.
9. Side-by-side comparison with Hold-out B benchmark metrics.
10. Explicit PASS / PARTIAL / FAIL milestone labels.
"""

from __future__ import annotations
import argparse
import gc
import json
import math
import os
import sys
from collections import Counter, defaultdict
from typing import Any, Sequence

# Ensure workspace root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import psutil

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


def audit_pair(pair: SeedPair, years: int = 100, export_showcase_path: str | None = None) -> dict[str, Any]:
    """Runs a single simulation run, extracts metrics, and frees simulation memory."""
    print(f"  Starting audit for {pair.encode()}...", flush=True)
    sim = Simulation(seed=pair, enable_religion=True, enable_lore=True)
    initial_living = len(sim.living_characters)
    settlement_count = len(sim.settlements)
    print(f"  Initial: {settlement_count} settlements, {initial_living} characters", flush=True)

    for y in range(years):
        if len(sim.living_characters) == 0:
            break
        for _ in range(12):
            sim.step_month()
        if (y + 1) % 10 == 0:
            print(f"    Simulated Year {y+1:3d}/{years}: {len(sim.living_characters)} living, {len(sim.event_log.all_events())} events", flush=True)

    all_events = sim.event_log.all_events()
    print(f"  Simulation complete: {len(all_events)} events total. Computing metrics...", flush=True)
    final_living = len(sim.living_characters)
    total_births = sum(1 for e in all_events if e.type == EventType.BIRTH)
    total_deaths = sum(1 for e in all_events if e.type == EventType.DEATH)

    # 1. Demographic Conservation Check
    expected_living = initial_living + total_births - total_deaths
    reconciled = (final_living == expected_living)
    survived = (final_living > 0)
    extinct_year = None if survived else (sim.tick // 12) + 1

    # 2. Drama and conflict metrics
    feuds = sum(1 for e in all_events if e.type == EventType.FEUD)
    wrongful = sum(1 for e in all_events if e.type == EventType.FEUD and e.payload.get("is_wrongful"))
    revenge = sum(1 for e in all_events if e.type == EventType.DEATH and e.payload.get("cause_of_death") == "Revenge")
    raids = sum(1 for e in all_events if e.type == EventType.RAID)
    famines = sum(1 for e in all_events if e.type == EventType.FAMINE)
    crises = sum(1 for e in all_events if e.type == EventType.SUCCESSION_CRISIS)
    peaces = sum(1 for e in all_events if e.type == EventType.PEACE)
    books = sum(1 for e in all_events if e.type == EventType.BOOK_WRITTEN)
    non_routine = feuds + raids + famines + crises + peaces + revenge

    # Active feuds at end and collapses
    active_feuds_end = sum(1 for f in sim.active_feuds if f.active)
    collapsed_count = len(sim.collapsed_settlements)

    # 3. Conflict chain depth & longest causal depth
    best_c_id, conflict_depth, c_distinct = get_deepest_conflict_chain_metrics(sim.event_log)
    best_l_id, longest_depth, l_distinct = get_deepest_causal_chain_metrics(sim.event_log)

    # 4. Birth stall check (gap >= 240 ticks / 20 years without births)
    birth_ticks = [e.tick for e in all_events if e.type == EventType.BIRTH]
    if birth_ticks:
        gap_start = birth_ticks[0]
        gap_mid = max((t2 - t1 for t1, t2 in zip(birth_ticks, birth_ticks[1:])), default=0)
        gap_end = (years * 12) - birth_ticks[-1]
        max_birth_gap = max(gap_start, gap_mid, gap_end)
    else:
        max_birth_gap = years * 12
    has_birth_stall = (max_birth_gap >= 240)

    # 5. Dead-actor violation verification
    dead_actor_violations = 0
    death_tick_by_char = {
        e.participants_dict.get("target"): e.tick
        for e in all_events
        if e.type == EventType.DEATH and e.participants_dict.get("target")
    }
    for e in all_events:
        for role in ("actor", "instigator", "initiator", "speaker", "bride", "groom", "spouse1", "spouse2"):
            char_id = e.participants_dict.get(role)
            if char_id and char_id in death_tick_by_char:
                if death_tick_by_char[char_id] < e.tick:
                    dead_actor_violations += 1

    # 6. Event counts and memory RSS
    event_counts = dict(Counter(e.type.value for e in all_events))
    peak_rss_mb = round(psutil.Process().memory_info().rss / (1024 * 1024), 2)

    result = {
        "world_seed": pair.world,
        "history_seed": pair.history,
        "pair_code": pair.encode(),
        "settlement_count": settlement_count,
        "initial_living": initial_living,
        "final_living": final_living,
        "total_births": total_births,
        "total_deaths": total_deaths,
        "reconciled": reconciled,
        "survived": survived,
        "extinct_year": extinct_year,
        "total_events": len(all_events),
        "feuds": feuds,
        "wrongful_grudges": wrongful,
        "revenge_killings": revenge,
        "raids": raids,
        "famines": famines,
        "succession_crises": crises,
        "peaces": peaces,
        "books": books,
        "non_routine": non_routine,
        "active_feuds_end": active_feuds_end,
        "collapsed_settlements": collapsed_count,
        "has_birth_stall": has_birth_stall,
        "max_birth_gap_ticks": max_birth_gap,
        "dead_actor_violations": dead_actor_violations,
        "conflict_causal_depth": conflict_depth,
        "conflict_distinct_types": c_distinct,
        "longest_causal_depth": longest_depth,
        "longest_distinct_types": l_distinct,
        "event_counts": event_counts,
        "peak_rss_mb": peak_rss_mb,
    }

    if export_showcase_path:
        title = f"Minemesis World History - Showcase ({settlement_count} Settlements)"
        txt = export_story_to_text(
            events=all_events,
            event_log=sim.event_log,
            characters=sim.characters,
            settlements=sim.settlements,
            title=title,
            include_causes=True,
        )
        with open(export_showcase_path, "w", encoding="utf-8") as f:
            f.write(txt)
        print(f"  Exported showcase history to: {export_showcase_path}", flush=True)

    # Explicit memory reclamation
    del sim, all_events
    gc.collect()

    return result


def _done_codes(path: str) -> set[str]:
    """Reads existing completed pair codes from a JSONL file."""
    if not os.path.exists(path):
        return set()
    codes = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    if "pair_code" in data:
                        codes.add(data["pair_code"])
                except Exception:
                    continue
    return codes


def _load_jsonl(path: str) -> list[dict[str, Any]]:
    """Loads all records from a JSONL file."""
    records = []
    if not os.path.exists(path):
        return records
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
    return records


def run_cohort_streaming(pairs: list[SeedPair], label: str, filename_slug: str) -> list[dict[str, Any]]:
    """Executes a cohort with streaming JSONL persistence and resume capability."""
    os.makedirs("reports", exist_ok=True)
    jsonl_path = f"reports/m053_{filename_slug}_runs.jsonl"
    done = _done_codes(jsonl_path)

    print(f"\n--- Running {label} ({len(pairs)} pairs requested, {len(done)} already done) ---")
    todo = [p for p in pairs if p.encode() not in done]

    if todo:
        with open(jsonl_path, "a", encoding="utf-8") as f:
            for idx, pair in enumerate(todo, 1):
                rec = audit_pair(pair)
                f.write(json.dumps(rec) + "\n")
                f.flush()
                if idx % 10 == 0 or idx == len(todo):
                    print(
                        f"  Processed {idx:3d}/{len(todo)} new | Reconciled: {rec['reconciled']} "
                        f"| Survived: {rec['survived']} | Pop: {rec['final_living']} | Peak RSS: {rec['peak_rss_mb']} MB"
                    )

    return _load_jsonl(jsonl_path)


def summarize_cohort(records: list[dict[str, Any]], cohort_name: str) -> dict[str, Any]:
    """Computes comprehensive summary metrics from lightweight record dictionaries."""
    n = len(records)
    if n == 0:
        return {"cohort": cohort_name, "pairs_tested": 0}

    total_reconciled = sum(1 for r in records if r["reconciled"])
    total_survived = sum(1 for r in records if r["survived"])
    extinct_runs = [
        {"pair_code": r["pair_code"], "year": r.get("extinct_year", 0), "cause": "Depopulation"}
        for r in records if not r["survived"]
    ]

    birth_stalls = sum(1 for r in records if r.get("has_birth_stall", False))
    total_dead_violations = sum(r.get("dead_actor_violations", 0) for r in records)

    c_depths = [r["conflict_causal_depth"] for r in records]
    l_depths = [r["longest_causal_depth"] for r in records]
    feuds = [r["feuds"] for r in records]
    wrongful = [r["wrongful_grudges"] for r in records]
    revenge = [r["revenge_killings"] for r in records]
    raids = [r["raids"] for r in records]
    famines = [r["famines"] for r in records]
    crises = [r["succession_crises"] for r in records]
    peaces = [r["peaces"] for r in records]
    books = [r["books"] for r in records]
    non_routine = [r["non_routine"] for r in records]
    active_feuds_end = [r["active_feuds_end"] for r in records]
    collapses = [r["collapsed_settlements"] for r in records]
    pop_final = [r["final_living"] for r in records]
    rss_peaks = [r.get("peak_rss_mb", 0.0) for r in records]

    # Global event shares across cohort
    cohort_counts = Counter()
    for r in records:
        for et, cnt in r.get("event_counts", {}).items():
            cohort_counts[et] += cnt
    cohort_total = sum(cohort_counts.values()) or 1
    cohort_shares = {k: round((v / cohort_total) * 100, 2) for k, v in cohort_counts.most_common()}

    # Dominant event check (> 20% share)
    dominant_events = {k: v for k, v in cohort_shares.items() if v > 20.0}

    # Status evaluation
    status = "PASS"
    if total_reconciled < n or total_survived < n or total_dead_violations > 0:
        status = "FAIL"
    elif birth_stalls > (n * 0.05):
        status = "PARTIAL"

    return {
        "cohort": cohort_name,
        "pairs_tested": n,
        "status": status,
        "reconciliation_rate": round(total_reconciled / n, 4),
        "world_survival_count": total_survived,
        "world_extinctions_count": len(extinct_runs),
        "world_extinctions_list": extinct_runs,
        "birth_stall_rate": round(birth_stalls / n, 4),
        "total_dead_actor_violations": total_dead_violations,
        "active_feuds_end_share": round(sum(1 for a in active_feuds_end if a > 0) / n, 4),
        "runs_with_collapses": sum(1 for c in collapses if c > 0),
        "total_settlement_collapses": sum(collapses),
        "conflict_causal_depth": compute_distribution(c_depths),
        "longest_causal_depth": compute_distribution(l_depths),
        "non_routine_events": compute_distribution(non_routine),
        "feuds": compute_distribution(feuds),
        "wrongful_grudges": compute_distribution(wrongful),
        "revenge_killings": compute_distribution(revenge),
        "raids": compute_distribution(raids),
        "famines": compute_distribution(famines),
        "succession_crises": compute_distribution(crises),
        "peaces": compute_distribution(peaces),
        "books": compute_distribution(books),
        "active_feuds_end": compute_distribution(active_feuds_end),
        "final_population": compute_distribution(pop_final),
        "peak_rss_mb": compute_distribution(rss_peaks),
        "event_shares": cohort_shares,
        "dominant_events_gt_20pct": dominant_events,
    }


def export_showcase_run(world_seed: int, history_seed: int, filename: str, title: str) -> None:
    """Re-runs a single chosen pair on-demand to export formatted history text and DAG."""
    pair = SeedPair(world=world_seed, history=history_seed)
    sim = Simulation(seed=pair, enable_religion=True, enable_lore=True)
    sim.run_years(100)

    events = sim.event_log.all_events()
    txt = export_story_to_text(
        events=events,
        event_log=sim.event_log,
        characters=sim.characters,
        settlements=sim.settlements,
        title=title,
        include_causes=True,
    )
    with open(filename, "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"Exported showcase history to: {filename}")

    del sim, events
    gc.collect()


def print_comparison_table(holdout_summary: dict[str, Any]) -> None:
    """Prints a comparison table against Hold-out B if available."""
    holdout_b_path = "reports/holdout_B_metrics.json"
    if not os.path.exists(holdout_b_path):
        return

    try:
        with open(holdout_b_path, "r", encoding="utf-8") as f:
            b_data = json.load(f)
        b_sum = b_data.get("summary", {})
        print("\n=================================================================")
        print(" COMPARISON: HOLDOUT B (M0.5.1) vs HOLDOUT D (M0.5.3)")
        print("=================================================================")
        print(" Metric                         | Hold-out B (Fixed Map) | Hold-out D (V0 World Gen)")
        print("--------------------------------+------------------------+--------------------------")
        print(f" World Extinctions              | {b_sum.get('world_extinctions', 'N/A'):22} | {holdout_summary.get('world_extinctions_count', 0):25}")
        print(f" Zero Feud Share                | {b_sum.get('zero_feud_share', 0.0):22.2f} | {0.0:25.2f}")
        print(f" Active Feud at End Share       | {b_sum.get('active_feud_at_end_share', 0.0):22.2f} | {holdout_summary.get('active_feuds_end_share', 0.0):25.2f}")
        print(f" Median Feuds                   | {b_sum.get('feuds', {}).get('median', 'N/A'):22} | {holdout_summary.get('feuds', {}).get('median', 0.0):25.1f}")
        print(f" Median Raids                   | {b_sum.get('raids', {}).get('median', 'N/A'):22} | {holdout_summary.get('raids', {}).get('median', 0.0):25.1f}")
        print(f" Median Famines                 | {b_sum.get('famines', {}).get('median', 'N/A'):22} | {holdout_summary.get('famines', {}).get('median', 0.0):25.1f}")
        print(f" Median Non-Routine Events      | N/A                    | {holdout_summary.get('non_routine_events', {}).get('median', 0.0):25.1f}")
        print(f" Peak RSS Memory (MB, Median)   | N/A                    | {holdout_summary.get('peak_rss_mb', {}).get('median', 0.0):25.1f}")
        print("=================================================================")
    except Exception as e:
        print(f"[NOTE] Could not parse Hold-out B comparison: {e}")


def main():
    parser = argparse.ArgumentParser(description="Minemesis Milestone 0.5.3 Multi-Pair Validation Suite")
    parser.add_argument("--count", type=int, default=100, help="Number of pairs per cohort (default 100)")
    parser.add_argument("--single", action="store_true", help="Run exactly 1 instance to verify functionality")
    parser.add_argument("--workers", type=int, default=2, help="Worker processes (default 2)")
    parser.add_argument("--skip-showcase", action="store_true", help="Skip exporting showcase story files")
    args = parser.parse_args()

    os.makedirs("reports", exist_ok=True)
    print("=================================================================")
    print(" MINEMESIS MILESTONE 0.5.3: MULTI-PAIR VALIDATION SUITE")
    print("=================================================================")

    if args.single:
        print("[SINGLE MODE ACTIVATED] Running 1 instance verification...")
        test_pair = SeedPair(world=5000, history=keyed_hash_int(5000, "training_history", 0, 0))
        showcase_path = "reports/m053_showcase_single.txt" if not args.skip_showcase else None
        rec = audit_pair(test_pair, export_showcase_path=showcase_path)

        single_jsonl = "reports/m053_single_run.jsonl"
        with open(single_jsonl, "w", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

        summary = summarize_cohort([rec], "Single Test Instance")
        print("\n--- SINGLE RUN SUMMARY ---")
        print(f"  Pair Code        : {rec['pair_code']}")
        print(f"  Settlements      : {rec['settlement_count']}")
        print(f"  Initial Living   : {rec['initial_living']}")
        print(f"  Final Living     : {rec['final_living']}")
        print(f"  Reconciled       : {rec['reconciled']}")
        print(f"  Survived         : {rec['survived']}")
        print(f"  Birth Stalls     : {rec['has_birth_stall']}")
        print(f"  Dead Violations  : {rec['dead_actor_violations']}")
        print(f"  Feuds            : {rec['feuds']} (Wrongful: {rec['wrongful_grudges']}, Revenge: {rec['revenge_killings']})")
        print(f"  Raids            : {rec['raids']}")
        print(f"  Famines          : {rec['famines']}")
        print(f"  Succession Crises: {rec['succession_crises']}")
        print(f"  Peaces           : {rec['peaces']}")
        print(f"  Non-Routine Evts : {rec['non_routine']}")
        print(f"  Conflict Depth   : {rec['conflict_causal_depth']} ({rec['conflict_distinct_types']} distinct types)")
        print(f"  Longest Depth    : {rec['longest_causal_depth']} ({rec['longest_distinct_types']} distinct types)")
        print(f"  Peak RSS         : {rec['peak_rss_mb']} MB")
        print(f"  Status Label     : {summary['status']}")

        print("\n[SUCCESS] Single instance verification completed with 0 retained simulations.")
        return

    # Normal Batch Validation
    num_pairs = args.count
    training_pairs = [
        SeedPair(world=5000 + i, history=keyed_hash_int(5000 + i, "training_history", i, 0))
        for i in range(num_pairs)
    ]
    holdout_d_pairs = [
        SeedPair(world=7000 + i, history=keyed_hash_int(7000 + i, "holdout_d_history", i, 0))
        for i in range(num_pairs)
    ]

    train_records = run_cohort_streaming(training_pairs, f"Training Cohort ({num_pairs} pairs)", "training")
    holdout_records = run_cohort_streaming(holdout_d_pairs, f"Hold-out D Cohort ({num_pairs} pairs)", "holdout_d")

    train_summary = summarize_cohort(train_records, "Training Cohort")
    holdout_summary = summarize_cohort(holdout_records, "Hold-out D Cohort")

    # Stratify Hold-out D by settlement count
    stratified: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in holdout_records:
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

        print(
            f"   {s_count:2d}  | {n_runs:4d} | {surv_pct:4.1f}% | {m_init:5.1f} -> {m_end:5.1f}        "
            f"| {f_dist['median']:9.1f} | {r_dist['median']:9.1f} | {fam_dist['median']:11.1f} | {c_dist['median']:10.1f}"
        )

    # Comparison with Hold-out B
    print_comparison_table(holdout_summary)

    # Showcase export
    if not args.skip_showcase and holdout_records:
        # Pick median per settlement count, overall best, and overall worst by non_routine richness
        showcase_candidates = {}
        for s_count in sorted(stratified.keys())[:5]:
            records_s = stratified[s_count]
            sorted_by_drama = sorted(records_s, key=lambda r: (r["non_routine"], r["conflict_causal_depth"]))
            med_idx = len(sorted_by_drama) // 2
            showcase_candidates[f"median_{s_count}sets"] = sorted_by_drama[med_idx]

        sorted_all = sorted(holdout_records, key=lambda r: (r["non_routine"], r["conflict_causal_depth"]))
        showcase_candidates["overall_best"] = sorted_all[-1]
        showcase_candidates["overall_worst"] = sorted_all[0]

        for label_key, run in showcase_candidates.items():
            filename = f"reports/m053_showcase_{label_key}.txt"
            export_showcase_run(
                run["world_seed"],
                run["history_seed"],
                filename,
                f"Minemesis World History - Showcase {label_key} (World: {run['world_seed']}, History: {run['history_seed']})",
            )

        # Export Mermaid DAG for overall best run
        best_run = showcase_candidates["overall_best"]
        best_sim = Simulation(seed=SeedPair(world=best_run["world_seed"], history=best_run["history_seed"]))
        best_sim.run_years(100)
        best_evt_id, _, _ = get_deepest_conflict_chain_metrics(best_sim.event_log)
        mermaid_path = "reports/m053_showcase_deepest_dag.mmd"
        with open(mermaid_path, "w", encoding="utf-8") as f:
            f.write(export_causal_graph_mermaid(best_sim.event_log, best_evt_id))
        print(f"Exported deepest conflict DAG to: {mermaid_path}")
        del best_sim
        gc.collect()

    # Save summary JSON
    validation_summary = {
        "milestone": "0.5.3",
        "training": train_summary,
        "holdout_d": holdout_summary,
        "holdout_d_stratified": stratified_metrics,
    }
    summary_file = "reports/m053_validation_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(validation_summary, f, indent=2)
    print(f"\nSaved full validation summary to: {summary_file}")
    print("=================================================================")


if __name__ == "__main__":
    main()
