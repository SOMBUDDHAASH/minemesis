"""
Organic NPC Interaction, Reputation & Social Standing System.
Connects player actions to settlement reputation, clan feuds, and historical dialogue.
"""

from __future__ import annotations
import random
from typing import Any, Dict, List, Optional, Tuple

from engine.entities.npc import NPC


class ReputationTracker:
    """Tracks player social standing across all settlements (-100 to +100)."""

    def __init__(self) -> None:
        self.scores: Dict[str, float] = {}

    def get_score(self, settlement_id: str) -> float:
        return self.scores.get(settlement_id, 0.0)

    def modify(self, settlement_id: str, delta: float) -> Tuple[float, str]:
        current = self.scores.get(settlement_id, 0.0)
        new_val = max(-100.0, min(100.0, current + delta))
        self.scores[settlement_id] = new_val
        return new_val, self.get_title(settlement_id)

    def get_title(self, settlement_id: str) -> str:
        score = self.get_score(settlement_id)
        if score <= -50.0:
            return "Outlaw"
        elif score <= -10.0:
            return "Suspicious Stranger"
        elif score <= 20.0:
            return "Unknown Traveler"
        elif score <= 50.0:
            return "Known Helper"
        elif score <= 80.0:
            return "Trusted Citizen"
        else:
            return "Regional Folk Hero"


class InteractionEngine:
    """Manages player interactions with simulated NPCs and generates organic dialogue."""

    def __init__(self) -> None:
        self.active_npc: Optional[NPC] = None
        self.menu_open: bool = False
        self.dialogue_history: List[str] = []
        self.reputation = ReputationTracker()

    def open_interaction(self, npc: NPC) -> None:
        self.active_npc = npc
        self.menu_open = True
        self.dialogue_history.clear()
        standing = self.reputation.get_title(npc.settlement_id)
        score = self.reputation.get_score(npc.settlement_id)
        self.dialogue_history.append(
            f"Approached {npc.name} ({npc.profession}, Clan {npc.last_name})."
        )
        self.dialogue_history.append(
            f"Location: {npc.settlement_name} | Standing: {standing} ({score:+.0f})"
        )
        self.dialogue_history.append(f"Current Activity: {npc.current_activity}")

    def close_interaction(self) -> None:
        self.menu_open = False
        self.active_npc = None

    def execute_action(self, action: str, player: any, app: any = None) -> str:
        if not self.active_npc:
            return "No NPC selected."

        npc = self.active_npc
        set_id = npc.settlement_id

        if action == "talk":
            greeting = self._generate_dialogue(npc, player)
            self.dialogue_history.append(f"{npc.name}: \"{greeting}\"")
            return greeting

        elif action == "help":
            # Helping the village boosts settlement reputation and defensibility/food
            new_score, title = self.reputation.modify(set_id, +25.0)
            npc.affinity_to_player += 30.0

            # Record into historical chronicle if app/bridge provided
            if app and hasattr(app, "bridge"):
                year = (app.bridge.total_simulated_ticks // 12) + 1
                app.bridge.recent_chronicle_events.append(
                    f"[Year {year}] PATRONAGE: Traveler provided vital labor & supplies to {npc.settlement_name}, "
                    f"earning the gratitude of Clan {npc.last_name}! (Standing: {title})"
                )

            resp = (
                f"{npc.name} (Clan {npc.last_name}): \"May the ancestors bless your generosity, traveler! "
                f"You have aided our hearth in {npc.settlement_name}. Our clan shall not forget this!\" "
                f"(Reputation: +25 -> {title})"
            )
            self.dialogue_history.append(resp)
            return resp

        elif action == "gift":
            npc.affinity_to_player += 15.0
            new_score, title = self.reputation.modify(set_id, +5.0)
            resp = f"{npc.name} accepts your offering with a warm bow. (Affinity: +15, Reputation: +5)"
            self.dialogue_history.append(resp)
            return resp

        elif action == "trade":
            standing = self.reputation.get_title(set_id)
            if standing == "Outlaw":
                resp = f"{npc.name} spits: \"We do not trade with condemned outlaws! Begone!\""
            elif standing == "Suspicious Stranger":
                resp = f"{npc.name}: \"Prices are doubled for outsiders. 5x Oak Planks (Cost: 10 Stone).\""
            elif standing in ("Trusted Citizen", "Regional Folk Hero"):
                resp = f"{npc.name}: \"For our honored friend, best trade rates: 15x Planks, 10x Bread, 4x Copper.\""
            else:
                resp = f"{npc.name} displays village goods: 10x Loam Dirt, 5x Oak Planks, 2x Native Copper."
            self.dialogue_history.append(resp)
            return resp

        elif action == "steal":
            success = (random.random() < 0.40)
            if success:
                resp = f"You deftly pickpocketed 3x Silver Ore from {npc.name} undetected!"
            else:
                npc.affinity_to_player -= 50.0
                npc.is_hostile = True
                new_score, title = self.reputation.modify(set_id, -30.0)
                resp = f"CAUGHT! {npc.name} shouts: \"Thief! Guards, seize this scoundrel!\" (Reputation: -30 -> {title})"
                if app and hasattr(app, "_alert_nearby_guards"):
                    app._alert_nearby_guards(npc)
            self.dialogue_history.append(resp)
            return resp

        elif action == "attack":
            npc.health = max(0.0, npc.health - 6.0)
            npc.affinity_to_player = -100.0
            new_score, title = self.reputation.modify(set_id, -60.0)

            if npc.health <= 0:
                npc.alive = False
                resp = f"FATAL BLOW! You struck down {npc.name}! The settlement cries out in agony! (Standing: {title})"
            else:
                npc.is_hostile = True
                resp = f"You struck {npc.name} (Health: {npc.health:.1f}/20)! They brandish steel!"

            self.dialogue_history.append(resp)

            # Trigger family grief & witness vengeance in app
            if app:
                player_pos = (player.x, player.y, player.z)
                for other in getattr(app, "npcs", []):
                    if other.settlement_id == npc.settlement_id:
                        witness_cry = other.kin_react_to_violence(npc, player_pos)
                        if witness_cry:
                            self.dialogue_history.append(witness_cry)

                # Record murder/crime to historical chronicle
                if hasattr(app, "bridge"):
                    year = (app.bridge.total_simulated_ticks // 12) + 1
                    verb = "slaughtered" if not npc.alive else "assaulted"
                    app.bridge.recent_chronicle_events.append(
                        f"[Year {year}] BLOOD-FEUD: Traveler {verb} {npc.name} in {npc.settlement_name}! "
                        f"Clan {npc.last_name} swears eternal vengeance! (Player branded: {title})"
                    )

            return resp

        return "Unknown action."

    def _generate_dialogue(self, npc: NPC, player: any) -> str:
        standing = self.reputation.get_title(npc.settlement_id)

        # 1. Hostile or Outlaw
        if npc.is_hostile or standing == "Outlaw":
            return f"Draw no closer, murderer! The steel of Clan {npc.last_name} will taste your blood!"

        # 2. Suspicious
        if standing == "Suspicious Stranger":
            return f"Keep your hands where the watch can see them, traveler. We have no love for wandering vagabonds."

        # 3. Known Helper or Hero
        if standing in ("Known Helper", "Trusted Citizen", "Regional Folk Hero"):
            greetings = [
                f"Welcome back, honored friend! Clan {npc.last_name} always has a warm hearth for you.",
                f"Greetings! Since you aided our village, the granary is secure and the folk rest easy.",
                f"Hail, benefactor of {npc.settlement_name}! Even the children know your deeds.",
            ]
            return random.choice(greetings)

        # 4. Neutral / Unknown Traveler
        # Check clan feuds first
        if npc.rival_family_names and (hash(npc.name) % 2 == 0):
            rival = npc.rival_family_names[0]
            return (
                f"I am {npc.name} of Clan {npc.last_name}. A word of counsel: steer clear of the {rival} clan. "
                "Their elders have held a bitter grudge against our family since the famine of Year 14."
            )

        # Profession-specific dialogue
        if npc.profession in ("Smith", "Blacksmith"):
            return (
                f"I am {npc.name}, forge-master of {npc.settlement_name}. If you bring iron ore from the deep crags, "
                "I can hammer honest tools for the harvest."
            )
        elif npc.profession == "Farmer":
            return (
                f"Peace upon you, traveler. Our barley fields stretch south to the river. "
                f"May the rains hold so our kin do not starve when winter falls."
            )
        elif npc.profession in ("Priest", "Scholar", "Scribe"):
            return (
                f"Greetings in the grace of {npc.faith}. I tend the sacred scrolls of {npc.settlement_name}. "
                "Every birth, marriage, and passing is recorded in our parchment archives."
            )
        elif npc.is_guard:
            return (
                f"Hold, traveler. I stand watch for {npc.settlement_name}. Keep the peace, obey the night curfew, "
                "and no harm shall befall you."
            )
        elif npc.spouse_name:
            return (
                f"Good day to you. My spouse {npc.spouse_name} and I have lived in {npc.settlement_name} for thirty winters. "
                "We welcome peaceful wanderers."
            )

        return (
            f"Greetings, traveler. I am {npc.name}. May your journey across our valley bring you prosperity."
        )
