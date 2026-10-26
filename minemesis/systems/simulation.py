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
import gc
from typing import Any, Callable, Optional, Set
from minemesis.core.event_log import Event, EventLog
from minemesis.core.invariants import InvariantViolationError, validate_event_actors_alive
from minemesis.core.types import EventType
from minemesis.models.belief import Belief
from minemesis.models.character import Character
from minemesis.models.memory import Memory
from minemesis.core.seed import SeedPair
from minemesis.models.relationship import Relationship, compute_relationship
from minemesis.models.settlement import Settlement, TradeRoute
from minemesis.models.demographics import DemographicRegistry
from minemesis.core.diplomacy import DiplomacyManager
from minemesis.systems.player_system import PlayerSystem
from minemesis.core.knowledge import KnowledgeEngine, KnowledgeOwnerType, KnowledgeTargetType
from minemesis.core.relationship_cache import RelationshipCache
from minemesis.systems.conflict import ActiveFeud, process_conflicts_and_economy
from minemesis.systems.gossip import propagate_gossip
from minemesis.systems.life_cycle import process_life_cycle
from minemesis.systems.memory_system import form_memories_from_belief
from minemesis.systems.perception import perceive_event
from minemesis.systems.world_gen import generate_world
from minemesis.systems.world_spec import WorldSpec


class Simulation:
    def __init__(
        self,
        seed: int | SeedPair | None = None,
        world_seed: Optional[int] = None,
        history_seed: Optional[int] = None,
        chronicle_seed: Optional[int] = None,
        enable_religion: Optional[bool] = None,
        enable_lore: Optional[bool] = None,
        world_provider: Optional[Any] = None,
        name_salt: int = 0,
        export_sink: Optional[Any] = None,
    ) -> None:
        self.export_sink = None
        h_seed = history_seed if history_seed is not None else chronicle_seed
        self.legacy_seed: Optional[int] = seed if isinstance(seed, int) else None
        if isinstance(seed, SeedPair):
            self.seed_pair = seed
        elif world_seed is not None and h_seed is not None:
            self.seed_pair = SeedPair(world=world_seed, history=h_seed)
        elif seed is not None:
            self.seed_pair = SeedPair.from_legacy(seed)
        elif world_seed is not None:
            self.seed_pair = SeedPair(world=world_seed, history=keyed_hash_int(world_seed, "default_history", 0, 0))
        elif h_seed is not None:
            self.seed_pair = SeedPair(world=keyed_hash_int(h_seed, "default_world", 0, 0), history=h_seed)
        else:
            self.seed_pair = SeedPair.from_legacy(42)

        self.name_salt = name_salt
        self.world_seed = self.seed_pair.world
        self.history_seed = self.seed_pair.history
        self.chronicle_seed = self.seed_pair.history  # backwards compatible alias
        self.seed = self.legacy_seed if self.legacy_seed is not None else self.history_seed
        self.tick = 0
        self.event_log = EventLog()
        self.settlements, self.characters, self.world_spec = generate_world(
            self.seed_pair, world_provider=world_provider, name_salt=name_salt
        )
        
        # Continuous state (Section 4.2)
        self.trade_routes: dict[tuple[str, str], TradeRoute] = {}
        self.active_trade_route_events: dict[tuple[str, str], int] = {}
        self.last_raid_ticks: dict[tuple[str, str], int] = {}

        # Subjective state
        self.beliefs_by_character: dict[str, dict[int, Belief]] = {
            c_id: {} for c_id in self.characters.keys()
        }
        self.memories: list[Memory] = []
        self.memories_by_observer: dict[str, list[Memory]] = {}
        self.superseded_memory_ids: set[int] = set()

        self.active_feuds: list[ActiveFeud] = []
        self.marriage_events: dict[tuple[str, str], int] = {}
        self.collapsed_settlements: set[str] = set()
        self.resolved_grievance_event_ids: set[int] = set()
        
        # Demographic Cohorts & Population Layering (Milestone 4)
        self.demographics = DemographicRegistry(
            world_seed=self.world_seed, history_seed=self.history_seed
        )
        for s in self.settlements.values():
            base_bg = max(50, int(80 * s.farmland))
            self.demographics.add_population(s.id, "child", "M", int(base_bg * 0.15), profession="Child")
            self.demographics.add_population(s.id, "child", "F", int(base_bg * 0.15), profession="Child")
            self.demographics.add_population(s.id, "young_adult", "M", int(base_bg * 0.20), profession="Laborer")
            self.demographics.add_population(s.id, "young_adult", "F", int(base_bg * 0.20), profession="Laborer")
            self.demographics.add_population(s.id, "adult", "M", int(base_bg * 0.12), profession="Farmer")
            self.demographics.add_population(s.id, "adult", "F", int(base_bg * 0.12), profession="Farmer")
            self.demographics.add_population(s.id, "elder", "M", int(base_bg * 0.03), profession="Elder")
            self.demographics.add_population(s.id, "elder", "F", int(base_bg * 0.03), profession="Elder")

        # Epistemic & Performance Systems (Milestone 0.5.4)
        self.knowledge_engine = KnowledgeEngine()
        self.relationship_cache = RelationshipCache(default_ttl_ticks=12)
        self.historical_archive: dict[str, dict[str, Any]] = {}
        self.diplomacy = DiplomacyManager()

        # Monotonic counters
        self.char_counter = [len(self.characters)]
        self.belief_counter = [0]
        self.memory_counter = [0]

        # Optional Standalone Religion Engine (Milestone R0)
        try:
            from minemesis.religion.religion_config import ENABLE_RELIGION_ENGINE
            from minemesis.religion.religion_engine import ReligionEngine
            r_enabled = ENABLE_RELIGION_ENGINE if enable_religion is None else enable_religion
            self.religion_engine: Optional[ReligionEngine] = (
                ReligionEngine(seed=self.seed, enabled=r_enabled)
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
            l_enabled = ENABLE_LORE_ENGINE if enable_lore is None else enable_lore
            self.lore_engine: Optional[LoreEngine] = (
                LoreEngine(seed=self.seed, enabled=l_enabled)
            )
        except ImportError:
            self.lore_engine = None

        # Player as Simulation Actor (Milestone 3)
        self.player_system = PlayerSystem()
        self.player_system.initialize_player(self)

        if export_sink:
            self.set_export_sink(export_sink)

    def set_export_sink(self, sink: Any) -> None:
        """Attaches an export sink and registers listeners."""
        self.export_sink = sink
        if self.export_sink:
            for s in self.settlements.values():
                self.export_sink.record_settlement(
                    id=s.id,
                    name=s.name,
                    founded_tick=0,
                    biome=getattr(s, "biome", "Temperate Forest"),
                    culture=getattr(s, "culture", "Common"),
                )
            self.event_log.add_listener(self._on_event_logged)

    def _on_event_logged(self, evt: Event) -> None:
        """Streams event to export sink."""
        if not self.export_sink:
            return

        part_tuples = []
        for role, entity_id in evt.participants:
            name_at_time = self.resolve_character_name(entity_id)
            part_tuples.append((entity_id, role, name_at_time))

        importance = 1.0
        if evt.type in (EventType.FEUD, EventType.DEATH, EventType.REVELATION, EventType.BOOK_WRITTEN, EventType.SETTLEMENT_COLLAPSE):
            importance = 2.0

        self.export_sink.record_event(
            event_id=evt.id,
            tick=evt.tick,
            year=(evt.tick // 12) + 1,
            event_type=evt.type.value,
            description=evt.description,
            thread_id=None,
            importance=importance,
            participants=part_tuples,
            causes=evt.causes,
        )

        if evt.type in (EventType.FEUD, EventType.FEUD_BEGINS):
            instigator = evt.participants_dict.get("instigator", "")
            target = evt.participants_dict.get("target", "")
            self.export_sink.record_epistemic_case(
                case_id=f"feud_{evt.id}",
                case_type="Feud",
                year=(evt.tick // 12) + 1,
                subject_character_id=target,
                ground_truth=f"Dispute between {self.resolve_character_name(instigator)} and {self.resolve_character_name(target)}",
                believer_character_id=instigator,
                belief_summary=f"Accusation of hostility against {self.resolve_character_name(target)}",
                source_type="DIRECT_OBSERVATION" if not evt.payload.get("is_wrongful") else "WRONGFUL_ASSUMPTION",
                confidence=0.95,
            )
        elif evt.type == EventType.REVELATION:
            rec = evt.participants_dict.get("recipient", "")
            wit = evt.participants_dict.get("witness", "")
            self.export_sink.record_epistemic_case(
                case_id=f"revelation_{evt.id}",
                case_type="Revelation",
                year=(evt.tick // 12) + 1,
                subject_character_id=wit,
                ground_truth=f"Uncovered truth transmitted by {self.resolve_character_name(wit)}",
                believer_character_id=rec,
                belief_summary="Received truthful revelation regarding prior grievances",
                source_type="REVELATION",
                confidence=0.90,
            )
        elif evt.type == EventType.DEATH and evt.payload.get("is_revenge"):
            killer = evt.participants_dict.get("actor", "")
            victim = evt.participants_dict.get("target") or evt.participants_dict.get("deceased", "")
            self.export_sink.record_epistemic_case(
                case_id=f"revenge_{evt.id}",
                case_type="Revenge Killing",
                year=(evt.tick // 12) + 1,
                subject_character_id=victim,
                ground_truth=f"Death of {self.resolve_character_name(victim)} in retribution",
                believer_character_id=killer,
                belief_summary="Retribution enacted for perceived blood debt",
                source_type="VENGEANCE_BELIEF",
                confidence=1.0,
            )
        elif evt.type == EventType.BOOK_WRITTEN and self.lore_engine and self.lore_engine.enabled:
            book_id = evt.payload.get("book_id")
            if book_id:
                book = self.lore_engine.get_book(book_id)
                if book:
                    pages = book.pages
                    self.export_sink.record_book(
                        book_id=book.id,
                        title=book.title,
                        author_id=book.author_id,
                        author_name=book.author_name,
                        year_written=(evt.tick // 12) + 1,
                        settlement_id=book.settlement_id or evt.location,
                        topic=str(getattr(book, "genre", "History")),
                        pages=pages,
                    )
                    book._pages = None

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

    def resolve_character_name(self, char_id: str) -> str:
        """Resolves a character or entity ID to their authentic display_name."""
        if not char_id or str(char_id).strip() in ("", "None", "Unknown", "unknown", "Someone", "someone"):
            return "Citizen"
        if char_id in self.characters:
            c = self.characters[char_id]
            return c.display_name or c.full_name
        if char_id in self.historical_archive:
            arch = self.historical_archive[char_id]
            return arch.get("display_name") or arch.get("name") or "Citizen"
        if char_id in self.settlements:
            return self.settlements[char_id].name
        if self.religion_engine and char_id in self.religion_engine.religions:
            return self.religion_engine.religions[char_id].name
        return str(char_id)

    # -------------------------------------------------------------------------
    # PersonStore Protocol Implementation (Milestone 1 & Milestone 4)
    # -------------------------------------------------------------------------
    def get_person(self, person_id: str) -> Optional[Character]:
        """Returns living or loaded Character from self.characters."""
        return self.characters.get(person_id)

    def materialize_person(self, person_id: str) -> Optional[Character]:
        """Ensures person entity is materialized, reconstructing from archive if needed."""
        if person_id in self.characters:
            return self.characters[person_id]
        if person_id in self.historical_archive:
            arch = self.historical_archive[person_id]
            c = Character(
                id=arch["id"],
                first_name=arch.get("first_name", "Citizen"),
                last_name=arch.get("last_name", "Commoner"),
                settlement_id=arch.get("settlement_id", ""),
                age_ticks=arch.get("age_ticks", 240),
                sex=arch.get("sex", "M"),
                alive=False,
                death_tick=arch.get("death_tick"),
                spouse_id=arch.get("spouse_id"),
                father_id=arch.get("father_id"),
                mother_id=arch.get("mother_id"),
                children_ids=list(arch.get("children_ids", [])),
                profession=arch.get("profession", "Laborer"),
                family_id=arch.get("family_id", ""),
                name_ordinal=arch.get("name_ordinal", 1),
                display_name=arch.get("display_name", arch.get("name", "")),
            )
            return c
        return None

    def is_alive(self, person_id: str) -> bool:
        c = self.characters.get(person_id)
        return c.alive if c else False

    def get_living_ids(self) -> list[str]:
        return [c.id for c in self.characters.values() if c.alive]

    def get_settlement_living_ids(self, settlement_id: str) -> list[str]:
        return [c.id for c in self.characters.values() if c.alive and c.settlement_id == settlement_id]

    def get_settlement_total_population(self, settlement_id: str) -> int:
        """Returns total population of settlement: living promoted + background cohorts."""
        prom = len([c for c in self.characters.values() if c.alive and c.settlement_id == settlement_id])
        bg = self.demographics.get_settlement_population(settlement_id)
        return prom + bg

    def get_total_living_population(self) -> int:
        """Returns total living population across all settlements."""
        prom = len([c for c in self.characters.values() if c.alive])
        bg = self.demographics.get_total_population()
        return prom + bg

    def promote_ordinary_citizen(
        self,
        settlement_id: str,
        age_bracket: str = "adult",
        sex: Optional[str] = None,
        reason: str = "promotion",
    ) -> Optional[Character]:
        """Promotes a background citizen to a full Character entity and records in database."""
        existing_surnames = [c.last_name for c in self.characters.values() if c.settlement_id == settlement_id]
        char = self.demographics.promote_citizen(
            settlement_id=settlement_id,
            age_bracket=age_bracket,
            sex=sex,
            reason=reason,
            tick=self.tick,
            char_counter=self.char_counter,
            existing_surnames=existing_surnames,
            name_salt=self.name_salt,
        )
        if char:
            self.characters[char.id] = char
            self.beliefs_by_character[char.id] = {}
            if self.export_sink:
                self.export_sink.record_character(char)
        return char

    def get_book(self, book_id: str):
        """Retrieves a book by its unique ID."""
        if self.lore_engine and self.lore_engine.enabled:
            return self.lore_engine.get_book(book_id)
        return None

    def get_character_beliefs(self, character_id: str) -> dict[int, Belief]:
        """Read-only query helper: returns a copy of character beliefs."""
        return dict(self.beliefs_by_character.get(character_id, {}))

    def get_all_books(self):
        """Read-only query helper: returns all books penned in simulation."""
        if self.lore_engine and self.lore_engine.enabled:
            return self.lore_engine.library_manager.get_all_books()
        return []

    def export_minecraft_book(self, book_id: str):
        """Exports a book to Minecraft Written Book JSON structure."""
        if self.lore_engine and self.lore_engine.enabled:
            return self.lore_engine.export_minecraft_book(book_id)
        return None

    def execute_player_command(self, command: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executes a player command in the simulation."""
        return self.player_system.execute_command(command, args or {}, self)

    def get_relationship(self, source_id: str, target_id: str) -> Relationship:
        """
        Dynamically computes the relationship view between two characters from active memories
        and collective knowledge consensus, cached in RelationshipCache.
        Authoritative source of truth is NEVER relationships.
        Excludes memories stemming from superseded beliefs (Section 4.4).
        """
        if source_id not in self.characters or target_id not in self.characters:
            return Relationship(source_id, target_id, 0.0, 0.0, 0.0, 0.0, 0.0)

        cached = self.relationship_cache.get(source_id, target_id, self.tick)
        if cached is not None:
            return cached

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

        source_memories = self.memories_by_observer.get(source_id, [])

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

        trust = base_rel.trust
        fear = base_rel.fear
        respect = base_rel.respect
        hatred = base_rel.hatred
        loyalty = base_rel.loyalty

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
                trust += t_off
                hatred += h_off
                fear += f_off

        # Collective Knowledge modifier (M0.5.4)
        if self.knowledge_engine:
            s_fam = getattr(source, "family_id", "") or source.last_name
            t_fam = getattr(target, "family_id", "") or target.last_name
            k_trust, k_hatred, k_respect = self.knowledge_engine.get_reputation_offset(
                observer_settlement_id=source.settlement_id,
                observer_family_id=s_fam,
                target_char_id=target.id,
                target_family_id=t_fam,
                target_settlement_id=target.settlement_id,
            )
            trust += k_trust
            hatred += k_hatred
            respect += k_respect

        final_rel = Relationship(
            source_id=source_id,
            target_id=target_id,
            trust=max(-100.0, min(100.0, trust)),
            fear=max(0.0, min(100.0, fear)),
            respect=max(-100.0, min(100.0, respect)),
            hatred=max(0.0, min(100.0, hatred)),
            loyalty=loyalty,
        )

        self.relationship_cache.put(source_id, target_id, final_rel, self.tick)
        return final_rel

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
                knowledge_engine=self.knowledge_engine,
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
                for m in new_mems:
                    self.memories_by_observer.setdefault(m.observer_id, []).append(m)

                # Invalidate cached relationships for observer
                self.relationship_cache.invalidate_character(b.believer_id)

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
            name_salt=self.name_salt,
        )
        self._register_and_perceive_events(events_start)

        # Step 1b: Demographic Cohorts Background Flows (Milestone 4)
        living_promoted_by_s = {
            s_id: len([c for c in self.characters.values() if c.alive and c.settlement_id == s_id])
            for s_id in self.settlements.keys()
        }
        self.demographics.step_demographics(
            self.settlements,
            living_promoted_by_s,
            self.tick,
            self.seed,
        )

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
            for m in gossip_mems:
                self.memories_by_observer.setdefault(m.observer_id, []).append(m)
            self.relationship_cache.invalidate_character(b.believer_id)

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
            resolved_grievance_event_ids=self.resolved_grievance_event_ids,
        )
        self._register_and_perceive_events(conflict_start)

        # -------------------------------------------------------------
        # Step 3b: Geopolitics & Diplomacy (Milestone 2)
        # -------------------------------------------------------------
        diplomacy_start = len(self.event_log)
        self.diplomacy.step_diplomacy(
            settlements=self.settlements,
            trade_routes=self.trade_routes,
            active_feuds=self.active_feuds,
            marriage_events=self.marriage_events,
            event_log=self.event_log,
            tick=self.tick,
            seed=self.seed,
        )
        self._register_and_perceive_events(diplomacy_start)

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
        # Step 5b: Periodic Epistemic and Memory Lifecycle Compaction (M0.5.4)
        # -------------------------------------------------------------
        if self.tick > 0 and self.tick % 120 == 0:
            self.compact_history()

        # -------------------------------------------------------------
        # Step 5c: Annual Census & Religion Export Telemetry
        # -------------------------------------------------------------
        if self.export_sink and self.tick > 0 and self.tick % 12 == 0:
            year = self.tick // 12
            living_pop_by_s: dict[str, int] = {}
            for c in self.characters.values():
                if c.alive:
                    living_pop_by_s[c.settlement_id] = living_pop_by_s.get(c.settlement_id, 0) + 1
            for s_id, s in self.settlements.items():
                self.export_sink.record_census(
                    year=year,
                    settlement_id=s_id,
                    population=self.get_settlement_total_population(s_id),
                    food=s.food,
                    wealth=s.wealth,
                )
            if self.religion_engine and self.religion_engine.enabled:
                rel_counts: dict[str, int] = {}
                for c in self.characters.values():
                    if c.alive:
                        r = self.religion_engine.get_character_religion(c.id)
                        if r:
                            rel_counts[r.id] = rel_counts.get(r.id, 0) + 1
                for r_id, r in self.religion_engine.religions.items():
                    self.export_sink.record_religion(
                        rel_id=r.id,
                        name=r.name,
                        parent_id=getattr(r, "parent_id", None),
                        founded_year=(getattr(r, "founded_tick", 0) // 12) + 1,
                        founder_id=getattr(r, "founder_id", None),
                        traits=getattr(r, "traits", {}),
                        adherent_count=rel_counts.get(r_id, 0),
                    )
                for r in self.religion_engine.religions.values():
                    for site in getattr(r, "holy_sites", []):
                        self.export_sink.record_holy_site(
                            settlement_id=site.settlement_id,
                            religion_id=r.id,
                            dedication_year=(getattr(site, "consecrated_tick", 0) // 12) + 1,
                        )
                    for myth in getattr(r, "myths", []):
                        self.export_sink.record_myth(
                            myth_id=getattr(myth, "myth_id", getattr(myth, "id", f"m_{r.id}")),
                            religion_id=r.id,
                            title=getattr(myth, "title", "Sacred Lore"),
                            text=getattr(myth, "text", ""),
                            year_recorded=(getattr(myth, "origin_tick", 0) // 12) + 1,
                        )

        # -------------------------------------------------------------
        # Step 6: Advance Simulation Tick
        # -------------------------------------------------------------
        self.tick += 1

    def compact_history(self) -> None:
        """
        Tiered Epistemic and Memory Lifecycle Compaction (Milestone 0.5.4).
        - Tier 0: Living characters retain full state.
        - Tier 1: Recent dead (< 20 years) retained for active feuds/inheritance.
        - Tier 2: Historical dead (> 20 years) archived into compact HistoricalPerson dicts,
                  releasing individual Belief and Memory dict allocations.
        - Prunes decayed insignificant memories (intensity < 0.10) for characters not in feuds.
        - Reclaims heap memory via gc.collect().
        """
        protected_char_ids = set()
        for f in self.active_feuds:
            protected_char_ids.add(f.instigator_char_id)
            protected_char_ids.add(f.target_char_id)
        for s in self.settlements.values():
            if s.leader_id:
                protected_char_ids.add(s.leader_id)

        # 1. Tier 2 Dead Character Compaction (> 240 ticks / 20 years dead)
        for c_id, char in list(self.characters.items()):
            if not char.alive and char.death_tick is not None:
                if (self.tick - char.death_tick) > 240 and c_id not in protected_char_ids:
                    if c_id not in self.historical_archive:
                        self.historical_archive[c_id] = {
                            "id": char.id,
                            "first_name": char.first_name,
                            "last_name": char.last_name,
                            "display_name": char.display_name or char.full_name,
                            "name": char.display_name or char.full_name,
                            "name_ordinal": char.name_ordinal,
                            "age_ticks": char.age_ticks,
                            "sex": char.sex,
                            "birth_tick": (char.death_tick - char.age_ticks) if char.death_tick is not None else 0,
                            "death_tick": char.death_tick,
                            "settlement_id": char.settlement_id,
                            "family_id": getattr(char, "family_id", "") or char.last_name,
                            "father_id": char.father_id,
                            "mother_id": char.mother_id,
                            "spouse_id": char.spouse_id,
                            "children_ids": list(char.children_ids),
                            "profession": char.profession,
                        }
                    if hasattr(self, "export_sink") and self.export_sink:
                        self.export_sink.record_character(char, is_historical=True)
                    # Free individual belief and memory dict entries
                    if c_id in self.beliefs_by_character:
                        self.beliefs_by_character[c_id].clear()
                        del self.beliefs_by_character[c_id]
                    if c_id in self.memories_by_observer:
                        del self.memories_by_observer[c_id]
                    self.relationship_cache.invalidate_character(c_id)

        # 2. Prune decayed emotional memories for living characters
        for c_id, mem_list in list(self.memories_by_observer.items()):
            if c_id not in protected_char_ids and len(mem_list) > 20:
                retained = []
                for m in mem_list:
                    cur_int = m.current_intensity(self.tick)
                    if cur_int >= 0.10 or (self.tick - m.tick_formed) <= 60:
                        retained.append(m)
                self.memories_by_observer[c_id] = retained

        # 3. Clean relationship cache of expired entries
        now = self.tick
        expired = [k for k, v in self.relationship_cache._cache.items() if v[1] < now]
        for k in expired:
            del self.relationship_cache._cache[k]

        # 4. Unload rendered book pages to keep literature memory minimal (Lore Compression)
        if self.lore_engine and self.lore_engine.enabled:
            self.lore_engine.library_manager.unload_all_pages()

        gc.collect()

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

    def finalize_export(self) -> None:
        """Finalizes history export to .minemesis database."""
        if not self.export_sink:
            return
        from datetime import datetime, timezone
        from minemesis.export.schema import BUILD_ID, CURRENT_SCHEMA_VERSION

        # Record all remaining characters
        for char in self.characters.values():
            self.export_sink.record_character(char, is_historical=not char.alive)

        meta_info = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "build_id": BUILD_ID,
            "world_seed": self.world_seed,
            "history_seed": self.history_seed,
            "pair_code": getattr(self.seed_pair, "code", f"{self.world_seed}:{self.history_seed}"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "duration_ticks": self.tick,
        }
        self.export_sink.finalize(meta_info)
