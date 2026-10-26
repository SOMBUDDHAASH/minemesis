"""
Standalone Voxel Sandbox Game Engine for Milestone T1.

Implements full Minecraft-style game mechanics independently of the simulation:
- 3D Player Entity with position, velocity, camera pitch/yaw, and 0.6x1.8m AABB bounding box.
- 20 TPS Physics simulation: gravity, jump, ground friction, and 3D voxel collision detection/resolution.
- 3D DDA (Digital Differential Analyzer) voxel raycasting for block targeting (reach: 5.0 blocks).
- Block breaking and block placing with face normal detection.
- Chunk delta tracker maintaining all player block modifications per chunk.
- Viewport raycaster proof rendering 3D first-person perspective of the voxel world.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

from minemesis.systems.world_spec import WorldSpec
from translators.voxel.chunk_generator import ChunkData, generate_chunk
from translators.voxel.voxelspec import (
    BLOCK_AIR,
    BLOCK_BEDROCK,
    BLOCK_COBBLESTONE,
    BLOCK_DIRT,
    BLOCK_GRASS_BLOCK,
    BLOCK_NAMES,
    BLOCK_OAK_PLANKS,
    BLOCK_OAK_WOOD,
    BLOCK_OAK_LEAVES,
    BLOCK_SAND,
    BLOCK_STONE,
    BLOCK_WATER,
    SOLID_BLOCKS,
    VoxelWorldSpec,
)


@dataclass
class PlayerEntity:
    """
    Minecraft-style player entity with continuous 3D coordinates, physics, and camera.
    """
    id: str = "player_0"
    name: str = "Player"
    # Position (meters/blocks)
    x: float = 1200.0
    y: float = 80.0
    z: float = 1200.0
    # Velocity (m/s)
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    # Camera orientation (degrees)
    yaw: float = 0.0     # 0 = North (+Z), 90 = East (+X), 180 = South (-Z), 270 = West (-X)
    pitch: float = 0.0   # 0 = Horizon, +90 = Looking down, -90 = Looking up
    # Bounding Box (AABB) dimensions
    width: float = 0.6
    height: float = 1.8
    eye_height: float = 1.62
    # State flags
    on_ground: bool = False
    in_water: bool = False
    is_sprinting: bool = False
    health: float = 20.0
    selected_block: int = BLOCK_COBBLESTONE
    inventory: Dict[int, int] = field(default_factory=lambda: {
        BLOCK_COBBLESTONE: 64,
        BLOCK_OAK_PLANKS: 64,
        BLOCK_DIRT: 64,
    })

    def get_eye_position(self) -> Tuple[float, float, float]:
        return self.x, self.y + self.eye_height, self.z

    def get_look_vector(self) -> Tuple[float, float, float]:
        """Calculates normalized 3D forward look vector from yaw and pitch."""
        yaw_rad = math.radians(self.yaw)
        pitch_rad = math.radians(self.pitch)

        # Standard Minecraft camera conventions
        dx = -math.sin(yaw_rad) * math.cos(pitch_rad)
        dy = -math.sin(pitch_rad)
        dz = math.cos(yaw_rad) * math.cos(pitch_rad)

        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length > 0.0001:
            return dx / length, dy / length, dz / length
        return 0.0, 0.0, 1.0


class VoxelGameEngine:
    """
    Standalone Voxel Sandbox Engine.
    Handles player physics, voxel collisions, world streaming, and chunk delta recording.
    """

    GRAVITY = 32.0          # m/s^2
    WALK_SPEED = 4.3        # m/s
    SPRINT_SPEED = 5.6      # m/s
    JUMP_IMPULSE = 8.8      # m/s
    BLOCK_REACH = 5.0       # max blocks interaction range

    def __init__(self, world_spec: WorldSpec) -> None:
        self.world_spec = world_spec
        self.voxel_spec = VoxelWorldSpec(world_spec=world_spec)
        self.player = PlayerEntity()

        # Chunk storage and active cache
        self.chunks: Dict[Tuple[int, int], ChunkData] = {}
        # Chunk Deltas: (cx, cz) -> {(bx, by, bz): block_id}
        self.chunk_deltas: Dict[Tuple[int, int], Dict[Tuple[int, int, int], int]] = {}

        # Spawn player in the first settlement
        if self.world_spec.settlements:
            s0 = self.world_spec.settlements[0]
            sp_x, sp_z = self.voxel_spec.tile_to_block_center(s0.x, s0.y)
            sp_y = float(self.voxel_spec.get_interpolated_height(sp_x, sp_z) + 2)
            self.player.x = float(sp_x)
            self.player.y = sp_y
            self.player.z = float(sp_z)

        # Pre-load chunks around spawn
        self.ensure_chunks_around_player(radius=2)

    def get_chunk(self, cx: int, cz: int) -> ChunkData:
        """Retrieves chunk from memory or generates it on-demand."""
        key = (cx, cz)
        if key not in self.chunks:
            deltas = self.chunk_deltas.get(key, {})
            self.chunks[key] = generate_chunk(cx, cz, self.voxel_spec, deltas=deltas)
        return self.chunks[key]

    def ensure_chunks_around_player(self, radius: int = 2) -> None:
        """Loads all chunks in radius around player's current position."""
        pcx = int(self.player.x) // 16
        pcz = int(self.player.z) // 16
        for dz in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                self.get_chunk(pcx + dx, pcz + dz)

    def get_block_at(self, bx: int, by: int, bz: int) -> int:
        """Returns block ID at absolute world coordinates."""
        if by < 0 or by >= 256:
            return BLOCK_AIR
        cx = bx // 16
        cz = bz // 16
        lx = bx % 16
        lz = bz % 16
        chunk = self.get_chunk(cx, cz)
        return chunk.get_block(lx, by, lz)

    def set_block_at(self, bx: int, by: int, bz: int, block_id: int) -> bool:
        """Sets block ID at world coordinates and records chunk delta."""
        if by < 0 or by >= 256:
            return False

        cx = bx // 16
        cz = bz // 16
        lx = bx % 16
        lz = bz % 16

        chunk = self.get_chunk(cx, cz)
        chunk.set_block(lx, by, lz, block_id)

        # Record in chunk deltas
        chunk_key = (cx, cz)
        if chunk_key not in self.chunk_deltas:
            self.chunk_deltas[chunk_key] = {}
        self.chunk_deltas[chunk_key][(bx, by, bz)] = block_id
        return True

    # -------------------------------------------------------------------------
    # Physics & Voxel Collision Resolution
    # -------------------------------------------------------------------------
    def tick_physics(self, dt: float = 0.05, move_forward: float = 0.0, move_strafe: float = 0.0) -> None:
        """
        Executes one physics tick (dt = 0.05s / 20 TPS).
        Calculates acceleration, gravity, ground friction, and sweeps AABB collisions.
        """
        p = self.player

        # Check if in water
        block_at_feet = self.get_block_at(int(p.x), int(p.y), int(p.z))
        p.in_water = (block_at_feet == BLOCK_WATER)

        # Input movement vectors
        speed = self.SPRINT_SPEED if p.is_sprinting else self.WALK_SPEED
        yaw_rad = math.radians(p.yaw)

        # Forward vector
        fwd_x = -math.sin(yaw_rad)
        fwd_z = math.cos(yaw_rad)
        # Strafe right vector
        right_x = math.cos(yaw_rad)
        right_z = math.sin(yaw_rad)

        target_vx = (fwd_x * move_forward + right_x * move_strafe) * speed
        target_vz = (fwd_z * move_forward + right_z * move_strafe) * speed

        # Acceleration and friction
        friction = 0.65 if p.on_ground else 0.92
        p.vx = p.vx * friction + target_vx * (1.0 - friction)
        p.vz = p.vz * friction + target_vz * (1.0 - friction)

        # Gravity
        if p.in_water:
            p.vy = max(-4.0, p.vy - 8.0 * dt)
        else:
            p.vy = max(-32.0, p.vy - self.GRAVITY * dt)

        # Swept AABB Collision Resolution per Axis
        dx = p.vx * dt
        dy = p.vy * dt
        dz = p.vz * dt

        # 1. Resolve Y axis
        p.y += dy
        p.on_ground = False
        coll_y = self._check_voxel_collision(p.x, p.y, p.z)
        if coll_y:
            if dy < 0:
                # Landed on block
                p.y = math.ceil(p.y)
                p.on_ground = True
                p.vy = 0.0
            elif dy > 0:
                # Hit ceiling
                p.y = math.floor(p.y) - 0.01
                p.vy = 0.0

        # 2. Resolve X axis
        p.x += dx
        if self._check_voxel_collision(p.x, p.y, p.z):
            # Attempt auto-step (0.5m)
            if p.on_ground and not self._check_voxel_collision(p.x, p.y + 0.6, p.z):
                p.y += 0.6
            else:
                p.x -= dx
                p.vx = 0.0

        # 3. Resolve Z axis
        p.z += dz
        if self._check_voxel_collision(p.x, p.y, p.z):
            # Attempt auto-step (0.5m)
            if p.on_ground and not self._check_voxel_collision(p.x, p.y + 0.6, p.z):
                p.y += 0.6
            else:
                p.z -= dz
                p.vz = 0.0

    def jump(self) -> bool:
        """Executes jump if standing on solid ground or swimming."""
        if self.player.on_ground:
            self.player.vy = self.JUMP_IMPULSE
            self.player.on_ground = False
            return True
        elif self.player.in_water:
            self.player.vy = 4.0
            return True
        return False

    def _check_voxel_collision(self, px: float, py: float, pz: float) -> bool:
        """
        Tests if player's 0.6x1.8 AABB intersects any solid voxel in the world.
        """
        hw = self.player.width / 2.0  # 0.3
        min_x = int(math.floor(px - hw))
        max_x = int(math.floor(px + hw))
        min_y = int(math.floor(py))
        max_y = int(math.floor(py + self.player.height))
        min_z = int(math.floor(pz - hw))
        max_z = int(math.floor(pz + hw))

        for by in range(min_y, max_y + 1):
            for bz in range(min_z, max_z + 1):
                for bx in range(min_x, max_x + 1):
                    b = self.get_block_at(bx, by, bz)
                    if b in SOLID_BLOCKS:
                        return True
        return False

    # -------------------------------------------------------------------------
    # 3D DDA Voxel Raycasting & Block Manipulation
    # -------------------------------------------------------------------------
    def raycast_block(self, max_dist: float = 5.0) -> Optional[Tuple[Tuple[int, int, int], Tuple[int, int, int], int]]:
        """
        3D Fast Voxel Traversal (DDA) along player look vector.
        Returns:
            ((hit_x, hit_y, hit_z), (face_nx, face_ny, face_nz), block_id) or None.
        """
        ox, oy, oz = self.player.get_eye_position()
        dx, dy, dz = self.player.get_look_vector()

        x = int(math.floor(ox))
        y = int(math.floor(oy))
        z = int(math.floor(oz))

        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1
        step_z = 1 if dz > 0 else -1

        delta_x = abs(1.0 / dx) if abs(dx) > 1e-6 else 1e9
        delta_y = abs(1.0 / dy) if abs(dy) > 1e-6 else 1e9
        delta_z = abs(1.0 / dz) if abs(dz) > 1e-6 else 1e9

        max_x = ((x + 1 - ox) if dx > 0 else (ox - x)) * delta_x
        max_y = ((y + 1 - oy) if dy > 0 else (oy - y)) * delta_y
        max_z = ((z + 1 - oz) if dz > 0 else (oz - z)) * delta_z

        face_normal = (0, 1, 0)
        dist = 0.0

        while dist < max_dist:
            b = self.get_block_at(x, y, z)
            if b in SOLID_BLOCKS:
                return (x, y, z), face_normal, b

            if max_x < max_y:
                if max_x < max_z:
                    dist = max_x
                    max_x += delta_x
                    x += step_x
                    face_normal = (-step_x, 0, 0)
                else:
                    dist = max_z
                    max_z += delta_z
                    z += step_z
                    face_normal = (0, 0, -step_z)
            else:
                if max_y < max_z:
                    dist = max_y
                    max_y += delta_y
                    y += step_y
                    face_normal = (0, -step_y, 0)
                else:
                    dist = max_z
                    max_z += delta_z
                    z += step_z
                    face_normal = (0, 0, -step_z)

        return None

    def break_targeted_block(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Breaks the block player is currently aiming at.
        Returns (x, y, z, broken_block_id) or None.
        """
        hit = self.raycast_block(self.BLOCK_REACH)
        if not hit:
            return None

        (bx, by, bz), _, block_id = hit
        if block_id == BLOCK_BEDROCK:
            return None  # Unbreakable

        # Set block to air and record chunk delta
        self.set_block_at(bx, by, bz, BLOCK_AIR)
        self.player.inventory[block_id] = self.player.inventory.get(block_id, 0) + 1
        return (bx, by, bz, block_id)

    def place_block_against_target(self, block_id: Optional[int] = None) -> Optional[Tuple[int, int, int]]:
        """
        Places block adjacent to the targeted face.
        Returns (x, y, z) of placed block or None.
        """
        hit = self.raycast_block(self.BLOCK_REACH)
        if not hit:
            return None

        (bx, by, bz), (nx, ny, nz), _ = hit
        target_x = bx + nx
        target_y = by + ny
        target_z = bz + nz

        # Prevent placing inside player's own body
        hw = self.player.width / 2.0
        if (
            math.floor(self.player.x - hw) <= target_x <= math.floor(self.player.x + hw)
            and math.floor(self.player.y) <= target_y <= math.floor(self.player.y + self.player.height)
            and math.floor(self.player.z - hw) <= target_z <= math.floor(self.player.z + hw)
        ):
            return None

        bid = block_id or self.player.selected_block
        if self.player.inventory.get(bid, 0) > 0:
            self.set_block_at(target_x, target_y, target_z, bid)
            self.player.inventory[bid] -= 1
            return (target_x, target_y, target_z)

        return None

    # -------------------------------------------------------------------------
    # Visual Proof: 3D First-Person ASCII/Raycast Viewport
    # -------------------------------------------------------------------------
    def render_ascii_viewport(self, width: int = 50, height: int = 20) -> str:
        """
        Renders a real-time first-person 3D raycast perspective of the voxel world.
        Visual proof that the engine renders 3D depth, terrain contours, and player structures.
        """
        chars = {
            BLOCK_AIR: " ",
            BLOCK_STONE: "#",
            BLOCK_GRASS_BLOCK: "\"",
            BLOCK_DIRT: ".",
            BLOCK_OAK_WOOD: "|",
            BLOCK_OAK_LEAVES: "*",
            BLOCK_WATER: "~",
            BLOCK_SAND: ":",
            BLOCK_COBBLESTONE: "%",
            BLOCK_OAK_PLANKS: "=",
            BLOCK_BEDROCK: "@",
        }

        lines = []
        fov = 70.0
        half_fov = fov / 2.0

        for row in range(height):
            # Pitch angle offset
            screen_y = (row - height / 2.0) / (height / 2.0)
            pitch_offset = screen_y * 35.0

            line_chars = []
            for col in range(width):
                # Yaw angle offset
                screen_x = (col - width / 2.0) / (width / 2.0)
                yaw_offset = screen_x * half_fov

                # Ray angle
                ray_yaw = self.player.yaw + yaw_offset
                ray_pitch = self.player.pitch + pitch_offset

                # Raycast forward
                y_rad = math.radians(ray_yaw)
                p_rad = math.radians(ray_pitch)
                dx = -math.sin(y_rad) * math.cos(p_rad)
                dy = -math.sin(p_rad)
                dz = math.cos(y_rad) * math.cos(p_rad)

                # March ray
                ox, oy, oz = self.player.get_eye_position()
                hit_char = " "
                for dist in range(1, 35):
                    rx = int(ox + dx * dist)
                    ry = int(oy + dy * dist)
                    rz = int(oz + dz * dist)
                    b = self.get_block_at(rx, ry, rz)
                    if b != BLOCK_AIR:
                        hit_char = chars.get(b, "?")
                        break

                line_chars.append(hit_char)
            lines.append("".join(line_chars))

        return "\n".join(lines)

    def get_summary_state(self) -> Dict[str, Any]:
        """Returns comprehensive real-time diagnostics of the voxel engine."""
        return {
            "player_position": (round(self.player.x, 2), round(self.player.y, 2), round(self.player.z, 2)),
            "player_chunk": (int(self.player.x) // 16, int(self.player.z) // 16),
            "camera": {"yaw": round(self.player.yaw, 1), "pitch": round(self.player.pitch, 1)},
            "on_ground": self.player.on_ground,
            "in_water": self.player.in_water,
            "total_chunks_loaded": len(self.chunks),
            "total_player_block_deltas": sum(len(d) for d in self.chunk_deltas.values()),
            "inventory": dict(self.player.inventory),
        }
