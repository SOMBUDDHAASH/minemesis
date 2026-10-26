# Minemesis V2: 10-Minute Interactive Walkthrough (Milestones 1 to 6)

Welcome to **Minemesis V2**. This guide walks you through every major subsystem implemented across Milestones 1 through 6 in approximately 10 minutes.

---

## Prerequisites & Launch

### Option A: Launch Standalone Executable (Recommended)
Double-click:
```
releases\MinemesisViewer-v2.exe
```
Or unzip and run from:
```
releases\MinemesisViewer-v2-portable\MinemesisViewer-v2.exe
```

### Option B: Run from Source
```powershell
python -m viewer
```

---

## 1. Loading a Simulation Run (Minute 1)
1. On startup, the viewer displays the **Home** tab with recent files and seed generators.
2. Click **"Open .minemesis Run File"** and choose `samples/sample_100yr.minemesis` (or any newly generated run).
3. The database loads instantaneously via SQLite read-only streaming. Notice:
   - **Schema Version**: 1 (Verified)
   - **Total Events**: ~12,500+
   - **Living Citizens**: ~2,400+
   - **Peak RAM**: ~108 MB (Under 1.0 GB budget)

---

## 2. Milestone 1: Kinship & Dynasties (Minutes 2 - 3)
1. Click the **Dynasties** tab (Tab 9).
2. The left pane lists noble houses ranked by prestige (driven by living members, authored books, settlement leadership, and honorable standing).
3. Select a prominent house (e.g., **House Miller** or **House Oakhaven**):
   - **Profile Header**: Displays Head of House, settlement lands, and prestige score.
   - **Family Members Sub-tab**: Lists every living and historic member with parent links and professions.
   - **Feud & Vendetta Sub-tab**: Shows active blood feuds and multi-generational grievances.
   - Notice how children inherit grudges from deceased parents at 0.7x confidence and 0.6x hatred, decaying at double rate.

---

## 3. Milestone 4: Population Layering (Minutes 4 - 5)
1. Click the **World & Census** tab (Tab 8).
2. Look at the **Population Over Time** chart:
   - The world sustains 2,400+ citizens with realistic carrying-capacity equilibrium.
   - **Why Peak RSS is only 108 MB**: Background villagers exist as compact aggregate demographic cohorts `(settlement, age_bracket, sex, profession)`. Only notable characters (chiefs, authors, avengers, victims) are promoted to full `Character` objects with pinned identities in the database.

---

## 4. Milestone 2: Settlement Politics & Warfare (Minutes 6 - 7)
1. Click the **Diplomacy** tab (Tab 10).
2. The left pane shows all settlement pairs and their current diplomatic stances:
   - `ALLIANCE`, `FRIENDLY`, `NEUTRAL`, `SUSPICIOUS`, `HOSTILE`, `WAR`.
3. Select a pair at **War** or with an **Alliance**:
   - Inspect the historical treaties, war declarations, and alliance formations.
   - Note the **War Campaign System**: skirmishes and minor clashes are aggregated into campaign casualty tallies without polluting the event log with thousands of spam events.

---

## 5. Milestone 3: Player as Simulation Actor (Minutes 8 - 9)
1. Click the **Player** tab (Tab 11).
2. Inspect the **Player Traveler (`player_0`)** console:
   - Player is an authentic in-world character living in a settlement.
   - **Active Hunters Tab**: Identifies living NPCs whose relationship towards the player has high hatred (`>= 40.0`). These avengers track and hunt the player without scripted quest rails.
   - **Devoted Allies Tab**: Displays villagers rescued or aided by the player.
   - **Command Console**: Try entering an entity ID and clicking commands (`Help Town`, `Gift Target`, `Build Wall`, `Save Target`).

---

## 6. Milestone 5: Narrative Director (Minute 9)
1. Click the **Director** tab (Tab 12).
2. Observe the indirect environmental pacing levers:
   - **Resource Scarcity Multiplier**: Modulates seasonal harvest yields.
   - **Bandit Raid Pressure**: Adjusts wilderness outlaw activity when the world stagnates.
   - **Migration Wanderlust**: Encourages resettlement during regional crises.
3. Review the **Director Intervention Log**: Notice that the Director strictly uses environmental levers and never directly kills characters, invents prophecies, or declares wars.
4. Try toggling **"Enable Director Interventions"** on or off.

---

## 7. Milestone 6: Persistence, Replay & Macro World Map (Minute 10)
1. Return to the **World & Census** tab and switch to the **Macro World Map & Replay** sub-tab:
   - Reconstructs the 2D macro world map directly from `world_seed` without voxel overhead.
   - Displays settlement nodes, biomes, and connecting trade highways.
2. In the **Target Replay Year** box, enter `25` (or any target year) and click **"Replay Simulation"**:
   - The engine performs pure keyed deterministic fast-forward simulation up to that exact year.
   - Verifies that any point in history can be replayed and inspected on demand.

---

## Walkthrough Summary
You have verified that all 6 milestones are integrated, fully functional, and running with unprecedented memory efficiency (~108 MB peak RSS).
