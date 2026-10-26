"""
Player as Simulation Actor System (Milestone 3).

Models the player as an authentic in-world character (`player_0`) subject to the
same perception, gossip, relationship views, and causal grammar rules as all citizens.
Supports player commands: kill, trade, gift, help, steal, build_wall, save.
Allows emergent bounty hunting and ally devotion without scripted quest rails.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from minemesis.core.rng import keyed_choice, keyed_float
from minemesis.core.types import BeliefSource, Emotion, EventType, Intent, Scale
from minemesis.models.belief import Belief
from minemesis.models.character import Character
from minemesis.models.memory import Memory
from minemesis.models.settlement import Settlement


class PlayerSystem:
    """
    Manages the player character (`player_0`) within the live simulation.
    """

    def __init__(self) -> None:
        self.player_id = "player_0"
        self.location: str = ""
        self.wealth: int = 150
        self.inventory: dict[str, int] = {"grain": 20, "tools": 2}
        self.command_history: list[dict[str, Any]] = []

    def initialize_player(self, sim: Any) -> Character:
        """
        Creates and registers `player_0` as a first-class character in the simulation.
        """
        # Place player in the first available settlement
        first_s_id = sorted(sim.settlements.keys())[0] if sim.settlements else "settlement_0"
        self.location = first_s_id

        player = Character(
            id=self.player_id,
            first_name="Player",
            last_name="Traveler",
            settlement_id=first_s_id,
            age_ticks=240,  # 20 years old
            sex="M",
            alive=True,
            suspicion=0.30,
            forgiveness=0.50,
            profession="Wanderer",
            family_id="Traveler",
            name_ordinal=1,
            display_name="Player Traveler",
        )

        sim.characters[self.player_id] = player
        sim.beliefs_by_character[self.player_id] = {}
        if sim.export_sink:
            sim.export_sink.record_character(player)

        return player

    def execute_command(self, command: str, args: dict[str, Any], sim: Any) -> dict[str, Any]:
        """
        Executes a player command in the simulation.
        Commands: kill, trade, gift, help, steal, build_wall, save.
        """
        cmd = command.strip().lower()
        player = sim.characters.get(self.player_id)
        if not player or not player.alive:
            return {"success": False, "error": "Player character is not alive."}

        tick = sim.tick
        start_evt_idx = len(sim.event_log)

        if cmd == "kill":
            target_id = args.get("target_id")
            target = sim.characters.get(target_id)
            if not target or not target.alive:
                return {"success": False, "error": f"Target '{target_id}' is invalid or already dead."}

            target.alive = False
            target.death_tick = tick
            evt = sim.event_log.append(
                tick=tick,
                location=target.settlement_id,
                event_type=EventType.DEATH,
                participants={"actor": self.player_id, "target": target.id},
                causes=[],
                intent=Intent.INTENTIONAL,
                scale=Scale.INDIVIDUAL,
                payload={
                    "cause_of_death": "Slain by Traveler",
                    "murderer": self.player_id,
                },
            )
            target.death_event_id = evt.id
            sim._register_and_perceive_events(start_evt_idx)

            res = {
                "success": True,
                "event_id": evt.id,
                "message": f"Player Traveler slew {target.display_name}. Kin and witnesses have formed vengeful grudges.",
            }

        elif cmd == "gift":
            target_id = args.get("target_id")
            amount = int(args.get("amount", 25))
            target = sim.characters.get(target_id)
            if not target or not target.alive:
                return {"success": False, "error": f"Target '{target_id}' is invalid or dead."}

            self.wealth = max(0, self.wealth - amount)
            evt = sim.event_log.append(
                tick=tick,
                location=target.settlement_id,
                event_type=EventType.PLAYER_ACTION,
                participants={"actor": self.player_id, "target": target.id},
                causes=[],
                intent=Intent.INTENTIONAL,
                scale=Scale.INDIVIDUAL,
                payload={"action": "gift", "amount": amount},
            )
            sim._register_and_perceive_events(start_evt_idx)

            # Instill gratitude memory in recipient
            mem_id = sim.memory_counter[0]
            sim.memory_counter[0] += 1
            gratitude_mem = Memory(
                id=mem_id,
                observer_id=target.id,
                belief_event_ref=evt.id,
                target_entity_id=self.player_id,
                emotion=Emotion.GRATITUDE,
                initial_intensity=80.0,
                decay_rate=0.005,
                tick_formed=tick,
            )
            sim.memories.append(gratitude_mem)
            sim.relationship_cache.invalidate_character(target.id)

            res = {
                "success": True,
                "event_id": evt.id,
                "message": f"Gifted {amount} coin to {target.display_name}. Gratitude formed.",
            }

        elif cmd == "help":
            s_id = args.get("settlement_id") or player.settlement_id
            s = sim.settlements.get(s_id)
            if not s:
                return {"success": False, "error": f"Settlement '{s_id}' not found."}

            s.food += 35
            s.stability = min(1.0, s.stability + 0.15)
            evt = sim.event_log.append(
                tick=tick,
                location=s_id,
                event_type=EventType.PLAYER_ACTION,
                participants={"actor": self.player_id, "target": s_id},
                causes=[],
                intent=Intent.INTENTIONAL,
                scale=Scale.AGGREGATE,
                payload={"action": "relief_aid", "food_donated": 35},
            )
            sim._register_and_perceive_events(start_evt_idx)
            res = {
                "success": True,
                "event_id": evt.id,
                "message": f"Delivered relief aid and food stores to {s.name}. Stability improved.",
            }

        elif cmd == "save":
            target_id = args.get("target_id")
            target = sim.characters.get(target_id)
            if not target or not target.alive:
                return {"success": False, "error": f"Target '{target_id}' is invalid or dead."}

            evt = sim.event_log.append(
                tick=tick,
                location=target.settlement_id,
                event_type=EventType.PLAYER_ACTION,
                participants={"actor": self.player_id, "target": target.id},
                causes=[],
                intent=Intent.INTENTIONAL,
                scale=Scale.INDIVIDUAL,
                payload={"action": "rescue", "saved_person": target.id},
            )
            sim._register_and_perceive_events(start_evt_idx)

            # High loyalty and gratitude memory formation
            mem_id1 = sim.memory_counter[0]
            mem_id2 = mem_id1 + 1
            sim.memory_counter[0] += 2
            sim.memories.append(
                Memory(
                    id=mem_id1,
                    observer_id=target.id,
                    belief_event_ref=evt.id,
                    target_entity_id=self.player_id,
                    emotion=Emotion.GRATITUDE,
                    initial_intensity=95.0,
                    decay_rate=0.002,
                    tick_formed=tick,
                )
            )
            sim.memories.append(
                Memory(
                    id=mem_id2,
                    observer_id=target.id,
                    belief_event_ref=evt.id,
                    target_entity_id=self.player_id,
                    emotion=Emotion.RESPECT,
                    initial_intensity=90.0,
                    decay_rate=0.003,
                    tick_formed=tick,
                )
            )
            sim.relationship_cache.invalidate_character(target.id)

            res = {
                "success": True,
                "event_id": evt.id,
                "message": f"Rescued {target.display_name}. Lifelong devotion and loyalty established.",
            }

        elif cmd == "steal":
            s_id = args.get("settlement_id") or player.settlement_id
            s = sim.settlements.get(s_id)
            if not s:
                return {"success": False, "error": f"Settlement '{s_id}' not found."}

            plundered = min(15, s.food)
            s.food -= plundered
            self.wealth += 20
            evt = sim.event_log.append(
                tick=tick,
                location=s_id,
                event_type=EventType.PLAYER_ACTION,
                participants={"actor": self.player_id, "target": s_id},
                causes=[],
                intent=Intent.INTENTIONAL,
                scale=Scale.AGGREGATE,
                payload={"action": "theft", "stolen_food": plundered},
            )
            sim._register_and_perceive_events(start_evt_idx)
            res = {
                "success": True,
                "event_id": evt.id,
                "message": f"Stole supplies from {s.name}. Settlement residents are outraged.",
            }

        elif cmd == "build_wall":
            s_id = args.get("settlement_id") or player.settlement_id
            s = sim.settlements.get(s_id)
            if not s:
                return {"success": False, "error": f"Settlement '{s_id}' not found."}

            s.defensibility = min(1.0, round(s.defensibility + 0.25, 2))
            evt = sim.event_log.append(
                tick=tick,
                location=s_id,
                event_type=EventType.PLAYER_ACTION,
                participants={"actor": self.player_id, "target": s_id},
                causes=[],
                intent=Intent.INTENTIONAL,
                scale=Scale.AGGREGATE,
                payload={"action": "build_wall", "new_defensibility": s.defensibility},
            )
            sim._register_and_perceive_events(start_evt_idx)
            res = {
                "success": True,
                "event_id": evt.id,
                "message": f"Constructed defensive palisade walls at {s.name}. Defensibility is now {s.defensibility}.",
            }

        elif cmd == "trade":
            s_id = args.get("settlement_id") or player.settlement_id
            s = sim.settlements.get(s_id)
            if not s:
                return {"success": False, "error": f"Settlement '{s_id}' not found."}

            self.wealth += 15
            s.wealth = max(0, s.wealth - 15)
            s.food += 10
            evt = sim.event_log.append(
                tick=tick,
                location=s_id,
                event_type=EventType.PLAYER_ACTION,
                participants={"actor": self.player_id, "target": s_id},
                causes=[],
                intent=Intent.INTENTIONAL,
                scale=Scale.AGGREGATE,
                payload={"action": "trade_goods"},
            )
            sim._register_and_perceive_events(start_evt_idx)
            res = {
                "success": True,
                "event_id": evt.id,
                "message": f"Traded caravan goods with merchants in {s.name}.",
            }

        else:
            return {"success": False, "error": f"Unknown command: '{command}'."}

        self.command_history.append({"tick": tick, "command": cmd, "args": args, "result": res})
        return res

    def get_player_hunters(self, sim: Any) -> list[dict[str, Any]]:
        """
        Returns all living characters who hold active hatred (>= 40.0) towards player_0.
        """
        hunters = []
        for c in sim.characters.values():
            if c.alive and c.id != self.player_id:
                rel = sim.get_relationship(c.id, self.player_id)
                if rel.hatred >= 40.0:
                    hunters.append({
                        "character_id": c.id,
                        "name": c.display_name,
                        "settlement_id": c.settlement_id,
                        "hatred": round(rel.hatred, 1),
                        "trust": round(rel.trust, 1),
                    })
        hunters.sort(key=lambda h: h["hatred"], reverse=True)
        return hunters

    def get_player_allies(self, sim: Any) -> list[dict[str, Any]]:
        """
        Returns all living characters who hold deep trust (>= 30.0) or loyalty towards player_0.
        """
        allies = []
        for c in sim.characters.values():
            if c.alive and c.id != self.player_id:
                rel = sim.get_relationship(c.id, self.player_id)
                if rel.trust >= 30.0 or rel.loyalty >= 30.0:
                    allies.append({
                        "character_id": c.id,
                        "name": c.display_name,
                        "settlement_id": c.settlement_id,
                        "trust": round(rel.trust, 1),
                        "loyalty": round(rel.loyalty, 1),
                    })
        allies.sort(key=lambda a: (a["loyalty"], a["trust"]), reverse=True)
        return allies

    def get_settlement_reputations(self, sim: Any) -> dict[str, float]:
        """
        Computes aggregate settlement reputation score towards player_0.
        """
        reps = {}
        for s_id in sim.settlements.keys():
            local_c = [c for c in sim.characters.values() if c.alive and c.settlement_id == s_id and c.id != self.player_id]
            if not local_c:
                reps[s_id] = 0.0
                continue
            total_trust = sum(sim.get_relationship(c.id, self.player_id).trust for c in local_c[:10])
            total_hatred = sum(sim.get_relationship(c.id, self.player_id).hatred for c in local_c[:10])
            score = (total_trust - total_hatred) / len(local_c[:10])
            reps[s_id] = round(score, 1)
        return reps
