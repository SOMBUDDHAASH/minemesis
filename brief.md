# Minemesis Agent Brief: Milestones 0.5 to 6

*Prepared for the coding agent. Read agent.md first, then this brief. This brief supersedes the 'Next Recommended Task' in the Milestone 0 report.*

## 1. Where we are

Milestone 0 proved the architecture: the event log, the Perception → Belief → Memory → Relationship → Decision pipeline, keyed deterministic RNG, and a 100-year headless run all work. It did not prove that the simulation produces history. A review of the seed-42 output found:

- **Causal chains are chronology, not causality.** The printed depth-39 chain lists trade caravans as causes of an accidental forestry death and of each other. The real chain is depth 3: accident → wrongful feud → peace.
- **281 of 557 events are routine trade caravans.** Routine logistics is world state, not history.
- **There is only one story.** Accidental death, wrongful feud, truth revealed, peace. It occurred twice, and no other source of conflict exists.
- **The world converges to a dull equilibrium.** Populations 21/19/23, wealth 1005–1070, and no active feud at Year 100.
- **Truth revelation appears to be a probability roll.** Who revealed it, how, and why then are not recorded.
- **Some passing tests are vacuous.** The depth test only asserts depth ≥ 3, and the story and demographic tests ran on very few seeds.

The architecture passed. The simulation did not. The goal of the next milestones is not passing tests. It is generated histories that read like history instead of event spam.

## 2. Standing rules (apply to every milestone)

1. **One milestone at a time.** At the end of each milestone, stop and deliver the report in section 3. Do not start the next milestone.
2. **Out of scope until instructed:** Narrative Director, terrain, voxels, rendering, graphics, pathfinding, crafting, networking.
3. **Determinism is a hard requirement.** Same seed means a byte-identical event log. Keep keyed hashing (WorldSeed, System, Entity, Tick, Salt). Give every new system its own system id. Never use shared mutable RNG state. Iterate over sorted keys only. Keep a fixed, documented per-tick update order. Adding systems will change the seed-42 digest; that is expected. Re-verify that two runs are identical and record the new digest.
4. **The Event Log is objective reality.** Events store ground truth only. Characters react to beliefs, never to raw events. Relationships stay derived views computed from memories. Do not weaken the architecture invariants or their tests.
5. **Amend agent.md through a changelog, not silent edits.** Create agent\_changelog.md (or bump agent.md to v1.1 with a changelog section) listing every amendment these milestones make: the causal grammar, new event types, belief supersession, and so on.
6. **No vacuous tests.** Every new acceptance test needs a negative control that proves the test can fail (for example, construct an invalid event and assert the validator rejects it). In each report, state for every criterion what result would have made it fail.
7. **No gaming.** Do not tune parameters to hit targets in a single seed. Report analytics across many seeds. Do not add hidden rubber-banding or balancing that forces convergence; the Milestone 0 failure was over-balance.
8. Keep code typed and readable, modules single-responsibility, and the event schema immutable (frozen dataclasses) and append-only.

## 3. Report format (end of every milestone)

- Summary of what changed and why; files created and modified.
- Test results (full pytest summary), plus each new test and its negative control.
- Determinism: two-run comparison and the new SHA-256 digest.
- Analytics: the 50-seed summary using the metrics in section 4.6.
- One complete readable history for seed 42, and a causal graph of one story.
- An honest list of weaknesses and anything that still looks like noise.
- Any decision that needs the human.

## 4. Milestone 0.5: Causal integrity and historical pressure

Goal: every cause pointer means real causation, the log contains only events worth remembering, and the world has more than one source of drama.

### 4.1 Causal grammar

Replace 'attach a recent event as cause' with explicit rules. Define a data table, CAUSE\_GRAMMAR, mapping each event type to (a) whether causes may be empty (root event) and (b) which event types may appear as causes. Validate in EventLog.append and raise on violation. Initial table:

```
Birth              causes: Marriage if the parents married during the simulation; root allowed for initial couples
Marriage           causes: root allowed; may cite Peace or TradeRouteFounded (alliance marriages)
Death              causes: root allowed (natural, accident); Raid (raid casualty); Famine (starvation); Feud + Death (revenge killing)
Feud               causes: at least one Death or Raid (the believed offence); may also cite an earlier Feud
Raid               causes: at least one of Feud, Famine, SuccessionCrisis
Peace              causes: Feud (required) plus Revelation, or exhaustion evidence (Raid/Death)
Revelation         causes: Death (required: the event whose truth is revealed); Feud if it ends one
Famine             causes: root allowed (environmental) or Raid (destroyed stores)
TradeRouteFounded  causes: root allowed; may cite Peace, Marriage or Famine
TradeRouteBroken   causes: Raid, Feud, Famine or SuccessionCrisis
ChiefChanged       causes: Death (the chief died) or SuccessionCrisis
SuccessionCrisis   causes: Death (the chief)
```

Requirements:

- Refine the table if the simulation needs it, but record every change in the changelog.
- A Death with Intent=Accidental and no genuine cause is a root event.
- Add a validator test with negative controls: a trade event, or a Birth, cited as the cause of an accident must be rejected.
- Replace the old depth test. Real causal depth is the longest path in the cause graph. Because the grammar validates every edge, depth is real by construction. Also report the number of distinct event types along the deepest path, and require at least 3 distinct types for the 0.5 acceptance chain.

### 4.2 Demote routine trade to state

For every candidate event ask: could a character reasonably remember, discuss, report, blame, celebrate or fear this? If not, it is state.

- Remove per-caravan Trade events. Settlement-pair trade flow becomes state (a trade-route record with volume and health).
- Emit events only for history: TradeRouteFounded and TradeRouteBroken. An embargo or pact event can come later.
- Trade still affects the simulation (food and wealth transfer). Form relationship memories only for notable caravan moments such as first contact, a rescued caravan, or a lost caravan, never one memory per caravan.

### 4.3 Truth revelation as a real event

The current peace-by-truth path must become a causal pipeline.

1. A witness holds a high-confidence first-hand belief about the true intent of an event.
2. A revelation opportunity arises: the witness can reach the instigator directly, or through a chain of Told beliefs via characters the instigator trusts. Use keyed RNG only to decide timing among legitimate opportunities, never to decide the outcome from nothing.
3. The instigator receives a conflicting belief. Resolution rule: compare the instigator's current belief confidence against the speaker's confidence × the instigator's trust in the speaker, adjusted by the instigator's suspicion trait. If the new belief wins, it supersedes the old one.
4. Emit a Revelation event with causes = \[the original Death\] plus the Feud if one is being ended. The payload records the witness, the path and the corrected intent.
5. Belief supersession (4.4) triggers memory re-appraisal.
6. Peace is then emitted with causes = \[Feud, Revelation\].

Also implement the other peace path honestly: negotiated peace through memory decay and fatigue, where Peace cites the Feud plus the Raid or Death events that exhausted it. Report how often each mechanism occurs. If one never occurs across 50 seeds, say so.

### 4.4 Belief supersession and memory re-appraisal

Events and memories are immutable. Implement correction without mutation:

- A Belief may reference supersedes (the believer's earlier belief about the same event).
- Memories formed from a superseded belief stay in the store but are flagged in a derived index. compute\_relationship excludes them, or heavily down-weights them.
- Re-appraisal forms new memories from the new belief: guilt or regret toward the wrongly accused, respect if the accused forgave, relief, with intensity scaled by the old hatred that was held.
- Test: hatred toward the wrongly accused drops after supersession and regret appears. A negative control shows hatred persists when the correction is rejected.

### 4.5 Historical pressure systems

Add exactly three new sources of drama. Keep each small and testable.

**Revenge.** When a character holds a hatred memory above threshold toward someone they believe killed a loved one, a keyed-RNG decision (influenced by forgiveness trait, opportunity and cooldown) can produce a revenge killing: a Death with Intent=Intentional and causes = \[the original Death, the Feud\]. The new Death can start a new feud on the other side, which makes grudges recursive. Add escalation limits so history does not end in extinction: fatigue, a per-character cooldown, the forgiveness trait, and a cap on active revenge cycles per settlement pair. In this milestone revenge is carried out by the feud instigator only. Kin involvement comes in Milestone 1.

**Leadership.** Each settlement has a chief. When the chief dies, a successor is chosen by rule (eldest competent child, otherwise the adult with the highest standing from accumulated positive relationships). If several candidates have strong mutual rivalry, or the chief died under disputed circumstances, a SuccessionCrisis occurs. It lowers settlement stability, which raises raid and feud probabilities and lowers trade-route health. Events: ChiefChanged, SuccessionCrisis.

**Scarcity.** Give each settlement its own productivity, derived at world generation from keyed RNG and terrain-like parameters (farmland, forest, ore, defensibility), so the world is asymmetric from the start. Food has seasonal variance and per-settlement noise. When food stays below a threshold for N ticks, emit Famine. Effects: starvation deaths (Death with cause Famine, causes = \[Famine\]); a hungry settlement either requests trade (TradeRouteFounded citing Famine) or raids a food-rich neighbour (Raid citing Famine), decided by leader traits and relationships.

**Anti-convergence.** Remove any mechanism that equalises wealth, food or population. End states should differ across settlements and across seeds.

### 4.6 Analytics: the 50-seed batch

Add a CLI command, for example `python main.py batch --seeds 50 --years 100 --out reports/`, that writes per-run metrics as CSV or JSON plus a markdown summary.

Per-run metrics:

- event counts by type and as a share of the log
- non-routine events (everything except Births, natural Deaths and Marriages)
- feuds, wrongful feuds, revenge killings, raids, famines, succession crises, chief changes
- peaces by mechanism (truth revelation vs negotiated)
- maximum real causal depth, and distinct event types along the deepest path
- active feuds at the final tick
- extinct settlements, and the largest settlement's share of population
- spread of wealth and food across settlements at the end

Aggregates: mean, median, min and max, plus the share of runs with zero feuds and the share with an active feud at Year 100.

Initial targets. Report against them and tune the simulation, not the targets. They are starting points, and only the two marked hard are test failures.

- zero-feud runs at most 5%
- median 3–10 feuds per run
- at least 40% of runs end with an active feud or unresolved tension
- no single event type above 50% of the log; Birth + Death + Marriage together at most 70%
- no cause-grammar violations (hard)
- zero extinct settlements across all 50 seeds (hard)
- at least 3 distinct event types on the deepest causal chain in most runs
- end-state wealth and food differ meaningfully across settlements (report the spread)

### 4.7 Deliverables and acceptance for 0.5

1. The changes above, with tests and negative controls.
2. One complete readable history for seed 42.
3. One causal graph of a single story (Mermaid or Graphviz DOT file).
4. The 50-seed statistical summary.
5. The report from section 3.

Acceptance: grammar enforced with negative controls; routine trade demoted; revelation is an event with a real witness path; at least three distinct sources of conflict observed across the 50 seeds; targets reported honestly, including the ones missed.

## 5. Milestone 1: Kinship consequences and belief-correction propagation

Do not start until 0.5 has been reviewed.

Goal: one death produces different reactions across a family, and corrections spread through families.

### 5.1 Kinship graph

- Implement kin\_degree(a, b). Parent, child, sibling and spouse are degree 1. Grandparent, grandchild, uncle or aunt, nephew or niece, cousin and in-law are degree 2.
- Keep explicit parent and spouse pointers for named characters. They are cheap and make revenge and inheritance queries trivial.

### 5.2 Reaction fan-out

- When a character forms a belief about a death, a reaction process runs for kin within degree 2, for friends above a positive-relationship threshold (capped at N per event), and for the settlement as one aggregate belief rather than one per villager.
- Reactions differ by role and are observer-specific: a spouse leans toward grief, a child toward anger and a drive for revenge, a sibling toward hatred or suspicion, a rival toward relief. Traits (suspicion, forgiveness) modulate intensity. Keyed RNG adds only small variation.
- Cap reactions per event so belief and memory counts do not explode. Background settlement members share the aggregate belief.

### 5.3 Family consequences

- Family standing is a derived view built from events involving members. It is not stored.
- Family feuds become possible: an offence against a member by a member of another family can create a family-level feud, with each side's members carrying inherited, attenuated beliefs (source Told by a parent or sibling).
- Multi-generation grudges: children inherit beliefs and a fraction of the hatred from parents, with lower confidence and faster decay. Test that a grudge can outlive its original participants.
- Extend revenge so kin, not only the instigator, can act.

### 5.4 Belief-correction propagation

Make this pipeline explicit and tested end to end: truth discovered → beliefs updated → memories re-appraised → relationships recomputed → peace becomes possible. Corrections propagate through the instigator's family and friends as Told beliefs, and family members re-appraise at different speeds.

### 5.5 Tests

Family revenge emergence, family reconciliation, family reputation propagation, multi-generation grudge, reaction cap respected, determinism, all earlier tests, and a rerun of the 50-seed batch with added metrics (reactions per death, family feuds, inherited grudges).

## 6. Roadmap after Milestone 1 (do not start without instruction)

**Milestone 2: Settlement politics.** A settlement-to-settlement stance (Alliance, Friendly, Neutral, Suspicious, Hostile, War) computed from trade, shared enemies, history, marriage ties, leader personality and resource pressure. New events: AllianceFormed, WarDeclared, TreatySigned. No scripted relationships.

**Milestone 3: The player as an actor in the headless sim.** A text command interface (kill, save, steal, gift, help, trade, and an abstract build-wall) that emits events through the same schema. Witnesses perceive the player through the normal pipeline, and attribution happens through beliefs. Acceptance: reproduce the emergent-story test by playing it (save a settlement, accidentally kill a brother in a war, be hunted, save the son, end the feud) without scripted quests.

**Milestone 4: Population layering and promotion.** Ordinary villagers are generated deterministically from (settlement, slot) and regenerate identically. A villager is promoted to a persistent character when involved in a notable event (the player saves or kills them, they become chief, they start a war). Aggregate events act as constraints on later detail: 17 plague deaths means 17 specific people existed and died. Scale population to hundreds or thousands, add memory pruning and compaction, and measure performance instead of guessing.

**Milestone 5: Narrative Director.** Only after the simulation produces enough content on its own. Permitted levers: raid frequency, migration pressure, bandit activity, faction aggression modifiers. Forbidden: killing characters, declaring wars, changing relationships, spawning stories. Every intervention is logged as a DirectorAction event with reason, lever and magnitude, and the Director reads defined tension metrics.

**Milestone 6 and later.** Save format (snapshot plus log tail, versioned generators, details committed once observed), then terrain, the voxel layer, and appearance derived from simulation state. These stay out of scope until the headless simulation is judged to read like history.

## 7. First instruction to the agent

Begin with Milestone 0.5 only, in this order: 4.1 causal grammar, 4.2 trade demotion, 4.3 and 4.4 revelation with belief supersession, 4.5 pressure systems, 4.6 analytics, 4.7 deliverables. Stop at the end of 0.5 and report.
