# Minemesis Live Layer Architecture Specification

## 1. Overview
The **Live Layer** bridges the high-level macro simulation (Milestones 1–6) and the real-time 3D voxel game environment. While the headless simulation operates in monthly ticks across hundreds of years, the player experiences the world in first-person at second-by-second scale.

---

## 2. Core Subsystems Required for Playable 3D Gameplay

### 2.1 Spatial Grounding & Entity Schedules
- **Home & Workplace Anchors**: Every promoted citizen and demographic cohort worker is assigned a spatial home coordinate (residential voxel footprint) and a workplace coordinate (farmland, mine, smithy, council hall).
- **Daily Schedules**:
  - `06:00 - 08:00`: Morning wake-up, household chores, travel to workplace.
  - `08:00 - 17:00`: Economic production (farming, mining, crafting, patrolling).
  - `17:00 - 20:00`: Socializing at the local tavern or shrine, gossip propagation, relationship updates.
  - `20:00 - 06:00`: Return home, sleep, rest.

### 2.2 Time Scale & Dual-Resolution Simulation
- **Configurable Time Scale**:
  - In standard real-time play, 1 real minute = 1 Minecraft game day (20 minutes default in vanilla Minecraft).
  - 1 game year = 360 game days $\approx$ 15 to 30 minutes of active play.
  - 75 game years = 20 to 40 hours of full campaign gameplay.
- **Time Skip Mechanism**:
  - Sleeping in a bed, fast-traveling along trade routes, or meditating advances the game by days or months instantaneously via the headless simulation tick pipeline.
- **Pre-History Length Configuration**:
  - Configurable start setting:
    - *Fresh World*: 10 years pre-history.
    - *Standard World*: 25 years pre-history.
    - *Old World*: 80 years pre-history (deep myths, mature noble houses).
    - *Ancient World*: 300+ years pre-history.

### 2.3 Dual Combat & Incident Resolvers
To guarantee that combat near the player and distant conflicts remain causally unified:
- **Detailed Resolver (Local Bubble, radius < 150 blocks around player)**:
  - Real-time physics, hitboxes, weapon damage, blocking, and line-of-sight.
  - Emits the exact same event schema (`EventType.DEATH`, `causes`, `intent`, `payload`).
- **Abstract Resolver (Distant / Strategic World)**:
  - Statistical strength, defensibility, and motivation score calculations.
  - Emits identical event schema, allowing seamless transition as the player approaches or retreats from a battle.

### 2.4 Epistemic Dialogue Generation
- Dialogue is generated dynamically from a character's **subjective beliefs and active memories**, not hard-coded trees:
  - When asked about a murder: if the character believes the wrongful rumor, they accuse the innocent target.
  - When asked about the player: characters check their `Relationship(player_0)` trust and hatred values.
  - If hatred >= 40: hostile threats or drawing weapons.
  - If trust >= 30: warm greetings, trading discounts, and protective aid.

### 2.5 Bridge Process & Protocol
- **IPC / WebSocket Bridge**:
  - Decoupled headless simulation runs as a background process or server.
  - Game client (Minecraft Fabric/Forge mod, or standalone engine) connects over a lightweight binary/JSON IPC socket.
  - Server streams local entity states and event notifications; client sends chunk deltas and player actions.
