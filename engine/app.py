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
from engine.core.process_bridge import SimulationBridge
from engine.entities.npc import NPC, VoxelHumanoidMesh
from engine.entities.interaction import InteractionEngine
from engine.entities.book_reader import BookReader
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

            # Stage E2: Living Entities, Schedules, and Book Archives
            self.humanoid_mesh = VoxelHumanoidMesh(self.ctx, self.shader.program, self.atlas)
            self.interaction = InteractionEngine()
            self.book_reader = BookReader()
            self.npcs: list[NPC] = []
            self._spawn_settlement_npcs()

            # Stage E3: Live Simulation Bridge, Game Shell & Overlays
            self.bridge = SimulationBridge(world_spec=self.world_spec, prehistory_years=20)
            self.paused: bool = False
            self.show_chronicle: bool = False
            self.show_world_map: bool = False
            self.save_message: str = ""

        self.peak_rss_mb: float = 0.0
        self.show_f3: bool = True
        self._pending_screenshot_path: Optional[str] = None

    def _alert_nearby_guards(self, victim: NPC) -> None:
        """Alerts settlement guards if player attacks or steals within hearing range."""
        if not victim or not self.player:
            return
        for npc in self.npcs:
            if npc.profession == "Guard" and npc.settlement_id == victim.settlement_id:
                dist = math.sqrt((npc.x - victim.x) ** 2 + (npc.z - victim.z) ** 2)
                if dist < 50.0:
                    npc.is_hostile = True
                    npc.target_pos = (self.player.x, self.player.y, self.player.z)
                    npc.current_activity = f"HUNTING INTRUDER (Defending {victim.name})!"

    def _spawn_settlement_npcs(self) -> None:
        """Populates living purpose-driven NPCs into each settlement."""
        for s in self.world_spec.settlements:
            bx = float(s.x * 8 + 4)
            bz = float(s.y * 8 + 4)
            by = float(self.chunk_mgr.generator.get_interpolated_height(int(bx), int(bz)) + 1)

            # 1. Chief / Elder
            self.npcs.append(NPC(
                character_id=f"{s.id}_chief",
                name=f"Chief {s.name}",
                profession="Chief",
                faith="Common Faith",
                settlement_id=s.name,
                home_pos=(bx, by, bz),
                work_pos=(bx + 6.0, by, bz + 4.0),
                shrine_pos=(bx + 12.0, by, bz + 8.0),
                well_pos=(bx + 3.0, by, bz + 3.0),
            ))
            # 2. Scholar / Scribe
            self.npcs.append(NPC(
                character_id=f"{s.id}_scholar",
                name=f"Scribe Aethelgard of {s.name}",
                profession="Scholar",
                faith="Sacred Way",
                settlement_id=s.name,
                home_pos=(bx - 4.0, by, bz - 4.0),
                work_pos=(bx - 8.0, by, bz + 6.0),
                shrine_pos=(bx + 12.0, by, bz + 8.0),
                well_pos=(bx + 3.0, by, bz + 3.0),
            ))
            # 3. Priest
            self.npcs.append(NPC(
                character_id=f"{s.id}_priest",
                name=f"Priestess Miriel",
                profession="Priest",
                faith="Sacred Way",
                settlement_id=s.name,
                home_pos=(bx + 8.0, by, bz - 4.0),
                work_pos=(bx + 12.0, by, bz + 8.0),
                shrine_pos=(bx + 12.0, by, bz + 8.0),
                well_pos=(bx + 3.0, by, bz + 3.0),
            ))
            # 4. Blacksmith
            self.npcs.append(NPC(
                character_id=f"{s.id}_smith",
                name=f"Thorvald the Smith",
                profession="Smith",
                faith="Common Faith",
                settlement_id=s.name,
                home_pos=(bx - 6.0, by, bz + 4.0),
                work_pos=(bx - 10.0, by, bz),
                shrine_pos=(bx + 12.0, by, bz + 8.0),
                well_pos=(bx + 3.0, by, bz + 3.0),
            ))
            # 5. Master Farmer
            self.npcs.append(NPC(
                character_id=f"{s.id}_farmer",
                name=f"Farmer Brand",
                profession="Farmer",
                faith="Common Faith",
                settlement_id=s.name,
                home_pos=(bx + 4.0, by, bz + 8.0),
                work_pos=(bx + 8.0, by, bz + 12.0),
                shrine_pos=(bx + 12.0, by, bz + 8.0),
                well_pos=(bx + 3.0, by, bz + 3.0),
            ))
            # 6. Town Guard
            self.npcs.append(NPC(
                character_id=f"{s.id}_guard",
                name=f"Warden Kenneth",
                profession="Guard",
                faith="Common Faith",
                settlement_id=s.name,
                home_pos=(bx, by, bz),
                work_pos=(bx, by, bz - 8.0),
                shrine_pos=(bx + 12.0, by, bz + 8.0),
                well_pos=(bx + 3.0, by, bz + 3.0),
            ))

    def _on_resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.render_ctx.set_viewport(0, 0, width, height)
        self.camera.update_projection(width / float(height))
        self.overlay.update_projection(width, height)

    def capture_screenshot(self, output_path: str | Path) -> None:
        self._pending_screenshot_path = str(output_path)
        self.run_frame()

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

        # Capture screenshot BEFORE buffer swap
        if self._pending_screenshot_path:
            p = Path(self._pending_screenshot_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            raw = self.ctx.fbo.read(components=3, alignment=1)
            img = Image.frombytes("RGB", (self.width, self.height), raw)
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            img.save(p)
            self._pending_screenshot_path = None

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

        # Advance live simulation bridge
        if not self.paused and not self.book_reader.is_reading:
            self.bridge.tick(dt, self)

        # Handle modal states: Chronicle Overlay [J]
        if self.show_chronicle:
            if inp.is_key_pressed(glfw.KEY_ESCAPE) or inp.is_key_pressed(glfw.KEY_J):
                self.show_chronicle = False
                self.window.set_mouse_capture(True)

            self._render_3d_scene(p)
            current_year = self.bridge.total_simulated_ticks // 12
            chron_lines = [
                "=== HISTORICAL CHRONICLE & LIVING RECORD ===",
                f"World Seed: {self.bridge.seed_pair.world} | History Seed: {self.bridge.seed_pair.history}",
                f"Era: Year {current_year} (Simulated Months: {self.bridge.total_simulated_ticks})",
                "--------------------------------------------------------------------------------",
            ]
            for ev in self.bridge.recent_chronicle_events[-12:]:
                chron_lines.append(ev)
            chron_lines.append("--------------------------------------------------------------------------------")
            chron_lines.append("[J / Esc] Close Chronicle Overlay")
            self.overlay.render_centered_overlay(chron_lines)
            return

        # Handle modal states: World Map Overlay [M]
        if self.show_world_map:
            if inp.is_key_pressed(glfw.KEY_ESCAPE) or inp.is_key_pressed(glfw.KEY_M):
                self.show_world_map = False
                self.window.set_mouse_capture(True)

            self._render_3d_scene(p)
            map_lines = [
                "=== CONTINENTAL WORLD MAP & SETTLEMENTS ===",
                f"World Seed: {self.bridge.seed_pair.world} | Continent Grid: 1024x1024 Voxels",
                f"Traveler Position: ({int(p.x)}, {int(p.z)}) | Elevation: {int(p.y)}m",
                "--------------------------------------------------------------------------------",
            ]
            for s in self.world_spec.settlements:
                sx = s.x * 8 + 4
                sz = s.y * 8 + 4
                dist = math.sqrt((p.x - sx) ** 2 + (p.z - sz) ** 2)
                def_score = self.bridge.settlement_defensibility.get(s.id, 10.0)
                map_lines.append(
                    f"  * {s.name:<14s} ({s.site_type:<8s}) Pos: ({sx:4d}, {sz:4d}) | Dist: {int(dist):4d}m | Defense: {def_score:.0f}%"
                )
            map_lines.append("--------------------------------------------------------------------------------")
            map_lines.append("[M / Esc] Close World Map")
            self.overlay.render_centered_overlay(map_lines)
            return

        # Handle modal states: Pause Menu
        if self.paused:
            if inp.is_key_pressed(glfw.KEY_ESCAPE) or inp.is_key_pressed(glfw.KEY_1):
                self.paused = False
                self.window.set_mouse_capture(True)
            elif inp.is_key_pressed(glfw.KEY_2):
                self.paused = False
                self.show_world_map = True
            elif inp.is_key_pressed(glfw.KEY_3):
                self.paused = False
                self.show_chronicle = True
            elif inp.is_key_pressed(glfw.KEY_4):
                self.bridge.save_world("saves/default", self)
                self.save_message = "World State Saved Successfully to saves/default/!"
            elif inp.is_key_pressed(glfw.KEY_5):
                self.bridge.skip_time(8.0, self)
                self.save_message = "Slept until sunrise (06:00). History and crops advanced!"

            self._render_3d_scene(p)
            pause_lines = [
                "=== MINEMESIS PAUSED ===",
                "Standalone 3D Voxel Civilization Game",
                "--------------------------------------------------",
                "[1] Resume Game",
                "[2] Continental World Map (M)",
                "[3] Historical Chronicle (J)",
                "[4] Quick Save World State",
                "[5] Sleep Until Morning (Advance 8h)",
                "[Esc] Resume Game",
                "--------------------------------------------------",
            ]
            if self.save_message:
                pause_lines.append(f"Status: {self.save_message}")
            self.overlay.render_centered_overlay(pause_lines)
            return

        # Handle modal states: Book Reader
        if self.book_reader.is_reading:
            if inp.is_key_pressed(glfw.KEY_ESCAPE):
                self.book_reader.close_book()
                self.window.set_mouse_capture(True)
            elif inp.is_key_pressed(glfw.KEY_N):
                self.book_reader.next_page()
            elif inp.is_key_pressed(glfw.KEY_P):
                self.book_reader.prev_page()

            # Render 3D scene paused in background
            self._render_3d_scene(p)
            # Render Book Reader Overlay
            self.overlay.render_overlay(self.book_reader.get_current_page_text())
            return

        # Handle modal states: NPC Interaction Menu
        if self.interaction.menu_open:
            active_npc = self.interaction.active_npc
            if inp.is_key_pressed(glfw.KEY_ESCAPE):
                self.interaction.close_interaction()
                self.window.set_mouse_capture(True)
            elif inp.is_key_pressed(glfw.KEY_1):
                self.interaction.execute_action("talk", p)
            elif inp.is_key_pressed(glfw.KEY_2):
                self.interaction.execute_action("trade", p)
            elif inp.is_key_pressed(glfw.KEY_3):
                self.interaction.execute_action("gift", p)
            elif inp.is_key_pressed(glfw.KEY_4):
                self.interaction.execute_action("help", p)
            elif inp.is_key_pressed(glfw.KEY_5):
                res = self.interaction.execute_action("steal", p)
                if "CAUGHT" in res:
                    self._alert_nearby_guards(active_npc)
            elif inp.is_key_pressed(glfw.KEY_6):
                self.interaction.execute_action("attack", p)
                # Find witnesses within 40m
                witnesses = [
                    npc for npc in self.npcs
                    if math.sqrt((npc.x - active_npc.x) ** 2 + (npc.z - active_npc.z) ** 2) < 40.0
                ]
                self.bridge.record_combat_encounter(
                    victim_npc=active_npc,
                    damage=6.0,
                    fatal=(active_npc.health <= 0.0),
                    witnesses=witnesses,
                )
                self._alert_nearby_guards(active_npc)

            # Render 3D scene paused in background
            self._render_3d_scene(p)

            # Render Interaction Menu Overlay
            if active_npc:
                menu_lines = [
                    f"=== INTERACTING WITH {active_npc.name.upper()} ===",
                    f"Profession: {active_npc.profession} | Faith: {active_npc.faith} | Settlement: {active_npc.settlement_id}",
                    f"Schedule: {active_npc.current_activity} | Health: {active_npc.health:.1f}/20.0 | Affinity: {active_npc.affinity_to_player:+.0f}",
                    "--------------------------------------------------",
                ]
                for d in self.interaction.dialogue_history[-5:]:
                    menu_lines.append(d)
                menu_lines.append("--------------------------------------------------")
                menu_lines.append("[1] Talk  [2] Trade  [3] Gift  [4] Help  [5] Steal  [6] Attack  [Esc] Leave")
                self.overlay.render_overlay(menu_lines)
            return

        # Standard First-Person Game Loop
        # In-game Pause on Escape
        if inp.is_key_pressed(glfw.KEY_ESCAPE):
            self.paused = True
            self.save_message = ""
            self.window.set_mouse_capture(False)

        # Chronicle [J] and World Map [M]
        if inp.is_key_pressed(glfw.KEY_J):
            self.show_chronicle = True
            self.window.set_mouse_capture(False)
        elif inp.is_key_pressed(glfw.KEY_M):
            self.show_world_map = True
            self.window.set_mouse_capture(False)

        # Toggle F3 HUD
        if inp.is_key_pressed(glfw.KEY_F3):
            self.show_f3 = not self.show_f3

        # Toggle F4 Wireframe Mode
        if inp.is_key_pressed(glfw.KEY_F4):
            self.chunk_mgr.wireframe = not self.chunk_mgr.wireframe

        # Toggle F5 Chunk Colors Debug Mode
        if inp.is_key_pressed(glfw.KEY_F5):
            self.chunk_mgr.chunk_debug_colors = not self.chunk_mgr.chunk_debug_colors

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

        # Proximity interaction checking (NPCs and Bookshelves/Lecterns)
        nearest_npc = None
        min_npc_dist = 3.5
        for npc in self.npcs:
            dist = math.sqrt((p.x - npc.x) ** 2 + (p.y - npc.y) ** 2 + (p.z - npc.z) ** 2)
            if dist < min_npc_dist:
                min_npc_dist = dist
                nearest_npc = npc

        hit = p.raycast_block(self.chunk_mgr, 5.0)

        # Triggers
        if nearest_npc and inp.is_key_pressed(glfw.KEY_E):
            self.window.set_mouse_capture(False)
            self.interaction.open_interaction(nearest_npc)
        elif hit and hit[2] in (100, 101) and inp.is_key_pressed(glfw.KEY_R):
            self.window.set_mouse_capture(False)
            book_data = BookReader.load_random_book_from_disk()
            self.book_reader.open_book(book_data)

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

        # 5. Advance NPC Schedules and AI
        for npc in self.npcs:
            d = math.sqrt((p.x - npc.x) ** 2 + (p.z - npc.z) ** 2)
            if d < 120.0:
                npc.update_schedule(self.sky.progress, dt)

        # 6. Render 3D Scene
        draw_calls = self._render_3d_scene(p)

        # 7. In-Game HUD Overlay
        if self.show_f3:
            tile_x, tile_z = self.chunk_mgr.generator.block_to_tile(int(p.x), int(p.z))
            t_idx = self.chunk_mgr.generator.grid.index(tile_x, tile_z)
            biome_id = self.chunk_mgr.generator.grid.biome[t_idx]
            biome_name = BIOME_NAMES[biome_id] if 0 <= biome_id < len(BIOME_NAMES) else "Grassland"

            # Targeted block
            target_str = "None"
            action_prompt = ""
            if hit:
                (hx, hy, hz), (nx, ny, nz), hbid = hit
                b_def = registry.get_by_id(hbid)
                bname = b_def.name if b_def else f"Block #{hbid}"
                target_str = f"{bname} at ({hx}, {hy}, {hz}) [Norm: ({nx},{ny},{nz})]"
                if hbid in (100, 101):
                    action_prompt = f" >> PRESS [R] TO READ {bname.upper()} <<"

            if nearest_npc:
                action_prompt = f" >> PRESS [E] TO SPEAK WITH {nearest_npc.name.upper()} ({nearest_npc.profession}) <<"

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

            ground_h = float(self.chunk_mgr.generator.get_interpolated_height(int(p.x), int(p.z)))
            chunks_meshed = sum(1 for c in self.chunk_mgr.chunks.values() if c.opaque_mesh is not None)
            sim_year = self.bridge.total_simulated_ticks // 12
            lines = [
                f"MINEMESIS VOXEL ENGINE [RECOVERY AUDIT] | FPS: {self.timer.fps:.1f}",
                f"Camera XYZ: {self.camera.x:.2f} / {self.camera.y:.2f} / {self.camera.z:.2f} (Yaw: {self.camera.yaw:.1f}°, Pitch: {self.camera.pitch:.1f}°)",
                f"Terrain Elevation: {ground_h:.1f}m (Eye Altitude: {self.camera.y - ground_h:+.1f}m) | Year {sim_year}",
                f"Chunks Loaded: {len(self.chunk_mgr.chunks)} | Chunks Meshed: {chunks_meshed}",
                f"Chunks Rendered: {self.chunk_mgr.chunks_rendered} | Draw Calls: {self.chunk_mgr.draw_calls}",
                f"Triangle Count: {self.chunk_mgr.triangles_rendered:,}",
                f"Wireframe [F4]: {'ON' if self.chunk_mgr.wireframe else 'OFF'} | Chunk Colors [F5]: {'ON' if self.chunk_mgr.chunk_debug_colors else 'OFF'}",
                f"Targeting: {target_str}",
                f"Hand [Slot {p.selected_slot + 1}]: {sel_name} ({sel_count}x) | Location: {near_set}",
            ]
            if action_prompt:
                lines.append(action_prompt)
            lines.append("Controls: [WASD] Move [Space] Jump [L/R Click] Mine/Build [F4] Wireframe [F5] Chunk Colors [F3] HUD [Esc] Pause")
            self.overlay.render_overlay(lines)

        # Crosshair in first-person gameplay
        if not self.paused and not self.book_reader.is_reading and not self.interaction.menu_open and not self.show_chronicle and not self.show_world_map:
            self.overlay.render_crosshair()

    def _render_3d_scene(self, p: PlayerController) -> int:
        """Renders sky, chunks, and 3D humanoids."""
        eye_x, eye_y, eye_z = p.get_eye_position()
        sun_dir = self.sky.get_sun_direction()
        sun_col = self.sky.get_sun_color()
        ambient_col = self.sky.get_ambient_sky_color()

        self.render_ctx.clear(ambient_col[0], ambient_col[1], ambient_col[2], 1.0)
        self.render_ctx.enable_depth_test(True)

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

        # 1. Render Chunks
        draw_calls, chunks_rendered, triangles_rendered = self.chunk_mgr.render(p.x, p.z)

        # 2. Render Humanoid NPCs (if not wireframe)
        if not self.chunk_mgr.wireframe:
            for npc in self.npcs:
                dist = math.sqrt((p.x - npc.x) ** 2 + (p.z - npc.z) ** 2)
                if dist < float(self.view_distance * 16):
                    npc.render(self.humanoid_mesh, self.shader, self.camera)

        return draw_calls

    def run(self, max_frames: Optional[int] = None) -> None:
        frames = 0
        while not self.window.should_close():
            self.run_frame()
            frames += 1
            if max_frames and frames >= max_frames:
                break
        self.window.destroy()
