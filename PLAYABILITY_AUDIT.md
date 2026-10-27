# Minemesis Playability Audit & Game Feel Recovery Plan

> [!IMPORTANT]
> **THE FUNDAMENTAL AUDIT QUESTION**  
> *"Would a player choose to walk around this world for 10 minutes even if the civilization simulation was disabled?"*  
> **Honest Answer Today: NO.**  
> The history simulation has depth, but the game feel is currently that of a rigid, sterile CAD viewer. A player does not feel weight, velocity, impact, resistance, or immersion.  
> As instructed: **Stop inventing systems from scratch. Blatantly copy proven architectures from 15+ years of open-source voxel game development.**

---

## 1. Deep Subsystem Benchmark Matrix

| Subsystem | Minemesis (Current) | Luanti (Minetest) | Cube 2 / Sauerbraten | Vintage Story | Veloren | Target Minemesis Adaptation |
|---|---|---|---|---|---|---|
| **Movement & Inertia** | Binary velocity: $v = \text{target}$ or static friction lerp. Zero momentum. | Quake-style vector friction + acceleration (`friction = 8.0`, `accelerate = 10.0`). Directional preservation in air. | Gold-standard fast FPS swept collision; Wall sliding along surface tangent planes. | High friction on terrain, momentum on ice/mud, physical body weight. | Continuous Rapier physics character capsule with physics impulse damping. | **Quake / Luanti kinematic physics**: Wishdir vector projection, ground friction, air control, and wall tangent sliding. |
| **Camera Feel** | Rigid translation locked to head coordinates. Instant starts/stops. | View bobbing (`bob_cycle` sine wave for pitch, roll, and Y), dynamic FOV shift on sprint ($+8^\circ$). | Smooth mouse acceleration curve, raw mouse delta accumulator, zero frame latency. | Head-bob linked to stride frequency, subtle tilt on strafe, breathing idle sway. | Interpolated third/first person camera with spring-damper easing. | **Luanti View Bobbing & Dynamic FOV**: Striding sinusoidal bob (Y & Roll), sprint FOV lerp ($75^\circ \to 83^\circ$), and landing impact dip. |
| **Mining Feel** | Instant 1-click disappearance. Zero resistance. Feels like an editor `delete`. | Break timer based on tool & block hardness (`dig_time`), 5-stage crack textures, punch cooldown. | Fast weapon recoil, immediate debris explosion, impact sparks. | Tool tier vs rock hardness, crack propagation animation, fatigue, stone clinking sounds. | Beam/strike raycast with damage numbers, particle sparks, and sound reverberation. | **Luanti Hardness Break Timer & Debris**: Hold-click break duration ($0.3\text{s} - 1.5\text{s}$), progressive face cracks ($0\% \to 100\%$), first-person hand punch swing, and 12-voxel debris burst. |
| **Block Placement** | Silent instant spawn. No hand swing. No audio/visual confirmation. | Hand swing animation, block placement sound, immediate face-normal snap, collision check against player capsule. | Instant visual feedback with muzzle flash / impact tracer. | Block placement animation, tactile click, preview ghost with orientation cues. | Material placement animation with particle puff. | **Tactile Placement**: First-person arm punch swing, placement puff particle, and ghost preview box. |
| **Inventory UX** | Static text table. No mouse drag-and-drop. Number keys only. | Mouse cursor interaction, hover tooltips, drag-and-drop stacks, right-click split, shift-click quick move. | Fast weapon wheel, instant binding. | Visual container slots, hover stats card, drag-and-drop cursor stack, sound feedback. | Rich ECS slot grid, drag-and-drop, category filters, item rarity styling. | **Luanti-Style Interactive GUI**: Mouse cursor picking, `cursor_stack` holding, drag-and-drop slot transfer, right-click single drop, and rich hover tooltips. |
| **NPC Navigation** | Straight-line displacement towards target. Halts permanently on 2-block walls. | Voxel node A* pathfinding, obstacle ray lookahead, step-up traversal. | Fast waypoint navigation, dynamic avoidance cones. | Navmesh / 3D voxel flood-fill pathfinding, pack movement, terrain hugging. | Rich behavior trees, obstacle avoidance steering, crowd flocking. | **Obstacle Lookahead Steering**: Forward whisker raycasts ($\pm 35^\circ$) to steer around obstacles, with step-up jump impulse when obstructed. |
| **Visual Feedback** | Static flat terrain. No particle systems, no dynamic light flash. | Particle spawners for digging, walking, and weather (`particle_spawner`). | Volumetric particle fountains, dynamic entity shadows. | Ambient wind swaying foliage, falling leaves, dust motes, block breaking fragments. | Rich GPU particle effects, lighting embers, water splashes. | **ModernGL Voxel Particle Engine**: GPU instanced 3D voxel debris bursts with gravity and bounce physics. |

---

## 2. Hard Priority Implementation Roadmap

```
[TIER A: KINETIC MOVEMENT & CAMERA FEEL]
  ├── 1. Quake/Luanti Acceleration & Friction Curves (Wishdir, Ground Friction 8.0, Air Control)
  ├── 2. Swept Wall-Sliding (Project velocity along obstacle surface plane instead of stopping dead)
  ├── 3. Dynamic View Bobbing (Sine stride oscillation on camera Y and roll)
  ├── 4. Dynamic Sprint FOV (Smooth exponential lerp from 75° to 83°)
  └── 5. Jump & Landing Impact Dip (Elastic compression impulse on touchdown)
            ↓
[TIER B: MINING, PUNCHING & TACTILE INTERACTION]
  ├── 1. Continuous Mining Hardness Timer (Hold Left Click to accumulate dig progress 0.0 -> 1.0)
  ├── 2. Face Crack Overlay Stages (Progressive visual breakdown on targeted block)
  ├── 3. First-Person Hand / Tool Punch Swing Animation (Parametric sin/cos arm swing)
  └── 4. Block Debris Particle Explosion (12-16 textured micro-voxels scattered with velocity & gravity)
            ↓
[TIER C: INTERACTIVE MOUSE INVENTORY UX]
  ├── 1. Mouse Cursor Slot Picking (Pick up stack onto cursor)
  ├── 2. Drag & Drop Stack Transfer (Drop stack into empty or matching slot)
  ├── 3. Right-Click Split / Single Item Drop (Distribute 1 item into slot)
  ├── 4. Hover Tooltip Card (Renders item name, category, hardness, stack count)
  └── 5. Shift-Click Quick Transfer (Instant transfer between 27-storage and 9-hotbar)
            ↓
[TIER D: NPC NAVIGATION & GROUNDING]
  ├── 1. Whisker Ray Obstacle Lookahead (Steer left/right around 2-block walls and trees)
  └── 2. Smooth Ground Conformance & Foot-Planting
```

---

## 3. Detailed Technical Blueprint: Blatant Copy Specifications

### 3.1 Tier A: Quake/Luanti Movement Physics (Blatantly Copied)
In Luanti (`src/client/localplayer.cpp`) and Quake (`pmove.c`):
Velocity is never set directly. It uses acceleration and friction vectors:
```python
# 1. Ground Friction:
speed = length(vel_horizontal)
if speed > 0.001:
    drop = speed * FRICTION * dt
    new_speed = max(0.0, speed - drop)
    vel_horizontal *= (new_speed / speed)

# 2. Acceleration towards wishdir:
wish_speed = SPRINT_SPEED if sprinting else WALK_SPEED
current_speed = dot(vel_horizontal, wish_dir)
add_speed = wish_speed - current_speed
if add_speed > 0:
    accel_speed = ACCELERATION * wish_speed * dt
    vel_horizontal += wish_dir * min(add_speed, accel_speed)
```
- **Wall Sliding**: When colliding with a wall along X or Z, instead of setting `vx = 0` or `vz = 0`, the velocity along the non-colliding axis is preserved, allowing buttery smooth sliding along walls!

### 3.2 Tier A: View Bobbing & Landing Dip
In Luanti (`src/client/camera.cpp`):
```python
if on_ground and speed > 0.1:
    bob_timer += dt * speed * 3.2
    bob_y = math.sin(bob_timer) * 0.05
    bob_roll = math.cos(bob_timer * 0.5) * 0.4  # Slight head roll
else:
    bob_timer = 0.0
    bob_y = lerp(bob_y, 0.0, dt * 10.0)
    bob_roll = lerp(bob_roll, 0.0, dt * 10.0)
```
- When landing (`not was_on_ground and on_ground`), apply a $-0.12$m downward dip that springs back over $0.15$s.

### 3.3 Tier B: Continuous Mining Hardness & Crack Stages
In Luanti (`src/client/game.cpp`):
Blocks are NOT destroyed in a single frame.
- Every block definition has `hardness` ($0.2$ for dirt/sand, $0.6$ for planks, $1.2$ for stone, $2.5$ for ores).
- While the player holds Left Mouse Button on the targeted block:
  $$\Delta_{\text{progress}} = \frac{dt}{\text{hardness}}$$
  $$\text{dig\_progress} \in [0.0, 1.0]$$
- When `dig_progress >= 1.0`: block breaks, drops item into inventory, and spawns a burst of 12 debris voxels.
- While mining: draw progressive crack lines on the targeted face (at $20\%$, $40\%$, $60\%$, $80\%$, $100\%$).
- If the player looks away or releases the button, progress resets.

### 3.4 Tier B: First-Person Hand / Tool Punch Swing Animation
- When left clicking (mining) or right clicking (placing):
  Trigger a $0.25$s sinusoidal punch swing:
  $$\text{swing\_angle} = \sin(\text{progress} \cdot \pi) \cdot 35^\circ$$
- Renders the hand / held block in the bottom-right corner of the camera swinging forward and downward to hit the targeted voxel.

### 3.5 Tier B: Debris Particle Burst Engine
- When a block breaks, spawn 12 micro-cubes ($0.15 \times 0.15 \times 0.15$):
  - Initial position: $hit\_pos + (0.5, 0.5, 0.5)$
  - Initial velocities: random sphere distribution $v \in [-2.5, +2.5]$ m/s with $+3.0$ m/s upward bias.
  - Gravity: $28.0$ m/s$^2$.
  - Lifetime: $0.6$ seconds, fading alpha.

### 3.6 Tier C: Interactive Drag-and-Drop Inventory GUI
In Luanti (`src/gui/guiFormSpecMenu.cpp`):
- When `[I]` or `[Tab]` is pressed, mouse cursor is freed.
- Mouse hover over any slot ($3 \times 9$ storage, 9 hotbar, 4 equipment):
  - Draws a bright gold highlight border around the hovered slot.
  - Displays a crisp hover tooltip card with item name, category, hardness, and count.
- **Left Click on slot**:
  - If `cursor_stack` is empty: pick up the stack from the slot into `cursor_stack`.
  - If `cursor_stack` has items: deposit into slot (or combine stacks if same block ID).
- **Right Click on slot**:
  - If `cursor_stack` has items: deposit exactly 1 item into the slot.
  - If `cursor_stack` is empty: pick up half the stack (split).
- **Shift-Click on slot**:
  - Instantly transfers between hotbar and main storage.

### 3.7 Tier D: NPC Obstacle Avoidance Steering
In Veloren / Luanti entity steering:
- When NPC moves towards target:
  - Cast 2 whisker rays ahead: left $+35^\circ$, right $-35^\circ$.
  - If the left whisker detects an obstacle, steer right: `yaw -= 45 * dt`.
  - If the right whisker detects an obstacle, steer left: `yaw += 45 * dt`.
  - If directly facing a 1-block obstacle, jump (`vy = 8.0`) to step up.
  - This prevents NPCs from walking endlessly into trees, house corners, or walls.

---

## 4. Immediate Execution Plan

We will implement this strictly along the Hard Priority Order:
1. **Tier A**: Movement physics (Quake acceleration, ground friction, wall slide, view bobbing, sprint FOV, landing compression).
2. **Tier B**: Mining progress accumulator, 5-stage face crack overlay, hand punch swing animation, and voxel debris burst.
3. **Tier C**: Interactive mouse drag-and-drop inventory GUI, hover tooltips, and shift-click quick move.
4. **Tier D**: NPC whisker obstacle avoidance steering.
5. **Verification**: Executable rebuild and hands-on validation.
