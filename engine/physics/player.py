"""
Player Entity Physics, AABB Voxel Collision Resolution, and 3D DDA Raycaster.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Dict, Optional, Tuple

from engine.world.block_registry import registry
from engine.world.chunk_manager import ChunkManager


@dataclass
class PlayerController:
    """
    3D Player Controller with Continuous Physics and Swept AABB Collision.
    """
    x: float = 1200.0
    y: float = 85.0
    z: float = 1200.0

    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0

    yaw: float = 0.0      # Degrees
    pitch: float = 0.0    # Degrees

    width: float = 0.6
    height: float = 1.8
    eye_height: float = 1.62

    on_ground: bool = False
    in_water: bool = False
    is_sprinting: bool = False

    # Hotbar & Inventory
    selected_slot: int = 0
    hotbar: list[int] = field(default_factory=lambda: [
        1,   # Limestone
        52,  # Oak Planks
        18,  # Loam Dirt
        19,  # Grass Turf
        3,   # Granite
        51,  # Oak Log
        89,  # Cut Stone Bricks
        21,  # Fine Sand
        97,  # Glass Pane
    ])
    inventory: Dict[int, int] = field(default_factory=lambda: {
        1: 64,
        52: 64,
        18: 64,
        19: 64,
        3: 64,
        51: 64,
        89: 64,
        21: 64,
        97: 64,
    })

    GRAVITY = 32.0          # m/s^2
    WALK_SPEED = 4.3        # m/s
    SPRINT_SPEED = 6.2      # m/s
    JUMP_IMPULSE = 8.8      # m/s
    BLOCK_REACH = 5.0       # max blocks reach

    def get_eye_position(self) -> Tuple[float, float, float]:
        return self.x, self.y + self.eye_height, self.z

    def get_look_vector(self) -> Tuple[float, float, float]:
        yaw_rad = math.radians(self.yaw)
        pitch_rad = math.radians(self.pitch)
        dx = -math.sin(yaw_rad) * math.cos(pitch_rad)
        dy = math.sin(pitch_rad)
        dz = math.cos(yaw_rad) * math.cos(pitch_rad)
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length > 0.0001:
            return dx / length, dy / length, dz / length
        return 0.0, 0.0, 1.0

    def tick_physics(
        self,
        chunk_mgr: ChunkManager,
        dt: float = 0.02,
        move_fwd: float = 0.0,
        move_strafe: float = 0.0,
    ) -> None:
        # Check water status
        block_at_feet = chunk_mgr.get_block_at(int(self.x), int(self.y), int(self.z))
        b_def = registry.get_by_id(block_at_feet)
        self.in_water = (b_def and b_def.category == "fluid")

        # Movement speeds
        speed = self.SPRINT_SPEED if self.is_sprinting else self.WALK_SPEED
        yaw_rad = math.radians(self.yaw)

        # Forward & Strafe vectors
        fwd_x = -math.sin(yaw_rad)
        fwd_z = math.cos(yaw_rad)
        right_x = math.cos(yaw_rad)
        right_z = math.sin(yaw_rad)

        target_vx = (fwd_x * move_fwd + right_x * move_strafe) * speed
        target_vz = (fwd_z * move_fwd + right_z * move_strafe) * speed

        friction = 0.60 if self.on_ground else 0.90
        self.vx = self.vx * friction + target_vx * (1.0 - friction)
        self.vz = self.vz * friction + target_vz * (1.0 - friction)

        # Gravity & vertical velocity
        if self.in_water:
            self.vy = max(-3.5, self.vy - 10.0 * dt)
        else:
            self.vy = max(-36.0, self.vy - self.GRAVITY * dt)

        # Swept AABB collision resolution per axis
        dx = self.vx * dt
        dy = self.vy * dt
        dz = self.vz * dt

        # 1. Y Axis
        self.y += dy
        self.on_ground = False
        if self._check_collision(chunk_mgr, self.x, self.y, self.z):
            if dy < 0:
                self.y = math.ceil(self.y)
                self.on_ground = True
                self.vy = 0.0
            elif dy > 0:
                self.y = math.floor(self.y) - 0.01
                self.vy = 0.0

        # 2. X Axis (with auto-step 0.5m)
        self.x += dx
        if self._check_collision(chunk_mgr, self.x, self.y, self.z):
            if self.on_ground and not self._check_collision(chunk_mgr, self.x, self.y + 0.6, self.z):
                self.y += 0.6
            else:
                self.x -= dx
                self.vx = 0.0

        # 3. Z Axis (with auto-step 0.5m)
        self.z += dz
        if self._check_collision(chunk_mgr, self.x, self.y, self.z):
            if self.on_ground and not self._check_collision(chunk_mgr, self.x, self.y + 0.6, self.z):
                self.y += 0.6
            else:
                self.z -= dz
                self.vz = 0.0

    def jump(self) -> bool:
        if self.on_ground:
            self.vy = self.JUMP_IMPULSE
            self.on_ground = False
            return True
        elif self.in_water:
            self.vy = 4.5
            return True
        return False

    def _check_collision(self, chunk_mgr: ChunkManager, px: float, py: float, pz: float) -> bool:
        hw = self.width / 2.0
        min_x = int(math.floor(px - hw))
        max_x = int(math.floor(px + hw))
        min_y = int(math.floor(py))
        max_y = int(math.floor(py + self.height))
        min_z = int(math.floor(pz - hw))
        max_z = int(math.floor(pz + hw))

        for by in range(min_y, max_y + 1):
            for bz in range(min_z, max_z + 1):
                for bx in range(min_x, max_x + 1):
                    bid = chunk_mgr.get_block_at(bx, by, bz)
                    if registry.is_solid(bid):
                        return True
        return False

    # -------------------------------------------------------------------------
    # 3D DDA Raycaster
    # -------------------------------------------------------------------------
    def raycast_block(
        self,
        chunk_mgr: ChunkManager,
        max_dist: float = 5.0,
    ) -> Optional[Tuple[Tuple[int, int, int], Tuple[int, int, int], int]]:
        """
        Fast 3D Voxel Traversal (DDA) along camera look vector.
        Returns ((hit_x, hit_y, hit_z), (normal_x, normal_y, normal_z), block_id) or None.
        """
        ox, oy, oz = self.get_eye_position()
        dx, dy, dz = self.get_look_vector()

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
            bid = chunk_mgr.get_block_at(x, y, z)
            if registry.is_solid(bid):
                return (x, y, z), face_normal, bid

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

    def break_targeted_block(self, chunk_mgr: ChunkManager) -> Optional[Tuple[int, int, int, int]]:
        hit = self.raycast_block(chunk_mgr, self.BLOCK_REACH)
        if not hit:
            return None
        (bx, by, bz), _, bid = hit
        if bid == 2:  # Basalt bedrock
            return None  # Unbreakable
        chunk_mgr.set_block_at(bx, by, bz, 0)
        self.inventory[bid] = self.inventory.get(bid, 0) + 1
        return (bx, by, bz, bid)

    def place_block_against_target(self, chunk_mgr: ChunkManager) -> Optional[Tuple[int, int, int]]:
        hit = self.raycast_block(chunk_mgr, self.BLOCK_REACH)
        if not hit:
            return None
        (bx, by, bz), (nx, ny, nz), _ = hit
        tx = bx + nx
        ty = by + ny
        tz = bz + nz

        # Prevent placing inside player AABB
        hw = self.width / 2.0
        if (
            math.floor(self.x - hw) <= tx <= math.floor(self.x + hw)
            and math.floor(self.y) <= ty <= math.floor(self.y + self.height)
            and math.floor(self.z - hw) <= tz <= math.floor(self.z + hw)
        ):
            return None

        bid = self.hotbar[self.selected_slot]
        if self.inventory.get(bid, 0) > 0:
            chunk_mgr.set_block_at(tx, ty, tz, bid)
            self.inventory[bid] -= 1
            return (tx, ty, tz)

        return None
