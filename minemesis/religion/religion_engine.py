"""
Central Orchestrator for the Standalone Religion Engine (Milestone R0 & R1: Religion Becomes History).

Subsystem Architecture:
1. Procedural Emergent Generation (Traits Knowledge Library)
2. Religious Interpretation Layer (Perception -> Religion Filter -> Belief)
3. Religious Tension System (Inter-faith & Sectarian Dynamics)
4. Religion Family Tree (Genealogy of Faiths)
5. Great Religious Figures (Prophets, Saints, Mystics, Martyrs, Reformers, Heretics)
6. Religious Heresy Engine (Orthodoxy, Heresy, Reformation, Counter-Reformation, Reunification)
7. Sacred Geography & Pilgrimages (Mountains, Forests, Rivers, Trees, Temples, Shrines)
8. Myth Creation Engine (Event -> Story -> Legend -> Myth)
9. Religious Virtue System (Moral codes & Character standing)
10. Dynamic Spread (Marriage, Trade, Family, Pilgrimages, Refugees, Missionaries, Conquests, Saint Cults)
11. Religious Analytics & Chronicle

HISTORIOGRAPHICAL DISCLOSURE & FUTURE ROADMAP:
The current structural model of institutional religious evolution (formal councils, canon,
orthodoxy vs. heresy, schisms, counter-reformations, excommunication, and dogmatic declarations)
draws heavily from Abrahamic and specifically Christian historiographical frameworks.
While emergent trait generation and sacred geography reflect global traditions, the institutional
conflict mechanisms in R1 reflect this specific structural heritage.
Future milestones (Milestone R1.5 and R2) will generalize this evolution into living faith systems,
incorporating Dharmic (darśana, cyclical renewal, philosophical lineages), East Asian (syncretic
coexistence, state ritual vs. folk practice, ancestors), and Indigenous traditions (animism,
land-centered ceremony, oral transmission without rigid dogmatic councils).
"""

from __future__ import annotations
from typing import Any, Mapping, Optional, Sequence
from minemesis.core.rng import KeyedRNG
from minemesis.core.types import EventType, Intent, Scale
from minemesis.models.character import Character
from minemesis.models.settlement import Settlement
from minemesis.religion.religion_analytics import (
    ReligiousAnalyticsReport,
    format_religion_family_tree,
    format_religious_analytics_summary,
    generate_religious_analytics,
)
from minemesis.religion.religion_config import (
    CLERGY_POPULATION_RATIO,
    COUNTER_REFORMATION_CHANCE,
    CULTURAL_MIXING_RATE,
    DEVOTION_DECAY_RATE,
    DOCTRINAL_BORROWING_CHANCE,
    ENABLE_RELIGION_ENGINE,
    FOLK_TRADITION_ABSORPTION_CHANCE,
    GREAT_FIGURE_EMERGENCE_CHANCE,
    HERESY_EMERGENCE_CHANCE,
    INITIAL_RELIGIONS_PER_WORLD,
    MYTH_EXCHANGE_CHANCE,
    MYTH_RETELL_INTERVAL,
    PILGRIMAGE_CHANCE,
    SCHISM_CHANCE_PER_TICK,
    SECT_REUNIFICATION_CHANCE,
    SYNCRETISM_CHANCE,
)
from minemesis.religion.religion_culture import (
    absorb_folk_tradition_into_religion,
    celebrate_local_customs,
    get_cultural_behavioral_pressure,
    initialize_settlement_culture,
    process_cultural_mixing,
)
from minemesis.religion.religion_effects import (
    get_character_effective_modifiers,
    get_religion_aggregate_modifiers,
    get_settlement_consumption_multiplier,
)
from minemesis.religion.religion_figures import (
    evaluate_martyrdom,
    evaluate_prophet_or_mystic_emergence,
)
from minemesis.religion.religion_generation import generate_world_religions
from minemesis.religion.religion_geography import (
    check_and_elevate_holy_site,
    evaluate_holy_site_discovery_or_construction,
    process_pilgrimage_economic_benefit,
)
from minemesis.religion.religion_heresies import (
    check_and_declare_heresy,
    establish_heretical_schism,
    evaluate_counter_reformation,
    evaluate_sect_reunification,
)
from minemesis.religion.religion_interpretation import apply_religious_interpretation_filter
from minemesis.religion.religion_models import (
    CharacterFaith,
    CulturalProfile,
    HolySite,
    HolySiteType,
    LoreStage,
    Religion,
    ReligiousFigure,
    ReligiousFigureType,
    ReligiousMyth,
    ReligiousRelationshipType,
    ReligiousRole,
    Saint,
    SiteTier,
)
from minemesis.religion.religion_myths import (
    create_initial_story_from_event,
    exchange_myths_across_trade_routes,
    retell_and_evolve_myths,
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
    process_conquest_conversion,
    process_family_faith_inheritance,
    process_marriage_conversion,
    process_religious_refugee_migration,
    process_saint_cult_conversions,
    process_trade_route_evangelism,
    update_settlement_dominant_religions,
)
from minemesis.religion.religion_syncretism import (
    evaluate_doctrinal_borrowing,
    evaluate_syncretic_fusion,
)
from minemesis.religion.religion_tensions import (
    calculate_religious_relationship_modifier,
    calculate_settlement_religious_tension,
    get_religious_relationship,
)
from minemesis.religion.religion_traits import ALL_RELIGION_TRAITS
from minemesis.religion.religion_virtues import evaluate_action_against_virtues


class ReligionEngine:
    """
    Self-contained Religion Engine subsystem for Minemesis.
    """

    def __init__(self, seed: int = 42, enabled: bool | None = None) -> None:
        self.seed = seed
        self.enabled = ENABLE_RELIGION_ENGINE if enabled is None else enabled
        self.rng = KeyedRNG(seed + 777, stream="religion_engine")
        self.religions: dict[str, Religion] = {}
        self.faiths: dict[str, CharacterFaith] = {}
        self.cultural_profiles: dict[str, CulturalProfile] = {}
        self.rel_counter = [1]
        self.site_counter = [1]
        self.figure_counter = [1]
        self.myth_counter = [1]
        self.folk_counter = [1]
        self.custom_counter = [1]
        self.dominant_by_settlement: dict[str, str] = {}
        self.settlement_tensions: dict[str, float] = {}
        self.settlement_faith_plantings: set[tuple[str, str]] = set()

    def initialize(
        self,
        seed: int | None = None,
        settlements: Mapping[str, Any] | None = None,
        characters: Mapping[str, Any] | None = None,
    ) -> None:
        """Initializes religions and populates starting faiths."""
        if seed is not None:
            self.seed = seed
            self.rng = KeyedRNG(seed + 777, stream="religion_engine")

        if not self.enabled:
            return

        settlement_ids = list(settlements.keys()) if settlements else ["set_oakhaven", "set_riverbend", "set_ironpeak"]
        self.religions = generate_world_religions(
            seed=self.seed,
            num_religions=INITIAL_RELIGIONS_PER_WORLD,
            settlement_ids=settlement_ids,
        )
        self.rel_counter[0] = len(self.religions) + 1

        # Initialize Cultural Profiles (Milestone R2.1 & R2.3)
        for s_id in settlement_ids:
            s_obj = settlements.get(s_id) if settlements else None
            s_name = getattr(s_obj, "name", s_id.replace("set_", "").capitalize())
            self.cultural_profiles[s_id] = initialize_settlement_culture(
                settlement_id=s_id,
                settlement_name=s_name,
                folk_counter=self.folk_counter,
                custom_counter=self.custom_counter,
                rng=self.rng,
            )

        if characters:
            char_list = sorted(list(characters.values()), key=lambda c: c.id)
            for idx, char in enumerate(char_list):
                s_id = char.settlement_id
                target_rel_id = None
                for r_id, r in sorted(self.religions.items()):
                    if s_id in r.dominant_settlements:
                        target_rel_id = r_id
                        break
                if not target_rel_id:
                    rel_keys = sorted(list(self.religions.keys()))
                    target_rel_id = rel_keys[idx % len(rel_keys)]

                is_clergy = self.rng.random() < CLERGY_POPULATION_RATIO
                role = self.rng.choice([ReligiousRole.PRIEST, ReligiousRole.SHAMAN, ReligiousRole.MONK]) if is_clergy else ReligiousRole.LAITY
                devotion = round(self.rng.uniform(0.7, 0.95) if is_clergy else self.rng.uniform(0.4, 0.8), 3)

                c_faith = CharacterFaith(
                    character_id=char.id,
                    religion_id=target_rel_id,
                    devotion=devotion,
                    religious_standing=round(self.rng.uniform(45.0, 65.0), 1),
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
                for s_id, dom_rel in self.dominant_by_settlement.items():
                    self.settlement_faith_plantings.add((dom_rel, s_id))

    def generate_religions(self, settlement_ids: Sequence[str] = ()) -> dict[str, Religion]:
        """Procedurally generates emergent religions."""
        if not self.enabled:
            return {}
        self.religions = generate_world_religions(
            seed=self.seed,
            num_religions=INITIAL_RELIGIONS_PER_WORLD,
            settlement_ids=settlement_ids,
        )
        self.rel_counter[0] = len(self.religions) + 1
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

    def _is_notable_conversion(
        self,
        character_id: str,
        new_religion_id: str,
        settlement_id: str,
        reason: str,
        characters: Mapping[str, Any] | None,
        settlements: Mapping[str, Any] | None,
    ) -> bool:
        """
        Determines whether a faith conversion is historically notable to record in EventLog.
        Routine private lay conversions update CharacterFaith state without flooding the EventLog.
        Notable conversions:
        1. Formal conquest, schism, or heresy conversions.
        2. Settlement Chief / Leader.
        3. Clergy / Priest / Prophet.
        4. First time a religion is planted in a settlement.
        """
        if reason in ("Conquest", "Schism", "Heresy"):
            return True

        if characters and character_id in characters:
            char = characters[character_id]
            # Chief conversion
            if settlements:
                for s in settlements.values():
                    if getattr(s, "chief_id", None) == character_id:
                        return True
            # Clergy conversion
            c_faith = self.faiths.get(character_id)
            if c_faith and c_faith.role != ReligiousRole.LAITY:
                return True

        # First time this faith has ever taken root in this settlement (faith planting)
        planting_key = (new_religion_id, settlement_id)
        if planting_key not in self.settlement_faith_plantings:
            self.settlement_faith_plantings.add(planting_key)
            return True

        return False

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
        Executes one monthly tick of religious simulation across all R1 subsystems.
        """
        if not self.enabled:
            return []

        emitted_events: list[dict[str, Any]] = []
        living = [c for c in characters.values() if c.alive] if characters else []

        # -------------------------------------------------------------
        # 1. Martyrdom, Saint Canonization & Myth Seeding for Deaths
        # -------------------------------------------------------------
        if recent_deaths:
            for d_char, cause_type, d_event_id in recent_deaths:
                c_faith = self.faiths.get(d_char.id)
                rel = self.religions.get(c_faith.religion_id) if c_faith else None
                if c_faith and rel:
                    # Check for Martyrdom (R1.4)
                    martyr = evaluate_martyrdom(
                        deceased_char=d_char,
                        deceased_faith=c_faith,
                        religion=rel,
                        cause_type=cause_type,
                        death_event_id=d_event_id,
                        tick=tick,
                        figure_counter=self.figure_counter,
                    )
                    if martyr:
                        event_data = {
                            "type": "GreatFigureEmergence",
                            "tick": tick,
                            "location": d_char.settlement_id,
                            "causes": [d_event_id] if d_event_id is not None else [],
                            "participants": [("martyr", martyr.character_name), ("religion", rel.name)],
                            "payload": martyr.to_dict(),
                        }
                        emitted_events.append(event_data)
                        self._emit_to_event_log(event_log, event_data)

                        # Seed Myth from Martyrdom (R1.7)
                        m_obj, m_payload = create_initial_story_from_event(
                            religion=rel,
                            event=event_log.get_event(d_event_id) if (event_log and d_event_id is not None) else None,
                            hero=d_char,
                            objective_summary=f"{d_char.name} was slain in the {cause_type.value}.",
                            tick=tick,
                            myth_counter=self.myth_counter,
                        )
                        myth_evt = {
                            "type": "MythRecorded",
                            "tick": tick,
                            "location": d_char.settlement_id,
                            "causes": [d_event_id] if d_event_id is not None else [],
                            "participants": [("hero", d_char.name), ("religion", rel.name)],
                            "payload": m_payload,
                        }
                        emitted_events.append(myth_evt)
                        self._emit_to_event_log(event_log, myth_evt)

                    else:
                        # Regular Saint Canonization check (R0)
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

        # -------------------------------------------------------------
        # 2. Dynamic Spread: Marriage, Trade, Clergy, Saint Cults
        # -------------------------------------------------------------
        if living:
            # Marriage Conversion
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
                            if self._is_notable_conversion(c_id, new_rel, c.settlement_id, "Marriage", characters, settlements):
                                emitted_events.append(event_data)
                                self._emit_to_event_log(event_log, event_data)

            # Trade Route Evangelism
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
                                if self._is_notable_conversion(c_id, new_rel, s_b, "TradeRoute", characters, settlements):
                                    emitted_events.append(event_data)
                                    self._emit_to_event_log(event_log, event_data)

            # Clergy Missionary Work
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
                    if self._is_notable_conversion(c_id, new_rel, cl.settlement_id, "Missionary", characters, settlements):
                        emitted_events.append(event_data)
                        self._emit_to_event_log(event_log, event_data)

            # Saint Cult Conversions (R1.9)
            for r in self.religions.values():
                if r.saints:
                    cult_converts = process_saint_cult_conversions(r, living, self.faiths, self.rng, tick)
                    for c_id, o_rel, n_rel in cult_converts:
                        set_loc = characters[c_id].settlement_id if (characters and c_id in characters) else "unknown"
                        event_data = {
                            "type": "Conversion",
                            "tick": tick,
                            "location": set_loc,
                            "causes": [],
                            "participants": [("convert", characters[c_id].name if characters else c_id), ("religion", r.name)],
                            "payload": {
                                "character_id": c_id,
                                "old_religion": o_rel,
                                "new_religion": n_rel,
                                "reason": "SaintCultVeneration",
                            },
                        }
                        if self._is_notable_conversion(c_id, n_rel, set_loc, "SaintCultVeneration", characters, settlements):
                            emitted_events.append(event_data)
                            self._emit_to_event_log(event_log, event_data)

        # -------------------------------------------------------------
        # 3. Sectarian Tension & Religious Refugees (R1.2 & R1.9)
        # -------------------------------------------------------------
        if settlements and living:
            for s_id in settlements.keys():
                tension = calculate_settlement_religious_tension(s_id, living, self.faiths, self.religions)
                self.settlement_tensions[s_id] = tension
                refugee_res = process_religious_refugee_migration(
                    settlement_id=s_id,
                    settlement_tension=tension,
                    settlement_characters=living,
                    settlements=settlements,
                    faiths=self.faiths,
                    dominant_by_settlement=self.dominant_by_settlement,
                    rng=self.rng,
                    tick=tick,
                )
                if refugee_res:
                    refugee, old_set, new_set, r_id = refugee_res
                    event_data = {
                        "type": "ReligiousRefugeeMigration",
                        "tick": tick,
                        "location": new_set,
                        "causes": [],
                        "participants": [("refugee", refugee.name), ("origin", old_set), ("destination", new_set)],
                        "payload": {
                            "character_id": refugee.id,
                            "origin_settlement": old_set,
                            "destination_settlement": new_set,
                            "religion_id": r_id,
                            "tension_level": round(tension, 1),
                        },
                    }
                    emitted_events.append(event_data)
                    self._emit_to_event_log(event_log, event_data)

        # -------------------------------------------------------------
        # 4. Great Figures: Prophets & Mystics (R1.4)
        # -------------------------------------------------------------
        if living and self.rng.random() < GREAT_FIGURE_EMERGENCE_CHANCE:
            for r in self.religions.values():
                if not r.is_extinct and len(r.adherents) >= 4:
                    fig = evaluate_prophet_or_mystic_emergence(
                        candidates=living,
                        faiths=self.faiths,
                        religion=r,
                        trigger_event_id=None,
                        tick=tick,
                        rng=self.rng,
                        figure_counter=self.figure_counter,
                    )
                    if fig:
                        c_obj = characters.get(fig.character_id) if characters else None
                        event_data = {
                            "type": "GreatFigureEmergence",
                            "tick": tick,
                            "location": c_obj.settlement_id if c_obj else "unknown",
                            "causes": [],
                            "participants": [(fig.figure_type.value.lower(), fig.character_name), ("religion", r.name)],
                            "payload": fig.to_dict(),
                        }
                        emitted_events.append(event_data)
                        self._emit_to_event_log(event_log, event_data)
                        break

        # -------------------------------------------------------------
        # 5. Sacred Geography & Pilgrimages (R1.6)
        # -------------------------------------------------------------
        if settlements and living:
            # Chance to discover/consecrate a Holy Site
            if self.rng.random() < 0.02 and len(self.religions) > 0:
                active_r = self.rng.choice(list(self.religions.values()))
                if len(active_r.holy_sites) < 3:
                    site_res = evaluate_holy_site_discovery_or_construction(
                        religion=active_r,
                        settlements=settlements,
                        living_characters=living,
                        tick=tick,
                        rng=self.rng,
                        site_counter=self.site_counter,
                    )
                    if site_res:
                        site, site_payload = site_res
                        event_data = {
                            "type": "HolySiteDiscovered",
                            "tick": tick,
                            "location": site.settlement_id,
                            "causes": [],
                            "participants": [("religion", active_r.name), ("site", site.name)],
                            "payload": site_payload,
                        }
                        emitted_events.append(event_data)
                        self._emit_to_event_log(event_log, event_data)

            # Process pilgrimages by devout adherents
            for c in living:
                c_faith = self.faiths.get(c.id)
                if c_faith and c_faith.devotion >= 0.70 and self.rng.random() < PILGRIMAGE_CHANCE:
                    c_rel = self.religions.get(c_faith.religion_id)
                    if c_rel and c_rel.holy_sites:
                        chosen_site = self.rng.choice(c_rel.holy_sites)
                        c_faith.pilgrimages_completed += 1
                        c_faith.devotion = min(1.0, round(c_faith.devotion + 0.05, 3))
                        c_faith.religious_standing = min(100.0, c_faith.religious_standing + 10.0)

                        # Economic benefit (R1.6)
                        econ_res = process_pilgrimage_economic_benefit(
                            pilgrim_home_id=c.settlement_id,
                            holy_site_settlement_id=chosen_site.settlement_id,
                            active_trade_routes=active_trade_routes,
                            rng=self.rng,
                        )

                        chosen_site.pilgrims_visited += 1
                        elevation_payload = check_and_elevate_holy_site(site=chosen_site, religion=c_rel, tick=tick, rng=self.rng)
                        if elevation_payload:
                            elev_event = {
                                "type": "HolySiteElevated",
                                "tick": tick,
                                "location": chosen_site.settlement_id,
                                "causes": [],
                                "participants": [("holy_site", chosen_site.name), ("religion", c_rel.name)],
                                "payload": elevation_payload,
                            }
                            emitted_events.append(elev_event)
                            self._emit_to_event_log(event_log, elev_event)

                        event_data = {
                            "type": "Pilgrimage",
                            "tick": tick,
                            "location": chosen_site.settlement_id,
                            "causes": [],
                            "participants": [("pilgrim", c.name), ("holy_site", chosen_site.name), ("religion", c_rel.name)],
                            "payload": {
                                "character_id": c.id,
                                "site_id": chosen_site.id,
                                "site_name": chosen_site.name,
                                "home_settlement": c.settlement_id,
                                "site_settlement": chosen_site.settlement_id,
                                "economic_benefit": econ_res,
                            },
                        }
                        emitted_events.append(event_data)
                        self._emit_to_event_log(event_log, event_data)

        # -------------------------------------------------------------
        # 6. Heresy, Schisms, Counter-Reformation & Reunification (R1.3 & R1.5)
        # -------------------------------------------------------------
        if settlements and living:
            # Check Heresy emergence
            if self.rng.random() < HERESY_EMERGENCE_CHANCE and len(self.religions) < 8:
                viable_rels = [r for r in self.religions.values() if not r.is_extinct and len(r.adherents) >= 4]
                if viable_rels:
                    chosen_rel = self.rng.choice(viable_rels)
                    heresy_res = check_and_declare_heresy(
                        religion=chosen_rel,
                        settlement_characters=living,
                        faiths=self.faiths,
                        all_traits=ALL_RELIGION_TRAITS,
                        tick=tick,
                        rng=self.rng,
                        figure_counter=self.figure_counter,
                    )
                    if heresy_res:
                        heretic_fig, followers, adopted_t_id, h_payload = heresy_res
                        h_event = {
                            "type": "HeresyDeclared",
                            "tick": tick,
                            "location": h_payload["settlement_id"],
                            "causes": [],
                            "participants": [("heretic", heretic_fig.character_name), ("mother_religion", chosen_rel.name)],
                            "payload": h_payload,
                        }
                        emitted_events.append(h_event)
                        self._emit_to_event_log(event_log, h_event)

                        # Establish breakaway schism
                        child_rel, schism_payload = establish_heretical_schism(
                            parent_religion=chosen_rel,
                            heretic_fig=heretic_fig,
                            follower_ids=followers,
                            adopted_trait_id=adopted_t_id,
                            faiths=self.faiths,
                            all_traits=ALL_RELIGION_TRAITS,
                            rel_counter=self.rel_counter,
                            tick=tick,
                            rng=self.rng,
                        )
                        self.religions[child_rel.id] = child_rel

                        schism_event = {
                            "type": "ReligiousSchism",
                            "tick": tick,
                            "location": h_payload["settlement_id"],
                            "causes": [],
                            "participants": [("founder", heretic_fig.character_name), ("sect", child_rel.name), ("parent_religion", chosen_rel.name)],
                            "payload": schism_payload,
                        }
                        emitted_events.append(schism_event)
                        self._emit_to_event_log(event_log, schism_event)

                        # Counter-Reformation by parent faith (R1.5)
                        if self.rng.random() < COUNTER_REFORMATION_CHANCE:
                            cr_payload = evaluate_counter_reformation(
                                parent_religion=chosen_rel,
                                child_religion=child_rel,
                                all_traits=ALL_RELIGION_TRAITS,
                                tick=tick,
                                rng=self.rng,
                            )
                            if cr_payload:
                                cr_event = {
                                    "type": "ReligiousReform",
                                    "tick": tick,
                                    "location": h_payload["settlement_id"],
                                    "causes": [],
                                    "participants": [("religion", chosen_rel.name)],
                                    "payload": cr_payload,
                                }
                                emitted_events.append(cr_event)
                                self._emit_to_event_log(event_log, cr_event)

            # Check Sectarian Reunification (R1.5)
            if self.rng.random() < SECT_REUNIFICATION_CHANCE and len(self.religions) > 2:
                all_rel_list = list(self.religions.values())
                for i in range(len(all_rel_list)):
                    for j in range(i + 1, len(all_rel_list)):
                        reun_payload = evaluate_sect_reunification(
                            rel_a=all_rel_list[i],
                            rel_b=all_rel_list[j],
                            all_religions=self.religions,
                            faiths=self.faiths,
                            tick=tick,
                            rng=self.rng,
                        )
                        if reun_payload:
                            reun_event = {
                                "type": "SectReunification",
                                "tick": tick,
                                "location": living[0].settlement_id if living else "unknown",
                                "causes": [],
                                "participants": [("surviving", reun_payload["surviving_religion_name"]), ("absorbed", reun_payload["absorbed_religion_name"])],
                                "payload": reun_payload,
                            }
                            emitted_events.append(reun_event)
                            self._emit_to_event_log(event_log, reun_event)
                            break

        # -------------------------------------------------------------
        # 7. Myth Generational Evolution (R1.7)
        # -------------------------------------------------------------
        if tick % MYTH_RETELL_INTERVAL == 0:
            for r in self.religions.values():
                myth_evolutions = retell_and_evolve_myths(r, tick, self.rng)
                for me in myth_evolutions:
                    event_data = {
                        "type": "MythRecorded",
                        "tick": tick,
                        "location": living[0].settlement_id if living else "unknown",
                        "causes": [me["root_event_id"]],
                        "participants": [("hero", me["hero_name"]), ("religion", r.name)],
                        "payload": me,
                    }
                    emitted_events.append(event_data)
                    self._emit_to_event_log(event_log, event_data)

        # -------------------------------------------------------------
        # 8. Local Customs & Seasonal Celebrations (R2.4)
        # -------------------------------------------------------------
        if self.cultural_profiles:
            for s_id, cp in sorted(self.cultural_profiles.items()):
                custom_events = celebrate_local_customs(s_id, cp, tick)
                for ce in custom_events:
                    event_data = {
                        "type": "LocalCustomCelebrated",
                        "tick": tick,
                        "location": s_id,
                        "causes": [],
                        "participants": [("settlement", s_id), ("custom", ce["custom_name"])],
                        "payload": ce,
                    }
                    emitted_events.append(event_data)
                    self._emit_to_event_log(event_log, event_data)

        # -------------------------------------------------------------
        # 9. Religious Syncretism & Doctrinal Borrowing (R1.5.1 & R1.5.4)
        # -------------------------------------------------------------
        if active_trade_routes and len(self.religions) >= 2 and living:
            active_pairs = []
            for (s_a, s_b), route in active_trade_routes.items():
                is_route_active = getattr(route, "active", getattr(route, "is_active", True))
                if is_route_active:
                    rel_a = self.get_settlement_religion(s_a)
                    rel_b = self.get_settlement_religion(s_b)
                    if rel_a and rel_b and rel_a.id != rel_b.id:
                        active_pairs.append((s_a, s_b, rel_a, rel_b))

            if active_pairs:
                s_a, s_b, r_a, r_b = self.rng.choice(active_pairs)

                # Doctrinal Borrowing
                if self.rng.random() < DOCTRINAL_BORROWING_CHANCE:
                    borrow_payload = evaluate_doctrinal_borrowing(
                        donor_rel=r_a,
                        recipient_rel=r_b,
                        all_traits=ALL_RELIGION_TRAITS,
                        tick=tick,
                        rng=self.rng,
                    )
                    if borrow_payload:
                        borrow_event = {
                            "type": "DoctrinalBorrowing",
                            "tick": tick,
                            "location": s_b,
                            "causes": [],
                            "participants": [("recipient", borrow_payload["recipient_religion_name"]), ("source", borrow_payload["donor_religion_name"])],
                            "payload": borrow_payload,
                        }
                        emitted_events.append(borrow_event)
                        self._emit_to_event_log(event_log, borrow_event)

                # Syncretic Fusion
                if self.rng.random() < SYNCRETISM_CHANCE:
                    settlement_chars = [c for c in living if c.settlement_id == s_b]
                    fusion_res = evaluate_syncretic_fusion(
                        rel_a=r_a,
                        rel_b=r_b,
                        settlement_id=s_b,
                        settlement_characters=settlement_chars,
                        faiths=self.faiths,
                        all_traits=ALL_RELIGION_TRAITS,
                        rel_counter=self.rel_counter,
                        tick=tick,
                        rng=self.rng,
                    )
                    if fusion_res:
                        new_sync_rel, sync_payload = fusion_res
                        self.religions[new_sync_rel.id] = new_sync_rel
                        sync_event = {
                            "type": "ReligiousSyncretism",
                            "tick": tick,
                            "location": s_b,
                            "causes": [],
                            "participants": [("syncretic_faith", new_sync_rel.name), ("parent_a", sync_payload["parent_rel_a_name"]), ("parent_b", sync_payload["parent_rel_b_name"])],
                            "payload": sync_payload,
                        }
                        emitted_events.append(sync_event)
                        self._emit_to_event_log(event_log, sync_event)

        # -------------------------------------------------------------
        # 10. Folk Tradition Absorption (R1.5.3)
        # -------------------------------------------------------------
        if self.cultural_profiles and self.rng.random() < FOLK_TRADITION_ABSORPTION_CHANCE:
            for s_id in sorted(self.cultural_profiles.keys()):
                cp = self.cultural_profiles[s_id]
                dom_rel = self.get_settlement_religion(s_id)
                if dom_rel:
                    unabsorbed = [ft for ft in cp.folk_traditions if not ft.is_absorbed_into_religion]
                    if unabsorbed:
                        ft_to_absorb = self.rng.choice(unabsorbed)
                        absorb_payload = absorb_folk_tradition_into_religion(dom_rel, ft_to_absorb, tick)
                        absorb_event = {
                            "type": "FolkTraditionAbsorbed",
                            "tick": tick,
                            "location": s_id,
                            "causes": [],
                            "participants": [("religion", dom_rel.name), ("tradition", ft_to_absorb.name)],
                            "payload": absorb_payload,
                        }
                        emitted_events.append(absorb_event)
                        self._emit_to_event_log(event_log, absorb_event)
                        break

        # -------------------------------------------------------------
        # 11. Myth Exchange across Trade Routes (R1.5.7)
        # -------------------------------------------------------------
        if active_trade_routes and self.rng.random() < MYTH_EXCHANGE_CHANCE:
            exchanges = exchange_myths_across_trade_routes(
                active_trade_routes=active_trade_routes,
                religions=self.religions,
                dominant_by_settlement=self.dominant_by_settlement,
                current_tick=tick,
                rng=self.rng,
                myth_counter=self.myth_counter,
            )
            for mex in exchanges:
                mex_event = {
                    "type": "MythExchanged",
                    "tick": tick,
                    "location": mex["destination_settlement"],
                    "causes": [mex["root_event_id"]] if mex.get("root_event_id") else [],
                    "participants": [("hero", mex["hero_name"]), ("origin_religion", mex["origin_religion"]), ("adopting_religion", mex["adopting_religion"])],
                    "payload": mex,
                }
                emitted_events.append(mex_event)
                self._emit_to_event_log(event_log, mex_event)

        # -------------------------------------------------------------
        # 12. Cultural Mixing across Trade Corridors (R2.9)
        # -------------------------------------------------------------
        if active_trade_routes and self.cultural_profiles:
            process_cultural_mixing(
                settlements=settlements or {},
                active_trade_routes=active_trade_routes,
                cultural_profiles=self.cultural_profiles,
                mixing_rate=CULTURAL_MIXING_RATE,
            )

        # -------------------------------------------------------------
        # 13. Devotion Maintenance & Dominant Faith Recalculation
        # -------------------------------------------------------------
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
        """Safely appends religious event to EventLog if provided."""
        if event_log is None:
            return
        try:
            type_val = event_data["type"]
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
            pass

    # -------------------------------------------------------------------------
    # Published External Interfaces
    # -------------------------------------------------------------------------
    def get_character_religion(self, character_id: str) -> Optional[Religion]:
        """Returns the Religion adhered to by a character, or None."""
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
        """Calculates active religion modifiers for character, settlement, or religion ID."""
        if not self.enabled:
            return {}

        if target_id in self.religions:
            return get_religion_aggregate_modifiers(self.religions[target_id])

        if target_id in self.faiths:
            faith = self.faiths[target_id]
            rel = self.religions.get(faith.religion_id)
            return get_character_effective_modifiers(faith, rel)

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

    def get_settlement_culture(self, settlement_id: str) -> Optional[CulturalProfile]:
        """Returns the CulturalProfile of a settlement."""
        if not self.enabled:
            return None
        return self.cultural_profiles.get(settlement_id)

    def get_cultural_pressure(self, settlement_id: str) -> dict[str, float]:
        """Returns behavioral decision modifiers exerted by settlement culture."""
        if not self.enabled:
            return {}
        return get_cultural_behavioral_pressure(settlement_id, self.cultural_profiles)

    def generate_analytics(
        self,
        settlements: Mapping[str, Any],
        characters: Mapping[str, Any],
        event_log: Any = None,
        current_tick: int = 0,
    ) -> ReligiousAnalyticsReport:
        """Generates comprehensive Milestones R1.10 and R2.10 analytics report."""
        living = [c for c in characters.values() if c.alive]
        all_myths = []
        for r in self.religions.values():
            all_myths.extend(r.myths)
        return generate_religious_analytics(
            religions=self.religions,
            faiths=self.faiths,
            settlements=settlements,
            living_characters=living,
            event_log=event_log,
            current_tick=current_tick,
            cultural_profiles=self.cultural_profiles,
            myths=all_myths,
        )

    def serialize(self) -> dict[str, Any]:
        """Serializes religion engine state to plain JSON-compatible dictionary."""
        if not self.enabled:
            return {"enabled": False}
        data = serialize_religion_state(
            religions=self.religions,
            faiths=self.faiths,
            rel_counter=self.rel_counter[0],
            site_counter=self.site_counter[0],
            seed=self.seed,
            figure_counter=self.figure_counter[0],
            myth_counter=self.myth_counter[0],
            cultural_profiles=self.cultural_profiles,
            folk_counter=self.folk_counter[0],
            custom_counter=self.custom_counter[0],
        )
        data["enabled"] = True
        return data

    def deserialize(self, data: dict[str, Any]) -> None:
        """Reconstitutes religion engine state from dictionary."""
        if not data.get("enabled", True):
            self.enabled = False
            return
        self.enabled = True
        res = deserialize_religion_state(data)
        self.religions = res[0]
        self.faiths = res[1]
        self.rel_counter = [res[2]]
        self.site_counter = [res[3]]
        self.seed = res[4]
        self.figure_counter = [res[5]]
        self.myth_counter = [res[6]]
        if len(res) > 7:
            self.cultural_profiles = res[7]
            self.folk_counter = [res[8]]
            self.custom_counter = [res[9]]
        self.rng = KeyedRNG(self.seed + 777, stream="religion_engine")
