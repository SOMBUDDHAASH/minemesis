# Minemesis Story Viewer - Release Notes (m0.5.2)

**Build Commit:** `e322da2`  
**Build Date:** `2026-10-24`  
**Executable Path:** `releases/MinemesisViewer-m0.5.2.exe` (and `releases/MinemesisViewer-latest.exe`)  
**Folder Distribution:** `releases/MinemesisViewer-m0.5.2-folder.zip`  

---

## What Changed In This Build
1. **Reconciled Demographics:** Fixed printed event numbering and population accounting so all birth, death, and census accounts match ground truth reality exactly.
2. **Determinism Hardened:** Guaranteed byte-identical simulation outcomes across different operating systems and processes by eliminating Python string hash salting.
3. **Event Balance Restored:** Demoted routine celebration and conversion spam down from 79% to ~8% of the event log so feuds, raids, and peace treaties stand out prominently.
4. **Subjective Literature:** Re-anchored procedural book creation in author beliefs and perspectives, ensuring penned chronicles reflect personal biases rather than omniscient truth.
5. **Interactive Story Viewer:** Delivered a complete Windows desktop application with 8 tabs to explore readable chronicles, causal roots, feud storylines, books, and beliefs.

---

## 3 Things To Look For In The Viewer
1. **The '↳ because: ...' Causal Clauses (Story Tab):** Notice how raids and feuds cleanly explain their root motivations back to historical grudges and deaths.
2. **Truth vs. Belief Comparison (People Tab):** Select any citizen to compare what they believe happened against objective reality, discovering how false rumors trigger conflicts.
3. **100-Year Population Trajectory (World Tab):** Examine the dynamic settlement census chart and the event share audit table proving spam elimination.

---

## Showcase Seeds Included
Pre-generated runs located in `releases/m0.5.2/`:
- `minemesis_run_seed42.json` (The Classic Baseline: balanced theological growth and stability)
- `minemesis_run_seed2029.json` (Escalated Blood Feud: multi-generational vendetta and raiding)
- `minemesis_run_seed2030.json` (Syncretism & Reform: rich doctrinal borrowing across settlements)
- `minemesis_run_seed2043.json` (Reconciled Diplomatic Run: complete demographic accounting)
- `minemesis_run_seed2011.json` (Survival Challenge: harsh generational pressures and migration)
