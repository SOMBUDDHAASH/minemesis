"""
Religion Engine Orchestrator (Milestone R0).

Core Philosophy:
- Operates as a self-contained, standalone plugin.
- Exposes clean published interfaces for external engines without leaking internal complexity.
- Implements the complete lifecycle: generation, social spread, evolution, schisms, and behavioral effects.
- Can be cleanly toggled on/off via ENABLE_RELIGION_ENGINE with zero impact on other systems.
"""

from __future__ import annotations
import random
from typing import Any, Mapping, Optional, Sequence

from minemesis.religion.religion_config import (
    CLERGY_POPULATION_RATIO,
    DEVOTION_DECAY_RATE,
    ENABLE_RELIGION_ENGINE,
    INITIAL_RELIGIONS_PER_WORLD,
    PILGRIMAGE_CHANCE,
    REFORMATION_CHANCE_ON_CRISIS,
    SCHISM_CHANCE_PER_TICK,
)
from minemesis.religion.religion_effects import (
    get_character_effective_modifiers,
    get_character_modifier,
    get_religion_aggregate_modifiers,
    get_settlement_consumption_multiplier,
)
from minemesis.religion.religion_generation import generate_world_religions
from minemesis.religion.religion_models import (
    CharacterFaith,
    HolySite,
    Religion,
    ReligiousRole,
    Saint,
)
from minemesis.religion.religion_schisms import (
    check_and_canonize_saint,
    trigger_religious_reformation,
    trigger_religious_schism,
)
from minemesis.religion.religion_serialization import (
    deserialize_religion_state,
    serialize_religion_state,
)
from minemesis.religion.religion_spread import (
    process_clergy_missionary_work,
    process_family_faith_inheritance,
    process_marriage_conversion,
    process_trade_route_evangelism,
    update_settlement_dominant_religions,
)


class ReligionEngine:
    """
    Self-contained Religion Engine subsystem.
    """

    def __init__(self, seed: int = 42, enabled: bool | None = None) -> None:
        self.seed = seed
        self.enabled = ENABLE_RELIGION_ENGINE if enabled is None else enabled
        self.rng = random.Random(seed + 777)
        self.religions: dict[str, Religion] = {}
        self.faiths: dict[str, CharacterFaith] = {}
        self.rel_counter = 1
        self.site_counter = 1
        self.dominant_by_settlement: dict[str, str] = {}

    def initialize(
        self,
        seed: int | None = None,
        settlements: Mapping[str, Any] | None = None,
        characters: Mapping[str, Any] | None = None,
    ) -> None:
        """
        Initializes the religion engine, generating starting faiths and assigning them to settlements/characters.
        """
        if seed is not None:
            self.seed = seed
            self.rng = random.Random(seed + 777)

        if not self.enabled:
            return

        settlement_ids = list(settlements.keys()) if settlements else ["set_oakhaven", "set_riverbend", "set_ironpeak"]
        self.religions = generate_world_religions(
            seed=self.seed,
            num_religions=INITIAL_RELIGIONS_PER_WORLD,
            settlement_ids=settlement_ids,
        )
        self.rel_counter = len(self.religions) + 1

        # Populate initial faiths for characters if provided
        if characters:
            char_list = sorted(list(characters.values()), key=lambda c: c.id)
            for idx, char in enumerate(char_list):
                # Assign religion matching settlement or alternating
                s_id = char.settlement_id
                target_rel_id = None
                for r_id, r in sorted(self.religions.items()):
                    if s_id in r.dominant_settlements:
                        target_rel_id = r_id
                        break
                if not target_rel_id:
                    rel_keys = sorted(list(self.religions.keys()))
                    target_rel_id = rel_keys[idx % len(rel_keys)]

                # Assign role: a small percentage become clergy
                is_clergy = self.rng.random() < CLERGY_POPULATION_RATIO
                role = self.rng.choice([ReligiousRole.PRIEST, ReligiousRole.SHAMAN, ReligiousRole.MONK]) if is_clergy else ReligiousRole.LAITY
                devotion = round(self.rng.uniform(0.7, 0.95) if is_clergy else self.rng.uniform(0.4, 0.8), 3)

                c_faith = CharacterFaith(
                    character_id=char.id,
                    religion_id=target_rel_id,
                    devotion=devotion,
                    conversion_tick=0,
                    role=role,
                    is_zealot=is_clergy and (devotion > 0.85),
                )
                self.faiths[char.id] = c_faith

            if settlements:
                self.dominant_by_settlement = update_settlement_dominant_religions(
                    settlements=settlements,
                    living_characters=char_list,
                    faiths=self.faiths,
                    religions=self.religions,
                )

    def generate_religions(self, settlement_ids: Sequence[str] = ()) -> dict[str, Religion]:
        """Procedurally generates emergent religions."""
        if not self.enabled:
            return {}
        self.religions = generate_world_religions(
            seed=self.seed,
            num_religions=INITIAL_RELIGIONS_PER_WORLD,
            settlement_ids=settlement_ids,
        )
        self.rel_counter = len(self.religions) + 1
        return self.religions

    def register_newborn(
        self,
        child_id: str,
        father_id: str | None,
        mother_id: str | None,
        settlement_id: str | None,
        tick: int,
    ) -> CharacterFaith | None:
        """Assigns inherited faith to a newborn child."""
        if not self.enabled:
            return None

        father_faith = self.faiths.get(father_id) if father_id else None
        mother_faith = self.faiths.get(mother_id) if mother_id else None
        dom_rel = self.dominant_by_settlement.get(settlement_id) if settlement_id else None

        child_faith = process_family_faith_inheritance(
            child_id=child_id,
            father_faith=father_faith,
            mother_faith=mother_faith,
            settlement_dominant_rel_id=dom_rel,
            rng=self.rng,
            tick=tick,
        )
        if child_faith:
            self.faiths[child_id] = child_faith
        return child_faith

    def update_tick(
        self,
        tick: int,
        event_log: Any = None,
        settlements: Mapping[str, Any] | None = None,
        characters: Mapping[str, Any] | None = None,
        active_trade_routes: Any = None,
        recent_deaths: Sequence[Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Executes one monthly tick of religious simulation:
        1. Social spread (marriage, trade routes, missionaries).
        2. Evolution (crisis reformations, saint canonization).
        3. Schisms & sect formation.
        4. Devotion decay & maintenance.
        5. Recalculate settlement dominant faiths.
        """
        if not self.enabled:
            return []

        emitted_events: list[dict[str, Any]] = []
        living = [c for c in characters.values() if c.alive] if characters else []

        # 1. Saint canonization for recent deaths
        if recent_deaths:
            for d_char, cause_type, d_event_id in recent_deaths:
                c_faith = self.faiths.get(d_char.id)
                rel = self.religions.get(c_faith.religion_id) if c_faith else None
                canon_res = check_and_canonize_saint(
                    deceased_char=d_char,
                    deceased_faith=c_faith,
                    religion=rel,
                    cause_of_death=cause_type,
                    tick=tick,
                    rng=self.rng,
                )
                if canon_res:
                    saint, r = canon_res
                    event_data = {
                        "type": "SaintCanonized",
                        "tick": tick,
                        "location": d_char.settlement_id,
                        "causes": [d_event_id] if d_event_id is not None else [],
                        "participants": [("saint", saint.character_name), ("religion", r.name)],
                        "payload": saint.to_dict(),
                    }
                    emitted_events.append(event_data)
                    self._emit_to_event_log(event_log, event_data)

        # 2. Marriage conversion
        if living:
            processed_pairs = set()
            for c in living:
                if c.spouse_id and c.spouse_id in self.faiths and c.id in self.faiths:
                    pair_key = tuple(sorted([c.id, c.spouse_id]))
                    if pair_key not in processed_pairs:
                        processed_pairs.add(pair_key)
                        conv = process_marriage_conversion(
                            self.faiths[c.id],
                            self.faiths[c.spouse_id],
                            self.rng,
                            tick,
                        )
                        if conv:
                            c_id, old_rel, new_rel = conv
                            event_data = {
                                "type": "Conversion",
                                "tick": tick,
                                "location": c.settlement_id,
                                "causes": [],
                                "participants": [("convert", characters[c_id].name if characters else c_id)],
                                "payload": {
                                    "character_id": c_id,
                                    "old_religion": old_rel,
                                    "new_religion": new_rel,
                                    "reason": "Marriage",
                                },
                            }
                            emitted_events.append(event_data)
                            self._emit_to_event_log(event_log, event_data)

        # 3. Trade route evangelism
        if active_trade_routes and settlements and characters:
            for (s_a, s_b), route in active_trade_routes.items():
                is_route_active = getattr(route, "active", getattr(route, "is_active", True))
                if is_route_active:
                    dom_a = self.dominant_by_settlement.get(s_a)
                    dom_b = self.dominant_by_settlement.get(s_b)
                    if dom_a and dom_b and dom_a != dom_b:
                        chars_in_b = [c for c in living if c.settlement_id == s_b]
                        conv = process_trade_route_evangelism(chars_in_b, self.faiths, dom_a, self.rng, tick)
                        if conv:
                            c_id, old_rel, new_rel = conv
                            event_data = {
                                "type": "Conversion",
                                "tick": tick,
                                "location": s_b,
                                "causes": [],
                                "participants": [("convert", characters[c_id].name if characters else c_id)],
                                "payload": {
                                    "character_id": c_id,
                                    "old_religion": old_rel,
                                    "new_religion": new_rel,
                                    "reason": "TradeRoute",
                                },
                            }
                            emitted_events.append(event_data)
                            self._emit_to_event_log(event_log, event_data)

        # 4. Clergy proselytization
        if characters and living:
            clergy = [c for c in living if self.faiths.get(c.id) and self.faiths[c.id].role != ReligiousRole.LAITY]
            for cl in clergy:
                town_chars = [c for c in living if c.settlement_id == cl.settlement_id]
                conv = process_clergy_missionary_work(cl.id, town_chars, self.faiths, self.rng, tick)
                if conv:
                    c_id, old_rel, new_rel = conv
                    event_data = {
                        "type": "Conversion",
                        "tick": tick,
                        "location": cl.settlement_id,
                        "causes": [],
                        "participants": [("convert", characters[c_id].name if characters else c_id), ("clergy", cl.name)],
                        "payload": {
                            "character_id": c_id,
                            "old_religion": old_rel,
                            "new_religion": new_rel,
                            "reason": "Missionary",
                        },
                    }
                    emitted_events.append(event_data)
                    self._emit_to_event_log(event_log, event_data)

        # 5. Religious Schisms (Occasional spontaneous reform / sect formation)
        if settlements and living and len(self.religions) < 6:
            if self.rng.random() < SCHISM_CHANCE_PER_TICK:
                # Pick a major religion
                viable_parents = [r for r in self.religions.values() if not r.is_extinct and len(r.adherents) >= 6]
                if viable_parents:
                    parent_rel = self.rng.choice(viable_parents)
                    # Pick a town with followers of this religion
                    target_settlements = [s_id for s_id in settlements.keys() if any(c.settlement_id == s_id and self.faiths.get(c.id) and self.faiths[c.id].religion_id == parent_rel.id for c in living)]
                    if target_settlements:
                        s_id = self.rng.choice(target_settlements)
                        town_followers = [c for c in living if c.settlement_id == s_id and self.faiths.get(c.id) and self.faiths[c.id].religion_id == parent_rel.id]
                        if town_followers:
                            instigator = self.rng.choice(town_followers)
                            schism_res = trigger_religious_schism(
                                parent_religion=parent_rel,
                                schism_settlement_id=s_id,
                                instigator_character_id=instigator.id,
                                living_characters=living,
                                faiths=self.faiths,
                                new_rel_counter=self.rel_counter,
                                tick=tick,
                                rng=self.rng,
                            )
                            if schism_res:
                                child_rel, converted_ids = schism_res
                                self.religions[child_rel.id] = child_rel
                                self.rel_counter += 1
                                event_data = {
                                    "type": "ReligiousSchism",
                                    "tick": tick,
                                    "location": s_id,
                                    "causes": [],
                                    "participants": [("prophet", instigator.name), ("parent_religion", parent_rel.name), ("sect", child_rel.name)],
                                    "payload": {
                                        "parent_religion_id": parent_rel.id,
                                        "child_religion_id": child_rel.id,
                                        "child_religion_name": child_rel.name,
                                        "converts_count": len(converted_ids),
                                    },
                                }
                                emitted_events.append(event_data)
                                self._emit_to_event_log(event_log, event_data)

        # 6. Recalculate Dominant Settlement Faiths & Devotion Decay
        for f in self.faiths.values():
            f.devotion = max(0.1, round(f.devotion - DEVOTION_DECAY_RATE, 3))

        if settlements:
            self.dominant_by_settlement = update_settlement_dominant_religions(
                settlements=settlements,
                living_characters=living,
                faiths=self.faiths,
                religions=self.religions,
            )

        return emitted_events

    def _emit_to_event_log(self, event_log: Any, event_data: dict[str, Any]) -> None:
        """Safely appends religious event to EventLog if provided and registered."""
        if event_log is None:
            return
        try:
            from minemesis.core.types import EventType, Intent, Scale
            type_val = event_data["type"]
            # Find matching enum value
            enum_type = None
            for e_t in EventType:
                if e_t.value == type_val:
                    enum_type = e_t
                    break
            if enum_type:
                event_log.append(
                    event_type=enum_type,
                    tick=event_data["tick"],
                    location=event_data["location"],
                    causes=event_data.get("causes", []),
                    intent=Intent.INTENTIONAL,
                    participants=event_data.get("participants", []),
                    scale=Scale.INDIVIDUAL,
                    payload=event_data.get("payload", {}),
                )
        except Exception:
            # Plugin isolation: failures to append to event_log do not crash religion engine
            pass

    # -------------------------------------------------------------------------
    # Published External Interfaces
    # -------------------------------------------------------------------------
    def get_character_religion(self, character_id: str) -> Optional[Religion]:
        """Returns the Religion object adhered to by a character, or None."""
        if not self.enabled:
            return None
        faith = self.faiths.get(character_id)
        if not faith:
            return None
        return self.religions.get(faith.religion_id)

    def get_character_faith(self, character_id: str) -> Optional[CharacterFaith]:
        """Returns the personal CharacterFaith object for a character, or None."""
        if not self.enabled:
            return None
        return self.faiths.get(character_id)

    def get_settlement_religion(self, settlement_id: str) -> Optional[Religion]:
        """Returns the dominant Religion of a settlement, or None."""
        if not self.enabled:
            return None
        rel_id = self.dominant_by_settlement.get(settlement_id)
        if not rel_id:
            return None
        return self.religions.get(rel_id)

    def get_religion_modifiers(self, target_id: str) -> dict[str, float]:
        """
        Calculates active religion modifiers.
        Accepts character_id, settlement_id, or religion_id.
        """
        if not self.enabled:
            return {}

        # 1. Direct religion_id
        if target_id in self.religions:
            return get_religion_aggregate_modifiers(self.religions[target_id])

        # 2. character_id
        if target_id in self.faiths:
            faith = self.faiths[target_id]
            rel = self.religions.get(faith.religion_id)
            return get_character_effective_modifiers(faith, rel)

        # 3. settlement_id
        if target_id in self.dominant_by_settlement:
            rel_id = self.dominant_by_settlement[target_id]
            rel = self.religions.get(rel_id)
            return get_religion_aggregate_modifiers(rel)

        return {}

    def get_settlement_consumption_multiplier(self, settlement_id: str) -> float:
        """Returns food consumption multiplier based on settlement dominant faith."""
        if not self.enabled:
            return 1.0
        rel = self.get_settlement_religion(settlement_id)
        return get_settlement_consumption_multiplier(rel)

    def serialize(self) -> dict[str, Any]:
        """Serializes religion engine state to plain JSON-compatible dictionary."""
        if not self.enabled:
            return {"enabled": False}
        data = serialize_religion_state(
            religions=self.religions,
            faiths=self.faiths,
            rel_counter=self.rel_counter,
            site_counter=self.site_counter,
            seed=self.seed,
        )
        data["enabled"] = True
        return data

    def deserialize(self, data: dict[str, Any]) -> None:
        """Reconstitutes religion engine state from dictionary."""
        if not data.get("enabled", True):
            self.enabled = False
            return
        self.enabled = True
        self.religions, self.faiths, self.rel_counter, self.site_counter, self.seed = (
            deserialize_religion_state(data)
        )
        self.rng = random.Random(self.seed + 777)
