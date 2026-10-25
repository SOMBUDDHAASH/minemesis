# Minemesis Story Viewer - Release Notes (m0.5.3)

**Build Commit:** `e519f52`  
**Build Date:** `2026-10-25`  
**Executable Path:** `releases/MinemesisViewer-m0.5.3.exe` (and `releases/MinemesisViewer-latest.exe`)  
**Folder Distribution:** `releases/MinemesisViewer-m0.5.3-folder.zip`  

---

## What Changed In This Build
1. **Global Naming Diversity & Scale Upgrade:** Expanded to 10-35 settlements and 35-55 initial villagers across 9 continental cultural traditions, guaranteeing unique personal and settlement names.
2. **Hard Target Demographics:** Replaced soft survival targets with zero-extinction requirements and verified exact mathematical demographic conservation (living = initial + births - deaths).
3. **High-Performance Simulation Engine:** Added memoized causal DAG graph traversal, observer-indexed memory lookups, and cached feud sets, keeping execution under 2 minutes for 8,000 citizens.
4. **Leak-Free Streaming Verifier:** Built a zero-memory-retention streaming JSONL verifier with instant `--single` audit mode and dynamic on-demand history exports.
5. **Interactive Map & Dual-Seed Viewer:** Includes visual world map inspection, Crockford Base32 seed code sharing, and rapid event text generation with zero raw ID leaks.

---

## 3 Things To Look For In The Viewer
1. **'🗺 Same map, new history' Feature (Toolbar):** Click this button to generate a new history seed while keeping the world geography constant, watching completely different families and feuds unfold across the same valleys and mountains.
2. **Interactive Settlement Inspection (🗺 Map Tab):** Click on any settlement circle to view its natural farmland, timber, ore, and defensibility endowments alongside year-end municipal stocks across 10-35 villages.
3. **Dual Seed Box and Typo-Tolerant Seed Codes:** Type any number or phrase in World Seed (Minecraft-style SHA-256 hash), or paste Crockford Base32 codes (e.g. `WB84Q-PGW6-H8FX5:HBSGH-DGGJ-CE46D:V0:6`) to replay exact procedural worlds.

---

## Showcase Seeds Included
Pre-generated runs located in `releases/m0.5.3/`:
- `minemesis_run_seed42.json` (The Classic Baseline: Streamford, Rockmount, Swiftwash)
- `minemesis_run_seed2029.json` (Escalated Blood Feud: multi-generational vendetta)
- `minemesis_run_seed2030.json` (Syncretism & Reform: rich doctrinal borrowing across settlements)
- `minemesis_run_seed2043.json` (Reconciled Diplomatic Run: complete demographic accounting)
- `minemesis_run_seed2011.json` (Survival Challenge: harsh generational pressures)
