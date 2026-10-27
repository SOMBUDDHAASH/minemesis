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
from engine.core.settings import GameSettings
from engine.core.audio import SoundEngine
from engine.core.process_bridge import SimulationBridge
from engine.entities.npc import NPC, VoxelHumanoidMesh
from engine.entities.interaction import InteractionEngine
from engine.entities.book_reader import BookReader
from engine.physics.player import PlayerController
from engine.render.context import RenderContext
from engine.render.camera import Camera3D
from engine.render.highlight import BlockHighlightRenderer
from engine.render.particles import ParticleSystem
from engine.render.hand import FirstPersonHandRenderer
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

        # 7. Game Settings & Smoothing
        self.settings = GameSettings.load()
        self.smooth_dx: float = 0.0
        self.smooth_dy: float = 0.0
        self.highlight_renderer = BlockHighlightRenderer(self.ctx)
        self.particles = ParticleSystem(self.ctx)
        self.hand_renderer = FirstPersonHandRenderer(self.ctx, self.atlas)
        self.audio = SoundEngine()

        # Window resize binding
        self.window.resize_callback = self._on_resize

        # 8. World Spec & Voxel Pipeline
        if self.spike_mode:
            # Stage E0 Spike Mode: Spinning textured cube
            self.camera = Camera3D(fov=self.settings.fov, aspect=width / float(height), near=0.1, far=500.0, x=0.0, y=1.2, z=-3.2)
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

            # Player Controller (Grounded, Fly Mode False by default)
            self.player = PlayerController()
            self.player.fly_mode = self.settings.fly_mode

            # Spawn player at the first settlement flush on highest solid voxel
            if self.world_spec.settlements:
                s0 = self.world_spec.settlements[0]
                sp_x = s0.x * 8 + 4
                sp_z = s0.y * 8 + 4
                sp_y = float(self.chunk_mgr.get_highest_solid_y(sp_x, sp_z) + 1.0)
                self.player.x = float(sp_x)
                self.player.y = sp_y
                self.player.z = float(sp_z)

            # Camera
            self.camera = Camera3D(
                fov=self.settings.fov,
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

            # Stage E3: Live Simulation Bridge, Game Shell & Overlays
            self.bridge = SimulationBridge(world_spec=self.world_spec, prehistory_years=20)
            self.paused: bool = False
            self.show_chronicle: bool = False
            self.show_world_map: bool = False
            self.show_inventory: bool = False
            self.show_settings: bool = False
            self.save_message: str = ""

            # Stage E2: Living Entities, Schedules, and Book Archives
            self.humanoid_mesh = VoxelHumanoidMesh(self.ctx, self.shader.program, self.atlas)
            self.interaction = InteractionEngine()
            self.book_reader = BookReader()
            self.npcs: list[NPC] = []
            self._spawn_settlement_npcs()

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
        """
        Populates living simulated citizens from the generational simulation into each settlement.
        Every NPC is an embodied character with real lineages, clan surnames, true spouses/children,
        feuds, and daily schedules.
        """
        sim = self.bridge.simulation
        all_chars = sim.characters

        for s in self.world_spec.settlements:
            bx = float(s.x * 8 + 4)
            bz = float(s.y * 8 + 4)
            by = float(self.chunk_mgr.generator.get_interpolated_height(int(bx), int(bz)) + 1)

            # Retrieve all living simulation characters belonging to this settlement
            sim_chars = [c for c in all_chars.values() if c.alive and c.settlement_id == s.id]
            if not sim_chars:
                continue

            # Prioritize family clusters (married couples with children)
            sim_chars_by_id = {c.id: c for c in sim_chars}

            # Group characters by family clan
            family_clans: dict[str, list[any]] = {}
            for c in sim_chars:
                family_clans.setdefault(c.last_name, []).append(c)

            # Assign distinct home coordinates per family clan flush on top of solid voxel
            family_homes: dict[str, tuple[float, float, float]] = {}
            clan_names = list(family_clans.keys())
            for idx, cname in enumerate(clan_names):
                angle = (idx * 2.0 * math.pi) / max(1, len(clan_names))
                dist = 14.0 + (idx % 3) * 6.0
                hx = bx + math.cos(angle) * dist
                hz = bz + math.sin(angle) * dist
                hy = float(self.chunk_mgr.get_highest_solid_y(hx, hz))
                family_homes[cname] = (hx, hy, hz)

            # Target 22 visible villagers for spawn settlement set_0 (and 12 for others)
            target_count = 22 if s.id == "set_0" else 12

            # Always ensure the actual simulated settlement leader (Chief) is spawned
            sim_settlement = sim.settlements.get(s.id)
            chief_char = sim_chars_by_id.get(sim_settlement.leader_id) if sim_settlement else None

            selected_chars = []
            if chief_char:
                chief_char.profession = "Chief"
                selected_chars.append(chief_char)

            for c in sim_chars:
                if c not in selected_chars:
                    selected_chars.append(c)
                if len(selected_chars) >= target_count:
                    break

            # Ensure essential roles are represented
            has_guard = any(c.profession in ("Guard", "Soldier") for c in selected_chars)
            has_smith = any(c.profession in ("Smith", "Blacksmith") for c in selected_chars)
            has_priest = any(c.profession in ("Priest", "Scholar", "Scribe") for c in selected_chars)

            if not has_guard and len(selected_chars) > 2:
                selected_chars[-1].profession = "Guard"
                if len(selected_chars) > 3:
                    selected_chars[-2].profession = "Guard"
            if not has_smith and len(selected_chars) > 1:
                selected_chars[1].profession = "Blacksmith"
            if not has_priest and len(selected_chars) > 0 and selected_chars[0] != chief_char:
                selected_chars[0].profession = "Scholar"

            # Common settlement landmarks with precise surface grounding
            well_y = float(self.chunk_mgr.get_highest_solid_y(bx, bz))
            well_pos = (bx, well_y, bz)

            sh_x, sh_z = bx + 16.0, bz + 12.0
            shrine_pos = (sh_x, float(self.chunk_mgr.get_highest_solid_y(sh_x, sh_z)), sh_z)

            tav_x, tav_z = bx - 12.0, bz + 10.0
            tavern_pos = (tav_x, float(self.chunk_mgr.get_highest_solid_y(tav_x, tav_z)), tav_z)

            guard_patrols = []
            for gx, gz in [
                (bx + 22.0, bz + 22.0),
                (bx - 22.0, bz + 22.0),
                (bx - 22.0, bz - 22.0),
                (bx + 22.0, bz - 22.0),
            ]:
                guard_patrols.append((gx, float(self.chunk_mgr.get_highest_solid_y(gx, gz)), gz))

            for c_idx, c in enumerate(selected_chars):
                home = family_homes.get(c.last_name, (bx, well_y, bz))

                # Determine workplace based on actual profession
                if c.profession in ("Smith", "Blacksmith"):
                    work = (bx - 14.0, by, bz - 8.0)
                elif c.profession == "Farmer":
                    work = (bx + 18.0, by, bz - 14.0)
                elif c.profession == "Woodcutter":
                    work = (bx - 18.0, by, bz + 14.0)
                elif c.profession in ("Priest", "Scholar", "Scribe"):
                    work = shrine_pos
                elif c.profession in ("Guard", "Soldier"):
                    work = guard_patrols[c_idx % len(guard_patrols)]
                elif c.profession in ("Chief", "Elder"):
                    work = (bx, by, bz - 12.0)
                else:
                    work = (bx + ((c_idx % 4) * 4.0 - 6.0), by, bz + ((c_idx % 3) * 4.0 - 4.0))

                # Ground workplace elevation
                wx, _, wz = work
                work = (wx, float(self.chunk_mgr.get_highest_solid_y(wx, wz)), wz)

                # Identify spouse name
                spouse_name = None
                if c.spouse_id and c.spouse_id in sim_chars_by_id:
                    spouse_name = sim_chars_by_id[c.spouse_id].name

                # Identify siblings
                sibling_ids = [
                    other.id for other in sim_chars
                    if other.id != c.id and (
                        (c.father_id and other.father_id == c.father_id) or
                        (c.mother_id and other.mother_id == c.mother_id)
                    )
                ]

                # Identify clan feuds / rivalries
                other_clans = [cn for cn in clan_names if cn != c.last_name]
                rival_names = [other_clans[0]] if other_clans else []

                # Resolve true religion from ReligionEngine
                char_faith = "Sacred Way"
                if sim.religion_engine and sim.religion_engine.enabled:
                    rel_obj = sim.religion_engine.get_character_religion(c.id)
                    if rel_obj:
                        char_faith = rel_obj.name
                    else:
                        set_rel = sim.religion_engine.get_settlement_religion(s.id)
                        if set_rel:
                            char_faith = set_rel.name

                npc = NPC(
                    character_id=c.id,
                    name=c.name,
                    first_name=c.first_name,
                    last_name=c.last_name,
                    family_id=c.family_id,
                    age_years=c.age_years,
                    sex=c.sex,
                    profession=c.profession,
                    faith=char_faith,
                    settlement_id=s.id,
                    settlement_name=s.name,
                    spouse_id=c.spouse_id,
                    spouse_name=spouse_name,
                    father_id=c.father_id,
                    mother_id=c.mother_id,
                    children_ids=list(c.children_ids),
                    sibling_ids=sibling_ids,
                    rival_family_names=rival_names,
                    home_pos=home,
                    work_pos=work,
                    shrine_pos=shrine_pos,
                    tavern_pos=tavern_pos,
                    well_pos=well_pos,
                    guard_patrol_points=guard_patrols,
                )

                # Ensure NPC spawn feet are grounded flush on solid surface
                npc.y = float(self.chunk_mgr.get_highest_solid_y(npc.x, npc.z))
                npc.is_grounded = True

                # Cache living kin names for fast lookup
                for kid in list(c.children_ids) + sibling_ids + ([c.spouse_id] if c.spouse_id else []):
                    if kid in sim_chars_by_id:
                        npc.kin_names[kid] = sim_chars_by_id[kid].name

                self.npcs.append(npc)

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

        # Handle modal states: Inventory Panel [I / Tab]
        if self.show_inventory:
            if inp.is_key_pressed(glfw.KEY_ESCAPE) or inp.is_key_pressed(glfw.KEY_I) or inp.is_key_pressed(glfw.KEY_TAB):
                self.show_inventory = False
                self.window.set_mouse_capture(True)

            # Hotbar slot selection 1-9 in inventory
            for k in range(glfw.KEY_1, glfw.KEY_9 + 1):
                if inp.is_key_pressed(k):
                    p.selected_slot = k - glfw.KEY_1

            # Mouse slot interactions: Left-click (Pick/Drop/Swap), Right-click (Split/Drop 1), Shift-click (Quick Move)
            is_shift = inp.is_key_down(glfw.KEY_LEFT_SHIFT) or inp.is_key_down(glfw.KEY_RIGHT_SHIFT)
            if inp.is_mouse_pressed(glfw.MOUSE_BUTTON_LEFT):
                slot = self.overlay.get_inventory_slot_under_cursor(inp.mouse_x, inp.mouse_y)
                if slot:
                    slot_type, slot_id = slot
                    p.inventory.handle_slot_click(slot_type, slot_id, button=1, shift=is_shift)
                    self.audio.play_click()
            elif inp.is_mouse_pressed(glfw.MOUSE_BUTTON_RIGHT):
                slot = self.overlay.get_inventory_slot_under_cursor(inp.mouse_x, inp.mouse_y)
                if slot:
                    slot_type, slot_id = slot
                    p.inventory.handle_slot_click(slot_type, slot_id, button=2, shift=is_shift)
                    self.audio.play_click()

            self._render_3d_scene(p)
            self.overlay.render_inventory_gui(p.inventory, inp.mouse_x, inp.mouse_y)
            return

        # Handle modal states: Settings Menu [O]
        if self.show_settings:
            if inp.is_key_pressed(glfw.KEY_ESCAPE) or inp.is_key_pressed(glfw.KEY_O):
                self.show_settings = False
                self.settings.save()
                self.window.set_mouse_capture(True)
            elif inp.is_key_pressed(glfw.KEY_1):
                self.settings.cycle_sensitivity()
            elif inp.is_key_pressed(glfw.KEY_2):
                self.settings.toggle_smoothing()
            elif inp.is_key_pressed(glfw.KEY_3):
                self.settings.cycle_fov()
                self.camera.fov = self.settings.fov
                self.camera.update_projection(self.width / float(self.height))
            elif inp.is_key_pressed(glfw.KEY_4):
                self.settings.toggle_invert_y()
            elif inp.is_key_pressed(glfw.KEY_5):
                self.settings.toggle_fly_mode()
                self.player.fly_mode = self.settings.fly_mode

            self._render_3d_scene(p)
            self.overlay.render_settings_menu(self.settings)
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
            elif inp.is_key_pressed(glfw.KEY_6):
                self.paused = False
                self.show_settings = True

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
                "[6] Game & Input Settings (O)",
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
                self.interaction.execute_action("talk", p, app=self)
            elif inp.is_key_pressed(glfw.KEY_2):
                self.interaction.execute_action("trade", p, app=self)
            elif inp.is_key_pressed(glfw.KEY_3):
                self.interaction.execute_action("gift", p, app=self)
            elif inp.is_key_pressed(glfw.KEY_4):
                self.interaction.execute_action("help", p, app=self)
            elif inp.is_key_pressed(glfw.KEY_5):
                res = self.interaction.execute_action("steal", p, app=self)
                if "CAUGHT" in res:
                    self._alert_nearby_guards(active_npc)
            elif inp.is_key_pressed(glfw.KEY_6):
                self.interaction.execute_action("attack", p, app=self)
                # Alert nearby guards
                self._alert_nearby_guards(active_npc)

            # Render 3D scene paused in background
            self._render_3d_scene(p)

            # Render Interaction Menu Overlay
            if active_npc:
                standing = self.interaction.reputation.get_title(active_npc.settlement_id)
                rep_score = self.interaction.reputation.get_score(active_npc.settlement_id)
                kin_str = f"Spouse: {active_npc.spouse_name or 'Unmarried'} | Kin: {len(active_npc.children_ids)} children, {len(active_npc.sibling_ids)} siblings"
                menu_lines = [
                    f"=== INTERACTING WITH {active_npc.name.upper()} ===",
                    f"Clan: {active_npc.last_name} | Profession: {active_npc.profession} | Faith: {active_npc.faith}",
                    f"{kin_str}",
                    f"Settlement: {active_npc.settlement_name} | Standing: {standing} ({rep_score:+.0f})",
                    f"Activity: {active_npc.current_activity} | Health: {active_npc.health:.1f}/20.0",
                    "--------------------------------------------------",
                ]
                for d in self.interaction.dialogue_history[-5:]:
                    menu_lines.append(d)
                menu_lines.append("--------------------------------------------------")
                menu_lines.append("[1] Talk  [2] Trade  [3] Gift  [4] Help Village (+Rep)  [5] Steal  [6] Attack  [Esc] Leave")
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

        # Inventory [I / Tab] and Settings [O]
        if inp.is_key_pressed(glfw.KEY_I) or inp.is_key_pressed(glfw.KEY_TAB):
            self.show_inventory = True
            self.window.set_mouse_capture(False)
        elif inp.is_key_pressed(glfw.KEY_O):
            self.show_settings = True
            self.window.set_mouse_capture(False)

        # Direct Fly Mode Toggle [F8] (or [F])
        if inp.is_key_pressed(glfw.KEY_F8) or inp.is_key_pressed(glfw.KEY_F):
            self.settings.toggle_fly_mode()
            self.player.fly_mode = self.settings.fly_mode

        # Direct Creative Build Mode Toggle [F9] (Infinite blocks & instant 1-click mining)
        if inp.is_key_pressed(glfw.KEY_F9):
            self.player.creative_mode = not self.player.creative_mode

        # Advance diurnal time cycle [T] (+6 hours: Dawn -> Work -> Tavern -> Night Curfew)
        if inp.is_key_pressed(glfw.KEY_T):
            self.sky.time_of_day = (self.sky.time_of_day + 300.0) % 1200.0

        # Toggle F3 HUD
        if inp.is_key_pressed(glfw.KEY_F3):
            self.show_f3 = not self.show_f3

        # Toggle F4 Wireframe Mode
        if inp.is_key_pressed(glfw.KEY_F4):
            self.chunk_mgr.wireframe = not self.chunk_mgr.wireframe

        # Toggle F5 Chunk Colors Debug Mode
        if inp.is_key_pressed(glfw.KEY_F5):
            self.chunk_mgr.chunk_debug_colors = not self.chunk_mgr.chunk_debug_colors

        # Mouse look with Raw Input & Exponential Smoothing
        if inp.mouse_captured:
            sens = self.settings.mouse_sensitivity
            if self.settings.camera_smoothing:
                smooth = self.settings.smoothing_factor
                self.smooth_dx = self.smooth_dx * (1.0 - smooth) + inp.delta_x * smooth
                self.smooth_dy = self.smooth_dy * (1.0 - smooth) + inp.delta_y * smooth
                dx_val = self.smooth_dx
                dy_val = self.smooth_dy
            else:
                dx_val = inp.delta_x
                dy_val = inp.delta_y

            inv_factor = -1.0 if self.settings.invert_y else 1.0
            p.yaw = (p.yaw - dx_val * sens) % 360.0
            p.pitch = max(-89.0, min(89.0, p.pitch - dy_val * sens * inv_factor))

        # Keyboard movement (with 3D Spectator Flight & Lift)
        move_fwd = 0.0
        move_strafe = 0.0
        move_up = 0.0
        if inp.is_key_down(glfw.KEY_W):
            move_fwd += 1.0
        if inp.is_key_down(glfw.KEY_S):
            move_fwd -= 1.0
        if inp.is_key_down(glfw.KEY_A):
            move_strafe -= 1.0
        if inp.is_key_down(glfw.KEY_D):
            move_strafe += 1.0

        p.is_sprinting = inp.is_key_down(glfw.KEY_LEFT_SHIFT)
        if p.fly_mode:
            # Fly Mode vertical lift & descent
            if inp.is_key_down(glfw.KEY_SPACE):
                move_up += 1.0
            if inp.is_key_down(glfw.KEY_LEFT_CONTROL) or inp.is_key_down(glfw.KEY_C) or inp.is_key_down(glfw.KEY_Q):
                move_up -= 1.0
        else:
            if inp.is_key_pressed(glfw.KEY_SPACE):
                p.jump()

        # Hotbar selection 1-9
        for k in range(glfw.KEY_1, glfw.KEY_9 + 1):
            if inp.is_key_pressed(k):
                p.selected_slot = k - glfw.KEY_1

        # Mouse wheel for hotbar
        if inp.scroll_delta != 0.0:
            p.selected_slot = int(p.selected_slot - inp.scroll_delta) % len(p.hotbar)

        # Block breaking / placing (Continuous mining accumulator & particle burst)
        if inp.mouse_captured:
            is_mining = inp.is_mouse_down(glfw.MOUSE_BUTTON_LEFT)
            broken = p.update_mining(self.chunk_mgr, dt, is_mining)
            if broken:
                bx, by, bz, bid = broken
                self.particles.spawn_block_break(bx, by, bz, bid)
                self.audio.play_break()

            if inp.is_mouse_pressed(glfw.MOUSE_BUTTON_RIGHT):
                placed = p.place_block_against_target(self.chunk_mgr)
                if placed:
                    self.audio.play_place()
        else:
            p.update_mining(self.chunk_mgr, dt, False)

        # Update dynamic particle kinematics
        self.particles.update(dt)

        # Dynamic Sprint FOV interpolation (Luanti/Minecraft camera expansion)
        target_fov = (self.settings.fov + 8.0) if p.is_sprinting else self.settings.fov
        self.camera.fov = self.camera.fov * max(0.0, 1.0 - 10.0 * dt) + target_fov * (10.0 * dt)
        self.camera.update_projection(self.width / float(self.height))

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
        p.tick_physics(self.chunk_mgr, dt=dt, move_fwd=move_fwd, move_strafe=move_strafe, move_up=move_up)

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

        # 5. Advance NPC Schedules and AI with Terrain Physics
        for npc in self.npcs:
            d = math.sqrt((p.x - npc.x) ** 2 + (p.z - npc.z) ** 2)
            if d < 120.0:
                npc.update_schedule(self.sky.progress, dt, self.chunk_mgr)

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

            # Active Hotbar Item
            active_item = p.inventory.get_active_item()
            sel_name = active_item.name if active_item else "Empty Slot"
            sel_count = active_item.count if active_item else 0

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
            sim_year = (self.bridge.total_simulated_ticks // 12) + 1
            hour = int(self.sky.progress * 24.0) % 24
            minute = int(((self.sky.progress * 24.0) % 1.0) * 60)

            time_phase = (
                "NIGHT CURFEW (Guards on Patrol)" if (self.sky.progress < 0.25 or self.sky.progress > 0.88)
                else "MORNING GATHERING (Village Well)" if self.sky.progress < 0.38
                else "DAY LABOR (Fields & Anvils)" if self.sky.progress < 0.70
                else "EVENING FELLOWSHIP (Tavern & Shrine)"
            )

            # Determine local settlement standing
            active_set_id = "set_0"
            for s in self.world_spec.settlements:
                dist = math.sqrt((p.x - (s.x * 8 + 4)) ** 2 + (p.z - (s.y * 8 + 4)) ** 2)
                if dist < 65.0:
                    active_set_id = s.id
                    break
            standing = self.interaction.reputation.get_title(active_set_id)
            rep_score = self.interaction.reputation.get_score(active_set_id)
            fly_str = " | FLY MODE: [ON] (F8)" if p.fly_mode else ""
            creat_str = " | CREATIVE: [ON] (F9)" if p.creative_mode else ""

            lines = [
                f"MINEMESIS | LIVING CIVILIZATION SANDBOX | FPS: {self.timer.fps:.1f}{fly_str}{creat_str}",
                f"World Clock: Year {sim_year} | Time: {hour:02d}:{minute:02d} [{time_phase}] [Press T to Advance]",
                f"Social Standing: {standing} ({rep_score:+.0f}) in {near_set}",
                f"Camera XYZ: {self.camera.x:.2f} / {self.camera.y:.2f} / {self.camera.z:.2f} | Ground: {p.on_ground} | Chunks Rendered: {self.chunk_mgr.chunks_rendered}",
                f"Targeting: {target_str}",
                f"Hand: {sel_name} ({sel_count}x) | Location: {near_set}",
            ]
            if nearest_npc:
                lines.append(
                    f" >> CITIZEN: {nearest_npc.name} (Clan {nearest_npc.last_name}, {nearest_npc.profession}) [Grounded: {nearest_npc.is_grounded}] <<"
                )
                lines.append(
                    f"    Activity: {nearest_npc.current_activity} | Press [E] to Speak / Help / Attack"
                )
            elif action_prompt:
                lines.append(action_prompt)
            lines.append("Controls: [WASD] Move [Space] Jump/Lift [F8] Fly [F9] Creative [E] Speak [I] Inv [F3] HUD [Esc] Pause")
            self.overlay.render_overlay(lines)

        # 8. Render Floating Overhead NPC Debug Labels (Name, Family, Job, Current Task)
        if not self.paused and not self.book_reader.is_reading and not self.interaction.menu_open and not self.show_chronicle and not self.show_world_map and not self.show_inventory and not self.show_settings:
            self.overlay.render_npc_overhead_labels(self.npcs, self.camera, max_dist=35.0)

        # Crosshair in first-person gameplay
        if not self.paused and not self.book_reader.is_reading and not self.interaction.menu_open and not self.show_chronicle and not self.show_world_map and not self.show_inventory and not self.show_settings:
            self.overlay.render_crosshair()

    def _render_3d_scene(self, p: PlayerController) -> int:
        """Renders sky, chunks, 3D humanoids, and interaction block outlines."""
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

        # 3. Render Block Highlight Outline, Face Normal, Ghost Preview, and Mining Cracks
        if not self.chunk_mgr.wireframe:
            hit = p.raycast_block(self.chunk_mgr, 5.0)
            if hit:
                (hx, hy, hz), (nx, ny, nz), _ = hit
                active_item = p.inventory.get_active_item()
                preview_bid = active_item.block_id if active_item else None
                self.highlight_renderer.render_highlight(
                    self.camera,
                    (hx, hy, hz),
                    (nx, ny, nz),
                    preview_bid,
                    dig_progress=p.dig_progress,
                )

        # 4. Render 3D Voxel Debris Particle Burst
        self.particles.render(self.camera)

        # 5. Render First-Person Embodied Arm & Held Item with Punch Swing
        if not self.chunk_mgr.wireframe:
            active_item = p.inventory.get_active_item()
            held_bid = active_item.block_id if active_item else None
            is_moving = p.on_ground and (abs(p.vx) + abs(p.vz) > 0.1)
            self.hand_renderer.render(
                self.camera,
                punch_progress=p.punch_anim_timer,
                bob_cycle=p.bob_cycle,
                is_moving=is_moving,
                held_block_id=held_bid,
            )

        return draw_calls

    def run(self, max_frames: Optional[int] = None) -> None:
        frames = 0
        while not self.window.should_close():
            self.run_frame()
            frames += 1
            if max_frames and frames >= max_frames:
                break
        self.window.destroy()
