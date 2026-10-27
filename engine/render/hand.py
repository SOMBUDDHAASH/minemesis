"""
First-Person Player Arm & Held Block Punch Swing Renderer for Minemesis Engine.
Renders an embodied first-person arm with idle breathing sway, stride bobbing, and kinetic punch swings.
"""

from __future__ import annotations
import math
from typing import Optional, Tuple
import moderngl
import numpy as np

from engine.render.camera import Camera3D
from engine.render.texture import TextureAtlas
from engine.world.block_registry import registry


HAND_VERT_SHADER = """
#version 330 core
layout (location = 0) in vec3 in_position;
layout (location = 1) in vec2 in_texcoord;
layout (location = 2) in vec3 in_normal;
layout (location = 3) in float in_ao;

uniform mat4 u_proj;
uniform mat4 u_view;
uniform mat4 u_model;

out vec2 v_texcoord;
out vec3 v_normal;
out float v_ao;

void main() {
    v_texcoord = in_texcoord;
    v_normal = in_normal;
    v_ao = in_ao;
    gl_Position = u_proj * u_view * u_model * vec4(in_position, 1.0);
}
"""

HAND_FRAG_SHADER = """
#version 330 core
in vec2 v_texcoord;
in vec3 v_normal;
in float v_ao;

uniform sampler2D u_texture;
uniform vec3 u_light_dir;
uniform vec3 u_light_color;
uniform vec3 u_ambient_color;

out vec4 fragColor;

void main() {
    vec4 tex = texture(u_texture, v_texcoord);
    if (tex.a < 0.1) discard;

    vec3 norm = normalize(v_normal);
    float diff = max(dot(norm, -u_light_dir), 0.0);
    vec3 lighting = u_ambient_color + u_light_color * diff;
    lighting *= v_ao;

    fragColor = vec4(tex.rgb * lighting, tex.a);
}
"""


class FirstPersonHandRenderer:
    """Renders the player's right hand and held item with punch swing kinetics."""

    def __init__(self, ctx: moderngl.Context, atlas: TextureAtlas) -> None:
        self.ctx = ctx
        self.atlas = atlas
        self.program = ctx.program(
            vertex_shader=HAND_VERT_SHADER,
            fragment_shader=HAND_FRAG_SHADER,
        )

        # Build arm mesh geometry
        verts = self._create_arm_geometry()
        self.vbo = ctx.buffer(np.array(verts, dtype=np.float32).tobytes())
        self.vao = ctx.vertex_array(
            self.program,
            [(self.vbo, "3f 2f 3f 1f", "in_position", "in_texcoord", "in_normal", "in_ao")],
        )
        self.vertex_count = len(verts) // 9

    def _create_arm_geometry(self) -> list[float]:
        v: list[float] = []
        skin_uv = self.atlas.get_uv_rect("npc_skin") if self.atlas else (0.5, 0.5, 0.5, 0.5)
        sleeve_uv = self.atlas.get_uv_rect("npc_body_Laborer") if self.atlas else skin_uv

        def add_box(min_pt, max_pt, uv_rect):
            u0, v0, u1, v1 = uv_rect
            x0, y0, z0 = min_pt
            x1, y1, z1 = max_pt
            faces = [
                ((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1), (0.0, 1.0, 0.0)),
                ((x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0), (0.0, -1.0, 0.0)),
                ((x1, y0, z1), (x0, y0, z1), (x0, y1, z1), (x1, y1, z1), (0.0, 0.0, 1.0)),
                ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (0.0, 0.0, -1.0)),
                ((x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0), (1.0, 0.0, 0.0)),
                ((x0, y0, z1), (x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (-1.0, 0.0, 0.0)),
            ]
            for p0, p1, p2, p3, norm in faces:
                nx, ny, nz = norm
                v.extend([
                    p0[0], p0[1], p0[2], u0, v1, nx, ny, nz, 1.0,
                    p1[0], p1[1], p1[2], u1, v1, nx, ny, nz, 1.0,
                    p2[0], p2[1], p2[2], u1, v0, nx, ny, nz, 1.0,

                    p0[0], p0[1], p0[2], u0, v1, nx, ny, nz, 1.0,
                    p2[0], p2[1], p2[2], u1, v0, nx, ny, nz, 1.0,
                    p3[0], p3[1], p3[2], u0, v0, nx, ny, nz, 1.0,
                ])

        # Hand box: 0.12 x 0.12 x 0.28
        add_box((-0.06, -0.06, -0.28), (0.06, 0.06, 0.0), skin_uv)
        # Forearm sleeve: 0.14 x 0.14 x 0.35
        add_box((-0.07, -0.07, 0.0), (0.07, 0.07, 0.35), sleeve_uv)

        return v

    def render(
        self,
        camera: Camera3D,
        punch_progress: float = 0.0,
        bob_cycle: float = 0.0,
        is_moving: bool = False,
        held_block_id: Optional[int] = None,
    ) -> None:
        """Renders first-person arm in screen space aligned with camera look orientation."""
        eye_x, eye_y, eye_z = camera.x, camera.y, camera.z
        yaw_rad = math.radians(camera.yaw)
        pitch_rad = math.radians(camera.pitch)

        # Camera axes
        fwd_x = -math.sin(yaw_rad) * math.cos(pitch_rad)
        fwd_y = math.sin(pitch_rad)
        fwd_z = math.cos(yaw_rad) * math.cos(pitch_rad)

        right_x = math.cos(yaw_rad)
        right_y = 0.0
        right_z = math.sin(yaw_rad)

        up_x = right_y * fwd_z - right_z * fwd_y
        up_y = right_z * fwd_x - right_x * fwd_z
        up_z = right_x * fwd_y - right_y * fwd_x

        # 1. Base offset relative to eye: lower right
        offset_right = 0.28
        offset_down = -0.24
        offset_fwd = 0.42

        # 2. Dynamic movement sway (breathing + stride)
        if is_moving:
            offset_right += math.cos(bob_cycle * 0.5) * 0.015
            offset_down += math.sin(bob_cycle) * 0.02
        else:
            # Subtle breathing
            offset_down += math.sin(bob_cycle * 0.8) * 0.005

        # 3. Kinetic punch swing (sinusoidal downward arc)
        swing_angle = 0.0
        if punch_progress > 0.001:
            sin_swing = math.sin(punch_progress * math.pi)
            swing_angle = sin_swing * 45.0
            offset_fwd += sin_swing * 0.12
            offset_down -= sin_swing * 0.06
            offset_right -= sin_swing * 0.08

        # Compute arm world position
        arm_x = eye_x + right_x * offset_right + up_y * offset_down * 0.0 + (0.0 * up_x) + fwd_x * offset_fwd
        arm_y = eye_y + offset_down + fwd_y * offset_fwd
        arm_z = eye_z + right_z * offset_right + fwd_z * offset_fwd

        # Build Model Matrix
        model = np.identity(4, dtype=np.float32)
        model[0, 3] = arm_x
        model[1, 3] = arm_y
        model[2, 3] = arm_z

        # Orientation: Rotate by yaw, pitch, and punch swing
        total_yaw = camera.yaw + 15.0 - (swing_angle * 0.4)
        total_pitch = camera.pitch - 15.0 - swing_angle

        rad_y = math.radians(total_yaw)
        cos_y, sin_y = math.cos(rad_y), math.sin(rad_y)
        rot_y = np.array([
            [cos_y, 0.0, sin_y, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [-sin_y, 0.0, cos_y, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ], dtype=np.float32)

        rad_p = math.radians(total_pitch)
        cos_p, sin_p = math.cos(rad_p), math.sin(rad_p)
        rot_p = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, cos_p, -sin_p, 0.0],
            [0.0, sin_p, cos_p, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ], dtype=np.float32)

        final_model = np.matmul(model, np.matmul(rot_y, rot_p))

        # Render pass
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.depth_func = "<="

        self.atlas.bind(unit=0)
        self.program["u_texture"].value = 0
        self.program["u_proj"].write(np.ascontiguousarray(camera.projection_matrix.T, dtype=np.float32).tobytes())
        self.program["u_view"].write(np.ascontiguousarray(camera.get_view_matrix().T, dtype=np.float32).tobytes())
        self.program["u_model"].write(np.ascontiguousarray(final_model.T, dtype=np.float32).tobytes())

        self.program["u_light_dir"].value = (0.4, -0.8, 0.4)
        self.program["u_light_color"].value = (1.0, 0.98, 0.92)
        self.program["u_ambient_color"].value = (0.45, 0.48, 0.52)

        self.vao.render(moderngl.TRIANGLES, vertices=self.vertex_count)
