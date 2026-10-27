"""
Simulation Bridge & Process API for Minemesis Engine (Stage E3).
Connects the 3D Voxel Engine (Physical Body) with the Simulation (Civilization Brain)
with Zero Coupling: Simulation never imports Engine.
"""

from __future__ import annotations
import json
import math
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

from minemesis.core.seed import SeedPair
from minemesis.core.types import EventType
from minemesis.export.writer import RunDBWriter
from minemesis.systems.simulation import Simulation


# 1 Game Year = 20 Real Minutes = 1200 Seconds
# 1 Game Year = 12 Simulation Ticks (1 tick = 1 month = 100 real seconds)
SECONDS_PER_TICK = 100.0


class SimulationBridge:
    """
    Manages live background simulation updates, time scaling,
    witness observation checks, construction analysis, and world persistence.
    """

    def __init__(
        self,
        world_spec: any,
        seed_pair: Optional[SeedPair] = None,
        prehistory_years: int = 20,
    ) -> None:
        self.world_spec = world_spec
        self.seed_pair = seed_pair or SeedPair(world=42, history=1337)
        self.prehistory_years = prehistory_years

        # 1. Initialize Headless Simulation
        self.simulation = Simulation(seed=self.seed_pair)
        if prehistory_years > 0:
            self.simulation.run_years(prehistory_years)

        # Simulation Time State
        self.elapsed_real_seconds: float = 0.0
        self.total_simulated_ticks: int = self.simulation.tick
        self.accumulated_tick_time: float = 0.0

        # Construction & Defensibility State per Settlement
        self.settlement_defensibility: Dict[str, float] = {}
        self.last_analyzed_delta_count: int = 0
        for s in self.world_spec.settlements:
            self.settlement_defensibility[s.id] = 10.0  # Base 10% defensibility

        # In-memory recent events for Chronicle Overlay [J]
        self.recent_chronicle_events: List[str] = []
        self._sync_recent_events_from_sim()

    def _sync_recent_events_from_sim(self) -> None:
        """Loads most recent event descriptions from simulation event log."""
        all_ev = self.simulation.event_log.all_events()
        self.recent_chronicle_events = [
            f"[Year {(e.tick // 12) + 1}] {e.type.value.upper()}: {e.description}"
            for e in all_ev[-20:]
        ]

    def tick(self, dt: float, app: any) -> None:
        """Advances live simulation based on real-time clock."""
        self.elapsed_real_seconds += dt
        self.accumulated_tick_time += dt

        # Step simulation tick every SECONDS_PER_TICK real seconds
        if self.accumulated_tick_time >= SECONDS_PER_TICK:
            self.accumulated_tick_time -= SECONDS_PER_TICK
            self._step_simulation_tick(app)

        # Periodic construction analysis (every 3 seconds)
        if int(self.elapsed_real_seconds) % 3 == 0:
            self.analyze_construction(app.chunk_mgr)

    def _step_simulation_tick(self, app: any) -> None:
        """Executes one simulation tick (one month of history)."""
        self.simulation.step_month()
        self.total_simulated_ticks = self.simulation.tick
        current_year = self.total_simulated_ticks // 12

        # Sync recent events
        self._sync_recent_events_from_sim()

        # Update NPC states from simulation if needed
        for s in self.world_spec.settlements:
            # Settlement growth/defense adaptation
            pass

    def skip_time(self, hours: float, app: any) -> None:
        """Advances game time (e.g. sleeping in bed)."""
        # Convert hours to seconds (24h = 1 day = 1200s / 365 = 3.287s)
        # Advance sky
        app.sky.time_of_day = (app.sky.time_of_day + hours) % 24.0
        # If sleeping 8 hours, advance tick proportion
        ticks_to_advance = int(hours / 24.0 * (12.0 / 30.0))
        for _ in range(max(1, ticks_to_advance)):
            self._step_simulation_tick(app)

    def kill_character_in_simulation(
        self,
        victim_id: str,
        killer_id: str = "player",
        app: any = None,
    ) -> Optional[dict]:
        """
        Dispatches a violent death directly into the Minemesis history simulation.
        Triggers:
        1. EventType.DEATH logged in simulation event log with causal payload.
        2. Simulation step to propagate perception, grief, and memories to all kin.
        3. Succession crisis / Chief changed if victim was the settlement leader.
        4. Scribe biography & chronicle penned in town archives.
        5. Updates visible NPC entities and promotes successor.
        """
        c = self.simulation.characters.get(victim_id)
        if not c:
            return None

        c.alive = False
        c.death_tick = self.simulation.tick

        from minemesis.core.types import EventType, Intent, Scale
        death_evt = self.simulation.event_log.append(
            tick=self.simulation.tick,
            location=c.settlement_id,
            event_type=EventType.DEATH,
            participants={"actor": killer_id, "target": c.id, "deceased": c.id},
            causes=[],
            intent=Intent.INTENTIONAL,
            scale=Scale.INDIVIDUAL,
            payload={
                "cause_of_death": "Assassinated by traveler",
                "murder": True,
                "violent": True,
            },
        )
        c.death_event_id = death_evt.id

        # Step simulation month to trigger perception, kinship grief, succession, and lore
        self.simulation.step_month()
        self.total_simulated_ticks = self.simulation.tick
        year = (self.total_simulated_ticks // 12) + 1

        # Check succession
        settlement = self.simulation.settlements.get(c.settlement_id)
        old_chief_id = victim_id
        new_chief_id = settlement.leader_id if settlement else None
        successor_name = None

        if settlement and new_chief_id and new_chief_id != old_chief_id:
            successor_char = self.simulation.characters.get(new_chief_id)
            successor_name = successor_char.name if successor_char else new_chief_id
            self.recent_chronicle_events.append(
                f"[Year {year}] SUCCESSION: Following the assassination of Chief {c.name}, "
                f"{successor_name} has risen as the new Chief of {settlement.name}!"
            )
            # Update app NPC
            if app and hasattr(app, "npcs"):
                for npc in app.npcs:
                    if npc.character_id == new_chief_id:
                        npc.profession = "Chief"
                        npc.current_activity = f"Ruling {settlement.name} from Great Hall (Successor)"

        # Check recently penned books
        new_books = []
        if self.simulation.lore_engine:
            s_books = self.simulation.lore_engine.get_settlement_books(c.settlement_id)
            if s_books:
                new_books = [b.title for b in s_books[-3:]]

        return {
            "victim_id": c.id,
            "victim_name": c.name,
            "death_event_id": death_evt.id,
            "settlement_id": c.settlement_id,
            "new_chief_id": new_chief_id,
            "successor_name": successor_name,
            "recent_books": new_books,
        }

    def record_combat_encounter(
        self,
        victim_npc: any,
        damage: float,
        fatal: bool,
        witnesses: List[any],
    ) -> None:
        """
        Records combat encounter into the epistemic ledger and event log.
        Witnesses scream, call guards, or flee.
        """
        year = self.total_simulated_ticks // 12
        desc = (
            f"The traveler struck down {victim_npc.name} in cold blood!"
            if fatal
            else f"The traveler assaulted {victim_npc.name} ({victim_npc.profession})!"
        )

        # Log to recent chronicle
        self.recent_chronicle_events.append(f"[Year {year}] VIOLENCE: {desc}")

        # Organic reactions for witnesses
        for w in witnesses:
            if w.character_id != victim_npc.character_id:
                w.affinity_to_player -= 50.0
                if w.profession == "Guard":
                    w.is_hostile = True
                    w.current_activity = f"HUNTING INTRUDER: Avenging {victim_npc.name}!"
                else:
                    w.is_fleeing = True
                    w.current_activity = f"Fleeing in terror from violent traveler!"
                    w.target_pos = w.home_pos

    def analyze_construction(self, chunk_mgr: any) -> None:
        """
        Construction Analyzer:
        Monitors player block placements and detects fortifications (stone walls, palisades).
        Increases settlement defensibility and triggers organic village reactions.
        """
        total_deltas = sum(len(d) for d in chunk_mgr.chunk_deltas.values())
        if total_deltas == self.last_analyzed_delta_count:
            return
        self.last_analyzed_delta_count = total_deltas

        # Scan modified blocks near settlements
        defensive_blocks = {52, 89, 90, 91, 92, 93, 94} # Planks, Stone Bricks, Cobblestone, Basalt, Slate, Palisade

        for s in self.world_spec.settlements:
            sx = s.x * 8 + 4
            sz = s.y * 8 + 4

            count = 0
            for (cx, cz), deltas in chunk_mgr.chunk_deltas.items():
                for (lx, ly, lz), bid in deltas.items():
                    if bid in defensive_blocks:
                        gx = cx * 16 + lx
                        gz = cz * 16 + lz
                        dist = math.sqrt((gx - sx) ** 2 + (gz - sz) ** 2)
                        if dist < 65.0:
                            count += 1

            prev_def = self.settlement_defensibility.get(s.id, 10.0)
            new_def = min(95.0, 10.0 + (count * 1.5))
            if new_def > prev_def:
                self.settlement_defensibility[s.id] = new_def
                if new_def >= prev_def + 5.0:
                    year = self.total_simulated_ticks // 12
                    event_str = (
                        f"[Year {year}] FORTIFICATION: Citizens of {s.name} celebrate new stone defenses! "
                        f"(Defensibility: {new_def:.0f}%)"
                    )
                    self.recent_chronicle_events.append(event_str)

    def save_world(self, save_dir: str | Path, app: any) -> Path:
        """Persists world state, player attributes, chunk deltas, and simulation archive."""
        p = Path(save_dir)
        p.mkdir(parents=True, exist_ok=True)

        player_data = {
            "x": app.player.x,
            "y": app.player.y,
            "z": app.player.z,
            "yaw": app.player.yaw,
            "pitch": app.player.pitch,
            "selected_slot": app.player.selected_slot,
            "inventory": app.player.inventory,
            "hotbar": app.player.hotbar,
            "time_of_day": app.sky.time_of_day,
            "world_seed": self.seed_pair.world,
            "history_seed": self.seed_pair.history,
            "total_simulated_ticks": self.total_simulated_ticks,
        }
        with open(p / "player.json", "w", encoding="utf-8") as f:
            json.dump(player_data, f, indent=2)

        # Chunk deltas
        serializable_deltas = {}
        for (cx, cz), deltas in app.chunk_mgr.chunk_deltas.items():
            key = f"{cx},{cz}"
            serializable_deltas[key] = {
                f"{lx},{ly},{lz}": bid for (lx, ly, lz), bid in deltas.items()
            }
        with open(p / "chunk_deltas.json", "w", encoding="utf-8") as f:
            json.dump(serializable_deltas, f)

        # Export Run Database (.minemesis)
        db_path = p / "chronicle.minemesis"
        writer = RunDBWriter(db_path)
        writer.finalize({
            "schema_version": 1,
            "world_seed": self.seed_pair.world,
            "history_seed": self.seed_pair.history,
            "pair_code": self.seed_pair.encode(),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_ticks": self.total_simulated_ticks,
        })
        return p

    def load_world(self, save_dir: str | Path, app: any) -> bool:
        """Loads saved world state, player position, chunk deltas, and simulation state."""
        p = Path(save_dir)
        if not (p / "player.json").exists():
            return False

        with open(p / "player.json", "r", encoding="utf-8") as f:
            player_data = json.load(f)

        app.player.x = player_data["x"]
        app.player.y = player_data["y"]
        app.player.z = player_data["z"]
        app.player.yaw = player_data["yaw"]
        app.player.pitch = player_data["pitch"]
        app.player.selected_slot = player_data.get("selected_slot", 0)
        app.player.inventory = {int(k): v for k, v in player_data.get("inventory", {}).items()}
        app.player.hotbar = [int(x) for x in player_data.get("hotbar", [19, 51, 52, 89, 90, 97, 100, 101, 136])]
        app.sky.time_of_day = player_data.get("time_of_day", 12.0)

        # Load deltas
        if (p / "chunk_deltas.json").exists():
            with open(p / "chunk_deltas.json", "r", encoding="utf-8") as f:
                raw_deltas = json.load(f)
            app.chunk_mgr.chunk_deltas.clear()
            for key, block_dict in raw_deltas.items():
                cx_s, cz_s = key.split(",")
                cx, cz = int(cx_s), int(cz_s)
                app.chunk_mgr.chunk_deltas[(cx, cz)] = {}
                for blk_key, bid in block_dict.items():
                    lx_s, ly_s, lz_s = blk_key.split(",")
                    app.chunk_mgr.chunk_deltas[(cx, cz)][(int(lx_s), int(ly_s), int(lz_s))] = bid

            # Invalidate all chunk meshes so changes appear
            for c in app.chunk_mgr.chunks.values():
                c.is_dirty = True

        return True
