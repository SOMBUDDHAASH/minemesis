"""
Data Model and File I/O for Minemesis Story Viewer.

Supports:
- Live simulation data capture into RunData container.
- Export / import of versioned minemesis_run.json files.
- Resilient backward-compatible deserialization.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import json
import os
from typing import Any, Mapping, Optional, Sequence


SCHEMA_VERSION = "1.0"


@dataclass
class EventProxy:
    """Lightweight event proxy to support history printer & formatter methods."""
    id: int
    tick: int
    location: str
    type_val: str
    participants: tuple[tuple[str, str], ...]
    causes: tuple[int, ...]
    intent_val: str
    scale_val: str
    payload: dict[str, Any]

    @property
    def type(self):
        # Allow .type.value access
        class _Type:
            def __init__(self, val):
                self.value = val
            def __str__(self):
                return self.value
            def __eq__(self, other):
                if hasattr(other, "value"):
                    return self.value == other.value
                return self.value == str(other)
            def __hash__(self):
                return hash(self.value)
        return _Type(self.type_val)

    @property
    def intent(self):
        class _Intent:
            def __init__(self, val):
                self.value = val
            def __eq__(self, other):
                if hasattr(other, "value"):
                    return self.value == other.value
                return self.value == str(other)
        return _Intent(self.intent_val)

    @property
    def participants_dict(self) -> dict[str, str]:
        return dict(self.participants)


@dataclass
class EventLogProxy:
    """Proxy providing EventLog read-only methods over a loaded run."""
    _events: list[EventProxy]
    _by_id: dict[int, EventProxy] = field(default_factory=dict)

    def __post_init__(self):
        self._by_id = {e.id: e for e in self._events}

    def all_events(self) -> list[EventProxy]:
        return self._events

    def get(self, event_id: int) -> Optional[EventProxy]:
        return self._by_id.get(event_id)

    def get_event(self, event_id: int) -> Optional[EventProxy]:
        return self._by_id.get(event_id)

    def __len__(self) -> int:
        return len(self._events)


@dataclass
class RunData:
    schema_version: str
    build_info: dict[str, Any]
    seed: int
    years: int
    toggles: dict[str, bool]
    events: list[dict[str, Any]]
    characters: dict[str, dict[str, Any]]
    settlements: dict[str, dict[str, Any]]
    beliefs: dict[str, dict[str, Any]]  # char_id -> event_id_str -> belief_dict
    books: list[dict[str, Any]]
    census: list[dict[str, Any]]
    event_share: dict[str, float]
    seed_pair: dict[str, int] = field(default_factory=dict)
    pair_code: str = ""
    world_spec: dict[str, Any] = field(default_factory=dict)
    generator_version: str = "v0"

    def get_event_log_proxy(self) -> EventLogProxy:
        proxies = []
        for d in self.events:
            p_raw = d.get("participants", ())
            if isinstance(p_raw, dict):
                p_tuples = tuple(p_raw.items())
            else:
                p_tuples = tuple((p[0], p[1]) for p in p_raw)
            proxies.append(EventProxy(
                id=d["id"],
                tick=d["tick"],
                location=d.get("location", ""),
                type_val=d.get("type", ""),
                participants=p_tuples,
                causes=tuple(d.get("causes", ())),
                intent_val=d.get("intent", "Intentional"),
                scale_val=d.get("scale", "Individual"),
                payload=dict(d.get("payload", {})),
            ))
        return EventLogProxy(_events=proxies)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "build_info": self.build_info,
            "seed": self.seed,
            "seed_pair": self.seed_pair,
            "pair_code": self.pair_code,
            "world_spec": self.world_spec,
            "generator_version": self.generator_version,
            "years": self.years,
            "toggles": self.toggles,
            "events": self.events,
            "characters": self.characters,
            "settlements": self.settlements,
            "beliefs": self.beliefs,
            "books": self.books,
            "census": self.census,
            "event_share": self.event_share,
        }

    def save_to_json(self, file_path: str) -> None:
        parent = os.path.dirname(file_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunData:
        return cls(
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            build_info=data.get("build_info", {}),
            seed=int(data.get("seed", 42)),
            years=int(data.get("years", 100)),
            toggles=data.get("toggles", {"religion": True, "lore": True}),
            events=data.get("events", []),
            characters=data.get("characters", {}),
            settlements=data.get("settlements", {}),
            beliefs=data.get("beliefs", {}),
            books=data.get("books", []),
            census=data.get("census", []),
            event_share=data.get("event_share", {}),
            seed_pair=data.get("seed_pair", {}),
            pair_code=data.get("pair_code", ""),
            world_spec=data.get("world_spec", {}),
            generator_version=data.get("generator_version", "v0"),
        )

    @classmethod
    def load_from_json(cls, file_path: str) -> RunData:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_simulation(
        cls,
        sim: Any,
        years: int,
        build_info: Optional[dict[str, Any]] = None,
    ) -> RunData:
        """Constructs a complete RunData object from a live Simulation instance."""
        # 1. Events
        ev_dicts = [e.to_dict() for e in sim.event_log.all_events()]

        # 2. Characters
        char_dicts = {}
        for c_id, c in sim.characters.items():
            char_dicts[c_id] = {
                "id": c.id,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "full_name": c.full_name,
                "settlement_id": c.settlement_id,
                "age_ticks": c.age_ticks,
                "age_years": c.age_years,
                "sex": c.sex,
                "alive": c.alive,
                "death_tick": getattr(c, "death_tick", None),
                "spouse_id": c.spouse_id,
                "father_id": c.father_id,
                "mother_id": c.mother_id,
                "children_ids": list(c.children_ids),
                "suspicion": c.suspicion,
                "forgiveness": c.forgiveness,
            }

        # 3. Settlements
        settle_dicts = {}
        for s_id, s in sim.settlements.items():
            settle_dicts[s_id] = {
                "id": s.id,
                "name": getattr(s, "name", s_id),
                "food": getattr(s, "food", 0),
                "wealth": getattr(s, "wealth", 0),
                "chief_id": getattr(s, "chief_id", None),
                "member_ids": list(getattr(s, "member_ids", ())),
            }

        # 4. Beliefs (for Truth vs Belief panel in People tab)
        belief_dicts = {}
        for c_id, b_map in sim.beliefs_by_character.items():
            b_inner = {}
            for e_id, b in b_map.items():
                b_inner[str(e_id)] = {
                    "event_ref": b.event_ref,
                    "source": b.source.value if hasattr(b.source, "value") else str(b.source),
                    "source_character_id": b.source_character_id,
                    "confidence": b.confidence,
                    "believed_type": b.believed_type.value if hasattr(b.believed_type, "value") else str(b.believed_type),
                    "believed_intent": b.believed_intent.value if hasattr(b.believed_intent, "value") else str(b.believed_intent),
                    "believed_actor": b.believed_actor,
                    "believed_target": b.believed_target,
                    "believed_location": b.believed_location,
                    "believed_payload": dict(b.believed_payload),
                }
            belief_dicts[c_id] = b_inner

        # 5. Books
        book_dicts = []
        if getattr(sim, "lore_engine", None) and sim.lore_engine.enabled:
            for b in sim.lore_engine.library_manager.get_all_books():
                book_dicts.append({
                    "id": b.id,
                    "title": b.title,
                    "author_id": b.author_id,
                    "author_name": b.author_name,
                    "author_literacy": b.author_literacy.value,
                    "genre": b.genre.value,
                    "settlement_id": b.settlement_id,
                    "creation_tick": b.creation_tick,
                    "creation_year": b.creation_year,
                    "perspective_bias": b.perspective_bias,
                    "pages": list(b.pages),
                    "total_word_count": b.total_word_count,
                    "is_damaged": b.is_damaged,
                })

        # 6. Event Share
        from collections import Counter
        counts = Counter(d["type"] for d in ev_dicts)
        total_evts = len(ev_dicts) or 1
        event_share = {k: round((v / total_evts) * 100, 2) for k, v in counts.most_common()}

        # 7. Census (yearly sampling)
        census = []
        for y in range(1, years + 1):
            y_tick = y * 12
            # Calculate living characters at year y
            set_pops = {}
            for s_id in settle_dicts.keys():
                pop = sum(1 for c in char_dicts.values() if c["settlement_id"] == s_id and (c["alive"] or (c.get("death_tick") or 99999) > y_tick))
                set_pops[s_id] = pop
            census.append({
                "year": y,
                "populations": set_pops,
                "total_population": sum(set_pops.values()),
            })

        toggles = {
            "religion": bool(sim.religion_engine and sim.religion_engine.enabled),
            "lore": bool(sim.lore_engine and sim.lore_engine.enabled),
        }

        # SeedPair and WorldSpec capture
        seed_pair_dict = {}
        pair_code = ""
        if hasattr(sim, "seed_pair"):
            seed_pair_dict = {"world": sim.seed_pair.world, "chronicle": sim.seed_pair.chronicle}
            pair_code = sim.seed_pair.encode()

        world_spec_dict = {}
        gen_ver = "v0"
        if hasattr(sim, "world_spec") and sim.world_spec is not None:
            world_spec_dict = sim.world_spec.to_dict()
            gen_ver = getattr(sim.world_spec, "generator_version", "v0")

        return cls(
            schema_version=SCHEMA_VERSION,
            build_info=build_info or {},
            seed=sim.seed,
            years=years,
            toggles=toggles,
            events=ev_dicts,
            characters=char_dicts,
            settlements=settle_dicts,
            beliefs=belief_dicts,
            books=book_dicts,
            census=census,
            event_share=event_share,
            seed_pair=seed_pair_dict,
            pair_code=pair_code,
            world_spec=world_spec_dict,
            generator_version=gen_ver,
        )
