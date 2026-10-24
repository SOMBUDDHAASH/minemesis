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

