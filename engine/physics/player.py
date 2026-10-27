"""
Player Entity Physics, AABB Voxel Collision Resolution, and 3D DDA Raycaster with Soft Cone.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional, Tuple

from engine.inventory.inventory import Inventory
from engine.inventory.item_stack import ItemStack
from engine.world.block_registry import registry
from engine.world.chunk_manager import ChunkManager


@dataclass
class PlayerController:
    """
    3D Player Controller with Continuous Physics, Swept AABB Collision,
    1.1m Slope Stepping, and Soft Cone Block Targeting.
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
    fly_mode: bool = False  # Strictly False by default (Player Bound by Gravity)

    # Minemesis Inventory v1
    inventory: Inventory = field(default_factory=Inventory)

    GRAVITY = 32.0          # m/s^2
    WALK_SPEED = 4.3        # m/s
    SPRINT_SPEED = 6.2      # m/s
    JUMP_IMPULSE = 8.8      # m/s
    BLOCK_REACH = 5.0       # max blocks reach

    # -------------------------------------------------------------------------
    # Backward Compatibility Proxies for Hotbar and Selected Slot
    # -------------------------------------------------------------------------
    @property
    def selected_slot(self) -> int:
        return self.inventory.selected_slot

    @selected_slot.setter
    def selected_slot(self, val: int) -> None:
        self.inventory.selected_slot = max(0, min(self.inventory.HOTBAR_SIZE - 1, int(val)))

    @property
    def hotbar(self) -> List[int]:
        return [s.block_id if s else 0 for s in self.inventory.hotbar]

    @hotbar.setter
    def hotbar(self, ids: List[int]) -> None:
        for i, bid in enumerate(ids[:self.inventory.HOTBAR_SIZE]):
            if bid > 0:
                self.inventory.hotbar[i] = ItemStack(block_id=bid, count=64)
            else:
                self.inventory.hotbar[i] = None

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
        self.in_water = (b_def is not None and b_def.category == "fluid")

        # -----------------------------------------------------------------
        # Debug Fly Mode (Bypasses Gravity and Ground Collision)
        # -----------------------------------------------------------------
        if self.fly_mode:
            speed = (self.SPRINT_SPEED * 2.5) if self.is_sprinting else (self.WALK_SPEED * 2.0)
            yaw_rad = math.radians(self.yaw)
            fwd_x = -math.sin(yaw_rad)
            fwd_z = math.cos(yaw_rad)
            right_x = math.cos(yaw_rad)
            right_z = math.sin(yaw_rad)

            self.vx = (fwd_x * move_fwd + right_x * move_strafe) * speed
            self.vz = (fwd_z * move_fwd + right_z * move_strafe) * speed
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.z += self.vz * dt
            self.on_ground = False
            return

        # -----------------------------------------------------------------
        # Standard Terrestrial Voxel Physics
        # -----------------------------------------------------------------
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

        # 1. Y Axis (Continuous gravity resolution)
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

        # 2. X Axis (with auto-step 1.1m for 1-block slopes)
        self.x += dx
        if self._check_collision(chunk_mgr, self.x, self.y, self.z):
            if self.on_ground and not self._check_collision(chunk_mgr, self.x, self.y + 1.1, self.z):
                self.y += 1.1
                # Settle down to obstacle top
                for _ in range(11):
                    if not self._check_collision(chunk_mgr, self.x, self.y - 0.1, self.z):
                        self.y -= 0.1
                    else:
                        break
            else:
                self.x -= dx
                self.vx = 0.0

        # 3. Z Axis (with auto-step 1.1m for 1-block slopes)
        self.z += dz
        if self._check_collision(chunk_mgr, self.x, self.y, self.z):
            if self.on_ground and not self._check_collision(chunk_mgr, self.x, self.y + 1.1, self.z):
                self.y += 1.1
                # Settle down to obstacle top
                for _ in range(11):
                    if not self._check_collision(chunk_mgr, self.x, self.y - 0.1, self.z):
                        self.y -= 0.1
                    else:
                        break
            else:
                self.z -= dz
                self.vz = 0.0

    def jump(self) -> bool:
        if self.fly_mode:
            self.vy = 8.0
            return True
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
        min_x = int(math.floor(px - hw + 0.02))
        max_x = int(math.floor(px + hw - 0.02))
        min_y = int(math.floor(py + 0.01))
        max_y = int(math.floor(py + self.height - 0.02))
        min_z = int(math.floor(pz - hw + 0.02))
        max_z = int(math.floor(pz + hw - 0.02))

        for by in range(min_y, max_y + 1):
            for bz in range(min_z, max_z + 1):
                for bx in range(min_x, max_x + 1):
                    bid = chunk_mgr.get_block_at(bx, by, bz)
                    if registry.is_solid(bid):
                        return True
        return False

    # -------------------------------------------------------------------------
    # 3D DDA Traversal & Soft Cone of Inquiry
    # -------------------------------------------------------------------------
    def _dda_traverse(
        self,
        chunk_mgr: ChunkManager,
        ox: float, oy: float, oz: float,
        dx: float, dy: float, dz: float,
        max_dist: float,
    ) -> Optional[Tuple[Tuple[int, int, int], Tuple[int, int, int], int, float]]:
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
                return (x, y, z), face_normal, bid, dist

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

    def raycast_block(
        self,
        chunk_mgr: ChunkManager,
        max_dist: float = 5.0,
    ) -> Optional[Tuple[Tuple[int, int, int], Tuple[int, int, int], int]]:
        """
        Raycasts along camera look vector with soft target volume / cone of inquiry.
        Returns ((hit_x, hit_y, hit_z), (normal_x, normal_y, normal_z), block_id) or None.
        """
        ox, oy, oz = self.get_eye_position()
        dx, dy, dz = self.get_look_vector()

        # 1. Primary central ray
        hit = self._dda_traverse(chunk_mgr, ox, oy, oz, dx, dy, dz, max_dist)
        if hit:
            return hit[0], hit[1], hit[2]

        # 2. Soft Target Volume (Interaction Cone: +/- 0.8 deg auxiliary rays)
        cone_offsets = [
            (-0.8, 0.0),
            (0.8, 0.0),
            (0.0, -0.8),
            (0.0, 0.8),
        ]
        best_hit = None
        min_dist = max_dist + 1.0

        for d_yaw, d_pitch in cone_offsets:
            yaw_rad = math.radians(self.yaw + d_yaw)
            pitch_rad = math.radians(self.pitch + d_pitch)
            adx = -math.sin(yaw_rad) * math.cos(pitch_rad)
            ady = math.sin(pitch_rad)
            adz = math.cos(yaw_rad) * math.cos(pitch_rad)
            alen = math.sqrt(adx * adx + ady * ady + adz * adz)
            if alen > 0.0001:
                adx, ady, adz = adx / alen, ady / alen, adz / alen

            c_hit = self._dda_traverse(chunk_mgr, ox, oy, oz, adx, ady, adz, max_dist)
            if c_hit and c_hit[3] < min_dist:
                min_dist = c_hit[3]
                best_hit = (c_hit[0], c_hit[1], c_hit[2])

        return best_hit

    def break_targeted_block(self, chunk_mgr: ChunkManager) -> Optional[Tuple[int, int, int, int]]:
        hit = self.raycast_block(chunk_mgr, self.BLOCK_REACH)
        if not hit:
            return None
        (bx, by, bz), _, bid = hit
        if bid == 2:  # Basalt bedrock
            return None  # Unbreakable
        chunk_mgr.set_block_at(bx, by, bz, 0)
        self.inventory.add_item(bid, 1)
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

        active_item = self.inventory.get_active_item()
        if not active_item or active_item.count <= 0:
            return None

        bid = self.inventory.consume_active_item()
        if bid is not None:
            chunk_mgr.set_block_at(tx, ty, tz, bid)
            return (tx, ty, tz)

        return None
