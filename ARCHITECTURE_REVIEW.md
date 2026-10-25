# MINEMESIS ARCHITECTURE REVIEW & SYSTEM AUDIT
**Document Version:** 1.0.0 (Milestone 0.5.3 Complete)  
**Target:** External Architectural Analysis & Performance Optimization  
**Date:** October 2026  
**Status:** Canonical Reference Specification  

---

## EXECUTIVE SUMMARY

Minemesis is a deterministic, event-driven historical simulation engine built in Python 3.14. The system operates on the core epistemological thesis: **"Reality is objective; historical drama is subjective."**

Objective events (births, deaths, marriages, raids, famines, feuds, revelations, schisms, book publications) are recorded in an append-only, immutable **Event Log**. Characters do not interact with raw events directly; they observe events through a **Perception Filter** that generates subjective **Beliefs**. Beliefs trigger emotional **Memories** that decay over time. Inter-character **Relationships** are computed dynamically on demand by aggregating active memories. Decisions (feuds, alliances, succession disputes, books, religious reforms) are made strictly from subjective beliefs and emotional states, emitting new objective events whose causal antecedents are validated against a strict **Causal Grammar**.

This document outlines the complete architectural layout, data models, object lifecycles, computational complexity, memory profiles, graph structures, bottlenecks, and scale projections.

---

## 1. REPOSITORY TREE

```
D:\MINEMESIS
├── .gitignore                          # Git exclusions (pycache, build, dist, venv)
├── agent.md                            # High-level product vision and design constraints
├── agent_changelog.md                  # Milestone progress and audit trail
├── brief.md                            # Core engine thesis and architectural rules
├── main.py                             # CLI launcher and entry point
├── requirements-dev.txt                # Development dependencies (pytest, psutil, pyinstaller)
├── ARCHITECTURE_REVIEW.md             # This document
│
├── minemesis/                          # Core simulation package
│   ├── __init__.py                     # Package metadata
│   ├── analytics.py                    # Multi-run evaluation, metrics aggregation, validation summaries
│   ├── cli.py                          # Command-line interface and simulation runner
│   │
│   ├── core/                           # Invariable core infrastructure
│   │   ├── __init__.py                 # Subpackage init
│   │   ├── causal_grammar.py           # Validates DAG causal links (valid parent/child event types)
│   │   ├── event_log.py                # Append-only immutable EventLog and Event schema
│   │   ├── history_printer.py          # Causal chain rendering, Mermaid DAG export, linear history
│   │   ├── invariants.py               # Pre/post-condition assertion verifiers (living actor checks)
│   │   ├── rng.py                      # Pure keyed hashing RNG routines (hashlib.sha256-based)
│   │   ├── seed.py                     # SeedPair container (world seed vs history seed split)
│   │   └── types.py                    # Enums: EventType, Intent, Scale, Emotion, BeliefSource
│   │
│   ├── models/                         # Domain entity dataclasses
│   │   ├── __init__.py                 # Subpackage init
│   │   ├── belief.py                   # Subjective Belief schema with supersession tracking
│   │   ├── character.py                # Character entity schema (kinship, age, status, traits)
│   │   ├── memory.py                   # Emotional Memory schema (exponential decay model)
│   │   ├── relationship.py             # Dynamically computed interpersonal relationship view
│   │   └── settlement.py               # Settlement entity & continuous TradeRoute state
│   │
│   ├── systems/                        # Simulation lifecycle, economy, and conflict systems
│   │   ├── __init__.py                 # Subpackage init
│   │   ├── cast_gen.py                 # Initial character demographic seeding and family trees
│   │   ├── conflict.py                 # Feuds, raids, famines, revenge killings, peace treaties
│   │   ├── gossip.py                   # Monthly knowledge propagation and rumor distortion
│   │   ├── life_cycle.py               # Births, deaths, aging, inter/intra-settlement marriages
│   │   ├── memory_system.py            # Belief-to-memory transformation and re-appraisal
│   │   ├── perception.py               # Event-to-belief perception filter and bias engine
│   │   ├── simulation.py               # Master simulation loop (step_month, run_years)
│   │   ├── world_gen.py                # Legacy and bridge world generation dispatch
│   │   ├── world_gen_v0.py             # Milestone 0.5.3 V0 procedural world generator (10-35 sites)
│   │   └── world_spec.py               # WorldSpec dataclass and WorldProvider protocol
│   │
│   ├── religion/                       # Standalone Religion Engine (Milestones R0, R1, R1.5, R2)
│   │   ├── __init__.py                 # Subpackage init
│   │   ├── religion_analytics.py       # Religious distribution, schism, and syncretism metrics
│   │   ├── religion_config.py          # Religion system toggles and constants
│   │   ├── religion_culture.py         # Cultural dimensions, social values, village customs
│   │   ├── religion_effects.py         # Demographic, trade, and morale modifiers from traits
│   │   ├── religion_engine.py          # Master ReligionEngine update tick and coordinator
│   │   ├── religion_figures.py         # Saints, prophets, martyrs, and religious figure tracking
│   │   ├── religion_generation.py      # Initial theology generation from natural geographic features
│   │   ├── religion_geography.py       # Sacred sites, pilgrimages, site tier elevation
│   │   ├── religion_heresies.py        # Heresy declaration, doctrinal divergence, inquisitions
│   │   ├── religion_interpretation.py  # Religious cognitive filter applied to character perception
│   │   ├── religion_models.py          # Dataclasses: Religion, Faith, HolySite, Myth, FolkTradition
│   │   ├── religion_myths.py           # Procedural myth making, embellishment, retellings
│   │   ├── religion_schisms.py         # Sect fracturing, parent-child lineages, reunification
│   │   ├── religion_serialization.py   # JSON / schema export of religious entities
│   │   ├── religion_spread.py          # Organic conversion, missionary work, trade route drift
│   │   ├── religion_syncretism.py      # Trait borrowing, folk absorption, syncretic faiths
│   │   ├── religion_tensions.py        # Inter-faith theological hostility & relationship offsets
│   │   ├── religion_traits.py          # Theological trait library (cosmology, taboos, virtues)
│   │   └── religion_virtues.py         # Action evaluation against faith virtues & sins
│   │
│   ├── lore/                           # Standalone Literature Engine (Milestone L0)
│   │   ├── __init__.py                 # Subpackage init
│   │   ├── lore_engine.py              # Master LoreEngine update tick and coordinator
│   │   ├── lore_generators.py          # Procedural text generators (chronicles, scriptures, tragedies)
│   │   ├── lore_libraries.py           # Town archives, temple libraries, household shelves, book damage
│   │   ├── lore_models.py              # Dataclasses: Book, Library, LiteracyLevel, BookGenre
│   │   └── lore_templates.py           # Text framing, vocabulary sets, perspective bias templates
│   │
│   └── tests/                          # Automated Pytest suite (18 test suites)
│       ├── test_cast_gen.py            # Demographic ratios and family linkages
│       ├── test_causal_chains.py       # Causal path extraction and metrics
│       ├── test_causal_grammar.py      # Grammar rules and illegal causal links
│       ├── test_demographics.py        # Strict demographic conservation ($P = P_0 + B - D$)
│       ├── test_determinism.py         # Byte-identical re-run verification
│       ├── test_entropy_confinement.py # Cross-subsystem entropy containment
│       ├── test_feud_reconciliation.py # Peace mechanisms and feud closure
│       ├── test_historical_pressures.py# Scarcity, famine, and raid dynamics
│       ├── test_lore_engine.py         # Procedural book generation and libraries
│       ├── test_name_domain_isolation.py# Structural equality across name salts + negative control
│       ├── test_pipeline_invariants.py # Invariant enforcement (dead actor checks)
│       ├── test_religion_engine.py     # Religion formation, holy sites, traits
│       ├── test_religion_history.py    # Schisms, heresies, and historical integration
│       ├── test_revelation_pipeline.py # Truth revelation and belief supersession
│       ├── test_seed_pair.py           # SeedPair encoding, decoding, and validation
│       ├── test_syncretism_and_culture.py# Trait borrowing, customs, cultural profiles
│       ├── test_world_gen_v0.py        # Procedural world site distribution and geography
│       └── test_wrongful_grudge.py     # Distorted beliefs leading to wrongful feuds
│
├── viewer/                             # Standalone Tkinter Desktop Story Viewer (Step 7)
│   ├── __init__.py                     # Package init
│   ├── __main__.py                     # Entry point for python -m viewer
│   ├── app.py                          # GUI application window, controls, log view
│   ├── export.py                       # Text, Markdown, and JSON export utilities
│   ├── formatter.py                    # Event formatting, indentation, color tags
│   ├── model.py                        # Read-only UI state model wrapper
│   ├── threads.py                      # Background worker thread for simulation execution
│   └── tests/                          # Viewer isolation tests
│       ├── test_boundaries.py          # Asserts Minemesis never imports Viewer
│       ├── test_causes.py              # Validates UI cause graph rendering
│       └── test_formatter.py           # Validates event text rendering
│
├── scripts/                            # Operational automation scripts
│   ├── audit_step2.py                  # Step 2 verification script
│   ├── build_viewer.py                 # PyInstaller packaging script for Windows .exe
│   ├── generate_comprehensive_pdf.py   # PDF generator for milestone summaries
│   ├── generate_lore_pdf.py            # PDF generator for literature engine report
│   ├── generate_m053_showcases.py      # Showcase story exporter for M0.5.3
│   ├── generate_religion_pdf.py        # PDF generator for religion engine report
│   ├── profile_architecture.py         # Subsystem profiler and deep memory analyzer
│   ├── run_holdout_a.py                # Hold-out A verification runner
│   ├── run_holdout_b.py                # Hold-out B verification runner
│   ├── run_m052_validation.py          # M0.5.2 50-pair validation runner
│   └── run_m053_validation.py          # M0.5.3 multi-pair multiprocessing runner
│
├── reports/                            # Generated validation reports and metrics
├── releases/                           # Packaged binaries and release notes
└── dist/                               # PyInstaller output directories
```

---

## 2. DATA MODEL SPECIFICATION

### 2.1 Character (`minemesis/models/character.py`)
Represents an individual human in the simulation.
```python
@dataclass
class Character:
    id: str                               # Unique ID, e.g., "char_0"
    first_name: str                       # Given name, e.g., "Corin"
    last_name: str                        # Patronymic/dynastic name, e.g., "Blackwood"
    settlement_id: str                    # Current settlement ID, e.g., "set_0"
    age_ticks: int                        # Age in months (12 ticks = 1 year)
    sex: str                              # "M" or "F"
    alive: bool = True                    # Vital status
    death_tick: Optional[int] = None      # Tick of death
    death_event_id: Optional[int] = None  # Pointer to DEATH event in EventLog
    spouse_id: Optional[str] = None       # ID of living spouse, or None
    father_id: Optional[str] = None       # ID of biological father
    mother_id: Optional[str] = None       # ID of biological mother
    children_ids: list[str] = field(...)  # List of biological children IDs
    suspicion: float = 0.5                # Cognitive bias in [0.0, 1.0]
    forgiveness: float = 0.5              # Memory decay bias in [0.0, 1.0]
    profession: str = "Laborer"           # Social role
    family_id: str = ""                   # Family / clan identifier
```
- **Approximate In-Memory Count:** Initial: 400 to 1,250. Year 100: 3,000 to 8,000.
- **Object References:** Strings only (`id`, `settlement_id`, `spouse_id`, `father_id`, `mother_id`, `children_ids`). **Zero direct object pointers.**

---

### 2.2 Settlement (`minemesis/models/settlement.py`)
Represents a geographic community and civic economic hub.
```python
@dataclass
class Settlement:
    id: str                               # Unique ID, e.g., "set_0"
    name: str                             # Display name, e.g., "Oakhaven"
    x: int                                # Spatial coordinate X
    y: int                                # Spatial coordinate Y
    leader_id: Optional[str] = None       # Current chief / leader character ID
    food: int = 100                       # Granary inventory
    wood: int = 100                       # Lumber inventory
    ore: int = 50                         # Metal inventory
    wealth: int = 50                      # Treasury / trade surplus
    member_ids: list[str] = field(...)    # List of resident character IDs
    farmland: float = 1.0                 # Food output multiplier [0.50, 2.50]
    forest: float = 1.0                   # Wood output multiplier [0.50, 2.50]
    ore_richness: float = 1.0             # Ore output multiplier [0.50, 2.50]
    defensibility: float = 1.0            # Raid defense multiplier [0.50, 2.50]
    water_access: float = 0.5             # Water / trade accessibility [0.0, 1.0]
    stability: float = 1.0                # Civic cohesion [0.0, 1.0]
    consecutive_starvation_ticks: int = 0 # Starvation counter
    active_famine_event_id: Optional[int] # Active famine event ID, or None
    active_famine_start_tick: Optional[int]
    adequate_food_ticks: int = 12
    last_famine_end_tick: int = -100
```
- **Approximate In-Memory Count:** 10 to 35 settlements per world (V0).
- **Object References:** Strings (`id`, `leader_id`, `member_ids`). Contains no direct character pointers.

---

### 2.3 Event (`minemesis/core/event_log.py`)
The objective, immutable atom of history.
```python
@dataclass(frozen=True)
class Event:
    id: int                               # Monotonic unique integer sequence (0, 1, 2...)
    tick: int                             # Month of occurrence
    location: str                         # Settlement ID or coordinate string
    type: EventType                       # Enum: BIRTH, DEATH, FEUD, RAID, BOOK_WRITTEN...
    participants: tuple[tuple[str, str], ...] # Immutable tuple of (role, entity_id) pairs
    causes: tuple[int, ...]               # Immutable tuple of ancestor Event IDs
    intent: Intent                        # Enum: INTENTIONAL, ACCIDENTAL, MILITARY_ACTION...
    scale: Scale                          # Enum: INDIVIDUAL, FAMILY, AGGREGATE, REGIONAL
    payload: Mapping[str, Any]            # Immutable mapping of contextual metadata
```
- **Approximate In-Memory Count:** Year 20: ~3,500. Year 100: 15,000 to 40,000 events.
- **Object References:** Integer event IDs in `causes`. Strings in `participants` and `payload`.

---

### 2.4 Belief (`minemesis/models/belief.py`)
Subjective interpretation of an event formed by an individual observer.
```python
@dataclass(frozen=True)
class Belief:
    belief_id: int                        # Monotonic integer ID
    believer_id: str                      # Character ID of the observer
    event_ref: int                        # Objective Event ID referenced
    source: BeliefSource                  # Enum: WITNESSED, TOLD, INFERRED
    source_character_id: Optional[str]    # Character ID who shared rumor, or None
    confidence: float                     # Epistemic certainty [0.0, 1.0]
    tick_acquired: int                    # Month learned
    believed_type: EventType              # Perceived event type (may be distorted)
    believed_intent: Intent               # Perceived intent (e.g. Accidental -> Intentional)
    believed_actor: Optional[str]         # Accused/perceived actor ID
    believed_target: Optional[str]        # Perceived victim ID
    believed_location: str                # Perceived location
    believed_payload: Mapping[str, Any]   # Subjective details
    supersedes_belief_id: Optional[int]   # ID of prior belief replaced upon truth revelation
```
- **Approximate In-Memory Count:** Year 20: ~200,000. Year 100: **1,500,000 to 4,500,000**.
- **Object References:** Strings (`believer_id`, `source_character_id`, `believed_actor`, `believed_target`), Integers (`event_ref`, `supersedes_belief_id`).

---

### 2.5 Memory (`minemesis/models/memory.py`)
Emotional reaction formed by an observer in response to a **Belief** (never an Event).
```python
@dataclass(frozen=True)
class Memory:
    id: int                               # Monotonic integer ID
    observer_id: str                      # Character ID
    belief_event_ref: int                 # Objective Event ID from belief
    target_entity_id: Optional[str]       # Target of emotion (character or settlement ID)
    emotion: Emotion                      # Enum: GRIEF, ANGER, GRATITUDE, REGRET, RELIEF...
    initial_intensity: float              # Strength at formation [0.0, 100.0]
    decay_rate: float                     # Exponential decay constant per tick [0.005, 0.05]
    tick_formed: int                      # Month formed
    source_belief_id: int = 0             # Pointer to originating Belief ID
```
- **Approximate In-Memory Count:** Year 20: ~6,000. Year 100: 30,000 to 90,000.
- **Object References:** Strings (`observer_id`, `target_entity_id`), Integers (`belief_event_ref`, `source_belief_id`).

---

### 2.6 Book (`minemesis/lore/lore_models.py`)
Procedural literary manuscript, scripture, chronicle, or journal.
```python
@dataclass
class Book:
    id: str                               # Unique ID, e.g., "book_0"
    title: str                            # Generated title
    author_id: str                        # Author character ID
    author_name: str                      # Author full name string
    author_literacy: LiteracyLevel        # Literacy level enum
    genre: BookGenre                      # Enum: HISTORICAL_CHRONICLE, RELIGIOUS_TEXT, TRAGEDY...
    settlement_id: str                    # Repository settlement ID
    creation_tick: int                    # Month written
    creation_year: int                    # Year written
    sources: list[int]                    # Event IDs cited as source material
    perspective_bias: str                 # "Objective", "Orthodox", "Grievance", "Hagiographic"
    pages: list[str]                      # Paginated text strings (formatted for Minecraft books)
    total_word_count: int                 # Total word length
    original_book_id: Optional[str]       # None if original, parent ID if translation/copy
    is_damaged: bool = False              # Physical integrity flag
```
- **Approximate In-Memory Count:** Year 20: ~450. Year 100: 2,000 to 5,500 books.
- **Object References:** Strings (`id`, `author_id`, `settlement_id`), Integer Event IDs (`sources`).

---

### 2.7 Religion (`minemesis/religion/religion_models.py`)
An emergent theological, cultural, and moral tradition.
```python
@dataclass
class Religion:
    id: str                               # e.g., "rel_0"
    name: str                             # Generated name, e.g., "The Sacred Hearth"
    parent_religion_id: Optional[str]     # Parent faith ID if schismatic
    child_religion_ids: list[str]         # Fractured sects
    syncretic_parents: list[str]          # Contributing faiths if syncretic
    borrowed_traits: dict[str, str]       # {trait_id: donor_religion_id}
    absorbed_folk_traditions: list[str]   # Absorbed local traditions
    regional_profiles: dict[str, RegionalDoctrineProfile] # Regional drift
    cultural_traditions: list[str]        # Customs and annual rites
    founded_tick: int                     # Origin tick
    founded_year: int                     # Origin year
    traits: dict[str, ReligionTrait]      # Active doctrinal traits
    adherents: set[str]                   # Character IDs of faithful
    dominant_settlements: set[str]        # Settlement IDs where faith is plurality
    schisms: list[str]                    # Event descriptions
    reforms: list[str]                    # Reform descriptions
    generation: int = 0                   # Lineage depth
    holy_sites: list[HolySite]            # Associated shrines and temples
    saints: list[Saint]                   # Canonized historical figures
    figures: list[ReligiousFigure]       # Prophets, martyrs, reformers
    myths: list[ReligiousMyth]            # Procedural myths and oral stories
    scripture_name: Optional[str]         # Associated scripture title
    reformation_level: int = 0
    is_extinct: bool = False
```
- **Approximate In-Memory Count:** 4 to 12 active religions per world.
- **Object References:** String sets (`adherents`, `dominant_settlements`), String IDs (`parent_religion_id`, `child_religion_ids`). Contains nested dataclass lists for `HolySite`, `Saint`, `ReligiousFigure`, `ReligiousMyth`.

---

### 2.8 World (`minemesis/systems/world_spec.py`)
Immutable geographic, topological, and economic specification.
```python
@dataclass(frozen=True)
class WorldSpec:
    world_seed: int                       # Geographic seed
    map_width: int                        # Grid width (e.g. 1000)
    map_height: int                       # Grid height (e.g. 1000)
    settlements: tuple[SettlementSite, ...] # Immutable tuple of settlement endowments
    generator_version: str = "v0"
    digest: str = ""                      # SHA-256 canonical digest of world layout
```
- **Approximate In-Memory Count:** Exactly 1 per `Simulation` instance.
- **Object References:** Contains tuple of immutable `SettlementSite` objects.

---

## 3. SIMULATION LOOP (EXACT EXECUTION ORDER)

```
Simulation Initialization:
Simulation.__init__(seed_pair)
  ├── SeedPair initialization (world_seed, history_seed)
  ├── EventLog instantiation (empty list + id lookup map)
  ├── World Generation:
  │     ├── WorldGenV0.generate(world_seed) -> WorldSpec (sites, coordinates, resources)
  │     ├── Settlement instances instantiated from WorldSpec sites
  │     └── CastGen.generate_cast(history_seed, settlements) -> initial Characters
  ├── Continuous State Initialization:
  │     ├── TradeRoutes initialized between adjacent settlements
  │     ├── Empty containers: beliefs_by_character, memories, memories_by_observer
  │     └── Monotonic counters initialized ([char_count], [0])
  ├── Religion Engine Initialization:
  │     ├── ReligionGeneration.seed_religions(settlements, characters)
  │     └── Newborn registration / faith mapping
  └── Literature Engine Initialization:
        └── LibraryManager setup (archives, temple libraries per settlement)

Monthly Update Step:
Simulation.step_month() (Called 12 times per simulated year)
  │
  ├── 0. Extinction Check:
  │     └── if len(living_characters) == 0: terminate simulation early
  │
  ├── 1. Life Cycle System (process_life_cycle):
  │     ├── 1a. Aging: Increment age_ticks for all living characters.
  │     │       Clear spouse_id if partner died.
  │     ├── 1b. Marriages:
  │     │       Filter singles (M/F, age >= 18, alive).
  │     │       Evaluate pair eligibility (incest avoidance, family branch check).
  │     │       Evaluate interpersonal hatred (< 15.0).
  │     │       Emit MARRIAGE events. Set mutual spouse_id.
  │     │       Homesteading migration if target settlement critical (<= 4 pop).
  │     ├── 1c. Births:
  │     │       Scan married fertile couples (female age 18-45, pregnancy intervals).
  │     │       Emit BIRTH events. Instantiate new Character entity.
  │     ├── 1d. Natural & Accidental Deaths:
  │     │       Actuarial mortality curves based on age_years.
  │     │       Accidental hazards (workplace / wilderness accidents).
  │     │       Emit DEATH events (intent=ACCIDENTAL). Set alive=False.
  │     └── 1e. Perception & Memory Pass:
  │             └── _register_and_perceive_events() for life cycle events.
  │
  ├── 2. Knowledge Propagation / Gossip (propagate_gossip):
  │     ├── 2a. Group living characters by settlement.
  │     ├── 2b. Sample conversational pairs within settlement (keyed RNG).
  │     ├── 2c. Identify notable beliefs known to speaker but unknown to listener.
  │     ├── 2d. Attenuate confidence based on listener's trust in speaker.
  │     ├── 2e. Apply cognitive distortion (hatred transforms Accidental -> Intentional).
  │     ├── 2f. Emit new subjective Belief (source=TOLD).
  │     └── 2g. Form corresponding emotional Memories for listener.
  │
  ├── 3. Conflict, Scarcity, Economy & Feuds (process_conflicts_and_economy):
  │     ├── 3a. Economic Production:
  │     │       Food harvest scaled by seasonal multiplier and farmland endowment.
  │     │       Food consumption (1 per capita). Spoilage of excess granary stores.
  │     │       Wealth generation from mining (ore_richness) and logging (forest).
  │     ├── 3b. Famine & Starvation:
  │     │       Evaluate starvation ticks. Emit FAMINE event when food == 0.
  │     │       Starvation deaths and desperate food raids.
  │     ├── 3c. Trade Route Maintenance:
  │     │       Form new routes or break active routes if feuds emerge between sites.
  │     ├── 3d. Leadership & Succession Crises:
  │     │       Replace dead leaders. Emit SUCCESSION_CRISIS if civic stability low.
  │     ├── 3e. Blood Feud Declaration:
  │     │       Characters scan beliefs for unavenged kin deaths or raids.
  │     │       Evaluate relationship hatred (>= 40.0).
  │     │       Emit FEUD event (flagged as wrongful if root death was accidental).
  │     ├── 3f. Revenge Killings:
  │     │       Active feuds trigger assassination / retaliatory revenge killings.
  │     │       Emit DEATH event (intent=INTENTIONAL, cause=Revenge).
  │     ├── 3g. Raids:
  │     │       Escalated feuds trigger aggregate raids against target settlement.
  │     │       Emit RAID event. Plunder food/wealth, burn structures.
  │     ├── 3h. Peace Reconciliation:
  │     │       Evaluate peace conditions: Truth Revelation (distorted belief cleared)
  │     │       or Negotiated Settlement (fatigue / resource exhaustion).
  │     │       Emit PEACE event. Close active feud and resolve grievances.
  │     └── 3i. Perception & Memory Pass:
  │             └── _register_and_perceive_events() for conflict events.
  │
  ├── 4. Standalone Religion Engine (update_tick):
  │     ├── 4a. Register newborns into parental faith.
  │     ├── 4b. Martyrdom & Saint Canonization checks from recent deaths.
  │     ├── 4c. Organic religious conversion along trade routes and within communities.
  │     ├── 4d. Sacred site discovery, pilgrimages, and sanctuary tier elevation.
  │     ├── 4e. Heresy declarations and sectarian theological schisms.
  │     ├── 4f. Syncretism: trait borrowing, folk tradition absorption.
  │     ├── 4g. Myth generation from heroic deeds; oral retellings and embellishment.
  │     └── 4h. Perception & Memory Pass:
  │             └── _register_and_perceive_events() for religious events.
  │
  ├── 5. Standalone Literature Engine (update_tick):
  │     ├── 5a. Identify literate scholars, priests, historians, and chroniclers.
  │     ├── 5b. Evaluate genre eligibility based on recent world events:
  │     │       - Historical Chronicles (from significant EventLog milestones)
  │     │       - Religious Scriptures & Commentaries (from religious myths)
  │     │       - Tragedies & Feud Epics (from deep causal conflict chains)
  │     │       - Local Folklore (from village customs and oral traditions)
  │     ├── 5c. Procedural Text Generation:
  │     │       Compose paginated text, apply author perspective bias, wrap words.
  │     ├── 5d. Library Cataloging:
  │     │       Store generated Book in Town Archive, Temple Library, or Household Shelf.
  │     │       Emit BOOK_WRITTEN event.
  │     ├── 5e. Library Degradation:
  │     │       Damage or destroy books in archives during enemy raids.
  │     │       Emit ARCHIVE_DAMAGED event.
  │     └── 5f. Perception & Memory Pass:
  │             └── _register_and_perceive_events() for literary events.
  │
  └── 6. Advance Time:
        └── self.tick += 1 (Month increments; year = tick // 12)
```

---

## 4. OBJECT LIFECYCLE & OWNERSHIP MATRIX

| Object Type | Creator | Owner | References Stored By | Destroyer / Pruning Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Character** | `CastGen` (init), `process_life_cycle` (birth) | `Simulation.characters: dict[str, Character]` | `Settlement.member_ids`, `Character.spouse_id`, `children_ids`, `Event.participants`, `Belief.believer_id`, `Memory.observer_id` | **NEVER DESTROYED.** When dead, `alive=False`, `death_tick` recorded; retained indefinitely in `Simulation.characters`. |
| **Event** | Systems via `EventLog.append()` | `EventLog._events: list[Event]`, `EventLog._by_id: dict[int, Event]` | `Event.causes` (as parent IDs), `Belief.event_ref`, `Book.sources`, `ActiveFeud.root_cause_event_id` | **NEVER DESTROYED.** Append-only immutable log. Never deleted, mutated, or truncated. |
| **Belief** | `perceive_event()`, `propagate_gossip()` | `Simulation.beliefs_by_character: dict[str, dict[int, Belief]]` | `Memory.source_belief_id`, `Belief.supersedes_belief_id` | **NEVER DESTROYED.** Superseded beliefs are flagged and retained in memory dictionary. |
| **Memory** | `form_memories_from_belief()` | `Simulation.memories: list[Memory]`, `Simulation.memories_by_observer: dict[str, list[Memory]]` | `compute_relationship()` queries them on demand | **NEVER DESTROYED.** Decayed memories ($I \approx 0.0$) and superseded memories remain in memory lists forever. |
| **Settlement**| `WorldGenV0` | `Simulation.settlements: dict[str, Settlement]` | `Character.settlement_id`, `Book.settlement_id`, `HolySite.settlement_id`, `TradeRoute` | **NEVER DESTROYED.** If abandoned, added to `collapsed_settlements: set[str]`. |
| **Religion**  | `ReligionGeneration`, `ReligionSchisms` | `ReligionEngine.religions: dict[str, Religion]` | `Faith.religion_id`, `Character` queries, `Religion.child_religion_ids` | **NEVER DESTROYED.** Extinct religions retain `is_extinct=True` and persist in historical record. |
| **Book**      | `LoreEngine.update_tick()` | `LibraryManager._all_books: dict[str, Book]`, `Library._books: dict[str, Book]` | `Event.payload`, `LibraryManager` | **NEVER DESTROYED.** If damaged or burned in a raid, `is_damaged=True` or removed from active library, but retained in `_all_books`. |

---

## 5. COMPUTATIONAL COMPLEXITY ANALYSIS

| System / Subsystem | Input Size Parameters | Empirical Big-O | Nested Loop Structure | Bottleneck Severity |
| :--- | :--- | :---: | :--- | :---: |
| **Marriages** (`life_cycle.py`) | $S_m$ single men, $S_f$ single women | $O(S_m \times S_f \times M)$ | `for m in singles_m:`<br>&nbsp;&nbsp;`for f in singles_f:`<br>&nbsp;&nbsp;&nbsp;&nbsp;`compute_relationship()` (scans memories) | **CRITICAL (Top CPU Bottleneck)**. At pop 7,000, evaluates $10^6$ pairs monthly. |
| **Aging & Mortality** (`life_cycle.py`) | $N$ living characters | $O(N)$ | Single flat loop over `sorted(characters.keys())`. | Low ($< 0.05$s/year). |
| **Perception Pass** (`perception.py`) | $E_{\text{new}}$ monthly events, $W$ witnesses | $O(E_{\text{new}} \times W)$ | `for evt in new_events:`<br>&nbsp;&nbsp;`for char in witnesses:`<br>&nbsp;&nbsp;&nbsp;&nbsp;`perceive_event()` | **HIGH**. Scales directly with population density and event frequency. |
| **Gossip Propagation** (`gossip.py`) | $S$ settlements, $R$ residents | $O(S \times B_{\text{speaker}})$ | `for s_id in settlements:`<br>&nbsp;&nbsp;`pair = sample(residents, 2)`<br>&nbsp;&nbsp;`scan notable beliefs` | Low ($O(S)$ bounded by constant sample size). |
| **Feud Scanning** (`conflict.py`) | $N$ characters, $B$ beliefs per character | $O(N \times B \times M)$ | `for char in sorted_chars:`<br>&nbsp;&nbsp;`for event_ref in char_beliefs:`<br>&nbsp;&nbsp;&nbsp;&nbsp;`get_relationship(char, accused)` | **HIGH**. Scans beliefs and walks memory lists per candidate offence. |
| **Raids & Revenge** (`conflict.py`) | $F$ active feuds (capped $\le 4$) | $O(F)$ | Bounded iteration over small feud list. | Low (hard-capped at 4 active feuds). |
| **Religion Spread** (`religion_spread.py`) | $S$ settlements, $R$ religions | $O(S \times R)$ | Calculates theological pressure per site per faith. | Moderate. |
| **Religion Virtues** (`religion_virtues.py`) | $E_{\text{new}}$ events, $T$ traits | $O(E_{\text{new}} \times T)$ | Evaluates every event actor's deed against trait virtues. | Moderate (constant factor overhead on all events). |
| **Literature Generation** (`lore_engine.py`) | $K$ writers, $E_{\text{recent}}$ events | $O(K \times E_{\text{recent}})$ | Identifies literate actors, filters candidate events, formats text. | Moderate. |
| **Causal Graph Traversal** (`history_printer.py`) | $E$ total events, $D$ DAG depth | $O(E + V)$ with memoization<br>($O(2^D)$ without) | Dynamic programming recursion with `memo: dict[int, list[int]]`. | Low during simulation; Moderate during final batch metrics export. |

---

## 6. MEMORY ANALYSIS & HEAP BREAKDOWN

### 6.1 Individual Object Footprint (Measured on Python 3.14 x64)

| Object Type | Shallow `sys.getsizeof` | Deep Recursive Size (Bytes) | Contributing Overhead Elements |
| :--- | :---: | :---: | :--- |
| **Character** | 48 B | **1,847 B** | `__dict__`, string identifiers, lists (`children_ids`), names |
| **Event** | 48 B | **8,568 B** | `participants` tuple-of-tuples, `causes` tuple, `payload` dictionary |
| **Settlement** | 48 B | **6,171 B** | `member_ids` list, resource dictionaries, spatial coordinates |
| **Belief** | 48 B | **9,461 B** | `believed_payload` dict, string identifiers, enums, supersession keys |
| **Memory** | 48 B | **3,284 B** | Emotional enum, float decay parameters, string target IDs |
| **Book** | 48 B | **7,239 B** | Raw UTF-8 page string list, metadata, Minecraft NBT formatting |
| **Religion** | 48 B | **114,296 B** | Trait mappings, `holy_sites`, `saints`, `figures`, `myths`, adherent sets |

---

### 6.2 Empirical Population Scaling Projections

| Simulation Scale | Living Characters | Total Events | Total Memories | Total Beliefs | Deep Sim Size (MB) | Process Working Set (RSS) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **100 Characters (Year 10)** | 100 | ~250 | ~450 | ~12,000 | **12 MB** | **85 MB** |
| **1,000 Characters (Year 30)** | 1,000 | ~2,500 | ~4,200 | ~140,000 | **135 MB** | **450 MB** |
| **3,000 Characters (Year 100, 11 Sets)**| 3,167 | 15,136 | ~28,000 | ~950,000 | **920 MB** | **2,392 MB (2.39 GB)** |
| **7,500 Characters (Year 100, 24 Sets)**| 7,725 | 37,997 | ~68,000 | ~2,800,000 | **2,850 MB** | **7,110 MB (7.11 GB)** |
| **10,000 Characters (Projected)** | 10,000 | ~55,000 | ~110,000 | ~4,500,000 | **4,600 MB** | **11,800 MB (11.8 GB)** |

> [!CAUTION]
> **The Primary RAM Culprit is the Belief Explosion:**
> In a 100-year simulation of 24 settlements, the simulation generates **2.8 to 3.5 million Belief objects**. Because each character maintains a dictionary mapping `event_ref -> Belief`, and beliefs are never pruned, Python heap memory swells to **~7.1 GB**.

---

## 7. HISTORY STORAGE & ARCHIVAL

1. **How Events Are Stored:**
   Events are stored strictly in `minemesis.core.event_log.EventLog`. The class maintains two internal collections:
   - `self._events: list[Event]` (indexed chronologically by integer event ID).
   - `self._by_id: dict[int, Event]` (hash map for $O(1)$ random access by ID).
2. **Deletion & Pruning:**
   - **Events are NEVER deleted.** The Event Log is an immutable, append-only ledger representing objective historical reality.
   - **Memories are NEVER pruned.** Even when emotional intensity decays below $0.001$, memory objects remain appended to `self.memories` and `self.memories_by_observer`.
   - **Beliefs are NEVER pruned.** When a belief is superseded via truth revelation, it is not removed; it is flagged with `supersedes_belief_id`, leaving both old and new beliefs in the character's belief dictionary.
3. **Compression:**
   - **Books are uncompressed.** The procedural text of every page is stored as raw Python `str` instances in `Book.pages: list[str]`.
   - **Payloads are uncompressed.** Event and belief payloads use standard Python dictionaries with duplicate string keys.
4. **Reference Integrity:**
   - Entity references across boundaries are strictly **string identifiers** (`"char_42"`, `"set_3"`, `"rel_1"`) or **integer IDs** (`event.causes = (12, 14)`).
   - The engine contains **no cyclic direct object pointers**. However, the lack of pruning means all historical entities remain reachable from the root `Simulation` object, preventing Python's garbage collector from freeing any allocated historical record during a run.

---

## 8. EVENT GRAPH (CAUSAL DAG) STRUCTURE

```
                  [Event #0: World Genesis]
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
       [Event #10: Famine]          [Event #12: Accidental Death]
               │                             │ (Perception Distorted)
               │                             ▼
               │                    [Event #25: Wrongful Feud]
               │                             │
               └──────────────┬──────────────┘
                              ▼
                     [Event #45: Raid]
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
      [Event #60: Revenge]          [Event #62: Archive Damaged]
               │                             │
               └──────────────┬──────────────┘
                              ▼
                     [Event #90: Peace]
                              │
                              ▼
                  [Event #110: Book Written]
                   ("The Tragedy of Oakhaven")
```

### Graph Characteristics:
- **Topology:** Directed Acyclic Graph (DAG).
- **Edge Direction:** Directed **backward** from child events to parent cause events (`Event.causes: tuple[int, ...]`).
- **Forward Traversal:** The `Event` dataclass does **NOT** store forward edge references (`effects: tuple[int, ...]`). To traverse forward (descendants), the system must perform a full linear scan of `event_log.all_events()` or build a reverse index.
- **Causal Grammar Enforcement:** Every call to `event_log.append()` invokes `minemesis.core.causal_grammar.validate_causes(event_type, causes, event_log)`. If a child event cites an illegal parent type (e.g., a `Marriage` citing a `Raid` without an intervening `Peace` or `TradeRouteFounded`), a `CausalGrammarError` is raised immediately.
- **Depth Traversal:** Longest causal path and conflict chain depths are evaluated using backward depth-first search with memoization (`memo: dict[int, list[int]]`). Memoization avoids exponential $O(2^D)$ branching, reducing traversal across 40,000 events to under **0.45 seconds**.

---

## 9. SAVE FORMAT PLAN

### 9.1 Current Format
The current simulation uses ephemeral in-memory execution with ad-hoc downstream serialization:
- **Full History JSON:** `releases/m0.5.3/minemesis_run_seed*.json` (Single JSON document dumping characters, settlements, all events, and books). File size: **15–45 MB per 100-year run**.
- **Metrics JSONL:** `reports/m053_training_runs.jsonl` (One JSON line per evaluated seed containing aggregated metrics).
- **Mermaid DAGs:** `reports/*.mmd` (Text graph format for visual inspection).
- **Limitation:** **There is currently NO bidirectional save/load engine.** The simulation cannot be paused at Year 50, saved to disk, and resumed at Year 51.

### 9.2 Future Tiered Archival Plan
To support multi-thousand-year histories without RAM exhaustion, a tiered persistence format is planned:

```
┌───────────────────────────────────────────────────────────────┐
│                    ACTIVE WORKING MEMORY                      │
│  - Living Characters (ID-indexed struct-of-arrays)            │
│  - Settlements & Active Trade Routes                          │
│  - Active Feuds (max 4)                                       │
│  - Ephemeral Short-Term Buffer: Last 24 ticks of Events       │
│  - Active Emotional Memories (intensity > 5.0)                │
└───────────────────────────────┬───────────────────────────────┘
                                │ Tiered Flush (every 12 ticks)
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                TIERED HISTORICAL STORAGE                      │
│                                                               │
│  1. SQLite / DuckDB Cold Archive:                             │
│     - events table (id, tick, type, location, causes_blob)    │
│     - books table (id, author_id, genre, text_compressed)     │
│     - deceased_characters table (demographics, death_event)   │
│                                                               │
│  2. Pruned Epistemic Index:                                   │
│     - Decayed memories (intensity < 1.0) flushed to disk      │
│     - Beliefs compacted into bitsets / summary vectors        │
└───────────────────────────────────────────────────────────────┘
```

---

## 10. BOTTLENECK IDENTIFICATION (TOP 10 CPU & TOP 10 RAM)

### Top 10 CPU Bottlenecks
1. **Unindexed Marriage Candidate Pair Evaluation (`life_cycle.py` lines 54–82):**  
   *Evidence:* Performs a nested Cartesian product loop (`singles_m` $\times$ `singles_f`) every single month. At 1,000 unmarried adults, this executes **$1,000,000$ iterations per month**, calling `keyed_float` and `get_relationship` in every iteration.
2. **Dynamic Relationship Aggregation from Raw Memories (`simulation.py` lines 177–237):**  
   *Evidence:* `get_relationship` does not read a cached score; it iterates over `memories_by_observer[source_id]`, filtering out superseded memories and computing exponential decay exponents on every call.
3. **Perception and Memory Filtering Overhead (`perception.py` lines 40–115):**  
   *Evidence:* Profiling confirms perception accounts for **25.2% of total simulation runtime** (1.98s per 20 years), repeatedly checking witness lists and allocating new Belief and Memory objects.
4. **Keyed RNG Hashing Operations (`rng.py` lines 18–35):**  
   *Evidence:* Every stochastic decision invokes `hashlib.sha256(f"{seed}:{domain}:{key}:{tick}".encode("utf-8"))`. In a 100-year run with 7,500 people, `sha256` is called **over 12,000,000 times**.
5. **Religion Engine Virtue Evaluation (`religion_virtues.py` lines 20–85):**  
   *Evidence:* Profiling shows the Religion Engine consumes **40.2% of simulation runtime**. Every emitted event evaluates the actor's deed against the virtue tables of all active religious traits.
6. **Feud Grievance Scanning (`conflict.py` lines 410–465):**  
   *Evidence:* All living characters iterate over their personal belief dictionaries searching for unavenged death events, querying `get_relationship` for every potential suspect.
7. **Causal DAG Longest Path Concatenation (`history_printer.py` lines 33–57):**  
   *Evidence:* `longest_ancestor_path + [event_id]` creates new list allocations during recursive memoized graph walks.
8. **Literature Engine Word-Boundary Pagination (`lore_generators.py` lines 120–180):**  
   *Evidence:* String splitting, line wrapping, and page length truncation for Minecraft NBT book formatting.
9. **Trade Route Spatial Distance Recalculation (`settlement.py` lines 50–52):**  
   *Evidence:* Euclidean square roots calculated on every candidate route search without a precomputed spatial distance matrix.
10. **Demographic Actor Liveness Validation (`invariants.py` lines 15–35):**  
    *Evidence:* Every perceived event linearly scans participant dictionaries and verifies living status against `characters` hash maps.

---

### Top 10 RAM Bottlenecks
1. **Unbounded Belief Proliferation (`Simulation.beliefs_by_character`):**  
   *Evidence:* 203,941 beliefs created in 20 years; over **2.8 million beliefs** in 100 years. Consumes **> 3.5 GB of heap**.
2. **Unpruned Decayed Memories (`Simulation.memories`):**  
   *Evidence:* Over 68,000 Memory instances remain in memory even when emotional intensity has decayed to 0.0.
3. **Dual Event Indexing (`EventLog._events` and `EventLog._by_id`):**  
   *Evidence:* All 40,000 Event objects are stored in both a sequential list and an ID lookup dictionary, doubling pointer overhead.
4. **Raw String Storage in Procedural Books (`Book.pages`):**  
   *Evidence:* 5,500 books storing 3–6 pages of uncompressed UTF-8 English text consume over **40 MB** of raw string memory.
5. **Standard Dataclass Heap Overhead:**  
   *Evidence:* Dataclass instances without `__slots__` allocate a 48-byte object header plus an internal `__dict__` (~104 bytes) for every single character, belief, and memory.
6. **String Key Duplication Across Payloads:**  
   *Evidence:* Repeated dictionary keys (`"description"`, `"victim_id"`, `"accused_id"`, `"is_wrongful"`) duplicated across millions of dictionaries.
7. **Dead Character Retention (`Simulation.characters`):**  
   *Evidence:* 4,200 dead characters remain fully resident in the main entity dictionary alongside living characters.
8. **Causal DAG Memoization Dictionaries (`memo: dict[int, list[int]]`):**  
   *Evidence:* Metric calculation creates a 40,000-entry dictionary where values are lists of integers, consuming **~65 MB** during metric evaluation.
9. **Religion Myth Embellishment Accumulation (`Religion.myths`):**  
   *Evidence:* Hundreds of `ReligiousMyth` instances retain both original objective truth strings and expanding lists of embellishment strings.
10. **Viewer History Formatter Buffer (`viewer/formatter.py`):**  
    *Evidence:* Loading 40,000 events into the Tkinter Text widget creates hundreds of thousands of UI text tags, consuming **> 500 MB** in the GUI process.

---

## 11. SUBSYSTEM PROFILING DATA

The following empirical profiling data was recorded directly on the Windows 11 host environment using `minemesis.systems.simulation.Simulation` and `cProfile`:

```
========================================================================
SUBSYSTEM BENCHMARK (20 Simulated Years, 27 Settlements, Initial Pop: 1,212)
========================================================================
World Generation + Cast Gen + Religion Seeding:  0.0447 sec  ( 0.5%)
Monthly Simulation Loop (240 ticks):             7.8828 sec  (99.5%)
------------------------------------------------------------------------
Simulation Subsystem Breakdown:
  1. Standalone Religion Engine:                 3.1713 sec  (40.2%)
  2. Perception & Memory Formation:              1.9847 sec  (25.2%)
  3. Conflict, Feuds, Economy & Raids:           1.6429 sec  (20.8%)
  4. LifeCycle (Marriages, Births, Deaths):      0.5148 sec  ( 6.5%)
  5. Standalone Literature / Books Engine:       0.3966 sec  ( 5.0%)
  6. Gossip / Rumor Propagation:                 0.1608 sec  ( 2.0%)
------------------------------------------------------------------------
Post-Simulation Operations:
  - Causal DAG Depth Analysis (3,651 events):    0.0027 sec
  - History Export (Causal DAG + Mermaid):       0.0001 sec
========================================================================

========================================================================
FULL 100-YEAR RUNTIME BY SETTLEMENT SCALE (From M0.5.3 Multi-Pair Suite)
========================================================================
Scale Tier A (11 Settlements, Initial Pop: 494  -> Final Pop: 3,167):
  Total Events: 15,136  | Peak RSS: 2,392.69 MB | Wall Time:  122.66 sec ( 2.04 min)

Scale Tier B (24 Settlements, Initial Pop: 1,104 -> Final Pop: 7,725):
  Total Events: 37,997  | Peak RSS: 7,110.28 MB | Wall Time:  678.73 sec (11.31 min)

Scale Tier C (27 Settlements, Initial Pop: 1,212 -> Final Pop: 7,638):
  Total Events: 39,470  | Peak RSS: 6,035.49 MB | Wall Time:  862.50 sec (14.38 min)
========================================================================
```

---

## 12. SCALE PROJECTION & FAILURE POINT MATRIX

| Population | Duration | Total Events | Est. Beliefs | Est. Peak RAM | Est. Wall Time | Expected Failure Mode / Bottleneck |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **100** | 100 Yrs | ~2,500 | ~150,000 | 180 MB | ~15 sec | **None.** Stable and lightweight. |
| **1,000** | 100 Yrs | ~12,000 | ~800,000 | 1.8 GB | ~1.5 min | **None.** Easily fits within standard desktop RAM. |
| **10,000** | 100 Yrs | ~60,000 | ~5,000,000 | **12.5 GB** | ~25 min | **High RAM Pressure.** Marriage loop evaluates $6 \times 10^6$ pairs/month. |
| **100** | 1,000 Yrs | ~25,000 | ~1,500,000 | 2.2 GB | ~2.5 min | **None.** Event log remains manageable. |
| **1,000** | 1,000 Yrs | ~120,000 | ~8,000,000 | **18.5 GB** | ~25 min | **SWAP THRASHING.** Memory exceeds 16 GB physical limits. |
| **10,000** | 1,000 Yrs | ~600,000 | ~50,000,000 | **> 90 GB** | **> 6 hours** | **OUT OF MEMORY (OOM CRASH).** `MemoryError` during belief creation. |
| **1,000** | 4,000 Yrs | ~500,000 | ~35,000,000 | **> 75 GB** | **> 3 hours** | **OOM CRASH.** EventLog and belief heap exhaustion. |
| **10,000** | 4,000 Yrs | ~2,500,000 | ~200,000,000 | **> 350 GB** | **> 40 hours** | **CATASTROPHIC FAILURE.** In-memory Python heap cannot scale here without cold storage. |

---

## 13. ARCHITECTURE DIAGRAMS (ASCII)

### 13.1 Module Dependency Graph
```
                          [ cli.py / viewer ]
                                  │
                                  ▼
                     [ systems.simulation.Simulation ]
                                  │
        ┌──────────────┬──────────┴──────────┬──────────────┐
        ▼              ▼                     ▼              ▼
[ systems.life_cycle ] [ systems.conflict ] [ religion ]   [ lore ]
        │              │                     │              │
        └──────────────┼─────────────────────┼──────────────┘
                       ▼                     ▼
             [ systems.perception ] ──> [ systems.memory_system ]
                       │                     │
                       ▼                     ▼
             [ models.belief ]       [ models.memory ]
                       │                     │
                       └──────────────┬──────┘
                                      ▼
                           [ models.relationship ]
                                      │
                                      ▼
                           [ core.event_log.EventLog ]
                                      │
                                      ▼
                           [ core.causal_grammar ]
```

---

### 13.2 Epistemic Data Flow Graph
```
           +---------------------------------------+
           |           OBJECTIVE REALITY           |
           |        (core.event_log.EventLog)      |
           +---------------------------------------+
                              │
                              │ New Event Emitted (Birth, Death, Raid...)
                              ▼
           +---------------------------------------+
           |           PERCEPTION FILTER           |
           |       (systems.perception.py)         |
           |  - Witness distance & line of sight   |
           |  - Cognitive bias (suspicion)         |
           |  - Religion interpretation filter     |
           +---------------------------------------+
                              │
                              │ Perceived Interpretation
                              ▼
           +---------------------------------------+
           |          SUBJECTIVE BELIEFS           |
           |        (models.belief.Belief)         |
           |  - May distort Accidental -> Hostile  |
           |  - Tracks superseding revelations     |
           +---------------------------------------+
                              │
                              │ Emotional Reaction
                              ▼
           +---------------------------------------+
           |          EMOTIONAL MEMORIES           |
           |        (models.memory.Memory)         |
           |  - Grief, Anger, Gratitude, Regret    |
           |  - Exponential decay per tick         |
           +---------------------------------------+
                              │
                              │ Dynamic Aggregation
                              ▼
           +---------------------------------------+
           |             RELATIONSHIPS             |
           |     (models.relationship.py View)     |
           |  - Trust, Fear, Respect, Hatred       |
           |  - Calculated on demand; never stored |
           +---------------------------------------+
                              │
                              │ Motivation & Decisions
                              ▼
           +---------------------------------------+
           |          DECISION SYSTEMS             |
           |  - Feud declarations & Raids          |
           |  - Marriages & Alliances              |
           |  - Religious Schisms & Heresies       |
           |  - Procedural Book Authoring          |
           +---------------------------------------+
                              │
                              │ Causal Action
                              ▼
           [ Validated against Causal Grammar ] ──> Emits to EventLog
```

---

### 13.3 Lifetime Ownership Graph
```
[ Simulation Instance ]
  ├── owns ──> [ settlements: dict[str, Settlement] ]
  ├── owns ──> [ characters: dict[str, Character] ] (Living AND Dead)
  ├── owns ──> [ event_log: EventLog ]
  │                 ├── owns ──> [ _events: list[Event] ] (All historical events)
  │                 └── owns ──> [ _by_id: dict[int, Event] ]
  ├── owns ──> [ beliefs_by_character: dict[str, dict[int, Belief]] ]
  │                 └── owns ──> [ Belief ] (Millions of subjective records)
  ├── owns ──> [ memories: list[Memory] ] (All historic emotional reactions)
  ├── owns ──> [ trade_routes: dict[tuple, TradeRoute] ]
  ├── owns ──> [ active_feuds: list[ActiveFeud] ] (Max 4 active)
  ├── owns ──> [ religion_engine: ReligionEngine ]
  │                 ├── owns ──> [ religions: dict[str, Religion] ]
  │                 └── owns ──> [ faiths: dict[str, Faith] ]
  └── owns ──> [ lore_engine: LoreEngine ]
                    └── owns ──> [ library_manager: LibraryManager ]
                                      ├── owns ──> [ _all_books: dict[str, Book] ]
                                      └── owns ──> [ _settlement_libraries: dict ]
```

---

### 13.4 Event Graph Structure (Causal DAG Walk)
```
  Event #12 (Accidental Hunting Death)
      │
      ├───────────────────────────────────────────┐
      ▼                                           ▼
  Belief #45 (Actor: "Hunter",                 Belief #46 (Accidental Truth)
              Intent: INTENTIONAL)                │
      │                                           │
      ▼                                           │
  Memory #80 (Anger: 85.0)                        │
      │                                           │
      ▼                                           │
  Relationship (Hatred: 65.0)                     │
      │                                           │
      ▼                                           │
  Event #105: FEUD Declared (Wrongful)            │
      │                                           │
      ▼                                           │
  Event #140: RAID Launched                       │
      │                                           │
      ▼                                           │
  Event #180: REVENGE Killing                     │
      │                                           │
      ├───────────────────────────────────────────┘
      ▼
  Event #210: PEACE (Truth Revealed via Evidence)
      │
      ▼
  Belief #45 Superseded by Belief #46
      │
      ▼
  Re-Appraisal Memories Formed:
  - REGRET (Intensity: 62.0)
  - RELIEF (Intensity: 70.0)
      │
      ▼
  Event #245: BOOK_WRITTEN ("Chronicle of the Tragic Bloodshed")
```

---

### 13.5 Save/Load Architecture Pipeline (Future Tiered Archival)
```
                          [ RUNTIME SIMULATION ]
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
 [ Active Working State ]                            [ Historical Stream ]
 - Living Characters                                 - Immutable Events
 - Active Settlements                                - Completed Books
 - Active Feuds (< 4)                                - Deceased Characters
 - Decaying Memories (> 1.0)                         - Superseded Beliefs
           │                                                   │
           ▼                                                   ▼
  [ RAM Working Heap ]                                [ Cold Tier Archiver ]
  (Flat Struct-of-Arrays)                             (Batched every 12 ticks)
           │                                                   │
           ▼                                                   ▼
┌────────────────────────┐                           ┌────────────────────────┐
│ State Snapshot (CBOR)  │                           │  SQLite / Parquet DB   │
│ - Compact binary state │                           │ - events table         │
│ - Fast save / restore  │                           │ - books table          │
│ - Size: < 5 MB         │                           │ - causal_edges table   │
└────────────────────────┘                           └────────────────────────┘
           │                                                   │
           └─────────────────────────┬─────────────────────────┘
                                     ▼
                             [ RESTORE WORLD ]
```

---

## 14. RECOMMENDED OPTIMIZATIONS (EXTERNAL REVIEW GUIDANCE)

The following high-leverage architectural modifications will yield massive performance and memory dividends without sacrificing historical depth or requiring a rewrite in a lower-level language:

1. **Replace Dataclasses with `__slots__` or NamedTuples for Beliefs & Memories:**  
   *Projected Savings:* **40–50% reduction in RAM footprint.** Eliminates the per-instance `__dict__` overhead across millions of objects.
2. **Epistemic Belief Pruning & Compact Vectors:**  
   *Projected Savings:* **~3.0 GB RAM reclaimed.** Routine life events (births/natural deaths of strangers) do not need individual `Belief` objects per citizen. Only dramatic events (killings, feuds, raids, miracles) should generate discrete beliefs; background knowledge can be represented as an integer vector or bitset.
3. **Partitioned Spatial Marriage Indexing:**  
   *Projected Savings:* **90% reduction in LifeCycle CPU time.** Partition single men and women by settlement ID. Match locally first; only evaluate cross-settlement pairs along active trade routes. Replaces $O(S_m \times S_f)$ with $O(\sum s_{m,i} \times s_{f,i})$.
4. **Cached Interpersonal Relationships:**  
   *Projected Savings:* **15–20% reduction in total CPU time.** Cache computed `Relationship` records with an invalidation tick; recompute only when a character acquires a new memory targeting that specific individual.
5. **Cold History Tiering (SQLite Event Archive):**  
   *Projected Savings:* Enables simulations to run for **1,000+ years** within a constant 2–3 GB memory ceiling by streaming events older than 24 ticks to an embedded SQLite database.
