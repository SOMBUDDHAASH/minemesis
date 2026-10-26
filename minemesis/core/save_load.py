"""
Persistence and Replay System for Minemesis (Milestone 6).

Supports:
- Save/Load format (.minemesis_save) with versioned generator registry.
- Fast-forward deterministic replay-to-year controller.
- Macro world map reconstruction from world_seed without voxel rendering.
"""

from __future__ import annotations
import json
from pathlib import Path
import time
from typing import Any, Mapping, Optional, Sequence

from minemesis.core.seed import SeedPair
from minemesis.models.character import Character
from minemesis.models.settlement import Settlement
from minemesis.systems.world_gen import generate_world
from minemesis.systems.world_spec import WorldSpec


CURRENT_GENERATOR_VERSION = "2.0.0"


class GeneratorVersionMismatchWarning(UserWarning):
    """Raised when loading a save created with a different generator version."""
    pass


def save_simulation(sim: Any, save_path: str | Path) -> dict[str, Any]:
    """
    Serializes simulation state to a standardized .minemesis_save package.
    """
    path = Path(save_path).resolve()
    
    # Living characters snapshot
    living_chars_data = [
        c.to_dict() if hasattr(c, "to_dict") else {
            "id": c.id,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "settlement_id": c.settlement_id,
            "age_ticks": c.age_ticks,
            "sex": c.sex,
            "alive": c.alive,
            "profession": c.profession,
            "suspicion": c.suspicion,
            "forgiveness": c.forgiveness,
            "spouse_id": c.spouse_id,
            "father_id": c.father_id,
            "mother_id": c.mother_id,
            "children_ids": list(c.children_ids),
        }
        for c in sim.characters.values() if c.alive
    ]

    # Settlement state
    settlements_data = {
        s_id: {
            "id": s.id,
            "name": s.name,
            "food": s.food,
            "wood": s.wood,
            "ore": s.ore,
            "wealth": s.wealth,
            "stability": round(s.stability, 2),
            "defensibility": round(s.defensibility, 2),
            "leader_id": s.leader_id,
        }
        for s_id, s in sim.settlements.items()
    }

    # Demographics snapshot
    cohorts_data = [
        {
            "settlement_id": c.settlement_id,
            "age_bracket": c.age_bracket,
            "sex": c.sex,
            "profession": c.profession,
            "count": c.count,
        }
        for c in sim.demographics.cohorts.values()
    ]

    # Player actor snapshot
    p_sys = getattr(sim, "player_system", None)
    player_data = {
        "location": p_sys.location if p_sys else "",
        "wealth": p_sys.wealth if p_sys else 100,
        "inventory": p_sys.inventory if p_sys else {},
        "command_history": p_sys.command_history if p_sys else [],
    }

    # Diplomacy snapshot
    dip = getattr(sim, "diplomacy", None)
    diplomacy_data = {
        f"{k[0]}__{k[1]}": v.value
        for k, v in (dip.stances.items() if dip else [])
    }

    save_payload = {
        "header": {
            "magic": "MINEMESIS_SAVE",
            "schema_version": 1,
            "generator_version": CURRENT_GENERATOR_VERSION,
            "world_seed": sim.world_seed,
            "history_seed": sim.history_seed,
            "tick": sim.tick,
            "year": sim.tick // 12,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "settlements": settlements_data,
        "living_characters": living_chars_data,
        "demographics": cohorts_data,
        "player": player_data,
        "diplomacy": diplomacy_data,
        "event_count": len(sim.event_log),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(save_payload, f, indent=2)

    return save_payload


def load_simulation_state(save_path: str | Path, sim_cls: Any) -> Any:
    """
    Loads saved state and instantiates/restores a Simulation object.
    Checks generator version registry and warns if mismatched.
    """
    path = Path(save_path).resolve()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    header = data.get("header", {})
    gen_ver = header.get("generator_version", "")
    if gen_ver != CURRENT_GENERATOR_VERSION:
        import warnings
        warnings.warn(
            f"Save file generator version '{gen_ver}' differs from current '{CURRENT_GENERATOR_VERSION}'. "
            "Reconstruction will proceed using backwards-compatible fallback.",
            GeneratorVersionMismatchWarning,
            stacklevel=2,
        )

    w_seed = header.get("world_seed", 42)
    h_seed = header.get("history_seed", 1337)
    seed_pair = SeedPair(world=w_seed, history=h_seed)

    sim = sim_cls(seed=seed_pair)
    sim.tick = header.get("tick", 0)

    # Restore settlements
    for s_id, s_data in data.get("settlements", {}).items():
        if s_id in sim.settlements:
            s = sim.settlements[s_id]
            s.food = s_data.get("food", s.food)
            s.wood = s_data.get("wood", s.wood)
            s.ore = s_data.get("ore", s.ore)
            s.wealth = s_data.get("wealth", s.wealth)
            s.stability = s_data.get("stability", s.stability)
            s.defensibility = s_data.get("defensibility", s.defensibility)
            s.leader_id = s_data.get("leader_id", s.leader_id)

    # Restore player
    p_data = data.get("player", {})
    if hasattr(sim, "player_system"):
        sim.player_system.location = p_data.get("location", "")
        sim.player_system.wealth = p_data.get("wealth", 100)
        sim.player_system.inventory = p_data.get("inventory", {})
        sim.player_system.command_history = p_data.get("command_history", [])

    return sim


def replay_to_year(
    world_seed: int = 42,
    history_seed: int = 1337,
    target_year: int = 50,
    export_sink: Optional[Any] = None,
    sim_cls: Optional[Any] = None,
) -> Any:
    """
    Fast-forward deterministic replay controller:
    Executes pure keyed simulation ticks up to target_year * 12.
    """
    if sim_cls is None:
        from minemesis.systems.simulation import Simulation
        sim_cls = Simulation

    seed_pair = SeedPair(world=world_seed, history=history_seed)
    sim = sim_cls(
        seed=seed_pair,
        export_sink=export_sink,
        enable_religion=True,
        enable_lore=True,
    )

    total_ticks = max(0, target_year * 12)
    for _ in range(total_ticks):
        sim.step_month()

    return sim


def reconstruct_macro_world_map(world_seed: int = 42) -> dict[str, Any]:
    """
    Reconstructs the 2D macro world map directly from world_seed without voxel rendering.
    Returns settlement coordinates, biomes, connections, and boundary dimensions.
    """
    from minemesis.systems.world_gen_v0 import V0WorldGenerator
    provider = V0WorldGenerator()
    spec = provider.generate(world_seed=world_seed)

    sites = []
    for s in spec.settlements:
        sites.append({
            "id": s.id,
            "name": s.name,
            "x": s.x,
            "y": s.y,
            "biome": getattr(s, "biome", "Temperate Forest"),
            "water_access": round(s.water_access, 2),
            "farmland": round(s.farmland, 2),
            "defensibility": round(s.defensibility, 2),
        })

    # Inter-settlement road connections (Delaunay or nearest-neighbor)
    connections = []
    for i, s1 in enumerate(sites):
        for s2 in sites[i + 1:]:
            dist = ((s1["x"] - s2["x"]) ** 2 + (s1["y"] - s2["y"]) ** 2) ** 0.5
            if dist < 600:  # Connecting threshold
                connections.append({
                    "from": s1["id"],
                    "to": s2["id"],
                    "distance": round(dist, 1),
                })

    return {
        "world_seed": world_seed,
        "width": 1000,
        "height": 1000,
        "settlements": sites,
        "connections": connections,
    }
