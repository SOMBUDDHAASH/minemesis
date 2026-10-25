"""
Procedural Literature Engine Orchestrator for Milestone L0 (No LLMs).

Operationalizes:
- Procedural authoring across all 9 genres based strictly on simulation state.
- Perspective bias tracking (author point-of-view vs objective reality).
- Dynamic character literacy levels.
- Settlement archives, repositories, and Minecraft-compatible book exports.
- Cultural amnesia and archive devastation during raids.
- Byte-identical deterministic output per seed.
"""

from __future__ import annotations
from typing import Any, Mapping, Optional, Sequence

from minemesis.core.causal_grammar import CAUSE_GRAMMAR
from minemesis.core.event_log import Event, EventLog
from minemesis.core.rng import KeyedRNG, keyed_float
from minemesis.core.types import EventType, Intent, Scale
from minemesis.lore.lore_generators import (
    generate_biography,
    generate_family_history,
    generate_historical_chronicle,
    generate_legal_record,
    generate_local_folklore,
    generate_myth_collection,
    generate_personal_journal,
    generate_religious_text,
    generate_travel_account,
)
from minemesis.lore.lore_libraries import LibraryManager
from minemesis.lore.lore_models import Book, BookGenre, LibraryType, LiteracyLevel
from minemesis.models.character import Character

ENABLE_LORE_ENGINE: bool = True


class LoreEngine:
    """
    Core engine managing the procedural literature, literacy system,
    historical chronicles, and settlement archives for Minemesis.
    """

    def __init__(self, seed: int, enabled: Optional[bool] = None) -> None:
        self.seed = seed
        self.enabled = ENABLE_LORE_ENGINE if enabled is None else enabled
        # Distinct keyed PRNG for Lore System to preserve simulation core isolation
        self.rng = KeyedRNG(seed ^ 0x4C4F5245, stream="lore_engine")
        self.library_manager = LibraryManager()
        self.book_counter = 0
        self.character_literacy: dict[str, LiteracyLevel] = {}
        self.written_biographies: set[str] = set()
        self.written_scriptures: set[str] = set()

    def get_character_literacy(
        self,
        character: Character,
        role: Optional[str] = None,
    ) -> LiteracyLevel:
        """
        Determines and caches a character's literacy level based on their
        station, age, role, and deterministic distribution.
        """
        if character.id in self.character_literacy:
            return self.character_literacy[character.id]

        # Priestly or scholarly roles held by role, not population-wide roll (Directive 4)
        if role:
            r_lower = role.lower()
            if "priest" in r_lower or "shaman" in r_lower or "monk" in r_lower:
                level = LiteracyLevel.PRIEST
                self.character_literacy[character.id] = level
                return level
            elif "historian" in r_lower or "scribe" in r_lower or "chronicler" in r_lower:
                level = LiteracyLevel.HISTORIAN
                self.character_literacy[character.id] = level
                return level
            elif "scholar" in r_lower:
                level = LiteracyLevel.SCHOLAR
                self.character_literacy[character.id] = level
                return level

        # Population-wide roll (Directive 4):
        # Adult literacy heavily weighted toward Illiterate (>= 60%),
        # with Educated/Scholar/Historian rare (<= 15% combined).
        r = keyed_float(self.seed, "character_literacy", character.id, 0, salt=0x51A7)
        if r < 0.65:
            level = LiteracyLevel.ILLITERATE
        elif r < 0.88:
            level = LiteracyLevel.BASIC_LITERACY
        elif r < 0.96:
            level = LiteracyLevel.EDUCATED
        elif r < 0.99:
            level = LiteracyLevel.SCHOLAR
        else:
            level = LiteracyLevel.HISTORIAN

        self.character_literacy[character.id] = level
        return level

    def _next_book_id(self) -> str:
        self.book_counter += 1
        return f"book_{self.seed}_{self.book_counter}"

    def _emit_book_event(
        self,
        book: Book,
        event_log: EventLog,
        raw_causes: Sequence[int],
        tick: int,
    ) -> Event:
        """
        Emits an objective BOOK_WRITTEN event into the EventLog,
        strictly validating causes against CAUSE_GRAMMAR.
        """
        # Filter causes: must exist in event log and have an allowed EventType
        allowed = CAUSE_GRAMMAR[EventType.BOOK_WRITTEN].allowed_cause_types
        valid_causes: list[int] = []
        for c_id in raw_causes:
            if c_id in event_log._by_id:
                if event_log._by_id[c_id].type in allowed:
                    valid_causes.append(c_id)
            if len(valid_causes) >= 5:
                break

        return event_log.append(
            tick=tick,
            location=book.settlement_id,
            event_type=EventType.BOOK_WRITTEN,
            participants=[("author", book.author_id)],
            causes=valid_causes,
            intent=Intent.INTENTIONAL,
            scale=Scale.INDIVIDUAL,
            payload={
                "book_id": book.id,
                "title": book.title,
                "genre": book.genre.value,
                "author_literacy": book.author_literacy.value,
                "perspective_bias": book.perspective_bias,
                "word_count": book.total_word_count,
            },
        )

    def update_tick(
        self,
        tick: int,
        event_log: EventLog,
        characters: Mapping[str, Character],
        settlements: Mapping[str, Any],
        beliefs_by_character: Optional[Mapping[str, Mapping[int, Any]]] = None,
        memories: Optional[Sequence[Any]] = None,
        relationships_by_character: Optional[Mapping[str, Mapping[str, Any]]] = None,
        religion_engine: Optional[Any] = None,
        trade_routes: Sequence[Any] = (),
        recent_events: Sequence[Event] = (),
    ) -> None:
        """
        Monthly tick update for literature generation, journal reactions,
        archive storage, and raid devastation.
        """
        if not self.enabled:
            return

        # -----------------------------------------------------------------
        # 1. Reactive Literature & Archive Damage from Recent Events
        # -----------------------------------------------------------------
        for evt in recent_events:
            # 1.1 Raid: Devastation to Settlement Archives
            if evt.type == EventType.RAID:
                target_settlement = evt.location
                affected = self.library_manager.damage_archive(
                    settlement_id=target_settlement,
                    damage_ratio=0.35,
                    rng=self.rng,
                )
                if affected:
                    event_log.append(
                        tick=tick,
                        location=target_settlement,
                        event_type=EventType.ARCHIVE_DAMAGED,
                        participants=[("archive", target_settlement)],
                        causes=[evt.id],
                        intent=Intent.MILITARY_ACTION,
                        scale=Scale.AGGREGATE,
                        payload={
                            "affected_count": len(affected),
                            "affected_titles": [b.title for b in affected[:3]],
                        },
                    )

            # 1.2 Feud or Peace: Official Legal Records
            elif evt.type in (EventType.FEUD, EventType.PEACE):
                loc = evt.location
                loc_chars = [c for c in characters.values() if c.alive and c.settlement_id == loc]
                if loc_chars:
                    # Choose elder or scholar as magistrate
                    magistrate = max(
                        loc_chars,
                        key=lambda c: (
                            self.get_character_literacy(c) in (LiteracyLevel.SCHOLAR, LiteracyLevel.HISTORIAN),
                            c.age_ticks,
                        ),
                    )
                    mag_lit = self.get_character_literacy(magistrate)
                    if mag_lit != LiteracyLevel.ILLITERATE:
                        settle_obj = settlements.get(evt.location)
                        s_name = getattr(settle_obj, "name", None) or (settle_obj.get("name") if isinstance(settle_obj, dict) else evt.location)
                        book = generate_legal_record(
                            book_id=self._next_book_id(),
                            event=evt,
                            author_name=magistrate.full_name,
                            author_id=magistrate.id,
                            tick=tick,
                            rng=self.rng,
                            literacy=mag_lit,
                            settlement_name=s_name,
                        )
                        self.library_manager.add_book(book, LibraryType.TOWN_ARCHIVE)
                        self._emit_book_event(book, event_log, [evt.id], tick)

            # 1.3 Notable Death: Biography and Personal Journals
            elif evt.type == EventType.DEATH:
                deceased_id = evt.participants_dict.get("deceased") or (
                    evt.participants[0][1] if evt.participants else None
                )
                if deceased_id and deceased_id in characters:
                    deceased = characters[deceased_id]

                    # A. Biography if deceased was elder or leader
                    if deceased.id not in self.written_biographies and deceased.age_years >= 45:
                        self.written_biographies.add(deceased.id)
                        settlement_chars = [
                            c for c in characters.values() if c.alive and c.settlement_id == deceased.settlement_id
                        ]
                        if settlement_chars:
                            author = max(
                                settlement_chars,
                                key=lambda c: (
                                    self.get_character_literacy(c)
                                    in (LiteracyLevel.HISTORIAN, LiteracyLevel.SCHOLAR, LiteracyLevel.EDUCATED),
                                    c.age_ticks,
                                ),
                            )
                            author_lit = self.get_character_literacy(author)
                            if author_lit != LiteracyLevel.ILLITERATE:
                                # Gather deceased events
                                d_events = [
                                    e for e in event_log.all_events()
                                    if any(p[1] == deceased.id for p in e.participants)
                                ]
                                author_beliefs = (
                                    beliefs_by_character.get(author.id, {}) if beliefs_by_character else {}
                                )
                                book = generate_biography(
                                    book_id=self._next_book_id(),
                                    subject=deceased,
                                    author=author,
                                    subject_events=d_events,
                                    tick=tick,
                                    rng=self.rng,
                                    literacy=author_lit,
                                    author_beliefs=author_beliefs,
                                )
                                self.library_manager.add_book(book, LibraryType.SCHOLARS_STUDY)
                                self._emit_book_event(book, event_log, [evt.id], tick)

                    # B. Personal Journal of surviving kin / spouse
                    d_fam = getattr(deceased, "family_id", "") or deceased.last_name
                    surviving_kin = [
                        c for c in characters.values()
                        if c.alive and (
                            (bool(d_fam) and (getattr(c, "family_id", "") or c.last_name) == d_fam)
                            or c.spouse_id == deceased.id
                        )
                    ]
                    surviving_kin.sort(key=lambda c: c.id)
                    for kin in surviving_kin[:2]:
                        kin_lit = self.get_character_literacy(kin)
                        if kin_lit != LiteracyLevel.ILLITERATE and self.rng.random() < 0.40:
                            kin_beliefs = []
                            if beliefs_by_character and kin.id in beliefs_by_character:
                                kin_beliefs = list(beliefs_by_character[kin.id].values())
                            kin_mems = [m for m in (memories or []) if getattr(m, "character_id", None) == kin.id]
                            kin_rels = (relationships_by_character or {}).get(kin.id, {})

                            book = generate_personal_journal(
                                book_id=self._next_book_id(),
                                character=kin,
                                memories=kin_mems,
                                beliefs=kin_beliefs,
                                relationships=kin_rels,
                                tick=tick,
                                rng=self.rng,
                                literacy=kin_lit,
                            )
                            self.library_manager.add_book(book, LibraryType.HOUSEHOLD_SHELF)
                            self._emit_book_event(book, event_log, [evt.id], tick)

            # 1.4 Marriage: Personal Journal reaction
            elif evt.type == EventType.MARRIAGE:
                for role, p_id in evt.participants:
                    if p_id in characters and characters[p_id].alive:
                        char = characters[p_id]
                        lit = self.get_character_literacy(char)
                        if lit != LiteracyLevel.ILLITERATE and self.rng.random() < 0.30:
                            c_beliefs = []
                            if beliefs_by_character and char.id in beliefs_by_character:
                                c_beliefs = list(beliefs_by_character[char.id].values())
                            c_mems = [m for m in (memories or []) if getattr(m, "character_id", None) == char.id]
                            c_rels = (relationships_by_character or {}).get(char.id, {})

                            book = generate_personal_journal(
                                book_id=self._next_book_id(),
                                character=char,
                                memories=c_mems,
                                beliefs=c_beliefs,
                                relationships=c_rels,
                                tick=tick,
                                rng=self.rng,
                                literacy=lit,
                            )
                            self.library_manager.add_book(book, LibraryType.HOUSEHOLD_SHELF)
                            self._emit_book_event(book, event_log, [evt.id], tick)
                            break  # one partner writes

            # 1.5 Pilgrimage: Travel Account
            elif evt.type == EventType.PILGRIMAGE:
                pilgrim_id = evt.participants_dict.get("pilgrim") or (
                    evt.participants[0][1] if evt.participants else None
                )
                if pilgrim_id and pilgrim_id in characters and characters[pilgrim_id].alive:
                    pilgrim = characters[pilgrim_id]
                    lit = self.get_character_literacy(pilgrim)
                    if lit != LiteracyLevel.ILLITERATE:
                        site_name = evt.payload.get("site_name", "the sacred shrine")
                        site_settlement = evt.location
                        book = generate_travel_account(
                            book_id=self._next_book_id(),
                            pilgrim=pilgrim,
                            holy_site_name=site_name,
                            holy_site_settlement=site_settlement,
                            tick=tick,
                            rng=self.rng,
                            literacy=lit,
                        )
                        self.library_manager.add_book(book, LibraryType.SCHOLARS_STUDY)
                        self._emit_book_event(book, event_log, [evt.id], tick)

            # 1.6 Religious Schism / Syncretism: New Scripture
            elif evt.type in (EventType.RELIGIOUS_SCHISM, EventType.RELIGIOUS_SYNCRETISM):
                new_rel_id = evt.payload.get("new_religion_id") or evt.payload.get("religion_id")
                if new_rel_id and new_rel_id not in self.written_scriptures and religion_engine:
                    new_rel = religion_engine.religions.get(new_rel_id)
                    if new_rel:
                        # Find priest or scholar adherent
                        adherents = [
                            c for c in characters.values()
                            if c.alive and religion_engine.get_character_faith(c.id)
                            and religion_engine.get_character_faith(c.id).religion_id == new_rel_id
                        ]
                        if adherents:
                            author = adherents[0]
                            self.written_scriptures.add(new_rel_id)
                            book = generate_religious_text(
                                book_id=self._next_book_id(),
                                religion=new_rel,
                                author=author,
                                tick=tick,
                                rng=self.rng,
                                literacy=LiteracyLevel.PRIEST,
                            )
                            self.library_manager.add_book(book, LibraryType.TEMPLE_LIBRARY)
                            self._emit_book_event(book, event_log, [evt.id], tick)

        # -----------------------------------------------------------------
        # 2. Initial Canonical Scripture Authoring (Tick 0 or Month 1)
        # -----------------------------------------------------------------
        if religion_engine and len(self.written_scriptures) == 0:
            for rel_id, rel in sorted(religion_engine.religions.items()):
                if rel_id not in self.written_scriptures:
                    adherents = [
                        c for c in characters.values()
                        if c.alive and religion_engine.get_character_faith(c.id)
                        and religion_engine.get_character_faith(c.id).religion_id == rel_id
                    ]
                    if adherents:
                        author = adherents[0]
                        self.written_scriptures.add(rel_id)
                        book = generate_religious_text(
                            book_id=self._next_book_id(),
                            religion=rel,
                            author=author,
                            tick=tick,
                            rng=self.rng,
                            literacy=LiteracyLevel.PRIEST,
                        )
                        self.library_manager.add_book(book, LibraryType.TEMPLE_LIBRARY)
                        self._emit_book_event(book, event_log, [], tick)

        # -----------------------------------------------------------------
        # 3. Periodic Annals & Compilations (Every 120 ticks = 10 Years)
        # -----------------------------------------------------------------
        if tick > 0 and tick % 120 == 0:
            for s_id in sorted(settlements.keys()):
                s_chars = [c for c in characters.values() if c.alive and c.settlement_id == s_id]
                if not s_chars:
                    continue

                # 3.1 Historical Chronicle
                historian = max(
                    s_chars,
                    key=lambda c: (
                        self.get_character_literacy(c) == LiteracyLevel.HISTORIAN,
                        self.get_character_literacy(c) == LiteracyLevel.SCHOLAR,
                        c.age_ticks,
                    ),
                )
                h_lit = self.get_character_literacy(historian)
                if h_lit != LiteracyLevel.ILLITERATE:
                    recent_set_events = [
                        e for e in event_log.all_events()
                        if e.location == s_id and e.tick >= tick - 120
                    ]
                    historian_beliefs = (
                        beliefs_by_character.get(historian.id, {}) if beliefs_by_character else {}
                    )
                    book = generate_historical_chronicle(
                        book_id=self._next_book_id(),
                        settlement_id=s_id,
                        events=recent_set_events,
                        author_name=historian.full_name,
                        author_id=historian.id,
                        tick=tick,
                        rng=self.rng,
                        literacy=h_lit,
                        author_beliefs=historian_beliefs,
                    )
                    self.library_manager.add_book(book, LibraryType.TOWN_ARCHIVE)
                    causes = [e.id for e in recent_set_events[:3]]
                    self._emit_book_event(book, event_log, causes, tick)

                # 3.2 Local Folklore & Sacred Traditions
                if religion_engine and hasattr(religion_engine, "cultural_profiles"):
                    profile = religion_engine.cultural_profiles.get(s_id)
                    if profile and (profile.folk_traditions or profile.local_customs):
                        storyteller = max(s_chars, key=lambda c: c.age_ticks)
                        st_lit = self.get_character_literacy(storyteller)
                        if st_lit != LiteracyLevel.ILLITERATE:
                            book = generate_local_folklore(
                                book_id=self._next_book_id(),
                                cultural_profile=profile,
                                author=storyteller,
                                tick=tick,
                                rng=self.rng,
                                literacy=st_lit,
                            )
                            self.library_manager.add_book(book, LibraryType.HOUSEHOLD_SHELF)
                            self._emit_book_event(book, event_log, [], tick)

                # 3.3 Myth Collection
                if religion_engine:
                    set_rel = religion_engine.get_settlement_religion(s_id)
                    if set_rel and getattr(set_rel, "myths", None):
                        myth_collector = max(
                            s_chars,
                            key=lambda c: (
                                self.get_character_literacy(c) in (LiteracyLevel.PRIEST, LiteracyLevel.SCHOLAR),
                                c.age_ticks,
                            ),
                        )
                        mc_lit = self.get_character_literacy(myth_collector)
                        if mc_lit != LiteracyLevel.ILLITERATE:
                            book = generate_myth_collection(
                                book_id=self._next_book_id(),
                                religion=set_rel,
                                author=myth_collector,
                                myths=set_rel.myths,
                                tick=tick,
                                rng=self.rng,
                                literacy=mc_lit,
                            )
                            self.library_manager.add_book(book, LibraryType.TEMPLE_LIBRARY)
                            self._emit_book_event(book, event_log, [], tick)

            # 3.4 Family Histories across Dynastic Lineages
            families: dict[str, list[Character]] = {}
            for c in characters.values():
                if c.alive:
                    f_key = getattr(c, "family_id", "") or c.last_name
                    families.setdefault(f_key, []).append(c)

            for f_key in sorted(families.keys()):
                kin_list = sorted(families[f_key], key=lambda c: c.id)
                if len(kin_list) >= 2:
                    patriarch = max(kin_list, key=lambda c: (c.age_ticks, c.id))
                    p_lit = self.get_character_literacy(patriarch)
                    if p_lit != LiteracyLevel.ILLITERATE:
                        f_events = [
                            e for e in event_log.all_events()
                            if any(p[1] in [k.id for k in kin_list] for p in e.participants)
                        ]
                        book = generate_family_history(
                            book_id=self._next_book_id(),
                            family_name=patriarch.last_name,
                            patriarch_or_author=patriarch,
                            kin_characters=kin_list,
                            family_events=f_events,
                            tick=tick,
                            rng=self.rng,
                            literacy=p_lit,
                        )
                        self.library_manager.add_book(book, LibraryType.HOUSEHOLD_SHELF)
                        causes = [e.id for e in f_events[:3]]
                        self._emit_book_event(book, event_log, causes, tick)

    def export_minecraft_book(self, book_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieves a book and formats it for Minecraft Written Book item data.
        """
        book = self.library_manager.get_book(book_id)
        if book:
            return book.to_minecraft_json()
        return None

    def get_book(self, book_id: str) -> Optional[Book]:
        return self.library_manager.get_book(book_id)

    def get_settlement_books(
        self,
        settlement_id: str,
        library_type: Optional[LibraryType] = None,
    ) -> list[Book]:
        return self.library_manager.get_settlement_books(settlement_id, library_type)

    def get_books_by_genre(self, genre: BookGenre) -> list[Book]:
        return self.library_manager.get_books_by_genre(genre)

    def to_dict(self) -> dict[str, Any]:
        """Serializes the complete LoreEngine state."""
        return {
            "seed": self.seed,
            "enabled": self.enabled,
            "book_counter": self.book_counter,
            "character_literacy": {k: v.value for k, v in sorted(self.character_literacy.items())},
            "written_biographies": sorted(self.written_biographies),
            "written_scriptures": sorted(self.written_scriptures),
            "library_manager": self.library_manager.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LoreEngine:
        """Restores a LoreEngine instance from serialized dictionary."""
        engine = cls(seed=int(data["seed"]), enabled=bool(data.get("enabled", True)))
        engine.book_counter = int(data.get("book_counter", 0))
        engine.character_literacy = {
            k: LiteracyLevel(v) for k, v in data.get("character_literacy", {}).items()
        }
        engine.written_biographies = set(data.get("written_biographies", []))
        engine.written_scriptures = set(data.get("written_scriptures", []))
        engine.library_manager = LibraryManager.from_dict(data.get("library_manager", {}))
        return engine
