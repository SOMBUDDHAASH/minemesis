"""
High-Performance 3D Voxel Debris Particle System for Minemesis Engine.
Spawns kinetic debris particles on block destruction with gravity, velocity scattering, and fading.
"""

from __future__ import annotations
import math
import random
from typing import List, Optional, Tuple
import moderngl
import numpy as np

from engine.render.camera import Camera3D
from engine.world.block_registry import registry


PARTICLE_VERT_SHADER = """
#version 330 core
layout (location = 0) in vec3 in_position;
layout (location = 1) in vec4 in_color;

uniform mat4 u_proj;
uniform mat4 u_view;

out vec4 v_color;

void main() {
    v_color = in_color;
    gl_Position = u_proj * u_view * vec4(in_position, 1.0);
}
"""

PARTICLE_FRAG_SHADER = """
#version 330 core
in vec4 v_color;
out vec4 fragColor;

void main() {
    fragColor = v_color;
}
"""


# Dominant palette colors for block particle debris (RGB)
BLOCK_PARTICLE_COLORS = {
    1: (0.75, 0.73, 0.68),   # Limestone
    2: (0.18, 0.18, 0.20),   # Basalt
    3: (0.62, 0.55, 0.52),   # Granite
    18: (0.45, 0.32, 0.22),  # Dirt
    19: (0.35, 0.62, 0.22),  # Grass
    21: (0.82, 0.76, 0.55),  # Sand
    51: (0.42, 0.30, 0.18),  # Oak Log
    52: (0.68, 0.52, 0.34),  # Oak Planks
    59: (0.28, 0.52, 0.20),  # Oak Leaves
    89: (0.58, 0.58, 0.58),  # Stone Bricks
    97: (0.85, 0.92, 0.96),  # Glass
    100: (0.55, 0.40, 0.28), # Bookshelf
    101: (0.60, 0.45, 0.30), # Lectern
    136: (0.25, 0.50, 0.85), # Water
}


class Particle:
    __slots__ = ("x", "y", "z", "vx", "vy", "vz", "size", "r", "g", "b", "alpha", "life", "max_life")

    def __init__(
        self,
        x: float, y: float, z: float,
        vx: float, vy: float, vz: float,
        color: Tuple[float, float, float],
        size: float = 0.08,
        life: float = 0.55,
    ) -> None:
        self.x = x
        self.y = y
        self.z = z
        self.vx = vx
        self.vy = vy
        self.vz = vz
        self.size = size
        self.r, self.g, self.b = color
        self.alpha = 1.0
        self.life = life
        self.max_life = life


class ParticleSystem:
    """Manages active block break debris particles and renders them in 3D ModernGL."""

    def __init__(self, ctx: moderngl.Context, max_particles: int = 512) -> None:
        self.ctx = ctx
        self.max_particles = max_particles
        self.particles: List[Particle] = []

        self.program = ctx.program(
            vertex_shader=PARTICLE_VERT_SHADER,
            fragment_shader=PARTICLE_FRAG_SHADER,
        )

        # Dynamic VBO for camera-facing particle quads (6 vertices per quad, 7 floats per vertex)
        self.vbo = ctx.buffer(reserve=max_particles * 6 * 7 * 4, dynamic=True)
        self.vao = ctx.vertex_array(
            self.program,
            [(self.vbo, "3f 4f", "in_position", "in_color")],
        )

    def spawn_block_break(self, bx: int, by: int, bz: int, block_id: int, count: int = 14) -> None:
        """Spawns an explosive burst of micro-voxel debris when a block is mined."""
        col = BLOCK_PARTICLE_COLORS.get(block_id, (0.6, 0.58, 0.55))
        cx = bx + 0.5
        cy = by + 0.5
        cz = bz + 0.5

        for _ in range(count):
            if len(self.particles) >= self.max_particles:
                self.particles.pop(0)

            ox = random.uniform(-0.35, 0.35)
            oy = random.uniform(-0.35, 0.35)
            oz = random.uniform(-0.35, 0.35)

            # Scatter velocities in sphere with upward bias
            speed = random.uniform(1.8, 3.8)
            theta = random.uniform(0.0, 2.0 * math.pi)
            phi = random.uniform(-0.3, 0.8)

            vx = math.cos(theta) * math.cos(phi) * speed
            vy = math.sin(phi) * speed + random.uniform(1.5, 3.2)
            vz = math.sin(theta) * math.cos(phi) * speed

            # Slight color jitter
            c_jitter = random.uniform(0.85, 1.15)
            pr = min(1.0, col[0] * c_jitter)
            pg = min(1.0, col[1] * c_jitter)
            pb = min(1.0, col[2] * c_jitter)

            p = Particle(
                x=cx + ox, y=cy + oy, z=cz + oz,
                vx=vx, vy=vy, vz=vz,
                color=(pr, pg, pb),
                size=random.uniform(0.06, 0.12),
                life=random.uniform(0.40, 0.70),
            )
            self.particles.append(p)

    def update(self, dt: float) -> None:
        """Updates particle kinematics with gravity, drag, and alpha fading."""
        alive: List[Particle] = []
        GRAVITY = 24.0

        for p in self.particles:
            p.life -= dt
            if p.life <= 0.0:
                continue

            p.vy -= GRAVITY * dt
            p.vx *= max(0.0, 1.0 - 1.5 * dt)
            p.vz *= max(0.0, 1.0 - 1.5 * dt)

            p.x += p.vx * dt
            p.y += p.vy * dt
            p.z += p.vz * dt

            # Fade alpha smoothly toward end of life
            p.alpha = max(0.0, min(1.0, p.life / (p.max_life * 0.5)))
            alive.append(p)

        self.particles = alive

    def render(self, camera: Camera3D) -> None:
        """Renders camera-facing particle quads."""
        if not self.particles:
            return

        verts: List[float] = []
        # Extract camera right and up vectors for billboarding
        fwd_x, fwd_y, fwd_z = camera.get_forward_vector()
        yaw_rad = math.radians(camera.yaw)
        right_x = math.cos(yaw_rad)
        right_z = math.sin(yaw_rad)
        up_x, up_y, up_z = 0.0, 1.0, 0.0

        for p in self.particles:
            s = p.size
            r, g, b, a = p.r, p.g, p.b, p.alpha

            # 4 billboard corners
            p0 = (p.x - right_x * s - up_x * s, p.y - up_y * s, p.z - right_z * s - up_z * s)
            p1 = (p.x + right_x * s - up_x * s, p.y - up_y * s, p.z + right_z * s - up_z * s)
            p2 = (p.x + right_x * s + up_x * s, p.y + up_y * s, p.z + right_z * s + up_z * s)
            p3 = (p.x - right_x * s + up_x * s, p.y + up_y * s, p.z - right_z * s + up_z * s)

            # 2 triangles (6 vertices)
            verts.extend([
                p0[0], p0[1], p0[2], r, g, b, a,
                p1[0], p1[1], p1[2], r, g, b, a,
                p2[0], p2[1], p2[2], r, g, b, a,

                p0[0], p0[1], p0[2], r, g, b, a,
                p2[0], p2[1], p2[2], r, g, b, a,
                p3[0], p3[1], p3[2], r, g, b, a,
            ])

        if not verts:
            return

        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.BLEND)

        self.program["u_proj"].write(np.ascontiguousarray(camera.projection_matrix.T, dtype=np.float32).tobytes())
        self.program["u_view"].write(np.ascontiguousarray(camera.get_view_matrix().T, dtype=np.float32).tobytes())

        raw_bytes = np.array(verts, dtype=np.float32).tobytes()
        self.vbo.write(raw_bytes)
        self.vao.render(moderngl.TRIANGLES, vertices=len(verts) // 7)
