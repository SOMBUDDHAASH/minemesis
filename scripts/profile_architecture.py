"""
Architecture profiling script for Minemesis.
Gathers empirical memory footprints, subsystem timings, and object graph metrics.
"""

from __future__ import annotations
import gc
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tracemalloc
import cProfile
import pstats
from collections import Counter
from dataclasses import is_dataclass, fields

from minemesis.core.seed import SeedPair
from minemesis.systems.simulation import Simulation
from minemesis.core.history_printer import (
    get_deepest_causal_chain_metrics,
    get_deepest_conflict_chain_metrics,
    format_causal_chain,
    export_causal_graph_mermaid,
)
from minemesis.core.types import EventType


def get_deep_size(obj, seen=None):
    """Recursively calculate the deep memory size of an object in bytes."""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)

    if isinstance(obj, dict):
        size += sum(get_deep_size(k, seen) + get_deep_size(v, seen) for k, v in obj.items())
    elif isinstance(obj, (list, tuple, set, frozenset)):
        size += sum(get_deep_size(i, seen) for i in obj)
    elif hasattr(obj, '__dict__'):
        size += get_deep_size(obj.__dict__, seen)
    elif hasattr(obj, '__slots__'):
        size += sum(get_deep_size(getattr(obj, s), seen) for s in obj.__slots__ if hasattr(obj, s))

    return size


def profile_run(world_seed=5000, history_seed=42, years=20):
    print(f"\n=======================================================")
    print(f"PROFILING RUN: World={world_seed}, History={history_seed}, Years={years}")
    print(f"=======================================================")

    # 1. World Gen Timing
    t0 = time.perf_counter()
    pair = SeedPair(world=world_seed, history=history_seed)
    sim = Simulation(seed=pair, enable_religion=True, enable_lore=True)
    t_init = time.perf_counter() - t0
    print(f"Subsystem: World Gen + Cast + Religion Init: {t_init:.4f}s")
    print(f"Initial Settlements: {len(sim.settlements)}, Characters: {len(sim.characters)}")

    # 2. Monthly Simulation Breakdown
    t_lifecycle_total = 0.0
    t_gossip_total = 0.0
    t_conflict_total = 0.0
    t_religion_total = 0.0
    t_lore_total = 0.0
    t_perception_total = 0.0

    total_ticks = years * 12
    t_sim_start = time.perf_counter()

    for y in range(years):
        for m in range(12):
            tick = y * 12 + m
            if len(sim.living_characters) == 0:
                break

            # Lifecycle
            t1 = time.perf_counter()
            events_start = len(sim.event_log)
            from minemesis.systems.life_cycle import process_life_cycle
            process_life_cycle(
                characters=sim.characters,
                settlements=sim.settlements,
                event_log=sim.event_log,
                marriage_events=sim.marriage_events,
                active_trade_route_events=sim.active_trade_route_events,
                get_relationship=sim.get_relationship,
                tick=sim.tick,
                seed=sim.seed,
                char_counter=sim.char_counter,
                name_salt=sim.name_salt,
            )
            t2 = time.perf_counter()
            t_lifecycle_total += (t2 - t1)

            sim._register_and_perceive_events(events_start)
            t3 = time.perf_counter()
            t_perception_total += (t3 - t2)

            # Gossip
            from minemesis.systems.gossip import propagate_gossip
            gossip_beliefs = propagate_gossip(
                characters=sim.characters,
                beliefs_by_character=sim.beliefs_by_character,
                get_relationship=sim.get_relationship,
                tick=sim.tick,
                seed=sim.seed,
                belief_counter=sim.belief_counter,
            )
            for b in gossip_beliefs:
                char_beliefs = sim.beliefs_by_character.setdefault(b.believer_id, {})
                char_beliefs[b.event_ref] = b
            t4 = time.perf_counter()
            t_gossip_total += (t4 - t3)

            # Conflict & Economy
            conflict_start = len(sim.event_log)
            from minemesis.systems.conflict import process_conflicts_and_economy
            process_conflicts_and_economy(
                characters=sim.characters,
                settlements=sim.settlements,
                trade_routes=sim.trade_routes,
                active_trade_route_events=sim.active_trade_route_events,
                last_raid_ticks=sim.last_raid_ticks,
                collapsed_settlements=sim.collapsed_settlements,
                beliefs_by_character=sim.beliefs_by_character,
                memories=sim.memories,
                superseded_memory_ids=sim.superseded_memory_ids,
                event_log=sim.event_log,
                active_feuds=sim.active_feuds,
                get_relationship=sim.get_relationship,
                tick=sim.tick,
                seed=sim.seed,
                belief_counter=sim.belief_counter,
                memory_counter=sim.memory_counter,
                resolved_grievance_event_ids=sim.resolved_grievance_event_ids,
            )
            t5 = time.perf_counter()
            t_conflict_total += (t5 - t4)

            sim._register_and_perceive_events(conflict_start)
            t6 = time.perf_counter()
            t_perception_total += (t6 - t5)

            # Religion
            if sim.religion_engine and sim.religion_engine.enabled:
                for c_id, c in sim.characters.items():
                    if c_id not in sim.religion_engine.faiths:
                        sim.religion_engine.register_newborn(
                            child_id=c_id, father_id=c.father_id, mother_id=c.mother_id,
                            settlement_id=c.settlement_id, tick=sim.tick
                        )
                rel_start = len(sim.event_log)
                sim.religion_engine.update_tick(
                    tick=sim.tick, event_log=sim.event_log, settlements=sim.settlements,
                    characters=sim.characters, active_trade_routes=sim.trade_routes, recent_deaths=[]
                )
                t7 = time.perf_counter()
                t_religion_total += (t7 - t6)
                sim._register_and_perceive_events(rel_start)
                t8 = time.perf_counter()
                t_perception_total += (t8 - t7)

            # Lore / Books
            if sim.lore_engine and sim.lore_engine.enabled:
                recent_month_events = sim.event_log.all_events()[events_start:]
                lore_start = len(sim.event_log)
                sim.lore_engine.update_tick(
                    tick=sim.tick, event_log=sim.event_log, characters=sim.characters,
                    settlements=sim.settlements, beliefs_by_character=sim.beliefs_by_character,
                    memories=sim.memories, religion_engine=sim.religion_engine,
                    trade_routes=sim.trade_routes, recent_events=recent_month_events
                )
                t9 = time.perf_counter()
                t_lore_total += (t9 - t8)
                sim._register_and_perceive_events(lore_start)
                t10 = time.perf_counter()
                t_perception_total += (t10 - t9)

            sim.tick += 1

    t_sim_total = time.perf_counter() - t_sim_start
    print(f"\nSimulation {years} Years Finished in: {t_sim_total:.4f}s")
    print(f"  - LifeCycle (Marriages, Births, Deaths): {t_lifecycle_total:.4f}s ({t_lifecycle_total/t_sim_total*100:.1f}%)")
    print(f"  - Perception & Memory Formation:        {t_perception_total:.4f}s ({t_perception_total/t_sim_total*100:.1f}%)")
    print(f"  - Conflict, Feuds, Economy & Raids:    {t_conflict_total:.4f}s ({t_conflict_total/t_sim_total*100:.1f}%)")
    print(f"  - Religion Engine:                      {t_religion_total:.4f}s ({t_religion_total/t_sim_total*100:.1f}%)")
    print(f"  - Literature / Books Engine:            {t_lore_total:.4f}s ({t_lore_total/t_sim_total*100:.1f}%)")
    print(f"  - Gossip / Rumors:                      {t_gossip_total:.4f}s ({t_gossip_total/t_sim_total*100:.1f}%)")

    # 3. Causal Analysis Timing
    t0_causal = time.perf_counter()
    best_c_id, conflict_depth, c_distinct = get_deepest_conflict_chain_metrics(sim.event_log)
    best_l_id, longest_depth, l_distinct = get_deepest_causal_chain_metrics(sim.event_log)
    t_causal = time.perf_counter() - t0_causal
    print(f"\nCausal Analysis Timing: {t_causal:.4f}s (Events: {len(sim.event_log)}, C-Depth: {conflict_depth}, L-Depth: {longest_depth})")

    # 4. History Export Timing
    t0_export = time.perf_counter()
    report_text = format_causal_chain(sim.event_log, best_c_id, characters=sim.characters)
    mermaid_text = export_causal_graph_mermaid(sim.event_log, best_c_id)
    t_export = time.perf_counter() - t0_export
    print(f"History Export Timing (format_causal_chain + mermaid): {t_export:.4f}s")

    # 5. Object Memory Footprint Measurement
    print("\n--- Object Memory Footprints (Deep Sizes) ---")
    sample_char = next(iter(sim.characters.values()))
    sample_event = sim.event_log.get(0)
    sample_set = next(iter(sim.settlements.values()))
    sample_belief = next((b for c_b in sim.beliefs_by_character.values() for b in c_b.values()), None)
    sample_memory = sim.memories[0] if sim.memories else None
    sample_book = sim.get_all_books()[0] if sim.get_all_books() else None
    sample_rel = next(iter(sim.religion_engine.religions.values())) if sim.religion_engine else None

    print(f"Character (shallow): {sys.getsizeof(sample_char)} B | deep: {get_deep_size(sample_char)} B")
    print(f"Event (shallow):     {sys.getsizeof(sample_event)} B | deep: {get_deep_size(sample_event)} B")
    print(f"Settlement (shallow):{sys.getsizeof(sample_set)} B | deep: {get_deep_size(sample_set)} B")
    if sample_belief:
        print(f"Belief (shallow):    {sys.getsizeof(sample_belief)} B | deep: {get_deep_size(sample_belief)} B")
    if sample_memory:
        print(f"Memory (shallow):    {sys.getsizeof(sample_memory)} B | deep: {get_deep_size(sample_memory)} B")
    if sample_book:
        print(f"Book (shallow):      {sys.getsizeof(sample_book)} B | deep: {get_deep_size(sample_book)} B (pages: {len(sample_book.pages)}, words: {sample_book.total_word_count})")
    if sample_rel:
        print(f"Religion (shallow):  {sys.getsizeof(sample_rel)} B | deep: {get_deep_size(sample_rel)} B")

    print(f"\n--- Total Collection Counts in Memory ---")
    print(f"Living Characters:    {len(sim.living_characters)}")
    print(f"Total Characters:     {len(sim.characters)}")
    print(f"Total Events:         {len(sim.event_log)}")
    print(f"Total Memories:       {len(sim.memories)}")
    print(f"Total Beliefs:        {sum(len(b) for b in sim.beliefs_by_character.values())}")
    print(f"Total Books:          {len(sim.get_all_books())}")
    print(f"Total Religions:      {len(sim.religion_engine.religions) if sim.religion_engine else 0}")

    total_sim_size = get_deep_size(sim)
    print(f"\nTotal Simulation Deep Memory Size: {total_sim_size / (1024*1024):.2f} MB")


if __name__ == "__main__":
    profile_run(years=20)
