"""
Voxel Humanoid NPC Entity with Personality, Lineage, and Visual Styling.
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple
import moderngl
import numpy as np


# Palette colors for NPC professions (RGB floats)
PROFESSION_COLORS = {
    "Chief": {"body": (0.85, 0.65, 0.15), "legs": (0.25, 0.15, 0.10), "hair": (0.75, 0.75, 0.75)},
    "Elder": {"body": (0.70, 0.60, 0.30), "legs": (0.25, 0.20, 0.15), "hair": (0.90, 0.90, 0.90)},
    "Scholar": {"body": (0.20, 0.35, 0.65), "legs": (0.15, 0.18, 0.25), "hair": (0.35, 0.25, 0.15)},
    "Scribe": {"body": (0.25, 0.40, 0.70), "legs": (0.15, 0.18, 0.25), "hair": (0.30, 0.20, 0.15)},
    "Priest": {"body": (0.80, 0.85, 0.90), "legs": (0.30, 0.20, 0.35), "hair": (0.80, 0.80, 0.80)},
    "Smith": {"body": (0.45, 0.35, 0.25), "legs": (0.20, 0.20, 0.22), "hair": (0.15, 0.15, 0.15)},
    "Blacksmith": {"body": (0.45, 0.35, 0.25), "legs": (0.20, 0.20, 0.22), "hair": (0.15, 0.15, 0.15)},
    "Farmer": {"body": (0.40, 0.60, 0.30), "legs": (0.35, 0.25, 0.15), "hair": (0.50, 0.35, 0.20)},
    "Woodcutter": {"body": (0.50, 0.40, 0.25), "legs": (0.30, 0.25, 0.20), "hair": (0.40, 0.25, 0.15)},
    "Laborer": {"body": (0.48, 0.45, 0.38), "legs": (0.25, 0.22, 0.20), "hair": (0.35, 0.25, 0.15)},
    "Merchant": {"body": (0.75, 0.50, 0.20), "legs": (0.20, 0.20, 0.30), "hair": (0.40, 0.30, 0.20)},
    "Weaver": {"body": (0.65, 0.35, 0.50), "legs": (0.25, 0.20, 0.25), "hair": (0.45, 0.30, 0.20)},
    "Guard": {"body": (0.55, 0.58, 0.62), "legs": (0.30, 0.32, 0.35), "hair": (0.20, 0.15, 0.10)},
    "Soldier": {"body": (0.55, 0.58, 0.62), "legs": (0.30, 0.32, 0.35), "hair": (0.20, 0.15, 0.10)},
    "Citizen": {"body": (0.60, 0.45, 0.35), "legs": (0.25, 0.22, 0.20), "hair": (0.30, 0.20, 0.15)},
    "Commoner": {"body": (0.60, 0.45, 0.35), "legs": (0.25, 0.22, 0.20), "hair": (0.30, 0.20, 0.15)},
}


class VoxelHumanoidMesh:
    """Procedural 3D Voxel Humanoid Mesh for ModernGL (Head, Torso, Arms, Legs)."""

    def __init__(self, ctx: moderngl.Context, program: moderngl.Program, atlas: any = None) -> None:
        self.ctx = ctx
        self.program = program
        self.atlas = atlas
        self.vaos: Dict[str, Tuple[moderngl.VertexArray, int]] = {}
        self._build_all_profession_meshes()

    def _build_all_profession_meshes(self) -> None:
        for prof_name, cols in PROFESSION_COLORS.items():
            verts = self._create_humanoid_geometry(prof_name, cols)
            vbo = self.ctx.buffer(np.array(verts, dtype=np.float32).tobytes())
            vao = self.ctx.vertex_array(
                self.program,
                [(vbo, "3f 2f 3f 1f", "in_position", "in_texcoord", "in_normal", "in_ao")],
            )
            self.vaos[prof_name] = (vao, len(verts) // 9)

    def _create_humanoid_geometry(self, prof_name: str, cols: dict) -> list[float]:
        v: list[float] = []

        if self.atlas:
            skin_uv = self.atlas.get_uv_rect("npc_skin")
            hair_uv = self.atlas.get_uv_rect(f"npc_hair_{prof_name}")
            body_uv = self.atlas.get_uv_rect(f"npc_body_{prof_name}")
            legs_uv = self.atlas.get_uv_rect(f"npc_legs_{prof_name}")
        else:
            skin_uv = (0.5, 0.5, 0.5, 0.5)
            hair_uv = (0.5, 0.5, 0.5, 0.5)
            body_uv = (0.5, 0.5, 0.5, 0.5)
            legs_uv = (0.5, 0.5, 0.5, 0.5)

        def add_box(min_pt, max_pt, uv_rect):
            u0, v0, u1, v1 = uv_rect
            x0, y0, z0 = min_pt
            x1, y1, z1 = max_pt
            # 6 faces of box
            faces = [
                # Top
                ((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1), (0.0, 1.0, 0.0)),
                # Bottom
                ((x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0), (0.0, -1.0, 0.0)),
                # Front (+Z)
                ((x1, y0, z1), (x0, y0, z1), (x0, y1, z1), (x1, y1, z1), (0.0, 0.0, 1.0)),
                # Back (-Z)
                ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (0.0, 0.0, -1.0)),
                # Right (+X)
                ((x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0), (1.0, 0.0, 0.0)),
                # Left (-X)
                ((x0, y0, z1), (x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (-1.0, 0.0, 0.0)),
            ]
            for p0, p1, p2, p3, norm in faces:
                nx, ny, nz = norm
                # Quad 2 triangles with UV mapping
                v.extend([
                    p0[0], p0[1], p0[2], u0, v1, nx, ny, nz, 1.0,
                    p1[0], p1[1], p1[2], u1, v1, nx, ny, nz, 1.0,
                    p2[0], p2[1], p2[2], u1, v0, nx, ny, nz, 1.0,

                    p0[0], p0[1], p0[2], u0, v1, nx, ny, nz, 1.0,
                    p2[0], p2[1], p2[2], u1, v0, nx, ny, nz, 1.0,
                    p3[0], p3[1], p3[2], u0, v0, nx, ny, nz, 1.0,
                ])

        # 1. Head (0.4 x 0.4 x 0.4) at y: 1.4 to 1.8
        add_box((-0.2, 1.4, -0.2), (0.2, 1.8, 0.2), skin_uv)

        # Hair cap
        add_box((-0.21, 1.65, -0.21), (0.21, 1.85, 0.21), hair_uv)

        # 2. Torso (0.45 x 0.65 x 0.25) at y: 0.75 to 1.4
        add_box((-0.22, 0.75, -0.12), (0.22, 1.4, 0.12), body_uv)

        # 3. Arms (0.15 x 0.6 x 0.15) at left & right
        add_box((-0.38, 0.75, -0.08), (-0.23, 1.35, 0.08), skin_uv)
        add_box((0.23, 0.75, -0.08), (0.38, 1.35, 0.08), skin_uv)

        # 4. Legs (0.18 x 0.75 x 0.18) at y: 0.0 to 0.75
        add_box((-0.20, 0.0, -0.09), (-0.02, 0.75, 0.09), legs_uv)
        add_box((0.02, 0.0, -0.09), (0.20, 0.75, 0.09), legs_uv)

        return v


class NPC:
    """Individual simulated character living in the 3D voxel world with deep kinship and social memory."""

    def __init__(
        self,
        character_id: str,
        name: str,
        first_name: str = "",
        last_name: str = "",
        family_id: str = "",
        age_years: int = 30,
        sex: str = "M",
        profession: str = "Citizen",
        faith: str = "Common Faith",
        settlement_id: str = "set_0",
        settlement_name: str = "Deepwick",
        # Kinship
        spouse_id: Optional[str] = None,
        spouse_name: Optional[str] = None,
        father_id: Optional[str] = None,
        mother_id: Optional[str] = None,
        children_ids: Optional[List[str]] = None,
        sibling_ids: Optional[List[str]] = None,
        # Feuds & Rivalries
        rival_family_ids: Optional[List[str]] = None,
        rival_family_names: Optional[List[str]] = None,
        # Positions in settlement
        home_pos: Tuple[float, float, float] = (1200.0, 80.0, 1200.0),
        work_pos: Tuple[float, float, float] = (1210.0, 80.0, 1210.0),
        shrine_pos: Tuple[float, float, float] = (1220.0, 80.0, 1200.0),
        tavern_pos: Tuple[float, float, float] = (1215.0, 80.0, 1205.0),
        well_pos: Tuple[float, float, float] = (1205.0, 80.0, 1205.0),
        guard_patrol_points: Optional[List[Tuple[float, float, float]]] = None,
    ) -> None:
        self.character_id = character_id
        self.name = name
        self.first_name = first_name or (name.split()[0] if name else "Citizen")
        self.last_name = last_name or (name.split()[-1] if len(name.split()) > 1 else "Commoner")
        self.family_id = family_id or self.last_name
        self.age_years = age_years
        self.sex = sex
        self.profession = profession
        self.faith = faith
        self.settlement_id = settlement_id
        self.settlement_name = settlement_name

        # Kinship relationships
        self.spouse_id = spouse_id
        self.spouse_name = spouse_name
        self.father_id = father_id
        self.mother_id = mother_id
        self.children_ids: List[str] = children_ids or []
        self.sibling_ids: List[str] = sibling_ids or []
        self.kin_names: Dict[str, str] = {}

        # Feuds
        self.rival_family_ids: List[str] = rival_family_ids or []
        self.rival_family_names: List[str] = rival_family_names or []

        # Positions
        self.home_pos = home_pos
        self.work_pos = work_pos
        self.shrine_pos = shrine_pos
        self.tavern_pos = tavern_pos
        self.well_pos = well_pos
        self.guard_patrol_points: List[Tuple[float, float, float]] = guard_patrol_points or [well_pos, home_pos, work_pos]
        self.patrol_index: int = 0
        self.patrol_timer: float = 0.0

        # Physical location & Terrain Physics
        self.x = home_pos[0]
        self.y = home_pos[1]
        self.z = home_pos[2]
        self.vy: float = 0.0
        self.is_grounded: bool = True
        self.GRAVITY: float = 24.0          # m/s^2
        self.STEP_HEIGHT: float = 1.1       # Can step up 1.1m slopes/steps
        self.SNAP_DISTANCE: float = 0.15    # Foot snap threshold to ground surface
        self.yaw: float = 0.0
        self.target_pos = work_pos

        # Behavioral & Social State
        self.is_guard: bool = profession in ("Guard", "Soldier")
        self.current_activity: str = "Resting at Home"
        self.health: float = 20.0
        self.alive: bool = True
        self.is_hostile: bool = False
        self.is_fleeing: bool = False
        self.affinity_to_player: float = 0.0
        self.grief_state: Optional[str] = None

    def kin_react_to_violence(self, victim: NPC, player_pos: Tuple[float, float, float]) -> str:
        """Triggers direct psychological reaction if victim is spouse, child, or sibling."""
        if victim.character_id == self.character_id:
            return ""

        # 1. Spouse reaction
        if self.spouse_id == victim.character_id:
            self.affinity_to_player = -100.0
            self.grief_state = f"Mourning slain spouse {victim.name}!"
            self.current_activity = f"Weeping in horror over spouse {victim.name}!"
            self.is_fleeing = True
            self.target_pos = self.home_pos
            return f"{self.name} screams: 'NO! My beloved {victim.name} is slain!'"

        # 2. Child reaction (witnessing parent killed)
        if (self.character_id in victim.children_ids) or (self.father_id == victim.character_id) or (self.mother_id == victim.character_id):
            self.affinity_to_player = -100.0
            self.grief_state = f"Traumatized: Parent {victim.name} murdered!"
            self.current_activity = f"Fleeing in terror from murderer of parent {victim.name}!"
            self.is_fleeing = True
            self.target_pos = self.home_pos
            return f"{self.name} weeps in terror: 'Mother! Father! The stranger murdered {victim.name}!'"

        # 3. Parent reaction (witnessing child killed)
        if (victim.character_id in self.children_ids) or (victim.father_id == self.character_id) or (victim.mother_id == self.character_id):
            self.affinity_to_player = -100.0
            self.grief_state = f"Heartbroken: Child {victim.name} slain!"
            self.current_activity = f"Cursing the heavens over slain child {victim.name}!"
            self.is_hostile = True
            self.target_pos = player_pos
            return f"{self.name} cries out in agonizing grief: 'My child {victim.name}! Blood will answer for blood!'"

        # 4. Sibling reaction
        if (victim.character_id in self.sibling_ids) or (self.character_id in victim.sibling_ids) or (
            (self.father_id and self.father_id == victim.father_id) or
            (self.mother_id and self.mother_id == victim.mother_id)
        ):
            self.affinity_to_player = -100.0
            self.grief_state = f"Vengeful: Sibling {victim.name} murdered!"
            self.current_activity = f"Seeking blood-vengeance for sibling {victim.name}!"
            self.is_hostile = True
            self.target_pos = player_pos
            return f"{self.name} draws steel: 'Clan {self.last_name} will have your head for slaying my kin {victim.name}!'"

        # 5. Guard duty
        if self.is_guard:
            self.is_hostile = True
            self.current_activity = f"HUNTING OUTLAW: Avenging murdered citizen {victim.name}!"
            self.target_pos = player_pos
            return f"Guard {self.name} shouts: 'Halt in the name of {self.settlement_name}! Slay the murderer!'"

        return ""

    def _avoid_obstacles(self, chunk_mgr: any, dir_x: float, dir_z: float) -> Tuple[float, float]:
        """Whisker Obstacle Avoidance (Veloren / Luanti steering model)."""
        if chunk_mgr is None:
            return dir_x, dir_z

        ahead_x = self.x + dir_x * 1.2
        ahead_z = self.z + dir_z * 1.2
        ahead_y = chunk_mgr.get_highest_solid_y(ahead_x, ahead_z)

        # If blocked by obstacle taller than step height (e.g. 2-block wall, tree, cottage)
        if ahead_y - self.y > self.STEP_HEIGHT:
            base_angle = math.atan2(dir_z, dir_x)
            # Whisker Left (+40 deg)
            w_left_a = base_angle + 0.70
            wl_x = self.x + math.cos(w_left_a) * 1.2
            wl_z = self.z + math.sin(w_left_a) * 1.2
            wl_y = chunk_mgr.get_highest_solid_y(wl_x, wl_z)

            # Whisker Right (-40 deg)
            w_right_a = base_angle - 0.70
            wr_x = self.x + math.cos(w_right_a) * 1.2
            wr_z = self.z + math.sin(w_right_a) * 1.2
            wr_y = chunk_mgr.get_highest_solid_y(wr_x, wr_z)

            if wl_y - self.y <= self.STEP_HEIGHT:
                return math.cos(w_left_a), math.sin(w_left_a)
            elif wr_y - self.y <= self.STEP_HEIGHT:
                return math.cos(w_right_a), math.sin(w_right_a)
            else:
                return math.cos(base_angle + 1.57), math.sin(base_angle + 1.57)

        return dir_x, dir_z

    def update_physics(self, chunk_mgr: any, dt: float) -> None:
        """
        Conforms NPC position to voxel terrain:
        - Downward gravity acceleration when in air
        - Auto-stepping up to 1.1m slopes
        - Precise foot-snapping to ground surface
        - Absolute prevention of floating or falling through terrain
        """
        if not self.alive or chunk_mgr is None:
            return

        ground_y = chunk_mgr.get_highest_solid_y(self.x, self.z, max_y=int(self.y + 4))

        # Check step-up condition (walking up a 1-block slope/ledge <= 1.1m)
        delta_y = ground_y - self.y
        if 0.0 < delta_y <= self.STEP_HEIGHT:
            self.y = ground_y
            self.vy = 0.0
            self.is_grounded = True
            return

        # Check step-down condition (walking down a 1-block slope/ledge <= 1.1m while grounded)
        if self.is_grounded and 0.0 <= -delta_y <= self.STEP_HEIGHT:
            self.y = ground_y
            self.vy = 0.0
            self.is_grounded = True
            return

        # Air physics (falling under gravity off ledge > 1.1m)
        if self.y > ground_y + self.SNAP_DISTANCE:
            self.vy = max(-30.0, self.vy - self.GRAVITY * dt)
            next_y = self.y + self.vy * dt
            if next_y <= ground_y:
                self.y = ground_y
                self.vy = 0.0
                self.is_grounded = True
            else:
                self.y = next_y
                self.is_grounded = False
        else:
            # On ground or within snap distance or sunken into slope
            self.y = ground_y
            self.vy = 0.0
            self.is_grounded = True

    def update_schedule(
        self,
        time_of_day_progress: float,
        dt: float,
        chunk_mgr: Optional[any] = None,
    ) -> None:
        """Evaluates diurnal schedule, curfew, grief, and moves toward current goal with terrain physics."""
        if not self.alive:
            return

        # Handle persistent grief or hostility first
        if self.grief_state:
            self.current_activity = self.grief_state
            if self.is_fleeing:
                self.target_pos = self.home_pos
        elif self.is_hostile:
            # Continues pursuing target_pos (player)
            pass
        else:
            # --- 24-HOUR DIURNAL SCHEDULE ---
            # 0.0 to 0.25 (Night 00:00 - 06:00) & 0.88 to 1.0 (Late Night 21:00 - 24:00): Curfew
            if time_of_day_progress < 0.25 or time_of_day_progress > 0.88:
                if self.is_guard:
                    self.current_activity = "Night Patrol (Enforcing Curfew & Guarding Perimeter)"
                    self.patrol_timer += dt
                    if self.patrol_timer > 8.0:
                        self.patrol_timer = 0.0
                        self.patrol_index = (self.patrol_index + 1) % len(self.guard_patrol_points)
                    self.target_pos = self.guard_patrol_points[self.patrol_index]
                else:
                    self.current_activity = "Sleeping in Bed (Night Curfew)"
                    self.target_pos = self.home_pos

            # 0.25 to 0.38 (Dawn & Morning Gathering 06:00 - 09:00): Village Well & Square
            elif time_of_day_progress < 0.38:
                if self.is_guard:
                    self.current_activity = "Morning Guard Duty at Settlement Gate"
                    self.target_pos = self.work_pos
                else:
                    self.current_activity = f"Greeting kin at Village Well ({self.last_name} Clan)"
                    self.target_pos = self.well_pos

            # 0.38 to 0.70 (Day Labor 09:00 - 17:00): Working at Trade
            elif time_of_day_progress < 0.70:
                if self.profession in ("Smith", "Blacksmith"):
                    self.current_activity = "Forging iron plowshares & weapons at the Anvil"
                elif self.profession == "Farmer":
                    self.current_activity = "Tending crops & granary in the fields"
                elif self.profession == "Woodcutter":
                    self.current_activity = "Hewing logs & timber for settlement hearths"
                elif self.profession in ("Priest", "Scholar", "Scribe"):
                    self.current_activity = f"Transcribing annals of {self.settlement_name} & scriptures"
                elif self.is_guard:
                    self.current_activity = "Inspecting perimeter & deterring bandit raiders"
                elif self.profession in ("Chief", "Elder"):
                    self.current_activity = "Holding council & judging disputes in Great Hall"
                else:
                    self.current_activity = f"Laboring at trade as {self.profession}"
                self.target_pos = self.work_pos

            # 0.70 to 0.88 (Evening 17:00 - 21:00): Shrine Worship or Tavern Fellowship
            else:
                if self.profession in ("Priest", "Elder") or (hash(self.character_id) % 3 == 0):
                    self.current_activity = f"Evening prayers to {self.faith} at the Stone Shrine"
                    self.target_pos = self.shrine_pos
                elif self.is_guard:
                    self.current_activity = "Preparing night lanterns for curfew watch"
                    self.target_pos = self.work_pos
                else:
                    self.current_activity = "Socializing & drinking ale at Village Tavern"
                    self.target_pos = self.tavern_pos

        # Move smoothly toward target position with whisker lookahead obstacle avoidance
        tx, ty, tz = self.target_pos
        dx = tx - self.x
        dz = tz - self.z
        dist = math.sqrt(dx * dx + dz * dz)

        if dist > 0.6:
            move_speed = 3.5 * dt if (self.is_fleeing or self.is_hostile) else 1.8 * dt
            dir_x = dx / dist
            dir_z = dz / dist

            # Whisker Obstacle Avoidance (Veloren / Luanti steering model)
            dir_x, dir_z = self._avoid_obstacles(chunk_mgr, dir_x, dir_z)

            self.x += dir_x * min(move_speed, dist)
            self.z += dir_z * min(move_speed, dist)
            self.yaw = math.degrees(math.atan2(-dir_x, dir_z))

        # Terrain physics conform
        if chunk_mgr is not None:
            self.update_physics(chunk_mgr, dt)

    def render(
        self,
        humanoid_mesh: VoxelHumanoidMesh,
        shader: any,
        camera: any,
    ) -> None:
        """Renders 3D humanoid mesh with position and yaw rotation."""
        model = np.identity(4, dtype=np.float32)

        # Translation
        model[0, 3] = self.x
        model[1, 3] = self.y
        model[2, 3] = self.z

        # Yaw Rotation
        yaw_rad = math.radians(self.yaw)
        cos_y, sin_y = math.cos(yaw_rad), math.sin(yaw_rad)
        rot_y = np.array([
            [cos_y, 0.0, sin_y, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [-sin_y, 0.0, cos_y, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ], dtype=np.float32)

        final_model = np.matmul(model, rot_y)
        shader.set_uniform_mat4("u_model", final_model)

        prof_key = self.profession if self.profession in PROFESSION_COLORS else "Citizen"
        if prof_key in humanoid_mesh.vaos:
            vao, count = humanoid_mesh.vaos[prof_key]
            vao.render(moderngl.TRIANGLES, vertices=count)
