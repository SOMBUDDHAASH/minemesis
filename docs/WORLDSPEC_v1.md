# WorldSpec v1.0 Architecture & Specification Freeze

## 1. Overview and Architectural Purpose
`WorldSpec` serves as the authoritative, immutable boundary contract separating macro world geography from:
1. The **Historical Simulation Engine** (`minemesis`): Consumes economic endowments, settlement locations, and travel route costs. Knows zero voxel block details.
2. The **Voxel Translator & Game Engine** (`translators/voxel/`): Generates 3D volumetric block terrain, caves, ores, structures, and player physics from tile data.
3. The **Viewer UI & Exporters**: Renders 2D topological maps, charts, and Minecraft Java world archives.

---

## 2. Three-Tier Architectural Decoupling

```
               +--------------------------------------+
               |              WorldSeed               |
               +--------------------------------------+
                                  |
                                  v
+--------------------------------------------------------------------+
| Tier 1: WorldSpec (Macro Geography & Topology)                    |
| - Dimensions: 300 x 300 tiles (1 tile = 8 x 8 blocks)              |
| - Platform-independent deterministic integer hash noise            |
| - Elevation, moisture, temperature, biomes, river flow, lakes     |
| - 10 Viable Settlements placed via catchment analysis             |
| - A* Travel Cost Highway Network between settlements              |
+--------------------------------------------------------------------+
              |                                          |
              v                                          v
+-----------------------------+           +----------------------------+
| Tier 2: Historical Sim      |           | Tier 2: VoxelSpec          |
| - Endowments, catchments    |           | - Volumetric heightmaps    |
| - Travel costs for trade    |           | - Ore depth distributions  |
| - Settlement profiles       |           | - Cave carving noise       |
| - ZERO 3D voxel dependency  |           | - Chunk coordinate mapping |
+-----------------------------+           +----------------------------+
                                                         |
                                                         v
                                          +----------------------------+
                                          | Tier 3: Game & Exporters   |
                                          | - Standalone Voxel Engine  |
                                          |   (Movement, Raycasting,   |
                                          |    Collision, Block edits) |
                                          | - Chunk Delta Persistence  |
                                          | - Minecraft Anvil Exporter |
                                          +----------------------------+
```

---

## 3. WorldSpec Tile Schema (RAM-Compact Flat Representation)
To prevent creating 90,000 Python tile objects in RAM, `WorldSpec` encodes 300x300 grids into contiguous bytearrays and typed flat arrays:
- `elevation`: `bytearray` of length $300 \times 300$ (values 0–255, sea level = 64).
- `temperature`: `bytearray` (0–255 mapped to 0.0–1.0).
- `moisture`: `bytearray` (0–255 mapped to 0.0–1.0).
- `biome`: `bytearray` mapping to Biome IDs (0=Ocean, 1=Beach, 2=Grassland, 3=Forest, 4=Taiga, 5=Snow, 6=Desert, 7=Swamp, 8=Hills, 9=Mountain).
- `river_flow`: `bytearray` (flow accumulation 0–255, 0 = dry land, >5 = creek, >25 = major river).
- `fertility`, `forest_density`, `ore_richness`, `fish_potential`, `stone`: flat arrays scaled 0–255.
- `travel_cost`: 1D float/int array computed from slope, water, and vegetation.

---

## 4. Settlement Catchment Analysis
Every settlement site's economic profile is derived strictly from its catchment radius (radius = 12 tiles):
- $\text{Farmland} = \sum \text{fertility} \times (1.0 - \text{slope})$
- $\text{Forest} = \sum \text{forest\_density}$
- $\text{Ore Richness} = \sum \text{ore\_richness} \times \text{slope}$
- $\text{Water Access} = \max(\text{river\_proximity}, \text{coast\_proximity})$
- $\text{Defensibility} = \text{elevation} + \text{surrounding\_slope} - \text{flat\_exposures}$

---

## 5. Chunk Delta Persistence Contract (Two-Way Interaction)
The bridge between the game engine and the simulation engine adheres to the **Chunk Delta Principle**:
1. **Never emit per-block events**: Placing a stone block never emits a simulation event.
2. **Chunk Delta Storage**: Player modifications are stored in a sparse dictionary:
   $$\Delta(\text{chunk}_x, \text{chunk}_z) = \{ (x, y, z): \text{new\_block\_id} \}$$
3. **Construction Analysis**: When aggregated chunk deltas in a settlement's territory exceed construction thresholds (e.g., 200+ contiguous stone blocks forming a perimeter), the analyzer emits a single macro event:
   $$\text{EventType.PLAYER\_ACTION} \quad (\text{action} = \text{"build\_wall"}, \, \text{defensibility} += 0.25)$$
   The simulation updates its defensibility metric, reducing raid success rates organically.

---

## 6. Specification Freeze Guarantee
This contract is frozen as of v1.0. Future expansions to game renderers or modding platforms will consume `WorldSpec` or `VoxelSpec` without altering the deterministic core.
