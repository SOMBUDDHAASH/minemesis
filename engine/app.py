"""
Main Application Engine Loop for Minemesis Standalone 3D Voxel Civilization Game.
"""

from __future__ import annotations
import math
import os
from pathlib import Path
import sys
import time
from typing import Optional, Tuple
import glfw
import numpy as np
import psutil
from PIL import Image

from engine.core.window import Window
from engine.core.timer import FrameTimer
from engine.physics.player import PlayerController
from engine.render.context import RenderContext
from engine.render.camera import Camera3D
from engine.render.shader import (
    ShaderProgram,
    BASIC_VOXEL_VERTEX_SHADER,
    BASIC_VOXEL_FRAGMENT_SHADER,
)
from engine.render.sky import SkyLighting
from engine.render.texture import TextureAtlas
from engine.render.cube import VoxelCubeMesh
from engine.ui.overlay import OverlayRenderer
from engine.world.block_registry import registry
from engine.world.chunk_manager import ChunkManager
from minemesis.systems.world_spec import WorldSpec
from minemesis.terrain.terrain_engine import BIOME_NAMES
from minemesis.terrain.world_provider_t0 import T0WorldProvider


class EngineApp:
    """
    Main Game Engine Application.
    Orchestrates GLFW windowing, ModernGL OpenGL 3.3 Core rendering, chunk streaming,
    voxel physics, and in-game HUD.
    """

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        title: str = "Minemesis Voxel Civilization Simulator",
        visible: bool = True,
        vsync: bool = True,
        spike_mode: bool = False,
        world_spec: Optional[WorldSpec] = None,
        view_distance: int = 8,
    ) -> None:
        self.width = width
        self.height = height
        self.spike_mode = spike_mode
        self.view_distance = view_distance
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

        # 5. UI Overlay Renderer
        self.overlay = OverlayRenderer(self.ctx, width, height)

        # 6. Sky & Day/Night Cycle
        self.sky = SkyLighting()

        # Window resize binding
        self.window.resize_callback = self._on_resize

        # 7. World Spec & Voxel Pipeline
        if self.spike_mode:
            # Stage E0 Spike Mode: Spinning textured cube
            self.camera = Camera3D(fov=65.0, aspect=width / float(height), near=0.1, far=500.0, x=0.0, y=1.2, z=-3.2)
            self.cube_mesh = VoxelCubeMesh(self.ctx, self.atlas)
            self.cube_vao = self.cube_mesh.create_vao(self.shader.program)
            self.cube_rot_x: float = 0.0
            self.cube_rot_y: float = 0.0
            self.player = None
            self.chunk_mgr = None
        else:
            # Stage E1: Full Voxel World Engine
            if world_spec is None:
                self.world_spec = T0WorldProvider().generate(42)
            else:
                self.world_spec = world_spec

            self.chunk_mgr = ChunkManager(
                self.ctx,
                self.atlas,
                self.shader.program,
                self.world_spec,
                view_distance=view_distance,
            )

            # Player Controller
            self.player = PlayerController()

            # Spawn player at the first settlement
            if self.world_spec.settlements:
                s0 = self.world_spec.settlements[0]
                sp_x = s0.x * 8 + 4
                sp_z = s0.y * 8 + 4
                sp_y = float(self.chunk_mgr.generator.get_interpolated_height(sp_x, sp_z) + 3)
                self.player.x = float(sp_x)
                self.player.y = sp_y
                self.player.z = float(sp_z)

            # Camera
            self.camera = Camera3D(
                fov=70.0,
                aspect=width / float(height),
                near=0.1,
                far=600.0,
                x=self.player.x,
                y=self.player.y + self.player.eye_height,
                z=self.player.z,
            )

            # Pre-load chunks around spawn
            self.chunk_mgr.update_player_position(self.player.x, self.player.z)

            # Capture mouse for FPS camera
            if visible:
                self.window.set_mouse_capture(True)

        self.peak_rss_mb: float = 0.0
        self.show_f3: bool = True

    def _on_resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.render_ctx.set_viewport(0, 0, width, height)
        self.camera.update_projection(width / float(height))
        self.overlay.update_projection(width, height)

    def capture_screenshot(self, output_path: str | Path) -> None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        raw = self.ctx.fbo.read(components=3, alignment=1)
        img = Image.frombytes("RGB", (self.width, self.height), raw)
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        img.save(p)

    def run_frame(self) -> None:
        dt = self.timer.tick()

        # Memory profiling
        mem_info = self.process.memory_info()
        rss_mb = mem_info.rss / (1024.0 * 1024.0)
        if rss_mb > self.peak_rss_mb:
            self.peak_rss_mb = rss_mb

        if self.spike_mode:
            self._run_spike_frame(dt, rss_mb)
        else:
            self._run_world_frame(dt, rss_mb)

        # Swap buffers and poll OS window events
        self.window.swap_buffers()
        self.window.poll_events()

    def _run_spike_frame(self, dt: float, rss_mb: float) -> None:
        if self.window.input.is_key_pressed(glfw.KEY_ESCAPE):
            self.window.close()

        self.cube_rot_x += 35.0 * dt
        self.cube_rot_y += 50.0 * dt

        self.render_ctx.clear(0.48, 0.72, 0.98, 1.0)
        self.render_ctx.enable_depth_test(True)
        self.render_ctx.enable_cull_face(True)

        self.atlas.bind(unit=0)
        self.shader.set_uniform_int("u_texture", 0)
        self.shader.set_uniform_mat4("u_proj", self.camera.projection_matrix)
        self.shader.set_uniform_mat4("u_view", self.camera.get_view_matrix())

        rx = math.radians(self.cube_rot_x)
        ry = math.radians(self.cube_rot_y)
        cx_c, sx_s = math.cos(rx), math.sin(rx)
        cy_c, sy_s = math.cos(ry), math.sin(ry)

        rot_x = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, cx_c, -sx_s, 0.0], [0.0, sx_s, cx_c, 0.0], [0.0, 0.0, 0.0, 1.0]], dtype=np.float32)
        rot_y = np.array([[cy_c, 0.0, sy_s, 0.0], [0.0, 1.0, 0.0, 0.0], [-sy_s, 0.0, cy_c, 0.0], [0.0, 0.0, 0.0, 1.0]], dtype=np.float32)
        self.shader.set_uniform_mat4("u_model", np.matmul(rot_y, rot_x))

        self.shader.set_uniform_vec3("u_light_dir", 0.4, -0.8, 0.4)
        self.shader.set_uniform_vec3("u_light_color", 1.0, 0.96, 0.88)
        self.shader.set_uniform_vec3("u_ambient_color", 0.38, 0.42, 0.48)
        self.shader.set_uniform_vec3("u_fog_color", 0.48, 0.72, 0.98)
        self.shader.set_uniform_float("u_fog_start", 20.0)
        self.shader.set_uniform_float("u_fog_end", 120.0)
        self.shader.set_uniform_vec3("u_camera_pos", self.camera.x, self.camera.y, self.camera.z)

        self.cube_mesh.render(self.cube_vao)

        lines = [
            f"MINEMESIS ENGINE v0.6.0 [STAGE E0 SPIKE]",
            f"FPS: {self.timer.fps:.1f}  (Frame Time: {dt * 1000.0:.2f} ms)",
            f"Memory RSS: {rss_mb:.1f} MB  (Peak: {self.peak_rss_mb:.1f} MB)",
            f"GPU: {self.render_ctx.renderer}",
            f"Controls: [Esc] Exit  [F12] Screenshot",
        ]
        self.overlay.render_overlay(lines)

    def _run_world_frame(self, dt: float, rss_mb: float) -> None:
        p = self.player
        inp = self.window.input

        # Toggle mouse capture / pause
        if inp.is_key_pressed(glfw.KEY_ESCAPE):
            self.window.set_mouse_capture(not inp.mouse_captured)

        # Toggle F3 HUD
        if inp.is_key_pressed(glfw.KEY_F3):
            self.show_f3 = not self.show_f3

        # Mouse look
        if inp.mouse_captured:
            sensitivity = 0.15
            p.yaw = (p.yaw - inp.delta_x * sensitivity) % 360.0
            p.pitch = max(-89.0, min(89.0, p.pitch - inp.delta_y * sensitivity))

        # Keyboard movement
        move_fwd = 0.0
        move_strafe = 0.0
        if inp.is_key_down(glfw.KEY_W):
            move_fwd += 1.0
        if inp.is_key_down(glfw.KEY_S):
            move_fwd -= 1.0
        if inp.is_key_down(glfw.KEY_A):
            move_strafe -= 1.0
        if inp.is_key_down(glfw.KEY_D):
            move_strafe += 1.0

        p.is_sprinting = inp.is_key_down(glfw.KEY_LEFT_SHIFT)
        if inp.is_key_pressed(glfw.KEY_SPACE):
            p.jump()

        # Hotbar selection 1-9
        for k in range(glfw.KEY_1, glfw.KEY_9 + 1):
            if inp.is_key_pressed(k):
                p.selected_slot = k - glfw.KEY_1

        # Mouse wheel for hotbar
        if inp.scroll_delta != 0.0:
            p.selected_slot = int(p.selected_slot - inp.scroll_delta) % len(p.hotbar)

        # Block breaking / placing
        if inp.mouse_captured:
            if inp.is_mouse_pressed(glfw.MOUSE_BUTTON_LEFT):
                p.break_targeted_block(self.chunk_mgr)
            elif inp.is_mouse_pressed(glfw.MOUSE_BUTTON_RIGHT):
                p.place_block_against_target(self.chunk_mgr)

        # 1. Physics Tick
        p.tick_physics(self.chunk_mgr, dt=dt, move_fwd=move_fwd, move_strafe=move_strafe)

        # 2. Update Camera to Player's Eye
        eye_x, eye_y, eye_z = p.get_eye_position()
        self.camera.x = eye_x
        self.camera.y = eye_y
        self.camera.z = eye_z
        self.camera.yaw = p.yaw
        self.camera.pitch = p.pitch

        # 3. Stream Chunks around Player
        self.chunk_mgr.update_player_position(p.x, p.z)

        # 4. Advance Day & Night Cycle
        self.sky.tick(dt)
        sun_dir = self.sky.get_sun_direction()
        sun_col = self.sky.get_sun_color()
        ambient_col = self.sky.get_ambient_sky_color()

        # 5. Clear Color & Render Pass
        self.render_ctx.clear(ambient_col[0], ambient_col[1], ambient_col[2], 1.0)

        # Configure shader uniforms
        self.atlas.bind(unit=0)
        self.shader.set_uniform_int("u_texture", 0)
        self.shader.set_uniform_mat4("u_proj", self.camera.projection_matrix)
        self.shader.set_uniform_mat4("u_view", self.camera.get_view_matrix())
        self.shader.set_uniform_mat4("u_model", np.identity(4, dtype=np.float32))

        self.shader.set_uniform_vec3("u_light_dir", sun_dir[0], sun_dir[1], sun_dir[2])
        self.shader.set_uniform_vec3("u_light_color", sun_col[0], sun_col[1], sun_col[2])
        self.shader.set_uniform_vec3("u_ambient_color", ambient_col[0], ambient_col[1], ambient_col[2])
        self.shader.set_uniform_vec3("u_fog_color", ambient_col[0], ambient_col[1], ambient_col[2])
        self.shader.set_uniform_float("u_fog_start", 60.0)
        self.shader.set_uniform_float("u_fog_end", float(self.view_distance * 16))
        self.shader.set_uniform_vec3("u_camera_pos", eye_x, eye_y, eye_z)

        # 6. Render Voxel Chunks
        draw_calls = self.chunk_mgr.render(p.x, p.z)

        # 7. In-Game HUD Overlay
        if self.show_f3:
            tile_x, tile_z = self.chunk_mgr.generator.block_to_tile(int(p.x), int(p.z))
            t_idx = self.chunk_mgr.generator.grid.index(tile_x, tile_z)
            biome_id = self.chunk_mgr.generator.grid.biome[t_idx]
            biome_name = BIOME_NAMES[biome_id] if 0 <= biome_id < len(BIOME_NAMES) else "Grassland"

            # Targeted block
            hit = p.raycast_block(self.chunk_mgr, 5.0)
            target_str = "None"
            if hit:
                (hx, hy, hz), (nx, ny, nz), hbid = hit
                b_def = registry.get_by_id(hbid)
                bname = b_def.name if b_def else f"Block #{hbid}"
                target_str = f"{bname} at ({hx}, {hy}, {hz}) [Norm: ({nx},{ny},{nz})]"

            # Active Hotbar Block
            sel_bid = p.hotbar[p.selected_slot]
            sel_bdef = registry.get_by_id(sel_bid)
            sel_name = sel_bdef.name if sel_bdef else f"Item #{sel_bid}"
            sel_count = p.inventory.get(sel_bid, 0)

            # Nearest Settlement
            near_set = "Wilderness"
            min_d = 9999.0
            for s in self.world_spec.settlements:
                dist = math.sqrt((p.x - (s.x * 8 + 4)) ** 2 + (p.z - (s.y * 8 + 4)) ** 2)
                if dist < min_d:
                    min_d = dist
                    if dist < 60.0:
                        near_set = f"{s.name} ({s.site_type}) [{int(dist)}m]"

            total_deltas = sum(len(d) for d in self.chunk_mgr.chunk_deltas.values())

            lines = [
                f"MINEMESIS VOXEL ENGINE v0.6.0 [STAGE E1] | FPS: {self.timer.fps:.1f}",
                f"XYZ: {p.x:.2f} / {p.y:.2f} / {p.z:.2f}  (Chunk: [{int(p.x)//16}, {int(p.z)//16}])",
                f"Facing: Yaw {p.yaw:.1f}° | Pitch {p.pitch:.1f}°",
                f"Biome: {biome_name} (Tile {tile_x}, {tile_z}) | Elev: {int(p.y)}m",
                f"Targeting: {target_str}",
                f"Active Hand [Slot {p.selected_slot + 1}]: {sel_name} ({sel_count}x)",
                f"Location: {near_set} | Chunks Loaded: {len(self.chunk_mgr.chunks)} (Draw Calls: {draw_calls})",
                f"Memory RSS: {rss_mb:.1f} MB (Peak: {self.peak_rss_mb:.1f} MB) | Deltas: {total_deltas}",
                f"Controls: [WASD] Move [Space] Jump [L-Click] Mine [R-Click] Place [1-9] Hotbar [F3] HUD [Esc] Cursor",
            ]
            self.overlay.render_overlay(lines)

    def run(self, max_frames: Optional[int] = None) -> None:
        frames = 0
        while not self.window.should_close():
            self.run_frame()
            frames += 1
            if max_frames and frames >= max_frames:
                break
        self.window.destroy()
