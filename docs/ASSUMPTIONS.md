# Architectural Assumptions & Design Choices (Big Build: M1-M6)

This log documents all design decisions and sensible defaults selected across Milestones 1 through 6.

## Milestone 1: Kinship, Dynasties, Epistemic Propagation
- **PersonStore Abstraction**: Introduced `PersonStore` protocol in `minemesis.core.person_store` with `get(person_id)` and `materialize(person_id)`. `Simulation` implements this store initially using existing `Character` instances; M4 swaps in the layered generator seamlessly without breaking kinship algorithms.
- **Kinship Degrees**: Degree 1 = Parents, Full Siblings, Children, Spouse. Degree 2 = Grandparents, Grandchildren, Aunts/Uncles, Nieces/Nephews, Half-Siblings.
- **Reaction Fan-Out**: When an event occurs, notable degree 1 and 2 kin, up to 3 friends, and up to 2 rivals receive personal reactions/beliefs. The wider settlement receives a single aggregated settlement opinion record rather than N individual beliefs.
- **Inherited Grudges**: Passed from parent to child upon death or notable grievance at 0.7x confidence and 0.6x hatred, decaying at 2x rate with source `TOLD_BY_PARENT`.
- **Peace by Revelation**: Feud resolution requires acceptance by a majority (>50%) of living degree-1 kin.
- **Dynasty Tab**: Added as a plugin tab in Viewer V2 with family tree navigation and feud lines.

## Milestone 4: Population Layering
- **Demographic Cohorts**: Ordinary villagers exist as aggregate population tallies by settlement, cohort, sex, and profession.
- **Deterministic Materialization**: When an ordinary villager is promoted or inspected, identity (name, traits, parents) is sampled deterministically from `(world_seed, settlement_id, cohort, slot)` using keyed RNG.
- **Promotion Invariant**: Promoted citizens become full `Character` objects with pinned identities in the database.

## Milestone 2: Settlement Politics
- **Diplomatic Stances**: Stances are `ALLIANCE`, `FRIENDLY`, `NEUTRAL`, `SUSPICIOUS`, `HOSTILE`, `WAR`.
- **War Campaigns**: Consequential raids are recorded as events; minor skirmishes during open war increment campaign casualty tallies to keep event count bounded.
- **Diplomacy Tab**: Map overlay and inter-settlement relationship matrix.

## Milestone 3: Player as Simulation Actor
- **Direct Simulation Participation**: The player is modeled as a first-class character (`player_0`) subject to the same perception, gossip, and causal grammar rules.
- **Emergent Bounty/Hunting**: Aggressive player actions create grudges and settlement hostility organically; avengers track and hunt the player without scripted quest logic.
- **Player Tab**: Viewer command console and reputation inspector.

## Milestone 5: Narrative Director
- **Indirect Levers Only**: The Director adjusts environment pressures (resource scarcity, banditry, migration waves). It is strictly forbidden from directly killing characters, inventing prophecies, or declaring wars.
- **Director Log Tab**: Viewer inspection tab with toggle to disable.

## Milestone 6: Persistence & Replay
- **Pure Replay & Save**: Saved state stores seed pair, tick, generator version, database snapshot, and player state. Randomness is fully keyed, enabling fast forward/replay to any target year.
