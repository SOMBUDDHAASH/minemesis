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
