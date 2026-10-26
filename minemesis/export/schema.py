"""
SQLite Run Database Schema (Version 1).

Adheres to Minemesis Viewer V2 Architecture:
- Single-file run archive (.minemesis)
- Normalized relational structure
- High-performance indexed tables
- Zero-RAM streaming writer compatible
"""

from __future__ import annotations

CURRENT_SCHEMA_VERSION = 1
BUILD_ID = "viewer-v2"

CREATE_TABLES_SQL = """
-- Meta information about the run
CREATE TABLE IF NOT EXISTS meta (
    schema_version INTEGER NOT NULL,
    build_id TEXT NOT NULL,
    world_seed INTEGER NOT NULL,
    history_seed INTEGER NOT NULL,
    pair_code TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    duration_ticks INTEGER NOT NULL,
    total_events INTEGER NOT NULL,
    total_characters INTEGER NOT NULL
);

-- Settlement founding and environment
CREATE TABLE IF NOT EXISTS settlements (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    founded_tick INTEGER NOT NULL,
    biome TEXT NOT NULL,
    culture TEXT NOT NULL
);

-- Annual settlement census
CREATE TABLE IF NOT EXISTS census (
    year INTEGER NOT NULL,
    settlement_id TEXT NOT NULL,
    population INTEGER NOT NULL,
    food REAL NOT NULL,
    wealth REAL NOT NULL,
    PRIMARY KEY (year, settlement_id)
);
CREATE INDEX IF NOT EXISTS idx_census_year ON census(year);
CREATE INDEX IF NOT EXISTS idx_census_settlement ON census(settlement_id);

-- Immutable chronological event log
CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY,
    tick INTEGER NOT NULL,
    year INTEGER NOT NULL,
    type TEXT NOT NULL,
    description TEXT NOT NULL,
    thread_id TEXT,
    importance REAL NOT NULL DEFAULT 1.0
);
CREATE INDEX IF NOT EXISTS idx_events_year ON events(year);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_thread ON events(thread_id);

-- Event participants with historical snapshot name
CREATE TABLE IF NOT EXISTS event_participants (
    event_id INTEGER NOT NULL,
    character_id TEXT NOT NULL,
    role TEXT NOT NULL,
    name_at_time TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ep_event ON event_participants(event_id);
CREATE INDEX IF NOT EXISTS idx_ep_char ON event_participants(character_id);

-- Causal DAG links between events
CREATE TABLE IF NOT EXISTS event_causes (
    event_id INTEGER NOT NULL,
    cause_id INTEGER NOT NULL,
    PRIMARY KEY (event_id, cause_id)
);
CREATE INDEX IF NOT EXISTS idx_ec_event ON event_causes(event_id);
CREATE INDEX IF NOT EXISTS idx_ec_cause ON event_causes(cause_id);

-- Character biographies and lineage
CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    name_ordinal INTEGER NOT NULL DEFAULT 1,
    birth_tick INTEGER NOT NULL,
    death_tick INTEGER,
    sex TEXT NOT NULL,
    settlement_id TEXT NOT NULL,
    mother_id TEXT,
    father_id TEXT,
    spouse_id TEXT,
    cause_of_death TEXT,
    profession TEXT NOT NULL DEFAULT 'Laborer',
    is_historical INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_char_settlement ON characters(settlement_id);
CREATE INDEX IF NOT EXISTS idx_char_display_name ON characters(display_name);

-- Epistemic ledger (Truth vs Subjective Belief)
CREATE TABLE IF NOT EXISTS epistemic_ledger (
    case_id TEXT NOT NULL,
    case_type TEXT NOT NULL,
    year INTEGER NOT NULL,
    subject_character_id TEXT NOT NULL,
    ground_truth TEXT NOT NULL,
    believer_character_id TEXT NOT NULL,
    belief_summary TEXT NOT NULL,
    source_type TEXT NOT NULL,
    confidence REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ledger_case ON epistemic_ledger(case_id);
CREATE INDEX IF NOT EXISTS idx_ledger_year ON epistemic_ledger(year);
CREATE INDEX IF NOT EXISTS idx_ledger_subject ON epistemic_ledger(subject_character_id);
CREATE INDEX IF NOT EXISTS idx_ledger_believer ON epistemic_ledger(believer_character_id);

-- Literature and written books
CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author_id TEXT NOT NULL,
    author_name TEXT NOT NULL,
    year_written INTEGER NOT NULL,
    settlement_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    pages_blob_compressed BLOB NOT NULL,
    page_count INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_books_settlement ON books(settlement_id);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author_id);
CREATE INDEX IF NOT EXISTS idx_books_year ON books(year_written);

-- Religious faiths and doctrines
CREATE TABLE IF NOT EXISTS religions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id TEXT,
    founded_year INTEGER NOT NULL,
    founder_id TEXT,
    traits_json TEXT NOT NULL DEFAULT '{}',
    adherent_count INTEGER NOT NULL DEFAULT 0
);

-- Holy sites
CREATE TABLE IF NOT EXISTS holy_sites (
    settlement_id TEXT NOT NULL,
    religion_id TEXT NOT NULL,
    dedication_year INTEGER NOT NULL,
    PRIMARY KEY (settlement_id, religion_id)
);
CREATE INDEX IF NOT EXISTS idx_hs_settlement ON holy_sites(settlement_id);
CREATE INDEX IF NOT EXISTS idx_hs_religion ON holy_sites(religion_id);

-- Sacred myths and oral histories
CREATE TABLE IF NOT EXISTS myths (
    id TEXT PRIMARY KEY,
    religion_id TEXT NOT NULL,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    year_recorded INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_myths_religion ON myths(religion_id);

-- Historical narrative threads
CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    event_count INTEGER NOT NULL
);

-- Name Integrity Audit Results
CREATE TABLE IF NOT EXISTS name_audit (
    character_id TEXT,
    issue_type TEXT NOT NULL,
    details TEXT NOT NULL
);

-- Macro WorldSpec & Geography
CREATE TABLE IF NOT EXISTS geography (
    world_seed INTEGER PRIMARY KEY,
    map_width INTEGER NOT NULL,
    map_height INTEGER NOT NULL,
    settlement_count INTEGER NOT NULL,
    terrain_blob_compressed BLOB,
    roads_json TEXT NOT NULL
);
"""
