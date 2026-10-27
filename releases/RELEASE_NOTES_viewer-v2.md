# Minemesis Viewer V2 - Release Notes

**Build Tag:** `viewer-v2`  
**Single-File Executable:** `MinemesisViewer-v2.exe` (24.17 MB)  
**Portable Folder Archive:** `MinemesisViewer-v2-portable.zip` (34.02 MB)  
**Measured Startup Times:**  
- Portable Folder: `0.389s` (Target: < 1.0s)  
- Single-File Exe: `2.673s` (Target: < 3.0s)  

---

## What Changed In Viewer V2
1. **Relational Run Database (.minemesis SQLite):** Replaced legacy monolithic in-memory JSON archives with high-performance SQLite files streaming in 1,000-row transactions. Keeps simulation heap flat across 100+ years.
2. **Engine-Level Name Integrity & Automated Audit Gate:** Every character receives a permanent given name, surname, and generational ordinal ('II', 'III'). Eliminated all placeholder tokens ('Master Thorne', 'raiding warlord'). Runs automated SQL audit check at run completion (0 issues).
3. **Modular Viewer Architecture:** Refactored into `viewer.core`, `viewer.data`, `viewer.services`, `viewer.ui.widgets`, and `viewer.ui.tabs`. Adding new tabs requires a single file via the `@register_tab` decorator without touching `app.py`.
4. **Persistent 320px Inspector Detail Panel:** Clicking any character, settlement, book, religion, or event instantly populates the right-side inspector pane without leaving the current tab. Double-clicking navigates to the entity's primary tab.
5. **Web-Style History Navigation (Back / Forward):** Full Alt+Left and Alt+Right traversal across all visited entities.
6. **Native Canvas Charts (Zero Bloat):** Canvas-based multi-series line charts and bar charts replacing heavy matplotlib/pandas dependencies to keep executable small (< 40MB) and startup instant.
7. **Parchment Literature Reader & Minecraft Export:** Dedicated book reader with parchment styling, paginated navigation, and one-click JSON/NBT export for Vanilla Minecraft lecterns.
8. **Bundled Showcase Samples:** Includes `sample_30yr_small.minemesis`, `sample_30yr_medium.minemesis`, and `sample_100yr_large.minemesis`.
