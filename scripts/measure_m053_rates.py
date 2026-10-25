"""
Script to measure exact empirical creation rates for beliefs, memories,
characters, and events over time across 10, 25, 50, and 100 years.
"""

from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from minemesis.core.seed import SeedPair
from minemesis.systems.simulation import Simulation

def measure_rates():
    # Run a standard 100-year simulation with V0 world (Pair 1 seed)
    pair = SeedPair(world=5000, history=15647747789945644669)
    sim = Simulation(seed=pair, enable_religion=True, enable_lore=True)
    
    milestones = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    results = []
    
    prev_tick = 0
    prev_beliefs = 0
    prev_memories = 0
    prev_events = 0
    prev_chars = len(sim.characters)

    print("Year | Living | Total Chars | Events | Total Beliefs | Total Memories | Beliefs/Mo | Mems/Mo | Births/Mo | Deaths/Mo")
    print("-" * 110)

    for target_year in milestones:
        ticks_to_run = (target_year * 12) - sim.tick
        for _ in range(ticks_to_run):
            sim.step_month()
        
        living = len(sim.living_characters)
        total_chars = len(sim.characters)
        events = len(sim.event_log)
        beliefs = sum(len(b) for b in sim.beliefs_by_character.values())
        mems = len(sim.memories)
        
        delta_ticks = sim.tick - prev_tick
        b_rate = (beliefs - prev_beliefs) / delta_ticks if delta_ticks > 0 else 0
        m_rate = (mems - prev_memories) / delta_ticks if delta_ticks > 0 else 0
        e_rate = (events - prev_events) / delta_ticks if delta_ticks > 0 else 0
        c_rate = (total_chars - prev_chars) / delta_ticks if delta_ticks > 0 else 0
        
        print(f"{target_year:4d} | {living:6d} | {total_chars:11d} | {events:6d} | {beliefs:13d} | {mems:14d} | {b_rate:10.1f} | {m_rate:7.1f} | {c_rate:9.2f} | {e_rate:9.2f}")
        
        prev_tick = sim.tick
        prev_beliefs = beliefs
        prev_memories = mems
        prev_events = events
        prev_chars = total_chars

if __name__ == "__main__":
    # Smoke test on 20 years to get rates fast
    pair = SeedPair(world=5000, history=42)
    sim = Simulation(seed=pair, enable_religion=True, enable_lore=True)
    print("Measuring rates for Year 5, 10, 15, 20...")
    for target_year in [5, 10, 15, 20]:
        ticks = (target_year * 12) - sim.tick
        for _ in range(ticks):
            sim.step_month()
        living = len(sim.living_characters)
        total_chars = len(sim.characters)
        events = len(sim.event_log)
        beliefs = sum(len(b) for b in sim.beliefs_by_character.values())
        mems = len(sim.memories)
        print(f"Yr {target_year:2d}: Living={living:4d}, TotalChars={total_chars:4d}, Events={events:5d}, Beliefs={beliefs:7d}, Memories={mems:5d}")
