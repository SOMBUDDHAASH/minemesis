# Agent Changelog

This document records all formal amendments and extensions to `agent.md` (Architecture Freeze v1.0).

---

## [Milestone 0.5] - 2026-10-24

### 1. Causal Grammar & Schema Validation
- **Added `CAUSE_GRAMMAR` table**: Explicitly defines allowed cause types and whether root events (empty causes) are permitted for each event type.
- **Enforced validation in `EventLog.append`**: Appending an event that cites unauthorized cause event types or omits required causes raises a `CausalGrammarError`.
- **Accidental deaths without preceding event**: Accidental deaths with no genuine antecedent are strictly root events (causes = empty), preventing spurious chronological links.

### 2. Event Types & Scope
- **Demoted routine trade to state**: Removed per-caravan `Trade` events. Routine trade flow is now maintained as settlement state (`TradeRoute` with volume and health).
- **Added new historical event types**:
  - `TradeRouteFounded`: Represents diplomatic/commercial opening of a trade corridor.
  - `TradeRouteBroken`: Represents closure of a corridor due to war, raid, famine, or crisis.
  - `Revelation`: Represents formal truth discovery of a past event's true intent via witness testimony.
  - `Famine`: Represents severe regional food crisis.
  - `ChiefChanged`: Represents orderly succession of settlement leadership.
  - `SuccessionCrisis`: Represents contested or unstable transfer of leadership.

### 3. Truth Revelation & Belief Supersession
- **Witness-Path Revelation**: Truth is no longer a random probability roll. It requires a witness holding a high-confidence belief to transmit the truth to the instigator through direct or trusted intermediary communication.
- **Belief Supersession**: Introduced `supersedes` reference on `Belief`. When a corrected belief wins credibility comparison, it supersedes the prior belief without mutating event or memory history.
- **Memory Re-appraisal**: Memories derived from superseded beliefs are discounted in relationship computation. Re-appraisal memories (e.g. regret, relief) are formed and scale with previously held hatred.

### 4. Historical Pressure Systems
- **Revenge**: Feud instigators holding high hatred toward a believed killer can commit intentional revenge killings (`Death` with causes `[original_death, feud]`).
- **Leadership & Succession**: Settlements track chiefs. Chief mortality triggers succession by hereditary rule or merit. Contested succession triggers `SuccessionCrisis`.
- **Scarcity & Asymmetric Productivity**: Settlements possess asymmetric resource endowments (farmland, forest, ore, defensibility). Seasonal variance and resource depletion produce `Famine`, motivating raids or trade treaties.
- **Anti-Convergence**: Removed artificial balancing constraints (such as forced migration to smaller settlements). Populations and resources now evolve organically.

---

## [Milestone 0.5.1] - 2026-10-24

### 1. Amendments to Architecture & Targets (`agent.md`)
- **Settlement Extinction & World Survival Target**:
  - *Previous target*: "Zero extinct settlements" across 100 years.
  - *Amended target*: "No world extinction (at least one settlement survives in every seed) and no unlogged population changes." Settlement collapses are allowed when population drops to $\le 4$ and must be formally logged as `SettlementCollapse` and `Migration`.
- **Demographic Conservation Rule**:
  - Total living world population must strictly equal $\text{Initial Population} + \sum \text{Births} - \sum \text{Deaths}$.
  - Settlement-level population transitions must strictly equal $\text{Initial} + \text{Births} - \text{Deaths} + \text{In-Migrations} - \text{Out-Migrations} + \text{In-Marriages} - \text{Out-Marriages}$.
  - Any unlogged relocation, silent homesteading, or artificial balancing is strictly forbidden.
- **Conflict Causal Depth Metric**:
  - Added alongside the general longest-path causal depth metric.
  - Measures directed causal chains restricted exclusively to conflict event types: `Death`, `Feud`, `Raid`, `Famine`, `SuccessionCrisis`, `Peace`, and `Revelation`.
  - Excludes routine demographic/administrative events (`Birth`, `Marriage`, `ChiefChanged`, `TradeRouteFounded`, `TradeRouteBroken`, `SettlementCollapse`, `Migration`).
  - Acceptance criterion: Conflict causal depth $\ge 3$ containing $\ge 3$ distinct conflict event types.

### 2. Causal Grammar Diff vs Table 4.1
Diff of implemented `CAUSE_GRAMMAR` against brief Table 4.1:

| Event Type | Table 4.1 Permitted Causes | Implemented `CAUSE_GRAMMAR` | Deviation & Justification |
| :--- | :--- | :--- | :--- |
| `Birth` | Empty (root) | Empty (root), `Marriage` | **Extension**: In Milestone 0, Births cite Marriage when parents are married. Permitted root when no prior marriage. Retained for pedigree traceability. |
| `Death` | `Raid`, `Famine`, `Feud` | `Raid`, `Famine`, `Feud`, `Death` (conditional) | **Extension (Revenge Resolution)**: Death citing Death is permitted **only** when the same event also cites `Feud` (revenge killing with `cause_of_death="Revenge"` in payload). Enforced by `_validate_death`. Accidental/natural deaths remain valid roots. |
| `Marriage` | Empty (root), `Peace` | Empty (root), `Peace`, `TradeRouteFounded` | **Restriction & Real Causality**: Milestone 0.5 had a recency fallback linking any marriage within 12 months of a Peace. Fixed in 0.5.1: Marriage cites `Peace` **only** if spouses come from the two opposing settlements party to that peace (alliance marriage). Also permits citing `TradeRouteFounded` for trade pact marriages. Otherwise root. |
| `Trade` | Demoted to state | Demoted to state | Per Milestone 0.5 design decision. Routine trades are state updates. |
| `TradeRouteFounded` | `Peace`, `Feud` (resolved) | `Peace`, Empty (root) | Diplomatic trade corridor creation. Root allowed for initial baseline treaties. |
| `TradeRouteBroken` | `Raid`, `Feud`, `Famine` | `Raid`, `Feud`, `Famine`, `SuccessionCrisis` | Added `SuccessionCrisis` as a valid disruptive cause for trade corridor failure. |
| `Raid` | `Famine`, `Feud`, `SuccessionCrisis` | `Famine`, `Feud`, `SuccessionCrisis` | Exact match with Table 4.1. |
| `Feud` | `Raid`, `Death`, `TradeRouteBroken` | `Raid`, `Death`, `TradeRouteBroken` | Exact match with Table 4.1. |
| `Peace` | `Feud`, `Revelation` | `Feud`, `Revelation`, `Famine` | Table 4.1 permits `Feud` and `Revelation`. Also permits `Famine` exhaustion peace where mutual starvation forces armistice. |
| `Revelation` | `Death`, `Raid`, `Feud` | `Death`, `Raid`, `Feud` | Exact match with Table 4.1. Cites the misunderstood origin event. |
| `Famine` | Empty (root) | Empty (root) | Exact match with Table 4.1. Environmental/seasonal shock. |
| `ChiefChanged` | `Death`, `SuccessionCrisis` | `Death`, `SuccessionCrisis`, Empty (root) | Root allowed for initial world setup chiefs. Normal transition cites predecessor's `Death`. |
| `SuccessionCrisis`| `Death` | `Death` | Exact match with Table 4.1. Occurs when chief dies without clear/stable heir. |
| `SettlementCollapse`| N/A (new event) | `Raid`, `Famine`, `Feud`, `Death`, `SuccessionCrisis` | **Added in 0.5.1**: Emitted when population drops to $\le 4$. Requires at least one driving crisis cause. |
| `Migration` | N/A (new event) | `SettlementCollapse`, `Famine`, `Raid` | **Added in 0.5.1**: Emitted to relocate survivors of a collapse or acute famine/raid. Cites the collapse or crisis. |

### 3. Economic Balancing & Resource Modeling
- **Food Storage Cap & Spoilage**:
  - Settlement food storage capacity dynamically scales with population: $\text{Storage Cap} = \text{pop} \times 36 + 150$ (roughly 3 years of maximum consumption buffer).
  - Food stock above the cap incurs a 15% spoilage degradation per monthly tick.
  - Population consumption is calibrated to 1 unit of food per capita per month, dropping 20% in harsh winter.
- **Non-Negative Wealth & Explicit Flows**:
  - Hard non-negative floor ($\text{wealth} \ge 0$) enforced on all settlements.
  - Wealth creation stems strictly from explicit production: mining richness generates $3 \times \text{ore\_richness}$ wealth/month, and timber generates $1 \times \text{forest\_density}$ wealth/month.
  - Trade import payments are strictly bounded by buyer wealth: `cost = min(needed * price, buyer.wealth)`. Sellers receive only what buyers actually pay; money is never minted from thin air.

### 4. Test Hardening: Before vs After

| Test Case | Before (Milestone 0.5) | After (Milestone 0.5.1) | Negative Control / Multi-Seed Evidence |
| :--- | :--- | :--- | :--- |
| `test_death_citing_death_rule` | Did not exist. `CAUSE_GRAMMAR` allowed Death to cite `[Raid, Famine, Feud]`. | Added validator `_validate_death`. Death may cite Death iff it also cites Feud. | **Negative control**: Asserts `CausalGrammarError` when Death cites Death without citing Feud. **Positive control**: Asserts success when Death cites Death + Feud. |
| `test_settlement_collapse_grammar` | Did not exist. | Added grammar validation for `SettlementCollapse`. | **Negative control**: Asserts `CausalGrammarError` when `SettlementCollapse` is a root event or cites unauthorized type (`Marriage`). |
| `test_migration_grammar` | Did not exist. | Added grammar validation for `Migration`. | **Negative control**: Asserts `CausalGrammarError` when `Migration` is a root event or cites unauthorized type (`Birth`). |
| `test_conflict_causal_chains` | Checked total DAG depth $\ge 5$ across all event types (often inflated by Birth/Marriage/Peace). | Asserts `conflict_depth >= 3` and `conflict_types >= 3` using only conflict event types. | Tested on Seed 42 and across Hold-out batches. Confirms non-trivial conflict evolution. |
| `test_demographic_conservation` | Checked `final_pop == initial_pop + births - deaths` globally, but silent migration occurred between settlements. | Strict world conservation AND settlement-level conservation accounting for logged migrations and marriages. | **Negative control**: Simulates an unlogged population mutation (+1 stealth migrant) and verifies test failure. |
| `test_historical_pressures` | Tested on a single seed (`seed=42`). No negative control. | Evaluates behavioural variety across **5 seeds** (`seeds=[42, 59, 101, 202, 303]`). Asserts $\ge 3$ unique pressure event types occur across the cohort. | **Negative control**: Mocks zero productivity/no seasonal stress and verifies that pressures fail to manifest. |
| `test_anti_convergence_diversity` | Tested on a single seed (`seed=42`). No negative control. | Asserts end-state population divergence across **5 seeds** (`seeds=[42, 59, 101, 202, 303]`). | **Negative control**: Simulates an artificially equalized world and verifies diversity metric rejects uniformity. |
| `test_feud_reconciliation` | Tested on a single seed (`seed=42`). No negative control. | Asserts peace by reconciliation occurs across **5 seeds** (`seeds=[42, 59, 101, 202, 303]`). | **Negative control**: Artificially locks forgiveness to zero and verifies reconciliation rate drops to zero. |
| `test_revelation_pipeline` | Tested on a single seed (`seed=42`). | Validates witness perception, transmission, belief supersession, and memory discounting across **5 seeds**. | Asserts belief supersession and relationship adjustment occur in live simulation runs across the cohort. |
| `test_marriage_peace_alliance_rule` | Did not exist. Spurious recency rule linked any marriage within 12 months to Peace. | Asserts that every Marriage citing Peace has spouses originating from the two feud belligerent settlements. | Tested across all 50 seeds; zero spurious recency-based marriage edges permitted. |

---

## [Milestone 0.5.2] - Reconciliation, Determinism Hardening, and Event Consolidation

### Step 1. Reconciliation, Demographics, and Marriage Funnel
- **Reconciliation of Seeds 2043, 2011, 2029, 2030**:
  - *Seed 2043*: Explained the 350 vs 140 discrepancy. The batch header reported 350 total simulation events, but the historical printer invoked `format_causal_chain(sim.event_log, target_id)` which prints only the ancestors of `target_id` (#140 at Year 44 Month 3). Events #141-349 and all births/marriages outside that backward tree were omitted from printout. Full simulation verified: 154 births, 104 deaths, exactly 80 living characters. Demographic identity holds: `30 + 154 - 104 = 80`.
  - *Seed 2011*: Confirmed world extinction occurred at Year 94 (all 57 people ever born had died). Diagnosed posthumous raid occurring at Year 96 due to lack of dead-actor checks.
- **Marriage and Birth Funnel Fix (Widow/Widower Remarriage)**:
  - *Before*: When a married character died, their surviving spouse's `spouse_id` was never cleared. Surviving widows and widowers (even in their 20s or 30s) remained permanently locked as "married" to a corpse, unable to enter `singles_m` or `singles_f`. In small settlements with sex imbalances, this triggered demographic collapse spirals where young unmarried women had zero available bachelors.
  - *After*: At each monthly life cycle step, `char.spouse_id` is automatically cleared to `None` if the spouse is deceased (`if not spouse or not spouse.alive: char.spouse_id = None`). Surviving widows/widowers freely re-enter the singles pool.
  - *Impact*: 20-year birth stall rate across 50 training seeds dropped from **8% (4/50)** to **0% (0/50)**. Seed 12 evolved from extinction (0 pop) to 46 living citizens; Seed 2011 evolved from extinction (0 pop) to 9 living citizens, with zero population floors or artificial fertility boosts.
- **Age Model Check**:
  - Lifespan model confirmed: Natural deaths occur strictly between ages 60 and 80 (mean 64.7, median 64.0). Maximum age alive at Year 100 across 50 seeds is 73 (mean 65.5).
  - Characters acting past Year 70 were identified not as ageless characters, but as deceased characters cited posthumously in raids, peace treaties, and revenge deaths.

### Step 2. Determinism Hardening & Cross-Process Isolation
- **Elimination of `hash()` and Unseeded State**:
  - *Before*: `lore_engine.py` computed literacy rolls using `(self.seed << 16) ^ hash(character.id) ^ salt`. In Python 3, string `hash()` is randomized per process unless `PYTHONHASHSEED` is pinned, causing divergence across processes.
  - *After*: Replaced all `hash()` calls with `keyed_float(self.seed, "character_literacy", character.id, 0, salt)`. Zero calls to `hash()` exist in the codebase outside `core/rng.py`.
- **`KeyedRNG` Implementation**:
  - Implemented `KeyedRNG` in `minemesis/core/rng.py`: A process-independent, platform-independent pseudo-random number generator backed entirely by keyed SHA-256 hashing.
  - Replaced all uses of `random.Random` across all subsystems (`lore_engine`, `lore_generators`, `lore_libraries`, `lore_templates`, `religion_engine`, `religion_generation`, `religion_culture`, `religion_figures`, `religion_geography`, `religion_heresies`, `religion_interpretation`, `religion_myths`, `religion_schisms`, `religion_spread`, `religion_syncretism`) with `KeyedRNG`.
- **Engine Zero-Overhead Toggles**:
  - Added `ENABLE_LORE_ENGINE` config alongside `ENABLE_RELIGION_ENGINE`.
  - When toggled off, `Simulation` instantiates zero religious or lore structures and bypasses all lore updates, generating zero religious/lore events in the event log.
- **Cross-Process Determinism & Toggle Tests**:
  - `test_cross_process_determinism_under_different_hashseeds`: Spawns two independent Python subprocesses with `PYTHONHASHSEED=0` and `PYTHONHASHSEED=12345` on seed 42. Verifies byte-identical event log SHA-256 digests (`hash_0 == hash_12345`). Includes negative control asserting that different seeds produce different digests.
  - `test_engine_toggle_off_zero_overhead_and_determinism`: Asserts that running with engines OFF produces zero religious/lore events and byte-identical outputs across runs. Includes negative control asserting engines ON produce religious and lore events.

### Step 3. Invariants: Dead Actors, World Extinction, and Collapse Feuds
- **Dead Actors Invariant Enforcement**:
  - Implemented `minemesis/core/invariants.py` with `validate_event_actors_alive` and `validate_entire_history_no_dead_actors`.
  - Every active participant (`actor`, `instigator`, `instigator_char`, `initiator`, `witness`, `recipient`, `spouse`, `spouse1`, `spouse2`, `author`, `party1`, `party2`) must be strictly alive at the tick of the event.
  - The subject may only be dead in a `Death` event (where `target`, `deceased`, `victim` is allowed), and if a killer/instigator acts, the killer must be alive.
  - Pipeline enforcement: `_register_and_perceive_events` validates all newly emitted events at every simulation tick, throwing `InvariantViolationError` if any deceased character acts.
- **Stop on World Extinction**:
  - In `simulation.py`, `step_month` and `run_years` immediately terminate when `len(self.living_characters) == 0`.
  - Prohibits any posthumous updates, phantom ghost migrations, or spurious events after extinction.
- **Settlement Collapse & Feud Invariants**:
  - *No False Peace*: Collapsing is an abandonment/extinction, not a reconciliation. When a settlement collapses, zero `Peace` events are emitted.
  - *Dormant Feuds*: Feuds involving the collapsed settlement are deactivated and logged as `dormant_feuds` in the `SettlementCollapse` event payload. Personal grievances and memories persist with surviving migrants.
  - *Raid Instigator Requirement*: Raids strictly require a living instigator residing in the attacking settlement with an active grievance (`hatred >= 20.0`). If the original instigator is dead or has forgiven the offense, the raid does not fire.
  - *Peace Treaty Representatives*: In Truth Revelation and Exhaustion peace events, both `party1` and `party2` are strictly living representatives (instigator/target or living settlement chiefs). Dead characters are never cited as signatories.
- **Test Hardening & Negative Controls**:
  - Added `test_dead_actors_invariant` in `test_pipeline_invariants.py`: Audits 50-year live simulation run with `validate_entire_history_no_dead_actors`.
  - Includes Negative Control 1: Verifies `validate_event_actors_alive` rejects events citing deceased actors at runtime.
  - Includes Negative Control 2: Verifies `validate_entire_history_no_dead_actors` detects and raises `InvariantViolationError` on posthumous actions.
  - Added `test_world_extinction_invariant`: Verifies zero posthumous events are emitted after world population drops to 0, with a negative control proving living worlds continue to advance.

### Step 4. Event Consolidation, Causality Hardening, and History Printing
- **Raid Consolidation & Consequence Filter**:
  - Minor skirmishes without casualties, route breakage, or heavy loot (>= 15 food) are recorded as state counters (`feud.minor_raids += 1`) without emitting a `RAID` event.
  - A `RAID` event is logged exclusively when there is genuine historical consequence: the 1st raid of a feud, a casualty death, or food stolen >= 15.
  - Archive devastation applies only to logged consequential raid events, not silent skirmishes.
- **Archive Damage Grief Scoping**:
  - In `memory_system.py`, grief memories for `ARCHIVE_DAMAGED` are formed strictly by elders (`age_years >= 50`), scholars, or culturally invested characters (`suspicion < 0.25`), rather than every resident in town.
- **Famine Consolidation (Spells vs Pulses)**:
  - Famine is modeled as a continuous historical spell rather than a bi-monthly pulse.
  - Settlements log ONE `FAMINE` event at spell onset. Starvation deaths during the spell cite the active famine.
  - A minimum recovery period of 12 consecutive months of adequate food is required before any subsequent famine can trigger.
- **Wealth Sinks & Emergency Food Trade**:
  - Enforced monthly municipal maintenance costs on settlements (`max(1, pop * 0.15 + wealth * 0.01)`).
  - Starving settlements with wealth >= 10 actively purchase emergency food at premium prices from neighboring settlements with surplus.
- **Grievance Closure on Peace**:
  - When a `Peace` treaty is signed (via Truth Revelation or exhaustion), the feud's root cause and antecedent conflict events are registered in `resolved_grievance_event_ids`.
  - Future feuds cannot cite resolved grievances, closing causal edges.
- **Lag Caps on Causal Edges**:
  - Enforced in `event_log.py` and `life_cycle.py`: A `Marriage` citing `Peace` must occur within 12 ticks of the treaty. A `Marriage` citing `TradeRouteFounded` must occur within 24 ticks. Beyond that, marriages are strictly routine roots.
- **History Printer & Automated Completeness Test**:
  - `format_causal_chain` now prints event causes explicitly (`Causes: [#...]`) and resolves character IDs to `Full Name (id)`.
  - Added `format_notable_deaths` extracting chiefs, martyrs, revenge victims, accident victims, and starvation casualties with causes.
  ### Step 5. Religion & Literature Audit, Event Volume Balancing, and Epistemological Integrity
- **Demotion of Routine Custom Celebrations to State**:
  - `LOCAL_CUSTOM_CELEBRATED` previously generated over 1,200 events per seed (~38% of the event log).
  - Routine annual village celebrations now update cultural state (`celebration_count`, `last_celebrated_tick`) without logging events.
  - Events are emitted exclusively on:
    1. The first time a local custom is celebrated (`celebration_count == 0`).
    2. Resumption of a celebration following an extended dormancy period ($\ge 60$ ticks / 5 years).
- **Books Read Author Beliefs Rather Than Raw Event Reality**:
  - In `minemesis/lore/lore_generators.py` (`generate_biography`, `generate_historical_chronicle`, `generate_family_history`, `generate_personal_journal`), books synthesize historical milestones from author beliefs passed via `author_beliefs`.
  - When an author believes an accidental death was intentional murder, the text explicitly records murder / deliberate slaying and names the accused actor, rather than citing raw event reality.
  - Added `test_books_read_author_beliefs_not_raw_reality` in `test_lore_engine.py` with positive assertions and a negative control proving fallback to raw reality when beliefs are absent.
- **Literacy Distribution Rebalance**:
  - Population-wide literacy distribution weighted to guarantee realistic historical demographics:
    - Illiterate: $\ge 65\%$ (exceeding $\ge 60\%$ target).
    - Basic Literacy: $23\%$.
    - Educated: $8\%$.
    - Scholar: $3\%$.
    - Historian: $1\%$.
    - Combined Educated / Scholar / Historian is $12\%$ (strictly meeting $\le 15\%$ target).
    - Professional roles (`Priest`, `Historian`, `Scholar`) are assigned based on role rather than random population-wide roll.
- **Lore Formatting & Text Generation Enhancements**:
  - Added word-boundary title truncation in `Book.to_minecraft_json()` to prevent mid-word slicing at the 32-character limit.
  - Removed duplicate concept roots in procedural religion generation (eliminating "Covenant Covenant" titles).
  - Formatted all raw settlement IDs to human-readable names (e.g. `Ironwood` instead of `set_ironwood`).
  - Expanded grudge and suspicion text templates to 5 distinct variations in `lore_templates.py` and 4 in `lore_generators.py`.
- **Historiographical Documentation Disclosure**:
  - Added explicit architectural and historiographical disclosure in `minemesis/religion/religion_engine.py` docstring.
  - Acknowledges that the institutional conflict model (councils, orthodoxy vs. heresy, formal schisms, excommunication) derives from Abrahamic / Christian historiographical patterns.
  - Clarifies that Milestones R1.5 and R2 generalize this into living faith systems including Dharmic, East Asian, and indigenous oral/ancestral traditions.
- **Existing Test Modification (Documented per Standing Rules)**:
  - *Test*: `minemesis/tests/test_syncretism_and_culture.py::test_100_year_unscripted_syncretism_and_culture`
  - *Before*:
    ```python
    custom_events = [e for e in sim.event_log.all_events() if e.type == EventType.LOCAL_CUSTOM_CELEBRATED]
    assert len(custom_events) > 50
    ```
  - *After*:
    ```python
    custom_events = [e for e in sim.event_log.all_events() if e.type == EventType.LOCAL_CUSTOM_CELEBRATED]
    assert len(custom_events) >= 5
    assert all(e.payload.get("is_first_celebration") or e.payload.get("is_resumed") for e in custom_events)
    ```
  - *Rationale*: Routine annual celebrations were demoted from log-flooding events (which constituted 38% of all events) to persistent cultural state updates. Only first celebrations and post-dormancy resumptions are logged as events, bringing `LocalCustomCelebrated` volume from ~1,200 events to ~12 events per run.





