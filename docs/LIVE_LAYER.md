# Minemesis Live Layer Architecture Specification
**Document Version:** 1.0.0 (Milestone E3)  
**System:** Minemesis Standalone 3D Voxel Civilization Game  
**Author:** DeepMind Antigravity Systems Engineering Team  

---

## 1. Overview & Core Philosophy

Minemesis is an entirely self-hosted, custom-coded standalone voxel civilization game. It has zero external dependencies on third-party commercial engines (Unity, Unreal, Godot) or Minecraft/Mojang Java/Anvil formats.

The architecture operates on a strict **Dual-System Separation**:
1. **The Civilization Brain (`minemesis/`)**: A pure-Python, deterministic historical simulation governing kinship, population layering, dynasties, religious schisms, epistemic beliefs, literature authoring, and causal event graphs. The simulation **never imports the engine**.
2. **The Physical Body (`engine/`)**: A custom 3D voxel engine built directly in Python using ModernGL (OpenGL 3.3 Core Profile), GLFW, and NumPy. It renders 16x16x256 voxel chunks with interior face culling, vertex ambient occlusion, swept AABB physics, dynamic atmospheric sky rendering, and procedural voxel humanoids.

Communication between the physical body and the civilization brain is mediated exclusively through the **Simulation Bridge (`engine/core/process_bridge.py`)**.

```
+------------------------------------------------------------------------+
|                      MINEMESIS SIMULATION BRAIN                        |
|   (Kinship, Dynasties, Religions, Books, Epistemic Ledger, Events)    |
+-----------------------------------+------------------------------------+
                                    |
                         Queue / API Bridge
                    (engine/core/process_bridge.py)
                                    |
+-----------------------------------+------------------------------------+
|                       MINEMESIS ENGINE BODY                            |
| (ModernGL Core 3.3, Chunks, Swept AABB Physics, Humanoids, Blueprints)  |
+------------------------------------------------------------------------+
```

---

## 2. Living NPC System & Spatial Registry

Every living entity in Minemesis is not merely a generic character model; each entity represents a persistent historical character from the settlement with recorded lineage, faith, profession, and home/work locations.

### 2.1 Voxel Humanoid Mesh & Deterministic Aesthetics
- Each humanoid is rendered as an articulated voxel mesh consisting of 6 primary body boxes: **Head**, **Hair Cap**, **Torso**, **Left Arm**, **Right Arm**, and **Legs**.
- Vertex geometry is generated once and textured through UV mapping from the procedural `TextureAtlas`.
- Professions determine the clothing palette, hair style, and equipment:
  - **Chief / Elder**: Royal amber robe (`#D7A528`), charcoal trousers, distinguished silver hair.
  - **Scholar / Scribe**: Deep sapphire scholar tunic (`#325AA5`), slate trousers, chestnut hair.
  - **Priest / Priestess**: Sacred ivory vestments (`#CDD7E6`), amethyst sash, silver hair.
  - **Blacksmith**: Leather artisan apron (`#735A41`), iron-gray trousers, dark hair.
  - **Farmer**: Forest green work tunic (`#649B4B`), earth trousers, straw-brown hair.
  - **Guard**: Polished iron mail (`#8C949E`), steel greaves, short dark hair.
  - **Citizen / Laborer**: Earth-toned homespun garments (`#9B735A`), sturdy boots.

### 2.2 Spatial Registry & Blueprints
NPCs are spatially anchored to settlement blueprint structures:
- **Home Position**: Assigned to a bed within a peasant cottage or longhouse.
- **Work Position**: Assigned to the village smithy, farm field, town archive, or guard tower.
- **Social Position**: Assigned to the village well or central market square.
- **Shrine Position**: Assigned to the village shrine or temple altar.

---

## 3. Daily Schedules & Routine Evaluation

NPCs evaluate their schedules continuously against the celestial day/night cycle (`sky.progress` from 0.0 to 1.0, representing 00:00 to 24:00):

| Time Window | Hour Range | Schedule Activity | Target Anchor |
|-------------|------------|-------------------|---------------|
| **0.00 – 0.25** | 00:00 – 06:00 | **Deep Sleep** | Bed in Personal Home |
| **0.25 – 0.50** | 06:00 – 12:00 | **Morning Labor** | Craft Smithy, Farm Field, or Archive |
| **0.50 – 0.60** | 12:00 – 14:00 | **Midday Gathering** | Village Well / Market Square |
| **0.60 – 0.75** | 14:00 – 18:00 | **Afternoon Labor** | Trade Workshops & Defensive Watch |
| **0.75 – 0.90** | 18:00 – 22:00 | **Evening Devotion** | Village Shrine / Faith Altar |
| **0.90 – 1.00** | 22:00 – 24:00 | **Return to Hearth** | Peasant Cottage / Longhouse |

NPCs navigate smoothly between anchors using raycast slope negotiation, smoothly turning their yaw to face their direction of movement.

---

## 4. Time Scale & Day/Night Progression

- **Standard Real-Time Ratio**: 1 Game Year = 20 Real-World Minutes (1200 seconds).
- **Simulation Ticks**: 1 Game Year comprises 12 monthly ticks. Thus, 1 simulation tick occurs every 100 real-world seconds.
- **Celestial Progression**: The sun sweeps an orbital arc across the sky with Rayleigh atmospheric color transitions:
  - Dawn / Dusk: Warm amber-rose (`#FF8C4B`, `#E65A4B`).
  - Noon: Brilliant solar gold (`#FFF5E0`) with deep azure ambient sky (`#7AB8FA`).
  - Night: Deep obsidian-navy (`#0A0F1E`) with subtle lunar luminescence.
- **Time Skipping**: Interacting with a bed advances the clock to dawn (06:00), instantly computing accumulated simulation ticks, crop cycles, and settlement census changes.

---

## 5. Dual-Fidelity Combat & Witness Line-of-Sight

When violence erupts in the physical voxel world, it directly impacts the social graph of the civilization:

1. **Hit Detection & Damage**:
   - The player deals 6.0 damage per attack with active weapons or tools.
   - NPCs possess 20.0 hit points.
2. **Witness Line-of-Sight Check**:
   - When an assault occurs, all NPCs within a 45-meter radius evaluate sightlines and hearing proximity.
3. **Organic Reactions**:
   - **Civilian NPCs**: Cry out in terror, lower affinity to the player to -100, and immediately flee toward their homes or the chieftain's longhouse.
   - **Guards**: Enter defensive alert mode (`is_hostile = True`), draw weapons, and hunt down the intruder.
4. **Historical Ledger Recording**:
   - The assault or homicide is transmitted across the `SimulationBridge` to the `EpistemicLedger` and `EventLog`. A blood feud or grievance event is logged against the traveler, permanently degrading reputation in that settlement and among allied factions.

---

## 6. Organic Dialogue & Interaction Menu

Proximity to an NPC within 3.5 meters activates the interactive prompt:  
`[E] Speak with {Name} ({Profession})`

Pressing `[E]` opens the six-fold interaction menu:
- **`[1] Talk`**: Generates context-sensitive dialogue reflecting the character's profession, faith, recent settlement events, and current affinity to the player.
- **`[2] Trade`**: Offers regional barter goods (timber, crops, copper ingots, quarried stone).
- **`[3] Gift`**: Offers resources to the villager (+15 affinity).
- **`[4] Help`**: Solicits settlement defense quests and requests fortification of vulnerable borders.
- **`[5] Steal`**: Stealth pickpocket check. If caught, screams alert guards and brand the player a thief.
- **`[6] Attack`**: Initiates physical combat and triggers the witness panic system.
- **`[Esc]`**: Leaves interaction and returns cursor to first-person mouse look.

---

## 7. Construction Analyzer & Settlement Defensibility

The Construction Analyzer bridges player creativity directly into settlement geopolitics:

1. **Block Monitoring**:
   - Tracks all chunk deltas (player-placed or broken blocks) within a 70-meter radius of each settlement center.
2. **Fortification Detection**:
   - Identifies structural defense blocks: `Stone Bricks` (ID 89), `Cobblestone` (ID 90), `Basalt Masonry` (ID 91), `Slate Shingles` (ID 92), and `Wood Palisades` (ID 94).
3. **Defensibility Metric**:
   - Base settlement defensibility begins at 10%.
   - Every 20 placed defensive masonry blocks increase settlement defensibility by +1.5%, up to a maximum of 95%.
4. **Settlement Adaptation**:
   - When defensibility increases by +5%, the village adapts:
     - The event is logged in the simulation chronicle:  
       `"Citizens of {Settlement} celebrate new stone defenses! (Defensibility: {X}%)"`
     - Villagers express gratitude during `[1] Talk` interactions.
     - Additional guard patrols spawn on the perimeter walls to man the battlements.

---

## 8. Physical Book Archives & Run Database Integration

Town archives and scholar lecterns house readable historical manuscripts:
- Approaching a **Town Archive Bookshelf** (ID 100) or **Scholar Lectern** (ID 101) within 4.0 meters displays:  
  `[R] Read Ancient Chronicle`
- Pressing `[R]` opens the full-screen book reader overlay:
  - Decompresses and displays authentic manuscripts written by historical scholars during the simulation.
  - Page-turning navigation via `[N]` (Next) and `[P]` (Previous).
  - Books contain genuine historical lore, diaries, philosophical treatises, and accounts of past feuds.

---

## 9. Persistence & World Delta Streaming

Worlds are saved under `saves/{world_name}/`:
- `player.json`: Coordinates, yaw/pitch orientation, health, hotbar, inventory, time of day.
- `chunk_deltas.json`: Sparse delta dictionary mapping `(cx, cz) -> {(lx, ly, lz): block_id}`. Only modified voxels are saved to disk, preserving minimal disk footprint.
- `chronicle.minemesis`: Exported SQLite relational database storing all meta, settlements, census, events, characters, epistemic cases, books, and religions.
