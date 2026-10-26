"""
Run Database Service (RunDatabase).
Wraps SQLite connection in read-only mode, providing high-performance
paginated queries, schema validation, and entity lookups.
"""

from __future__ import annotations
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping, Optional, Sequence
import zlib

from viewer.data.schema import (
    IncompatibleSchemaError,
    SUPPORTED_SCHEMA_VERSION,
    TABLE_NAMES,
)


class RunDatabase:
    """Read-only SQLite query engine for .minemesis run archives."""

    def __init__(self, db_path: str | Path) -> None:
        self.path = Path(db_path).resolve()
        if not self.path.exists():
            raise FileNotFoundError(f"Run database file not found: {self.path}")

        # Connect with read-only pragma
        self._conn = sqlite3.connect(f"file:{self.path.as_posix()}?mode=ro", uri=True)
        self._conn.row_factory = sqlite3.Row
        cur = self._conn.cursor()
        cur.execute("PRAGMA query_only = ON;")

        # Validate schema version
        self.meta = self._load_meta()
        version = int(self.meta.get("schema_version", 1))
        if version > SUPPORTED_SCHEMA_VERSION:
            raise IncompatibleSchemaError(
                f"File schema version ({version}) is newer than supported ({SUPPORTED_SCHEMA_VERSION}). Please update the viewer."
            )

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def _load_meta(self) -> dict[str, Any]:
        cur = self._conn.cursor()
        try:
            row = cur.execute("SELECT * FROM meta LIMIT 1").fetchone()
            if row:
                return dict(row)
        except Exception:
            pass
        return {
            "schema_version": 1,
            "build_id": "viewer-v2",
            "world_seed": 0,
            "history_seed": 0,
            "pair_code": "0:0",
            "generated_at": "",
            "duration_ticks": 0,
            "total_events": 0,
            "total_characters": 0,
        }

    def get_row_counts(self) -> dict[str, int]:
        counts = {}
        cur = self._conn.cursor()
        for t in TABLE_NAMES:
            try:
                row = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
                counts[t] = row[0] if row else 0
            except Exception:
                counts[t] = 0
        return counts

    def get_name_audit_issues(self) -> list[dict[str, Any]]:
        cur = self._conn.cursor()
        try:
            rows = cur.execute("SELECT character_id, issue_type, details FROM name_audit").fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    # -------------------------------------------------------------------------
    # Settlements & Census
    # -------------------------------------------------------------------------
    def get_settlements(self) -> list[dict[str, Any]]:
        cur = self._conn.cursor()
        rows = cur.execute("SELECT * FROM settlements ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def get_geography(self) -> Optional[dict[str, Any]]:
        cur = self._conn.cursor()
        try:
            row = cur.execute("SELECT * FROM geography LIMIT 1").fetchone()
            if row:
                d = dict(row)
                if d.get("roads_json"):
                    d["roads"] = json.loads(d["roads_json"])
                return d
        except Exception:
            pass
        return None

    def get_settlement(self, settlement_id: str) -> Optional[dict[str, Any]]:
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM settlements WHERE id = ?", (settlement_id,)).fetchone()
        return dict(row) if row else None

    def get_census(self, settlement_id: Optional[str] = None) -> list[dict[str, Any]]:
        cur = self._conn.cursor()
        if settlement_id:
            rows = cur.execute(
                "SELECT * FROM census WHERE settlement_id = ? ORDER BY year",
                (settlement_id,),
            ).fetchall()
        else:
            rows = cur.execute("SELECT * FROM census ORDER BY year, settlement_id").fetchall()
        return [dict(r) for r in rows]

    # -------------------------------------------------------------------------
    # Events & Causality
    # -------------------------------------------------------------------------
    def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        era: Optional[tuple[int, int]] = None,
        settlement_id: Optional[str] = None,
        event_types: Optional[Sequence[str]] = None,
        search: Optional[str] = None,
        major_only: bool = False,
        character_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []

        if era:
            clauses.append("e.year >= ? AND e.year <= ?")
            params.extend(era)

        if settlement_id:
            # Match location or participant from settlement
            clauses.append("e.event_id IN (SELECT event_id FROM event_participants WHERE character_id = ? OR character_id LIKE ?)")
            params.extend([settlement_id, f"%{settlement_id}%"])

        if event_types:
            placeholders = ",".join("?" for _ in event_types)
            clauses.append(f"e.type IN ({placeholders})")
            params.extend(event_types)

        if major_only:
            clauses.append("e.importance >= 2.0")

        if character_id:
            clauses.append("e.event_id IN (SELECT event_id FROM event_participants WHERE character_id = ?)")
            params.append(character_id)

        if search:
            clauses.append("(e.description LIKE ? OR e.type LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
        SELECT e.event_id, e.tick, e.year, e.type, e.description, e.thread_id, e.importance
        FROM events e
        {where_sql}
        ORDER BY e.event_id ASC
        LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cur = self._conn.cursor()
        rows = cur.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_event_count(
        self,
        era: Optional[tuple[int, int]] = None,
        settlement_id: Optional[str] = None,
        event_types: Optional[Sequence[str]] = None,
        search: Optional[str] = None,
        major_only: bool = False,
        character_id: Optional[str] = None,
    ) -> int:
        clauses = []
        params: list[Any] = []

        if era:
            clauses.append("year >= ? AND year <= ?")
            params.extend(era)
        if settlement_id:
            clauses.append("event_id IN (SELECT event_id FROM event_participants WHERE character_id = ?)")
            params.append(settlement_id)
        if event_types:
            placeholders = ",".join("?" for _ in event_types)
            clauses.append(f"type IN ({placeholders})")
            params.extend(event_types)
        if major_only:
            clauses.append("importance >= 2.0")
        if character_id:
            clauses.append("event_id IN (SELECT event_id FROM event_participants WHERE character_id = ?)")
            params.append(character_id)
        if search:
            clauses.append("(description LIKE ? OR type LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT COUNT(*) FROM events {where_sql}"
        cur = self._conn.cursor()
        row = cur.execute(sql, params).fetchone()
        return row[0] if row else 0

    def get_event(self, event_id: int) -> Optional[dict[str, Any]]:
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM events WHERE event_id = ?", (event_id,)).fetchone()
        if not row:
            return None
        res = dict(row)
        res["participants"] = self.get_event_participants(event_id)
        res["causes"] = self.get_event_causes(event_id)
        res["consequences"] = self.get_event_consequences(event_id)
        return res

    def get_event_participants(self, event_id: int) -> list[dict[str, Any]]:
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT character_id, role, name_at_time FROM event_participants WHERE event_id = ?",
            (event_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_event_causes(self, event_id: int) -> list[int]:
        cur = self._conn.cursor()
        rows = cur.execute("SELECT cause_id FROM event_causes WHERE event_id = ?", (event_id,)).fetchall()
        return [r[0] for r in rows]

    def get_event_consequences(self, event_id: int) -> list[int]:
        cur = self._conn.cursor()
        rows = cur.execute("SELECT event_id FROM event_causes WHERE cause_id = ?", (event_id,)).fetchall()
        return [r[0] for r in rows]

    # -------------------------------------------------------------------------
    # Characters
    # -------------------------------------------------------------------------
    def get_characters(
        self,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None,
        settlement_id: Optional[str] = None,
        living_only: bool = False,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []

        if settlement_id:
            clauses.append("settlement_id = ?")
            params.append(settlement_id)
        if living_only:
            clauses.append("death_tick IS NULL")
        if search:
            clauses.append("(display_name LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR id LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
        SELECT * FROM characters
        {where_sql}
        ORDER BY id
        LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        cur = self._conn.cursor()
        rows = cur.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_character_count(
        self,
        search: Optional[str] = None,
        settlement_id: Optional[str] = None,
        living_only: bool = False,
    ) -> int:
        clauses = []
        params: list[Any] = []
        if settlement_id:
            clauses.append("settlement_id = ?")
            params.append(settlement_id)
        if living_only:
            clauses.append("death_tick IS NULL")
        if search:
            clauses.append("(display_name LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR id LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])
        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        cur = self._conn.cursor()
        row = cur.execute(f"SELECT COUNT(*) FROM characters {where_sql}", params).fetchone()
        return row[0] if row else 0

    def get_character(self, character_id: str) -> Optional[dict[str, Any]]:
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM characters WHERE id = ?", (character_id,)).fetchone()
        return dict(row) if row else None

    def get_character_name(self, character_id: str) -> Optional[str]:
        cur = self._conn.cursor()
        row = cur.execute("SELECT display_name FROM characters WHERE id = ?", (character_id,)).fetchone()
        return row[0] if row else None

    def get_character_events(self, character_id: str) -> list[dict[str, Any]]:
        cur = self._conn.cursor()
        rows = cur.execute(
            """
            SELECT e.event_id, e.tick, e.year, e.type, e.description, ep.role
            FROM events e
            JOIN event_participants ep ON e.event_id = ep.event_id
            WHERE ep.character_id = ?
            ORDER BY e.event_id ASC
            """,
            (character_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_character_epistemic_cases(self, character_id: str) -> list[dict[str, Any]]:
        cur = self._conn.cursor()
        rows = cur.execute(
            """
            SELECT * FROM epistemic_ledger
            WHERE believer_character_id = ? OR subject_character_id = ?
            ORDER BY year ASC
            """,
            (character_id, character_id),
        ).fetchall()
        return [dict(r) for r in rows]

    # -------------------------------------------------------------------------
    # Literature & Books
    # -------------------------------------------------------------------------
    def get_books(
        self,
        settlement_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if settlement_id:
            clauses.append("settlement_id = ?")
            params.append(settlement_id)
        if search:
            clauses.append("(title LIKE ? OR author_name LIKE ? OR topic LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        limit_sql = f" LIMIT {int(limit)} OFFSET {int(offset)}" if limit is not None else ""
        cur = self._conn.cursor()
        rows = cur.execute(
            f"SELECT id, title, author_id, author_name, year_written, settlement_id, topic, page_count FROM books {where_sql} ORDER BY year_written DESC{limit_sql}",
            params,
        ).fetchall()
        return [dict(r) for r in rows]

    def get_book(self, book_id: str) -> Optional[dict[str, Any]]:
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not row:
            return None
        res = dict(row)
        blob = res.get("pages_blob_compressed")
        if blob:
            try:
                pages_json = zlib.decompress(blob).decode("utf-8")
                res["pages"] = json.loads(pages_json)
            except Exception:
                res["pages"] = ["[Error decompressing book pages]"]
        else:
            res["pages"] = []
        return res

    # -------------------------------------------------------------------------
    # Religions & Faith
    # -------------------------------------------------------------------------
    def get_religions(self) -> list[dict[str, Any]]:
        cur = self._conn.cursor()
        rows = cur.execute("SELECT * FROM religions ORDER BY founded_year ASC").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["traits"] = json.loads(d.get("traits_json", "{}"))
            except Exception:
                d["traits"] = {}
            result.append(d)
        return result

    def get_religion(self, religion_id: str) -> Optional[dict[str, Any]]:
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM religions WHERE id = ?", (religion_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["traits"] = json.loads(d.get("traits_json", "{}"))
        except Exception:
            d["traits"] = {}
        return d

    def get_holy_sites(self, religion_id: Optional[str] = None) -> list[dict[str, Any]]:
        cur = self._conn.cursor()
        if religion_id:
            rows = cur.execute("SELECT * FROM holy_sites WHERE religion_id = ?", (religion_id,)).fetchall()
        else:
            rows = cur.execute("SELECT * FROM holy_sites").fetchall()
        return [dict(r) for r in rows]

    def get_myths(self, religion_id: Optional[str] = None) -> list[dict[str, Any]]:
        cur = self._conn.cursor()
        if religion_id:
            rows = cur.execute("SELECT * FROM myths WHERE religion_id = ? ORDER BY year_recorded", (religion_id,)).fetchall()
        else:
            rows = cur.execute("SELECT * FROM myths ORDER BY year_recorded").fetchall()
        return [dict(r) for r in rows]

    # -------------------------------------------------------------------------
    # Threads
    # -------------------------------------------------------------------------
    def get_threads(self) -> list[dict[str, Any]]:
        cur = self._conn.cursor()
        rows = cur.execute("SELECT * FROM threads ORDER BY event_count DESC").fetchall()
        return [dict(r) for r in rows]

    def get_thread(self, thread_id: str) -> Optional[dict[str, Any]]:
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM threads WHERE id = ?", (thread_id,)).fetchone()
        return dict(row) if row else None

    def get_thread_events(self, thread_id: str) -> list[dict[str, Any]]:
        cur = self._conn.cursor()
        rows = cur.execute("SELECT * FROM events WHERE thread_id = ? ORDER BY event_id ASC", (thread_id,)).fetchall()
        return [dict(r) for r in rows]

    # -------------------------------------------------------------------------
    # Epistemic Ledger
    # -------------------------------------------------------------------------
    def get_epistemic_cases(
        self,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if search:
            clauses.append("(ground_truth LIKE ? OR belief_summary LIKE ? OR case_type LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        cur = self._conn.cursor()
        rows = cur.execute(
            f"SELECT * FROM epistemic_ledger {where_sql} ORDER BY year ASC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        return [dict(r) for r in rows]
