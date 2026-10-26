"""
Run Database Writer (Zero-RAM Streaming SQLite Exporter).

Streams simulation history directly to a single-file .minemesis database
in batched transactions, keeping memory footprint constant across centuries.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Mapping, Optional, Sequence
import zlib

from minemesis.export.schema import (
    BUILD_ID,
    CREATE_TABLES_SQL,
    CURRENT_SCHEMA_VERSION,
)

logger = logging.getLogger("minemesis.export")


class RunDBSink:
    """Interface / Base Sink for simulation historical telemetry."""

    def record_settlement(self, id: str, name: str, founded_tick: int, biome: str, culture: str) -> None:
        pass

    def record_geography(
        self,
        world_seed: int,
        map_width: int,
        map_height: int,
        settlement_count: int,
        terrain_blob_compressed: Optional[bytes],
        roads_json: str,
    ) -> None:
        pass

    def record_census(self, year: int, settlement_id: str, population: int, food: float, wealth: float) -> None:
        pass

    def record_event(
        self,
        event_id: int,
        tick: int,
        year: int,
        event_type: str,
        description: str,
        thread_id: Optional[str] = None,
        importance: float = 1.0,
        participants: Sequence[tuple[str, str, str]] = (),  # (character_id, role, name_at_time)
        causes: Sequence[int] = (),
    ) -> None:
        pass

    def record_character(self, char: Any, is_historical: bool = False) -> None:
        pass

    def record_characters(self, chars: Iterable[Any]) -> None:
        pass

    def record_book(
        self,
        book_id: str,
        title: str,
        author_id: str,
        author_name: str,
        year_written: int,
        settlement_id: str,
        topic: str,
        pages: Sequence[str],
    ) -> None:
        pass

    def record_religion(
        self,
        rel_id: str,
        name: str,
        parent_id: Optional[str],
        founded_year: int,
        founder_id: Optional[str],
        traits: Mapping[str, Any],
        adherent_count: int,
    ) -> None:
        pass

    def record_holy_site(self, settlement_id: str, religion_id: str, dedication_year: int) -> None:
        pass

    def record_myth(self, myth_id: str, religion_id: str, title: str, text: str, year_recorded: int) -> None:
        pass

    def record_epistemic_case(
        self,
        case_id: str,
        case_type: str,
        year: int,
        subject_character_id: str,
        ground_truth: str,
        believer_character_id: str,
        belief_summary: str,
        source_type: str,
        confidence: float,
    ) -> None:
        pass

    def record_thread(
        self,
        thread_id: str,
        title: str,
        category: str,
        start_year: int,
        end_year: int,
        event_count: int,
    ) -> None:
        pass

    def finalize(self, meta_info: Mapping[str, Any]) -> None:
        pass


class RunDBWriter(RunDBSink):
    """
    High-performance, zero-RAM SQLite exporter for Minemesis simulation runs.
    Flushes batches of 1,000 rows in single transactions.
    """

    BATCH_SIZE = 1000

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except OSError:
                pass
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(str(self.db_path))
        self._cursor = self._conn.cursor()

        # Performance pragmas
        self._cursor.execute("PRAGMA journal_mode = WAL;")
        self._cursor.execute("PRAGMA synchronous = NORMAL;")
        self._cursor.execute("PRAGMA cache_size = 10000;")
        self._cursor.execute("PRAGMA temp_store = MEMORY;")

        # Create schema and indices
        self._cursor.executescript(CREATE_TABLES_SQL)
        self._conn.commit()

        # Internal buffers
        self._buffers: dict[str, list[tuple]] = {
            "settlements": [],
            "census": [],
            "events": [],
            "event_participants": [],
            "event_causes": [],
            "characters": [],
            "epistemic_ledger": [],
            "books": [],
            "religions": [],
            "holy_sites": [],
            "myths": [],
            "threads": [],
        }

        self._written_characters: set[str] = set()
        self._written_settlements: set[str] = set()
        self._written_holy_sites: set[tuple[str, str]] = set()
        self._is_finalized = False

    def _flush_buffer(self, table: str) -> None:
        items = self._buffers[table]
        if not items:
            return

        if table == "settlements":
            sql = "INSERT OR REPLACE INTO settlements VALUES (?, ?, ?, ?, ?)"
        elif table == "census":
            sql = "INSERT OR REPLACE INTO census VALUES (?, ?, ?, ?, ?)"
        elif table == "events":
            sql = "INSERT OR REPLACE INTO events VALUES (?, ?, ?, ?, ?, ?, ?)"
        elif table == "event_participants":
            sql = "INSERT INTO event_participants VALUES (?, ?, ?, ?)"
        elif table == "event_causes":
            sql = "INSERT OR IGNORE INTO event_causes VALUES (?, ?)"
        elif table == "characters":
            sql = "INSERT OR REPLACE INTO characters VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        elif table == "epistemic_ledger":
            sql = "INSERT INTO epistemic_ledger VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        elif table == "books":
            sql = "INSERT OR REPLACE INTO books VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        elif table == "religions":
            sql = "INSERT OR REPLACE INTO religions VALUES (?, ?, ?, ?, ?, ?, ?)"
        elif table == "holy_sites":
            sql = "INSERT OR REPLACE INTO holy_sites VALUES (?, ?, ?)"
        elif table == "myths":
            sql = "INSERT OR REPLACE INTO myths VALUES (?, ?, ?, ?, ?)"
        elif table == "threads":
            sql = "INSERT OR REPLACE INTO threads VALUES (?, ?, ?, ?, ?, ?)"
        else:
            return

        self._cursor.executemany(sql, items)
        self._conn.commit()
        items.clear()

    def _check_flush(self, table: str) -> None:
        if len(self._buffers[table]) >= self.BATCH_SIZE:
            self._flush_buffer(table)

    def flush_all(self) -> None:
        for t in self._buffers.keys():
            self._flush_buffer(t)

    def record_settlement(self, id: str, name: str, founded_tick: int, biome: str, culture: str) -> None:
        if id in self._written_settlements:
            return
        self._written_settlements.add(id)
        self._buffers["settlements"].append((id, name, founded_tick, biome, culture))
        self._check_flush("settlements")

    def record_geography(
        self,
        world_seed: int,
        map_width: int,
        map_height: int,
        settlement_count: int,
        terrain_blob_compressed: Optional[bytes],
        roads_json: str,
    ) -> None:
        try:
            cur = self._conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO geography VALUES (?, ?, ?, ?, ?, ?)",
                (int(world_seed), int(map_width), int(map_height), int(settlement_count), terrain_blob_compressed, str(roads_json)),
            )
            self._conn.commit()
        except Exception as e:
            logger.warning("Failed to record geography: %s", e)

    def record_census(self, year: int, settlement_id: str, population: int, food: float, wealth: float) -> None:
        self._buffers["census"].append((year, settlement_id, int(population), float(food), float(wealth)))
        self._check_flush("census")

    def record_event(
        self,
        event_id: int,
        tick: int,
        year: int,
        event_type: str,
        description: str,
        thread_id: Optional[str] = None,
        importance: float = 1.0,
        participants: Sequence[tuple[str, str, str]] = (),
        causes: Sequence[int] = (),
    ) -> None:
        self._buffers["events"].append((
            int(event_id),
            int(tick),
            int(year),
            str(event_type),
            str(description),
            str(thread_id) if thread_id else None,
            float(importance),
        ))
        self._check_flush("events")

        for char_id, role, name_at_time in participants:
            clean_name = str(name_at_time).strip() or "Citizen"
            self._buffers["event_participants"].append((
                int(event_id),
                str(char_id),
                str(role),
                clean_name,
            ))
        self._check_flush("event_participants")

        for c_id in causes:
            self._buffers["event_causes"].append((int(event_id), int(c_id)))
        self._check_flush("event_causes")

    def record_character(self, char: Any, is_historical: bool = False) -> None:
        c_id = getattr(char, "id", None) or (char.get("id") if isinstance(char, dict) else None)
        if not c_id:
            return

        first_name = (
            getattr(char, "first_name", None)
            or (char.get("first_name") if isinstance(char, dict) else None)
            or "Citizen"
        )
        last_name = (
            getattr(char, "last_name", None)
            or (char.get("last_name") if isinstance(char, dict) else None)
            or "Commoner"
        )
        display_name = (
            getattr(char, "display_name", None)
            or (char.get("display_name") if isinstance(char, dict) else None)
            or f"{first_name} {last_name}".strip()
        )
        name_ordinal = int(
            getattr(char, "name_ordinal", 1)
            or (char.get("name_ordinal", 1) if isinstance(char, dict) else 1)
        )
        birth_tick = int(
            getattr(char, "birth_tick", 0)
            or (char.get("birth_tick", 0) if isinstance(char, dict) else 0)
        )
        death_tick = getattr(char, "death_tick", None) or (
            char.get("death_tick") if isinstance(char, dict) else None
        )
        if death_tick is not None:
            death_tick = int(death_tick)
            if birth_tick == 0 and hasattr(char, "age_ticks"):
                birth_tick = max(0, death_tick - getattr(char, "age_ticks", 0))

        sex = (
            getattr(char, "sex", "M")
            or (char.get("sex") if isinstance(char, dict) else "M")
        )
        settlement_id = (
            getattr(char, "settlement_id", "")
            or (char.get("settlement_id") if isinstance(char, dict) else "")
        )
        mother_id = getattr(char, "mother_id", None) or (
            char.get("mother_id") if isinstance(char, dict) else None
        )
        father_id = getattr(char, "father_id", None) or (
            char.get("father_id") if isinstance(char, dict) else None
        )
        spouse_id = getattr(char, "spouse_id", None) or (
            char.get("spouse_id") if isinstance(char, dict) else None
        )
        cause_of_death = (
            getattr(char, "cause_of_death", None)
            or (char.get("cause_of_death") if isinstance(char, dict) else None)
        )
        profession = (
            getattr(char, "profession", "Laborer")
            or (char.get("profession") if isinstance(char, dict) else "Laborer")
        )

        self._written_characters.add(c_id)
        self._buffers["characters"].append((
            str(c_id),
            str(first_name),
            str(last_name),
            str(display_name),
            int(name_ordinal),
            int(birth_tick),
            death_tick,
            str(sex),
            str(settlement_id),
            str(mother_id) if mother_id else None,
            str(father_id) if father_id else None,
            str(spouse_id) if spouse_id else None,
            str(cause_of_death) if cause_of_death else None,
            str(profession),
            1 if is_historical else 0,
        ))
        self._check_flush("characters")

    def record_characters(self, chars: Iterable[Any]) -> None:
        for c in chars:
            self.record_character(c, is_historical=False)

    def record_book(
        self,
        book_id: str,
        title: str,
        author_id: str,
        author_name: str,
        year_written: int,
        settlement_id: str,
        topic: str,
        pages: Sequence[str],
    ) -> None:
        pages_list = list(pages)
        pages_blob = zlib.compress(json.dumps(pages_list).encode("utf-8"))
        self._buffers["books"].append((
            str(book_id),
            str(title),
            str(author_id),
            str(author_name),
            int(year_written),
            str(settlement_id),
            str(topic),
            pages_blob,
            len(pages_list),
        ))
        self._check_flush("books")

    def record_religion(
        self,
        rel_id: str,
        name: str,
        parent_id: Optional[str],
        founded_year: int,
        founder_id: Optional[str],
        traits: Mapping[str, Any],
        adherent_count: int,
    ) -> None:
        def default_serializer(o: Any) -> Any:
            if hasattr(o, "to_dict"):
                return o.to_dict()
            if hasattr(o, "value"):
                return o.value
            return str(o)

        traits_dict: dict[str, Any] = {}
        if traits:
            for k, v in traits.items():
                if hasattr(v, "to_dict"):
                    traits_dict[k] = v.to_dict()
                elif hasattr(v, "value"):
                    traits_dict[k] = v.value
                elif isinstance(v, (str, int, float, bool, list, dict)):
                    traits_dict[k] = v
                else:
                    traits_dict[k] = str(v)
        traits_json = json.dumps(traits_dict, default=default_serializer)
        self._buffers["religions"].append((
            str(rel_id),
            str(name),
            str(parent_id) if parent_id else None,
            int(founded_year),
            str(founder_id) if founder_id else None,
            traits_json,
            int(adherent_count),
        ))
        self._check_flush("religions")

    def record_holy_site(self, settlement_id: str, religion_id: str, dedication_year: int) -> None:
        key = (settlement_id, religion_id)
        if key in self._written_holy_sites:
            return
        self._written_holy_sites.add(key)
        self._buffers["holy_sites"].append((str(settlement_id), str(religion_id), int(dedication_year)))
        self._check_flush("holy_sites")

    def record_myth(self, myth_id: str, religion_id: str, title: str, text: str, year_recorded: int) -> None:
        self._buffers["myths"].append((
            str(myth_id),
            str(religion_id),
            str(title),
            str(text),
            int(year_recorded),
        ))
        self._check_flush("myths")

    def record_epistemic_case(
        self,
        case_id: str,
        case_type: str,
        year: int,
        subject_character_id: str,
        ground_truth: str,
        believer_character_id: str,
        belief_summary: str,
        source_type: str,
        confidence: float,
    ) -> None:
        self._buffers["epistemic_ledger"].append((
            str(case_id),
            str(case_type),
            int(year),
            str(subject_character_id),
            str(ground_truth),
            str(believer_character_id),
            str(belief_summary),
            str(source_type),
            float(confidence),
        ))
        self._check_flush("epistemic_ledger")

    def record_thread(
        self,
        thread_id: str,
        title: str,
        category: str,
        start_year: int,
        end_year: int,
        event_count: int,
    ) -> None:
        self._buffers["threads"].append((
            str(thread_id),
            str(title),
            str(category),
            int(start_year),
            int(end_year),
            int(event_count),
        ))
        self._check_flush("threads")

    def _auto_generate_threads(self) -> None:
        """Derives storylines/threads from recorded events and links them."""
        # 1. Feud threads
        cur = self._conn.cursor()
        feud_events = cur.execute(
            "SELECT event_id, year, type, description FROM events WHERE type IN ('Feud', 'FeudBegins', 'FeudReconciliation') ORDER BY event_id"
        ).fetchall()
        if feud_events:
            min_y = feud_events[0][1]
            max_y = feud_events[-1][1]
            t_id = "thread_feuds"
            cur.execute(
                "INSERT OR REPLACE INTO threads VALUES (?, ?, ?, ?, ?, ?)",
                (t_id, "Inter-Family Blood Feuds & Vendettas", "Feuds", min_y, max_y, len(feud_events)),
            )
            cur.execute(
                "UPDATE events SET thread_id = ? WHERE type IN ('Feud', 'FeudBegins', 'FeudReconciliation')",
                (t_id,),
            )

        # 2. Religious threads
        rel_events = cur.execute(
            "SELECT event_id, year FROM events WHERE type IN ('ReligiousSchism', 'ReligiousSyncretism', 'HolySiteConsecrated', 'Pilgrimage') ORDER BY event_id"
        ).fetchall()
        if rel_events:
            min_y = rel_events[0][1]
            max_y = rel_events[-1][1]
            t_id = "thread_faith"
            cur.execute(
                "INSERT OR REPLACE INTO threads VALUES (?, ?, ?, ?, ?, ?)",
                (t_id, "The Evolution of Faith, Schisms, and Syncretism", "Faith", min_y, max_y, len(rel_events)),
            )
            cur.execute(
                "UPDATE events SET thread_id = ? WHERE type IN ('ReligiousSchism', 'ReligiousSyncretism', 'HolySiteConsecrated', 'Pilgrimage')",
                (t_id,),
            )

        # 3. Trade and Economic routes
        trade_events = cur.execute(
            "SELECT event_id, year FROM events WHERE type IN ('TradeRouteFounded', 'TradeRouteBroken', 'Raid') ORDER BY event_id"
        ).fetchall()
        if trade_events:
            min_y = trade_events[0][1]
            max_y = trade_events[-1][1]
            t_id = "thread_trade"
            cur.execute(
                "INSERT OR REPLACE INTO threads VALUES (?, ?, ?, ?, ?, ?)",
                (t_id, "Trade Networks, Expansion, and Border Raids", "Trade", min_y, max_y, len(trade_events)),
            )
            cur.execute(
                "UPDATE events SET thread_id = ? WHERE type IN ('TradeRouteFounded', 'TradeRouteBroken', 'Raid')",
                (t_id,),
            )

        # 4. Literature & Annals
        lore_events = cur.execute(
            "SELECT event_id, year FROM events WHERE type IN ('BookWritten', 'ArchiveDamaged') ORDER BY event_id"
        ).fetchall()
        if lore_events:
            min_y = lore_events[0][1]
            max_y = lore_events[-1][1]
            t_id = "thread_lore"
            cur.execute(
                "INSERT OR REPLACE INTO threads VALUES (?, ?, ?, ?, ?, ?)",
                (t_id, "Written Annals and Literary Records", "Lore", min_y, max_y, len(lore_events)),
            )
            cur.execute(
                "UPDATE events SET thread_id = ? WHERE type IN ('BookWritten', 'ArchiveDamaged')",
                (t_id,),
            )

        self._conn.commit()

    def finalize(self, meta_info: Mapping[str, Any]) -> None:
        """Flushes remaining buffers, runs Name Integrity Audit, and records meta header."""
        if self._is_finalized:
            return

        self.flush_all()
        self._auto_generate_threads()

        # Automated Name Integrity Audit
        audit_query = """
        SELECT id AS character_id, 'missing_name' AS issue_type, 'Missing display_name' AS details
        FROM characters WHERE display_name IS NULL OR display_name = ''
        UNION ALL
        SELECT DISTINCT character_id, 'dangling_participant' AS issue_type,
               'Invalid name_at_time: ' || COALESCE(name_at_time, 'NULL') AS details
        FROM event_participants
        WHERE name_at_time IS NULL OR name_at_time = '' OR name_at_time LIKE '%Unknown%' OR name_at_time LIKE '%None%'
        """
        audit_issues = self._cursor.execute(audit_query).fetchall()
        if audit_issues:
            logger.warning("Name Audit detected %d issues: %s", len(audit_issues), audit_issues[:5])
            self._cursor.executemany(
                "INSERT INTO name_audit VALUES (?, ?, ?)",
                audit_issues,
            )
        self._conn.commit()

        # Record meta info
        total_events = self._cursor.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        total_characters = self._cursor.execute("SELECT COUNT(*) FROM characters").fetchone()[0]

        self._cursor.execute(
            "INSERT INTO meta VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                int(meta_info.get("schema_version", CURRENT_SCHEMA_VERSION)),
                str(meta_info.get("build_id", BUILD_ID)),
                int(meta_info.get("world_seed", 0)),
                int(meta_info.get("history_seed", 0)),
                str(meta_info.get("pair_code", "")),
                str(meta_info.get("generated_at", "")),
                int(meta_info.get("duration_ticks", 0)),
                int(total_events),
                int(total_characters),
            ),
        )
        self._conn.commit()
        self._conn.close()
        self._is_finalized = True
