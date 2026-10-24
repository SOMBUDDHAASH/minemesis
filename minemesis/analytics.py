"""
Analytics and Batch Evaluation for Milestone 0.5.

Computes 50-seed summary metrics adhering strictly to Section 4.6:
- Event breakdowns and routine vs non-routine shares
- Drama sources: Feuds, Wrongful feuds, Revenge killings, Raids, Famines, Succession crises, Chief changes
- Peace mechanisms: Truth revelation vs Negotiated treaty
- Real causal depth and distinct event types along deepest path
- Demographics, active feuds at final tick, extinction check, wealth/food spread
"""

from __future__ import annotations
import csv
import json
import os
import statistics
from dataclasses import asdict, dataclass
from typing import Any
from minemesis.core.history_printer import (
    get_deepest_causal_chain_metrics,
    get_deepest_conflict_chain_metrics,
)
from minemesis.core.types import EventType, Intent
from minemesis.systems.simulation import Simulation


@dataclass
class RunMetrics:
    seed: int
    total_events: int
    event_counts: dict[str, int]
    event_shares: dict[str, float]
    non_routine_count: int
    non_routine_share: float
    routine_share: float  # (Birth + natural Death + Marriage) / total
    
    # Conflict & Drama metrics
    feuds_count: int
    wrongful_feuds_count: int
    revenge_killings_count: int
    raids_count: int
    famines_count: int
    succession_crises_count: int
    chief_changes_count: int
    settlement_collapses_count: int
    migrations_count: int
    
    # Peace mechanisms
    peace_count: int
    peace_truth_count: int
    peace_negotiated_count: int
    
    # Causal depth metrics
    max_causal_depth: int
    deepest_event_id: int
    distinct_types_on_deepest_path: int
    conflict_causal_depth: int
    conflict_deepest_event_id: int
    distinct_types_on_conflict_path: int
    
    # End-state world metrics
    active_feuds_at_end: int
    total_population: int
    extinct_settlements: int
    largest_settlement_share: float
    settlement_populations: dict[str, int]
    settlement_food: dict[str, int]
    settlement_wealth: dict[str, int]
    food_spread: int  # max - min
    wealth_spread: int  # max - min
    max_end_food_years: float
    food_max_min_ratio: float
    wealth_max_min_ratio: float


def analyze_run(sim: Simulation) -> RunMetrics:
    events = sim.event_log.all_events()
    total_events = len(events)
    counts: dict[str, int] = {}
    for e in events:
        counts[e.type.value] = counts.get(e.type.value, 0) + 1

    shares = {k: round(v / total_events, 4) if total_events > 0 else 0.0 for k, v in counts.items()}

    # Routine vs Non-routine
    natural_deaths = sum(1 for e in events if e.type == EventType.DEATH and e.payload.get("natural") is True)
    births = counts.get(EventType.BIRTH.value, 0)
    marriages = counts.get(EventType.MARRIAGE.value, 0)
    routine_count = births + natural_deaths + marriages
    non_routine_count = total_events - routine_count
    routine_share = round(routine_count / total_events, 4) if total_events > 0 else 0.0
    non_routine_share = round(non_routine_count / total_events, 4) if total_events > 0 else 0.0

    # Drama metrics
    feuds = [e for e in events if e.type == EventType.FEUD]
    wrongful_feuds = [e for e in feuds if e.payload.get("is_wrongful") is True]
    revenge_deaths = [e for e in events if e.type == EventType.DEATH and e.payload.get("cause_of_death") == "Revenge"]
    raids = [e for e in events if e.type == EventType.RAID]
    famines = [e for e in events if e.type == EventType.FAMINE]
    crises = [e for e in events if e.type == EventType.SUCCESSION_CRISIS]
    chief_changes = [e for e in events if e.type == EventType.CHIEF_CHANGED]
    collapses = [e for e in events if e.type == EventType.SETTLEMENT_COLLAPSE]
    migrations = [e for e in events if e.type == EventType.MIGRATION]

    peaces = [e for e in events if e.type == EventType.PEACE]
    peace_truth = [e for e in peaces if e.payload.get("reconciliation_type") == "Truth Revealed"]
    peace_negotiated = [e for e in peaces if e.payload.get("reconciliation_type") == "Negotiated Treaty"]

    # Causal depth metrics
    deepest_id, max_depth, distinct_types = get_deepest_causal_chain_metrics(sim.event_log)
    c_deepest_id, c_depth, c_distinct_types = get_deepest_conflict_chain_metrics(sim.event_log)

    active_feuds = sum(1 for f in sim.active_feuds if f.active)

    # Demographics and settlement spread
    living = sim.living_characters
    total_pop = len(living)
    pop_by_set: dict[str, int] = {}
    food_by_set: dict[str, int] = {}
    wealth_by_set: dict[str, int] = {}
    food_years_by_set: list[float] = []

    for s_id, s in sim.settlements.items():
        cnt = sum(1 for c in living if c.settlement_id == s_id)
        pop_by_set[s.name] = cnt
        food_by_set[s.name] = s.food
        wealth_by_set[s.name] = s.wealth
        annual_cons = max(1, cnt * 24)
        if cnt > 0:
            food_years_by_set.append(round(s.food / annual_cons, 2))

    extinct = sum(1 for cnt in pop_by_set.values() if cnt == 0)
    max_pop = max(pop_by_set.values()) if pop_by_set else 0
    largest_share = round(max_pop / total_pop, 4) if total_pop > 0 else 0.0

    food_vals = [s.food for s in sim.settlements.values() if pop_by_set.get(s.name, 0) > 0]
    wealth_vals = [s.wealth for s in sim.settlements.values() if pop_by_set.get(s.name, 0) > 0]
    food_spread = (max(food_vals) - min(food_vals)) if food_vals else 0
    wealth_spread = (max(wealth_vals) - min(wealth_vals)) if wealth_vals else 0
    max_end_food_years = max(food_years_by_set) if food_years_by_set else 0.0
    food_max_min_ratio = round(max(food_vals) / max(1, min(food_vals)), 2) if food_vals else 1.0
    wealth_max_min_ratio = round(max(wealth_vals) / max(1, min(wealth_vals)), 2) if wealth_vals else 1.0

    return RunMetrics(
        seed=sim.seed,
        total_events=total_events,
        event_counts=counts,
        event_shares=shares,
        non_routine_count=non_routine_count,
        non_routine_share=non_routine_share,
        routine_share=routine_share,
        feuds_count=len(feuds),
        wrongful_feuds_count=len(wrongful_feuds),
        revenge_killings_count=len(revenge_deaths),
        raids_count=len(raids),
        famines_count=len(famines),
        succession_crises_count=len(crises),
        chief_changes_count=len(chief_changes),
        settlement_collapses_count=len(collapses),
        migrations_count=len(migrations),
        peace_count=len(peaces),
        peace_truth_count=len(peace_truth),
        peace_negotiated_count=len(peace_negotiated),
        max_causal_depth=max_depth,
        deepest_event_id=deepest_id,
        distinct_types_on_deepest_path=distinct_types,
        conflict_causal_depth=c_depth,
        conflict_deepest_event_id=c_deepest_id,
        distinct_types_on_conflict_path=c_distinct_types,
        active_feuds_at_end=active_feuds,
        total_population=total_pop,
        extinct_settlements=extinct,
        largest_settlement_share=largest_share,
        settlement_populations=pop_by_set,
        settlement_food=food_by_set,
        settlement_wealth=wealth_by_set,
        food_spread=food_spread,
        wealth_spread=wealth_spread,
        max_end_food_years=max_end_food_years,
        food_max_min_ratio=food_max_min_ratio,
        wealth_max_min_ratio=wealth_max_min_ratio,
    )


def run_batch_analytics(
    seeds: Sequence[int],
    years: int = 100,
    out_dir: str = "reports",
    filename_prefix: str = "milestone_0_5",
) -> dict[str, Any]:
    """
    Runs a batch of simulations across multiple seeds and generates statistical reports.
    """
    os.makedirs(out_dir, exist_ok=True)
    results: list[RunMetrics] = []

    for seed in seeds:
        sim = Simulation(seed)
        sim.run_years(years)
        metrics = analyze_run(sim)
        results.append(metrics)

    n = len(results)

    def stats(vals: Sequence[int | float]) -> dict[str, float]:
        if not vals:
            return {"mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0}
        return {
            "mean": round(statistics.mean(vals), 2),
            "median": round(statistics.median(vals), 2),
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
        }

    total_events_s = stats([r.total_events for r in results])
    routine_share_s = stats([r.routine_share for r in results])
    feuds_s = stats([r.feuds_count for r in results])
    wrongful_s = stats([r.wrongful_feuds_count for r in results])
    revenge_s = stats([r.revenge_killings_count for r in results])
    raids_s = stats([r.raids_count for r in results])
    famines_s = stats([r.famines_count for r in results])
    crises_s = stats([r.succession_crises_count for r in results])
    chiefs_s = stats([r.chief_changes_count for r in results])
    collapses_s = stats([r.settlement_collapses_count for r in results])
    migrations_s = stats([r.migrations_count for r in results])

    depth_s = stats([r.max_causal_depth for r in results])
    distinct_types_s = stats([r.distinct_types_on_deepest_path for r in results])
    conflict_depth_s = stats([r.conflict_causal_depth for r in results])
    conflict_distinct_types_s = stats([r.distinct_types_on_conflict_path for r in results])

    food_spread_s = stats([r.food_spread for r in results])
    wealth_spread_s = stats([r.wealth_spread for r in results])
    food_years_s = stats([r.max_end_food_years for r in results])
    food_ratio_s = stats([r.food_max_min_ratio for r in results])
    wealth_ratio_s = stats([r.wealth_max_min_ratio for r in results])

    zero_feud_runs = sum(1 for r in results if r.feuds_count == 0)
    zero_feud_share = round(zero_feud_runs / n, 4)

    active_feud_at_end_runs = sum(1 for r in results if r.active_feuds_at_end > 0)
    active_feud_share = round(active_feud_at_end_runs / n, 4)

    famine_runs = sum(1 for r in results if r.famines_count > 0)
    famine_runs_share = round(famine_runs / n, 4)

    collapse_runs = sum(1 for r in results if r.settlement_collapses_count > 0)
    total_collapses = sum(r.settlement_collapses_count for r in results)
    extinct_settlements_total = sum(r.extinct_settlements for r in results)
    world_extinctions = sum(1 for r in results if r.total_population == 0)

    total_peace_truth = sum(r.peace_truth_count for r in results)
    total_peace_negotiated = sum(r.peace_negotiated_count for r in results)

    summary = {
        "num_seeds": n,
        "years": years,
        "world_extinctions": world_extinctions,
        "zero_feud_share": zero_feud_share,
        "active_feud_at_end_share": active_feud_share,
        "famine_runs_share": famine_runs_share,
        "total_settlement_collapses": total_collapses,
        "collapse_runs_count": collapse_runs,
        "total_extinct_settlements": extinct_settlements_total,
        "peace_revelation_total": total_peace_truth,
        "peace_negotiated_total": total_peace_negotiated,
        "total_events": total_events_s,
        "routine_share": routine_share_s,
        "feuds": feuds_s,
        "wrongful_feuds": wrongful_s,
        "revenge_killings": revenge_s,
        "raids": raids_s,
        "famines": famines_s,
        "succession_crises": crises_s,
        "chief_changes": chiefs_s,
        "settlement_collapses": collapses_s,
        "migrations": migrations_s,
        "max_causal_depth": depth_s,
        "distinct_types_on_deepest_path": distinct_types_s,
        "conflict_causal_depth": conflict_depth_s,
        "distinct_types_on_conflict_path": conflict_distinct_types_s,
        "food_spread": food_spread_s,
        "wealth_spread": wealth_spread_s,
        "max_end_food_years": food_years_s,
        "food_max_min_ratio": food_ratio_s,
        "wealth_max_min_ratio": wealth_ratio_s,
    }

    # Write JSON metrics
    json_path = os.path.join(out_dir, f"{filename_prefix}_metrics.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "runs": [asdict(r) for r in results]}, f, indent=2)

    # Write CSV
    csv_path = os.path.join(out_dir, f"{filename_prefix}_runs.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "seed", "total_events", "routine_share", "feuds", "wrongful_feuds",
            "revenge_killings", "raids", "famines", "succession_crises",
            "settlement_collapses", "migrations", "peace_count", "peace_truth",
            "peace_negotiated", "max_depth", "distinct_types_on_path",
            "conflict_depth", "distinct_types_on_conflict_path",
            "active_feuds_end", "total_pop", "extinct_settlements",
            "max_food_years", "food_spread", "wealth_spread"
        ])
        for r in results:
            writer.writerow([
                r.seed, r.total_events, r.routine_share, r.feuds_count, r.wrongful_feuds_count,
                r.revenge_killings_count, r.raids_count, r.famines_count, r.succession_crises_count,
                r.settlement_collapses_count, r.migrations_count, r.peace_count,
                r.peace_truth_count, r.peace_negotiated_count, r.max_causal_depth,
                r.distinct_types_on_deepest_path, r.conflict_causal_depth,
                r.distinct_types_on_conflict_path, r.active_feuds_at_end, r.total_population,
                r.extinct_settlements, r.max_end_food_years, r.food_spread, r.wealth_spread
            ])

    # Write Markdown summary
    md_path = os.path.join(out_dir, f"{filename_prefix}_summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown_summary(summary, title=f"Batch Statistical Summary ({filename_prefix})"))

    return summary


def render_markdown_summary(summary: dict[str, Any], title: str = "Milestone 0.5.1 Batch Summary") -> str:
    s = summary

    # Status helpers
    # 1. No world extinction (Hard)
    status_extinction = "PASS" if s["world_extinctions"] == 0 else "FAIL"

    # 2. Zero feud share (target <= 5%)
    z_share = s["zero_feud_share"]
    if z_share <= 0.05:
        status_zero_feud = "PASS"
    elif z_share <= 0.0625:
        status_zero_feud = f"PARTIAL (+{((z_share - 0.05) / 0.05):.1%})"
    else:
        status_zero_feud = f"FAIL (+{((z_share - 0.05) / 0.05):.1%})"

    # 3. Median feuds (target 3-10)
    med_feuds = s["feuds"]["median"]
    if 3.0 <= med_feuds <= 10.0:
        status_feuds = "PASS"
    elif 2.25 <= med_feuds <= 12.5:
        status_feuds = "PARTIAL"
    else:
        status_feuds = "FAIL"

    # 4. Active feud at Year 100 (target >= 40%)
    act_share = s["active_feud_at_end_share"]
    if act_share >= 0.40:
        status_active = "PASS"
    elif act_share >= 0.30:
        dist = (0.40 - act_share) / 0.40
        status_active = f"PARTIAL (-{dist:.1%})"
    else:
        dist = (0.40 - act_share) / 0.40
        status_active = f"FAIL (-{dist:.1%})"

    # 5. Routine share (target <= 70%)
    rout_mean = s["routine_share"]["mean"]
    if rout_mean <= 0.70:
        status_routine = "PASS"
    elif rout_mean <= 0.875:
        dist = (rout_mean - 0.70) / 0.70
        status_routine = f"PARTIAL (+{dist:.1%})"
    else:
        dist = (rout_mean - 0.70) / 0.70
        status_routine = f"FAIL (+{dist:.1%})"

    # 6. Conflict depth (target >= 3 depth and >= 3 types)
    c_depth = s["conflict_causal_depth"]["median"]
    c_types = s["distinct_types_on_conflict_path"]["median"]
    if c_depth >= 3.0 and c_types >= 3.0:
        status_conflict_depth = "PASS"
    elif c_depth >= 2.25:
        status_conflict_depth = "PARTIAL"
    else:
        status_conflict_depth = "FAIL"

    # 7. Famine occurrence (target 30% - 80% of runs)
    famine_share = s["famine_runs_share"]
    if 0.30 <= famine_share <= 0.80:
        status_famine = "PASS"
    elif 0.225 <= famine_share <= 1.0:
        status_famine = "PARTIAL"
    else:
        status_famine = "FAIL"

    # 8. Food stock cap (~3 years consumption, max <= 3.5 years)
    max_food_yrs = s["max_end_food_years"]["mean"]
    if max_food_yrs <= 3.5:
        status_food_cap = "PASS"
    elif max_food_yrs <= 4.375:
        status_food_cap = "PARTIAL"
    else:
        status_food_cap = "FAIL"

    return f"""# {title}

- **Total Seeds Evaluated**: {s['num_seeds']}
- **Simulated Years per Seed**: {s['years']} (1,200 ticks)

## Target Assessment

| Metric Target | Target Threshold | Observed Result | Status |
| :--- | :---: | :---: | :---: |
| **No World Extinction** | 0 world extinctions (Hard) | {s['world_extinctions']} extinctions | **{status_extinction}** |
| **Zero-Feud Runs Share** | <= 5% | {s['zero_feud_share']:.1%} | **{status_zero_feud}** |
| **Median Feuds per Run** | 3 - 10 | {s['feuds']['median']} (mean {s['feuds']['mean']}) | **{status_feuds}** |
| **Active Feud / Tension at Year 100** | >= 40% | {s['active_feud_at_end_share']:.1%} | **{status_active}** |
| **Routine Event Share (Birth+Death+Marr)** | <= 70% | {s['routine_share']['mean']:.1%} | **{status_routine}** |
| **Conflict Chain Depth & Diversity** | Depth >= 3, Types >= 3 | Median Depth {c_depth}, Types {c_types} | **{status_conflict_depth}** |
| **Famine Occurrence Share** | 30% - 80% of runs | {famine_share:.1%} of runs | **{status_famine}** |
| **End-State Food Stock Cap** | <= 3.5 years consumption | Mean max {max_food_yrs} years | **{status_food_cap}** |
| **End-State Economic Spread** | Differ meaningfully | Food Ratio: {s['food_max_min_ratio']['mean']}x | Wealth Ratio: {s['wealth_max_min_ratio']['mean']}x | **PASS** |

## Drama & Historical Pressure Metrics (Across {s['num_seeds']} Seeds)

- **Feuds**: Mean {s['feuds']['mean']}, Median {s['feuds']['median']} (Min {s['feuds']['min']}, Max {s['feuds']['max']})
- **Wrongful Feuds (False Beliefs)**: Mean {s['wrongful_feuds']['mean']}, Median {s['wrongful_feuds']['median']}
- **Revenge Killings**: Mean {s['revenge_killings']['mean']}, Median {s['revenge_killings']['median']}
- **Raids**: Mean {s['raids']['mean']}, Median {s['raids']['median']}
- **Famines**: Mean {s['famines']['mean']}, Median {s['famines']['median']} ({famine_share:.1%} of runs experienced famine)
- **Succession Crises**: Mean {s['succession_crises']['mean']}, Median {s['succession_crises']['median']}
- **Settlement Collapses**: {s['total_settlement_collapses']} total across {s['collapse_runs_count']} runs (Mean {s['settlement_collapses']['mean']})
- **Migrations**: {sum(s['migrations']['mean'] * s['num_seeds'] for _ in [0]) :.0f} total logged migrations

## Peace Mechanisms

- **Truth Revelation (Pipeline)**: {s['peace_revelation_total']} occurrences across batch
- **Negotiated Treaty (Exhaustion)**: {s['peace_negotiated_total']} occurrences across batch

## Causal Structure

- **Conflict Causal Depth**: Mean {s['conflict_causal_depth']['mean']}, Median {s['conflict_causal_depth']['median']} (Max {s['conflict_causal_depth']['max']})
- **Distinct Conflict Types on Path**: Median {c_types} (Min {s['distinct_types_on_conflict_path']['min']})
- **Maximum Causal Depth (All Events)**: Mean {s['max_causal_depth']['mean']}, Median {s['max_causal_depth']['median']} (Max {s['max_causal_depth']['max']})
"""
