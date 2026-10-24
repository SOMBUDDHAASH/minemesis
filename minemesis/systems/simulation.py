"""
Master Deterministic Simulation Loop.

Adheres strictly to agent.md Architecture Freeze v1.0 and Milestone 0.5:
- Deterministic execution with fixed update order.
- Event Log is the objective single source of truth.
- Characters react strictly to: Event -> Perception -> Belief -> Memory -> Relationship -> Decision -> Event.
- Continuous TradeRoute state management.
- Dynamic belief supersession and memory re-appraisal.
"""

from __future__ import annotations
from typing import Callable, Optional, Set
from minemesis.core.event_log import Event, EventLog
from minemesis.core.invariants import InvariantViolationError, validate_event_actors_alive
from minemesis.core.types import EventType
from minemesis.models.belief import Belief
from minemesis.models.character import Character
from minemesis.models.memory import Memory
from minemesis.models.relationship import Relationship, compute_relationship
from minemesis.models.settlement import Settlement, TradeRoute
from minemesis.systems.conflict import ActiveFeud, process_conflicts_and_economy
from minemesis.systems.gossip import propagate_gossip
from minemesis.systems.life_cycle import process_life_cycle
from minemesis.systems.memory_system import form_memories_from_belief
from minemesis.systems.perception import perceive_event
from minemesis.systems.world_gen import generate_world


class Simulation:
    def __init__(self, seed: int) -> None:
        self.seed = seed
        self.tick = 0
        self.event_log = EventLog()
        self.settlements, self.characters = generate_world(seed)
        
        # Continuous state (Section 4.2)
        self.trade_routes: dict[tuple[str, str], TradeRoute] = {}
        self.active_trade_route_events: dict[tuple[str, str], int] = {}
        self.last_raid_ticks: dict[tuple[str, str], int] = {}

        # Subjective state
        self.beliefs_by_character: dict[str, dict[int, Belief]] = {
            c_id: {} for c_id in self.characters.keys()
        }
        self.memories: list[Memory] = []
        self.superseded_memory_ids: set[int] = set()

        self.active_feuds: list[ActiveFeud] = []
        self.marriage_events: dict[tuple[str, str], int] = {}
        self.collapsed_settlements: set[str] = set()
        
        # Monotonic counters
        self.char_counter = [len(self.characters)]
        self.belief_counter = [0]
        self.memory_counter = [0]

        # Optional Standalone Religion Engine (Milestone R0)
        try:
            from minemesis.religion.religion_config import ENABLE_RELIGION_ENGINE
            from minemesis.religion.religion_engine import ReligionEngine
            self.religion_engine: Optional[ReligionEngine] = (
                ReligionEngine(seed=self.seed, enabled=ENABLE_RELIGION_ENGINE)
            )
            if self.religion_engine and self.religion_engine.enabled:
                self.religion_engine.initialize(
                    seed=self.seed,
                    settlements=self.settlements,
                    characters=self.characters,
                )
        except ImportError:
            self.religion_engine = None

        # Procedural Literature Engine (Milestone L0)
        try:
            from minemesis.lore.lore_engine import LoreEngine, ENABLE_LORE_ENGINE
            self.lore_engine: Optional[LoreEngine] = (
                LoreEngine(seed=self.seed, enabled=ENABLE_LORE_ENGINE)
            )
        except ImportError:
            self.lore_engine = None

    def get_character_religion(self, character_id: str):
        """Returns the Religion object adhered to by a character, or None."""
        if self.religion_engine:
            return self.religion_engine.get_character_religion(character_id)
        return None

    def get_settlement_religion(self, settlement_id: str):
        """Returns the dominant Religion of a settlement, or None."""
        if self.religion_engine:
            return self.religion_engine.get_settlement_religion(settlement_id)
        return None

    def get_religion_modifiers(self, target_id: str) -> dict[str, float]:
        """Returns active religion modifiers for character, settlement, or religion ID."""
        if self.religion_engine:
            return self.religion_engine.get_religion_modifiers(target_id)
        return {}

    def generate_religious_analytics(self):
        """Generates comprehensive religious analytics and chronicle report."""
        if self.religion_engine and self.religion_engine.enabled:
            return self.religion_engine.generate_analytics(
                settlements=self.settlements,
                characters=self.characters,
                event_log=self.event_log,
                current_tick=self.tick,
            )
        return None

    def get_settlement_books(self, settlement_id: str, library_type=None):
        """Returns all books stored in a settlement's libraries and archives."""
        if self.lore_engine and self.lore_engine.enabled:
            return self.lore_engine.get_settlement_books(settlement_id, library_type)
        return []

    def get_book(self, book_id: str):
        """Retrieves a book by its unique ID."""
        if self.lore_engine and self.lore_engine.enabled:
            return self.lore_engine.get_book(book_id)
        return None

    def export_minecraft_book(self, book_id: str):
        """Exports a book to Minecraft Written Book JSON structure."""
        if self.lore_engine and self.lore_engine.enabled:
            return self.lore_engine.export_minecraft_book(book_id)
        return None

    def get_relationship(self, source_id: str, target_id: str) -> Relationship:
        """
        Dynamically computes the relationship view between two characters from active memories.
        Authoritative source of truth is NEVER relationships.
        Excludes memories stemming from superseded beliefs (Section 4.4).
        """
        if source_id not in self.characters or target_id not in self.characters:
            return Relationship(source_id, target_id, 0.0, 0.0, 0.0, 0.0, 0.0)

        source = self.characters[source_id]
        target = self.characters[target_id]

        is_child = target.id in source.children_ids
        is_parent = target.id in (source.father_id, source.mother_id)
        is_sibling = (
            (source.father_id is not None and source.father_id == target.father_id)
            or (source.mother_id is not None and source.mother_id == target.mother_id)
        )
        is_family = is_child or is_parent or is_sibling
        is_spouse = source.spouse_id == target.id
        same_settlement = source.settlement_id == target.settlement_id

        source_memories = [m for m in self.memories if m.observer_id == source_id]

        base_rel = compute_relationship(
            source_id=source_id,
            target_id=target_id,
            memories=source_memories,
            current_tick=self.tick,
            is_family=is_family,
            is_spouse=is_spouse,
            same_settlement=same_settlement,
            superseded_memory_ids=self.superseded_memory_ids,
        )

        if self.religion_engine and self.religion_engine.enabled:
            faith_a = self.religion_engine.get_character_faith(source_id)
            faith_b = self.religion_engine.get_character_faith(target_id)
            rel_a = self.religion_engine.get_character_religion(source_id)
            rel_b = self.religion_engine.get_character_religion(target_id)
            if faith_a and faith_b and rel_a and rel_b:
                from minemesis.religion.religion_tensions import calculate_religious_relationship_modifier
                t_off, h_off, f_off, _ = calculate_religious_relationship_modifier(
                    faith_a=faith_a,
                    faith_b=faith_b,
                    rel_a=rel_a,
                    rel_b=rel_b,
                    all_religions=self.religion_engine.religions,
                )
                if t_off != 0.0 or h_off != 0.0 or f_off != 0.0:
                    return Relationship(
                        source_id=source_id,
                        target_id=target_id,
                        trust=max(-100.0, min(100.0, base_rel.trust + t_off)),
                        fear=max(0.0, min(100.0, base_rel.fear + f_off)),
                        respect=base_rel.respect,
                        hatred=max(0.0, min(100.0, base_rel.hatred + h_off)),
                        loyalty=base_rel.loyalty,
                    )

        return base_rel

    def _register_and_perceive_events(self, events_before: int) -> None:
        """
        Runs perception and memory formation for all events added since events_before.
        """
        new_events = self.event_log.all_events()[events_before:]
        for evt in new_events:
            validate_event_actors_alive(evt, self.characters)
            # R1.8: Evaluate character action against virtues
            if self.religion_engine and self.religion_engine.enabled:
                actor_id = evt.participants_dict.get("actor") or evt.participants_dict.get("instigator_char") or evt.participants_dict.get("initiator")
                if actor_id and actor_id in self.characters:
                    a_char = self.characters[actor_id]
                    a_faith = self.religion_engine.get_character_faith(actor_id)
                    a_rel = self.religion_engine.get_character_religion(actor_id)
                    if a_faith and a_rel:
                        from minemesis.religion.religion_virtues import evaluate_action_against_virtues
                        evaluate_action_against_virtues(
                            character=a_char,
                            faith=a_faith,
                            religion=a_rel,
                            action_type=evt.type,
                            action_role="actor",
                            action_payload=evt.payload,
                        )

            # 1. Perception: Event -> Beliefs
            new_beliefs = perceive_event(
                event=evt,
                characters=self.characters,
                get_relationship=self.get_relationship,
                seed=self.seed,
                belief_counter=self.belief_counter,
            )
            for b in new_beliefs:
                # Milestone R1.1: Religion Interpretation Filter
                if self.religion_engine and self.religion_engine.enabled:
                    observer = self.characters.get(b.believer_id)
                    if observer:
                        faith = self.religion_engine.get_character_faith(b.believer_id)
                        rel = self.religion_engine.get_character_religion(b.believer_id)
                        from minemesis.religion.religion_interpretation import apply_religious_interpretation_filter
                        b = apply_religious_interpretation_filter(
                            belief=b,
                            observer=observer,
                            faith=faith,
                            religion=rel,
                            event_intent=evt.intent,
                            rng=self.religion_engine.rng,
                        )

                char_beliefs = self.beliefs_by_character.setdefault(b.believer_id, {})
                char_beliefs[b.event_ref] = b

                # 2. Memory: Belief -> Memories
                new_mems = form_memories_from_belief(
                    belief=b,
                    characters=self.characters,
                    next_memory_id=self.memory_counter[0],
                    tick=self.tick,
                )
                self.memory_counter[0] += len(new_mems)
                self.memories.extend(new_mems)

    def step_month(self) -> None:
        """
        Executes a single monthly simulation tick in strictly deterministic order.
        """
        # Directive 4: Stop on world extinction (pop == 0)
        if len(self.living_characters) == 0:
            return

        # Ensure belief maps exist for newly born characters
        for c_id in self.characters.keys():
            if c_id not in self.beliefs_by_character:
                self.beliefs_by_character[c_id] = {}

        # -------------------------------------------------------------
        # Step 1: Life Cycle (Marriages, Births, Deaths)
        # -------------------------------------------------------------
        events_start = len(self.event_log)
        process_life_cycle(
            characters=self.characters,
            settlements=self.settlements,
            event_log=self.event_log,
            marriage_events=self.marriage_events,
            active_trade_route_events=self.active_trade_route_events,
            get_relationship=self.get_relationship,
            tick=self.tick,
            seed=self.seed,
            char_counter=self.char_counter,
        )
        self._register_and_perceive_events(events_start)

        # -------------------------------------------------------------
        # Step 2: Knowledge Propagation (Gossip / Rumors)
        # -------------------------------------------------------------
        gossip_beliefs = propagate_gossip(
            characters=self.characters,
            beliefs_by_character=self.beliefs_by_character,
            get_relationship=self.get_relationship,
            tick=self.tick,
            seed=self.seed,
            belief_counter=self.belief_counter,
        )
        for b in gossip_beliefs:
            char_beliefs = self.beliefs_by_character.setdefault(b.believer_id, {})
            char_beliefs[b.event_ref] = b
            gossip_mems = form_memories_from_belief(
                belief=b,
                characters=self.characters,
                next_memory_id=self.memory_counter[0],
                tick=self.tick,
            )
            self.memory_counter[0] += len(gossip_mems)
            self.memories.extend(gossip_mems)

        # -------------------------------------------------------------
        # Step 3: Conflict, Scarcity, Trade Routes, Leadership, Peace
        # -------------------------------------------------------------
        conflict_start = len(self.event_log)
        process_conflicts_and_economy(
            characters=self.characters,
            settlements=self.settlements,
            trade_routes=self.trade_routes,
            active_trade_route_events=self.active_trade_route_events,
            last_raid_ticks=self.last_raid_ticks,
            collapsed_settlements=self.collapsed_settlements,
            beliefs_by_character=self.beliefs_by_character,
            memories=self.memories,
            superseded_memory_ids=self.superseded_memory_ids,
            event_log=self.event_log,
            active_feuds=self.active_feuds,
            get_relationship=self.get_relationship,
            tick=self.tick,
            seed=self.seed,
            belief_counter=self.belief_counter,
            memory_counter=self.memory_counter,
        )
        self._register_and_perceive_events(conflict_start)

        # -------------------------------------------------------------
        # Step 4: Standalone Religion Engine (Milestone R0 & R1)
        # -------------------------------------------------------------
        if self.religion_engine and self.religion_engine.enabled:
            # Register newly born characters if any
            for c_id, c in self.characters.items():
                if c_id not in self.religion_engine.faiths:
                    self.religion_engine.register_newborn(
                        child_id=c_id,
                        father_id=c.father_id,
                        mother_id=c.mother_id,
                        settlement_id=c.settlement_id,
                        tick=self.tick,
                    )

            # Gather deaths from this month for martyrdom / saint checks
            recent_deaths = []
            for evt in self.event_log.all_events()[events_start:]:
                if evt.type == EventType.DEATH:
                    deceased_id = evt.participants_dict.get("deceased") or evt.participants_dict.get("target") or evt.participants_dict.get("victim")
                    if deceased_id and deceased_id in self.characters:
                        d_char = self.characters[deceased_id]
                        cause_type = EventType.DEATH
                        if evt.causes:
                            prior_evt = self.event_log.get_event(evt.causes[0])
                            if prior_evt:
                                cause_type = prior_evt.type
                        recent_deaths.append((d_char, cause_type, evt.id))

            religion_start = len(self.event_log)
            self.religion_engine.update_tick(
                tick=self.tick,
                event_log=self.event_log,
                settlements=self.settlements,
                characters=self.characters,
                active_trade_routes=self.trade_routes,
                recent_deaths=recent_deaths,
            )
            self._register_and_perceive_events(religion_start)

        # -------------------------------------------------------------
        # Step 5: Standalone Procedural Literature Engine (Milestone L0)
        # -------------------------------------------------------------
        if self.lore_engine and self.lore_engine.enabled:
            recent_month_events = self.event_log.all_events()[events_start:]
            lore_start = len(self.event_log)
            self.lore_engine.update_tick(
                tick=self.tick,
                event_log=self.event_log,
                characters=self.characters,
                settlements=self.settlements,
                beliefs_by_character=self.beliefs_by_character,
                memories=self.memories,
                religion_engine=self.religion_engine,
                trade_routes=self.trade_routes,
                recent_events=recent_month_events,
            )
            self._register_and_perceive_events(lore_start)

        # -------------------------------------------------------------
        # Step 6: Advance Simulation Tick
        # -------------------------------------------------------------
        self.tick += 1

    def run_years(self, years: int) -> None:
        """
        Runs the simulation for the specified number of simulated years (12 ticks/year).
        Terminates immediately if living population drops to 0 (world extinction).
        """
        total_ticks = years * 12
        for _ in range(total_ticks):
            if len(self.living_characters) == 0:
                break
            self.step_month()

    @property
    def living_characters(self) -> list[Character]:
        return [c for c in self.characters.values() if c.alive]

    @property
    def current_year(self) -> int:
        return self.tick // 12
