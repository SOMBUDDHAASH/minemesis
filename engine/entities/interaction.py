"""
Organic NPC Interaction and Dialogue System (Talk, Trade, Gift, Help, Steal, Attack).
"""

from __future__ import annotations
import random
from typing import Any, Dict, List, Optional, Tuple

from engine.entities.npc import NPC


class InteractionEngine:
    """Manages player interactions with simulated NPCs and generates organic dialogue."""

    def __init__(self) -> None:
        self.active_npc: Optional[NPC] = None
        self.menu_open: bool = False
        self.dialogue_history: List[str] = []

    def open_interaction(self, npc: NPC) -> None:
        self.active_npc = npc
        self.menu_open = True
        self.dialogue_history.clear()
        self.dialogue_history.append(f"Approached {npc.name} ({npc.profession} of {npc.settlement_id}).")
        self.dialogue_history.append(f"Current Activity: {npc.current_activity}")

    def close_interaction(self) -> None:
        self.menu_open = False
        self.active_npc = None

    def execute_action(self, action: str, player: any) -> str:
        if not self.active_npc:
            return "No NPC selected."

        npc = self.active_npc

        if action == "talk":
            greeting = self._generate_dialogue(npc, player)
            self.dialogue_history.append(f"{npc.name}: \"{greeting}\"")
            return greeting

        elif action == "gift":
            npc.affinity_to_player += 15.0
            resp = f"{npc.name} accepts your offering with gratitude! (Affinity: +15)"
            self.dialogue_history.append(resp)
            return resp

        elif action == "trade":
            resp = f"{npc.name} shows their trade goods: 10x Loam Dirt, 5x Oak Planks, 2x Native Copper."
            self.dialogue_history.append(resp)
            return resp

        elif action == "help":
            resp = (
                f"{npc.name}: \"Our settlement needs stronger stone walls and watchtowers to deter raiders. "
                "Any fortifications you construct around our borders directly safeguard our granary!\""
            )
            self.dialogue_history.append(resp)
            return resp

        elif action == "steal":
            success = (random.random() < 0.45)
            if success:
                resp = f"You deftly pickpocketed 3x Silver Ore from {npc.name} undetected!"
            else:
                npc.affinity_to_player -= 40.0
                npc.is_hostile = True
                resp = f"CAUGHT! {npc.name} shouts: \"Thief! Guards, seize this scoundrel!\""
            self.dialogue_history.append(resp)
            return resp

        elif action == "attack":
            npc.health = max(0.0, npc.health - 6.0)
            npc.is_hostile = True
            npc.affinity_to_player = -100.0
            if npc.health <= 0:
                resp = f"You struck down {npc.name}! The villagers cry out in horror and flee!"
            else:
                resp = f"You struck {npc.name} (Health: {npc.health:.1f}/20)! They draw their weapon!"
            self.dialogue_history.append(resp)
            return resp

        return "Unknown action."

    def _generate_dialogue(self, npc: NPC, player: any) -> str:
        if npc.is_hostile:
            return "Begone, enemy! Draw no closer or taste our steel!"

        if npc.affinity_to_player > 20.0:
            return f"Welcome back, honored friend! It gladdens my heart to see you walk among us in {npc.settlement_id}."

        templates = [
            f"Peace be upon you, traveler. I am {npc.name}. In our hall we honor the tenets of {npc.faith}.",
            f"The days grow shorter, yet our granary holds firm. May the harvest favor us all.",
            f"I have lived in this valley all my life. We welcome travelers who respect our customs and laws.",
            f"Have you visited our town archive? The scribes have preserved records of our ancestors since Year 1.",
        ]
        return random.choice(templates)
