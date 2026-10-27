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
    "Scholar": {"body": (0.20, 0.35, 0.65), "legs": (0.15, 0.18, 0.25), "hair": (0.35, 0.25, 0.15)},
    "Priest": {"body": (0.80, 0.85, 0.90), "legs": (0.30, 0.20, 0.35), "hair": (0.80, 0.80, 0.80)},
    "Smith": {"body": (0.45, 0.35, 0.25), "legs": (0.20, 0.20, 0.22), "hair": (0.15, 0.15, 0.15)},
    "Farmer": {"body": (0.40, 0.60, 0.30), "legs": (0.35, 0.25, 0.15), "hair": (0.50, 0.35, 0.20)},
    "Guard": {"body": (0.55, 0.58, 0.62), "legs": (0.30, 0.32, 0.35), "hair": (0.20, 0.15, 0.10)},
    "Citizen": {"body": (0.60, 0.45, 0.35), "legs": (0.25, 0.22, 0.20), "hair": (0.30, 0.20, 0.15)},
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
    """Individual simulated character living in the 3D voxel world."""

    def __init__(
        self,
        character_id: str,
        name: str,
        profession: str = "Citizen",
        faith: str = "Common Faith",
        settlement_id: str = "set_0",
        home_pos: Tuple[float, float, float] = (1200.0, 80.0, 1200.0),
        work_pos: Tuple[float, float, float] = (1210.0, 80.0, 1210.0),
        shrine_pos: Tuple[float, float, float] = (1220.0, 80.0, 1200.0),
        well_pos: Tuple[float, float, float] = (1205.0, 80.0, 1205.0),
    ) -> None:
        self.character_id = character_id
        self.name = name
        self.profession = profession
        self.faith = faith
        self.settlement_id = settlement_id

        self.home_pos = home_pos
        self.work_pos = work_pos
        self.shrine_pos = shrine_pos
        self.well_pos = well_pos

        self.x = home_pos[0]
        self.y = home_pos[1]
        self.z = home_pos[2]
        self.yaw: float = 0.0
        self.target_pos = work_pos

        # Organic AI state
        self.current_activity: str = "Working"
        self.health: float = 20.0
        self.is_hostile: bool = False
        self.is_fleeing: bool = False
        self.affinity_to_player: float = 0.0

    def update_schedule(self, time_of_day_progress: float, dt: float) -> None:
        """Evaluates daily schedule and moves toward current goal."""
        # 0.0 to 0.25 (Night 00:00 - 06:00): Sleep at home
        if time_of_day_progress < 0.25 or time_of_day_progress > 0.90:
            self.current_activity = "Sleeping at Home"
            self.target_pos = self.home_pos
        # 0.25 to 0.50 (Morning 06:00 - 12:00): Work at profession
        elif time_of_day_progress < 0.50:
            self.current_activity = f"Laboring as {self.profession}"
            self.target_pos = self.work_pos
        # 0.50 to 0.60 (Midday 12:00 - 14:00): Socializing at Well/Market
        elif time_of_day_progress < 0.60:
            self.current_activity = "Socializing at Village Well"
            self.target_pos = self.well_pos
        # 0.60 to 0.75 (Afternoon 14:00 - 18:00): Work
        elif time_of_day_progress < 0.75:
            self.current_activity = f"Working ({self.profession})"
            self.target_pos = self.work_pos
        # 0.75 to 0.90 (Evening 18:00 - 22:00): Worship at Shrine
        else:
            self.current_activity = f"Worshiping at {self.faith} Shrine"
            self.target_pos = self.shrine_pos

        # Move smoothly toward target position
        tx, ty, tz = self.target_pos
        dx = tx - self.x
        dz = tz - self.z
        dist = math.sqrt(dx * dx + dz * dz)

        if dist > 0.5:
            speed = 2.0 * dt
            self.x += (dx / dist) * min(speed, dist)
            self.z += (dz / dist) * min(speed, dist)
            self.yaw = math.degrees(math.atan2(-dx, dz))

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
