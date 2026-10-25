# Minemesis Story Viewer - Release Notes (m0.5.3)

**Build Commit:** `1a84f30`  
**Build Date:** `2026-10-24`  
**Executable Path:** `releases/MinemesisViewer-m0.5.3.exe` (and `releases/MinemesisViewer-latest.exe`)  
**Folder Distribution:** `releases/MinemesisViewer-m0.5.3-folder.zip`  

---

## What Changed In This Build
1. **Independent Dual Seed Split:** Decoupled world geography from history. World Seed governs terrain, settlement layout, and resources; History Seed governs families, traits, faiths, and events.
2. **Procedural World Generator v0:** Replaced fixed settlements with procedural site placement (3 to 7 settlements, minimum spacing 30, 100% economic viability across 500 tested seeds).
3. **Procedural Cast Generator & Name Domain Isolation:** Populates starting settlements with biologically sound families, >= 4 fertile couples per settlement, strict kin-avoidance guarantees, and completely isolated name keying ('name:').
4. **Interactive Map Tab:** Added a new 200x200 canvas map view in the Story Viewer to visualize settlement locations, archetypes, and click to inspect natural resource endowments.
5. **Crockford Base32 Seed Codes:** Typo-safe formatted codes with check digits allow one-click copying, sharing, and reloading of custom worlds.

---

## 3 Things To Look For In The Viewer
1. **'🗺 Same map, new history' Feature (Toolbar):** Click this button to generate a new history seed while keeping the world geography constant, watching completely different families and feuds unfold across the same valleys and mountains.
2. **Interactive Settlement Inspection (🗺 Map Tab):** Click on any settlement circle to view its natural farmland, timber, ore, and defensibility endowments alongside year-end municipal stocks.
3. **Dual Seed Box and Typo-Tolerant Seed Codes:** Type any number or phrase in World Seed (Minecraft-style SHA-256 hash), or paste Crockford Base32 codes (e.g. `WB84Q-PGW6-H8FX5:HBSGH-DGGJ-CE46D:V0:6`) to replay exact procedural worlds.

---

## Showcase Seeds Included
Pre-generated runs located in `releases/m0.5.3/`:
- `minemesis_run_seed42.json` (The Classic Baseline: Streamford, Rockmount, Swiftwash)
- `minemesis_run_seed2029.json` (Escalated Blood Feud: multi-generational vendetta)
- `minemesis_run_seed2030.json` (Syncretism & Reform: rich doctrinal borrowing across settlements)
- `minemesis_run_seed2043.json` (Reconciled Diplomatic Run: complete demographic accounting)
- `minemesis_run_seed2011.json` (Survival Challenge: harsh generational pressures)
