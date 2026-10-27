"""
Main Application Engine Loop and Stage E0 Packaging Spike for Minemesis.
"""

from __future__ import annotations
import math
import os
from pathlib import Path
import sys
import time
from typing import Optional
import glfw
import numpy as np
import psutil
from PIL import Image

from engine.core.window import Window
from engine.core.timer import FrameTimer
from engine.render.context import RenderContext
from engine.render.camera import Camera3D
from engine.render.shader import (
    ShaderProgram,
    BASIC_VOXEL_VERTEX_SHADER,
    BASIC_VOXEL_FRAGMENT_SHADER,
)
from engine.render.texture import TextureAtlas
from engine.render.cube import VoxelCubeMesh
from engine.ui.overlay import OverlayRenderer


class EngineApp:
    """
    Main Game Engine Application.
    Orchestrates GLFW windowing, ModernGL OpenGL 3.3 Core rendering, and game loops.
    """

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        title: str = "Minemesis Voxel Civilization Simulator",
        visible: bool = True,
        vsync: bool = True,
    ) -> None:
        self.width = width
        self.height = height
        self.process = psutil.Process(os.getpid())

        # 1. Initialize Window & Input
        self.window = Window(width, height, title, vsync=vsync, visible=visible)
        self.timer = FrameTimer()

        # 2. ModernGL Render Context
        self.render_ctx = RenderContext(width, height)
        self.ctx = self.render_ctx.ctx

        # 3. Procedural Texture Atlas
        self.atlas = TextureAtlas(self.ctx)

        # 4. Shader Program
        self.shader = ShaderProgram(self.ctx, BASIC_VOXEL_VERTEX_SHADER, BASIC_VOXEL_FRAGMENT_SHADER)

        # 5. 3D Camera
        self.camera = Camera3D(
            fov=65.0,
            aspect=width / float(height),
            near=0.1,
            far=500.0,
            x=0.0,
            y=1.2,
            z=-3.2,
        )
        self.camera.yaw = 0.0
        self.camera.pitch = -18.0

        # 6. Geometry: Textured Voxel Cube
        self.cube_mesh = VoxelCubeMesh(self.ctx, self.atlas)
        self.cube_vao = self.cube_mesh.create_vao(self.shader.program)

        # 7. UI Overlay Renderer
        self.overlay = OverlayRenderer(self.ctx, width, height)

        # Window resize binding
        self.window.resize_callback = self._on_resize

        # Cube rotation state
        self.cube_rot_x: float = 0.0
        self.cube_rot_y: float = 0.0

        # Memory tracking
        self.peak_rss_mb: float = 0.0

    def _on_resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.render_ctx.set_viewport(0, 0, width, height)
        self.camera.update_projection(width / float(height))
        self.overlay.update_projection(width, height)

    def capture_screenshot(self, output_path: str | Path) -> None:
        """Captures current framebuffer pixels to PNG file."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)

        raw = self.ctx.fbo.read(components=3, alignment=1)
        img = Image.frombytes("RGB", (self.width, self.height), raw)
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        img.save(p)

    def run_frame(self) -> None:
        """Executes a single frame: input, simulation/animation, 3D rendering, and HUD overlay."""
        dt = self.timer.tick()

        # Input handling
        if self.window.input.is_key_pressed(glfw.KEY_ESCAPE):
            self.window.close()

        # Update cube rotation animation
        self.cube_rot_x += 35.0 * dt
        self.cube_rot_y += 50.0 * dt

        # Memory profiling
        mem_info = self.process.memory_info()
        rss_mb = mem_info.rss / (1024.0 * 1024.0)
        if rss_mb > self.peak_rss_mb:
            self.peak_rss_mb = rss_mb

        # 1. Clear frame (Atmospheric sky blue)
        self.render_ctx.clear(0.48, 0.72, 0.98, 1.0)
        self.render_ctx.enable_depth_test(True)
        self.render_ctx.enable_cull_face(True)

        # 2. Render 3D Spinning Cube
        self.atlas.bind(unit=0)
        self.shader.set_uniform_int("u_texture", 0)

        # View and Projection matrices
        self.shader.set_uniform_mat4("u_proj", self.camera.projection_matrix)
        self.shader.set_uniform_mat4("u_view", self.camera.get_view_matrix())

        # Model matrix with rotation
        rx = math.radians(self.cube_rot_x)
        ry = math.radians(self.cube_rot_y)

        # Compute model matrix
        cx_c, sx_s = math.cos(rx), math.sin(rx)
        cy_c, sy_s = math.cos(ry), math.sin(ry)

        rot_x = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, cx_c, -sx_s, 0.0],
            [0.0, sx_s, cx_c, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ], dtype=np.float32)

        rot_y = np.array([
            [cy_c, 0.0, sy_s, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [-sy_s, 0.0, cy_c, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ], dtype=np.float32)

        model_mat = np.matmul(rot_y, rot_x)
        self.shader.set_uniform_mat4("u_model", model_mat)

        # Directional sun lighting and fog
        self.shader.set_uniform_vec3("u_light_dir", 0.4, -0.8, 0.4)
        self.shader.set_uniform_vec3("u_light_color", 1.0, 0.96, 0.88)
        self.shader.set_uniform_vec3("u_ambient_color", 0.38, 0.42, 0.48)
        self.shader.set_uniform_vec3("u_fog_color", 0.48, 0.72, 0.98)
        self.shader.set_uniform_float("u_fog_start", 20.0)
        self.shader.set_uniform_float("u_fog_end", 120.0)
        self.shader.set_uniform_vec3("u_camera_pos", self.camera.x, self.camera.y, self.camera.z)

        # Draw Cube
        self.cube_mesh.render(self.cube_vao)

        # 3. Render 2D Profiling HUD Overlay
        lines = [
            f"MINEMESIS ENGINE v0.6.0 [STAGE E0 SPIKE]",
            f"FPS: {self.timer.fps:.1f}  (Frame Time: {dt * 1000.0:.2f} ms)",
            f"Memory RSS: {rss_mb:.1f} MB  (Peak: {self.peak_rss_mb:.1f} MB)",
            f"GPU: {self.render_ctx.renderer}",
            f"Driver: {self.render_ctx.vendor} ({self.render_ctx.gl_version.split(' ')[0]})",
            f"Resolution: {self.width}x{self.height} | MSAA: 4x | VSync: On",
            f"Controls: [Esc] Exit  [F12] Screenshot",
        ]
        self.overlay.render_overlay(lines)

        # Check for screenshot trigger
        if self.window.input.is_key_pressed(glfw.KEY_F12):
            self.capture_screenshot("reports/screens/stage_e0_user_screenshot.png")

        # Swap buffers and poll OS window events
        self.window.swap_buffers()
        self.window.poll_events()

    def run(self, max_frames: Optional[int] = None) -> None:
        """Main game loop."""
        frames = 0
        while not self.window.should_close():
            self.run_frame()
            frames += 1
            if max_frames and frames >= max_frames:
                break
        self.window.destroy()
