"""
Minemesis Interactive 3D Voxel Sandbox Window (viewer/ui/voxel_window.py).

Provides an interactive Minecraft-style 3D sandbox directly inside Minemesis Viewer:
- Real-time 3D first-person voxel projection & 3D tactical isometric view.
- 20 TPS physics engine: gravity, jumping, auto-stepping, swept AABB collision resolution.
- 3D DDA voxel raycasting (5-block reach) with real-time targeted block wireframe outline.
- Interactive block breaking (Left-Click) and block placing (Right-Click).
- Minecraft-style 9-slot Hotbar HUD with block counts and active selection.
- Settlement teleporter: jump instantly to any settlement across the 300x300 continent.
- Two-way settlement construction analyzer: placing walls or mining alerts the user with live defensibility impacts.
- Direct Minecraft Java (.mca) Anvil export.
"""

from __future__ import annotations
import math
from pathlib import Path
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Any, Dict, List, Optional, Set, Tuple

from minemesis.systems.world_spec import WorldSpec, SettlementSite
from minemesis.terrain.terrain_engine import BIOME_NAMES, SEA_LEVEL
from minemesis.terrain.world_provider_t0 import T0WorldProvider
from translators.voxel.construction_analyzer import ConstructionAnalyzer, ConstructionRecord
from translators.voxel.game_engine import VoxelGameEngine, PlayerEntity
from translators.voxel.voxelspec import (
    BLOCK_AIR,
    BLOCK_BEDROCK,
    BLOCK_COAL_ORE,
    BLOCK_COBBLESTONE,
    BLOCK_DEEPSLATE,
    BLOCK_DIRT,
    BLOCK_GOLD_ORE,
    BLOCK_GRAVEL,
    BLOCK_GRASS_BLOCK,
    BLOCK_IRON_ORE,
    BLOCK_NAMES,
    BLOCK_OAK_LEAVES,
    BLOCK_OAK_PLANKS,
    BLOCK_OAK_WOOD,
    BLOCK_SAND,
    BLOCK_SNOW_BLOCK,
    BLOCK_STONE,
    BLOCK_WATER,
    SOLID_BLOCKS,
    VoxelWorldSpec,
)
from viewer.core.logging import log_error
from viewer.core.session import session
from viewer.ui.theme import theme


# Palette Colors for 3D Faces: (top_color, side_color, bottom_color)
BLOCK_FACE_COLORS: Dict[int, Tuple[str, str, str]] = {
    BLOCK_GRASS_BLOCK: ("#5da83b", "#775635", "#553a20"),
    BLOCK_DIRT: ("#7a5636", "#6c4c30", "#553a20"),
    BLOCK_STONE: ("#7a7e80", "#6a6e70", "#545759"),
    BLOCK_COBBLESTONE: ("#6e6e6e", "#5e5e5e", "#474747"),
    BLOCK_OAK_PLANKS: ("#b8945f", "#a08050", "#7f643e"),
    BLOCK_OAK_WOOD: ("#8f7450", "#5a432b", "#43321f"),
    BLOCK_OAK_LEAVES: ("#337e22", "#28661b", "#1c4a12"),
    BLOCK_SAND: ("#ded097", "#cfc186", "#a69a68"),
    BLOCK_GRAVEL: ("#85817c", "#736f6b", "#5a5754"),
    BLOCK_WATER: ("#3b74db", "#2e60bd", "#20468e"),
    BLOCK_BEDROCK: ("#262626", "#1c1c1c", "#121212"),
    BLOCK_COAL_ORE: ("#4a4c4d", "#3d3e3f", "#2a2b2c"),
    BLOCK_IRON_ORE: ("#8a8279", "#787067", "#5c564e"),
    BLOCK_GOLD_ORE: ("#9e9262", "#877c4f", "#6b623c"),
    BLOCK_SNOW_BLOCK: ("#f0f6fa", "#d9e4ed", "#b8c7d4"),
    BLOCK_DEEPSLATE: ("#38393d", "#2c2d30", "#1e1e21"),
}

# Hotbar block configuration (keys 1-9)
HOTBAR_ITEMS: List[Tuple[int, str, str]] = [
    (BLOCK_COBBLESTONE, "Cobblestone", "#6e6e6e"),
    (BLOCK_OAK_PLANKS, "Oak Planks", "#b8945f"),
    (BLOCK_DIRT, "Dirt", "#7a5636"),
    (BLOCK_GRASS_BLOCK, "Grass Block", "#5da83b"),
    (BLOCK_STONE, "Stone", "#7a7e80"),
    (BLOCK_OAK_WOOD, "Oak Log", "#5a432b"),
    (BLOCK_OAK_LEAVES, "Oak Leaves", "#337e22"),
    (BLOCK_SAND, "Sand", "#ded097"),
    (BLOCK_WATER, "Water", "#3b74db"),
]

# Singleton tracking
_active_voxel_window: Optional[VoxelInteractionWindow] = None


class VoxelInteractionWindow(tk.Toplevel):
    """
    Full 3D Minecraft Sandbox Interaction Window.
    Allows real-time walking, jumping, block breaking, placing, inventory selection,
    settlement teleports, and settlement defense impacts.
    """

    def __init__(
        self,
        parent: Optional[tk.Widget] = None,
        world_spec: Optional[WorldSpec] = None,
        settlement_id: Optional[str] = None,
        spawn_coords: Optional[Tuple[float, float, float]] = None,
    ) -> None:
        super().__init__(parent)

        global _active_voxel_window
        _active_voxel_window = self

        self.title("Minemesis 3D Voxel Sandbox [Minecraft Interaction Mode]")
        self.geometry("1100x780")
        self.minsize(860, 580)
        self.configure(bg="#14181f")

        # 1. Resolve or Generate WorldSpec
        if world_spec is not None:
            self.world_spec = world_spec
        elif session.db and session.db.meta.get("world_seed"):
            w_seed = int(session.db.meta["world_seed"])
            self.world_spec = T0WorldProvider().generate(w_seed)
        else:
            self.world_spec = T0WorldProvider().generate(42)

        # 2. Instantiate Voxel Game Engine and Construction Analyzer
        self.engine = VoxelGameEngine(self.world_spec)
        self.analyzer = ConstructionAnalyzer(self.world_spec)

        # 3. Position Player
        if spawn_coords:
            self.engine.player.x, self.engine.player.y, self.engine.player.z = spawn_coords
        elif settlement_id:
            self._teleport_to_settlement_id(settlement_id)

        # 4. State flags & Input tracking
        self.keys_down: Set[str] = set()
        self.view_mode: str = "first_person"  # "first_person" or "isometric"
        self.show_hud: bool = True
        self.is_running: bool = True
        self.hotbar_index: int = 0
        self.engine.player.selected_block = HOTBAR_ITEMS[self.hotbar_index][0]

        # Mouse look drag state
        self._last_mouse_x = 0
        self._last_mouse_y = 0
        self._mouse_drag_active = False

        # Floating notification ripples
        self._notifications: List[Dict[str, Any]] = []

        # FPS Tracking
        self._frame_times: List[float] = []
        self._fps: float = 30.0

        # Build UI layout
        self._build_ui()
        self._bind_events()

        # Start game loop
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._game_loop)

    def _build_ui(self) -> None:
        c = theme.colors

        # Top Control Bar
        top_bar = tk.Frame(self, bg="#1a202c", padx=12, pady=6)
        top_bar.pack(fill=tk.X, side=tk.TOP)

        # Title Pill
        lbl_title = tk.Label(
            top_bar,
            text="🎮 3D VOXEL SANDBOX",
            font=("Segoe UI", 9, "bold"),
            fg="#60a5fa",
            bg="#1e293b",
            padx=8,
            pady=3,
        )
        lbl_title.pack(side=tk.LEFT, padx=(0, 12))

        # Settlement Teleport Combobox
        tk.Label(top_bar, text="Settlement:", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#1a202c").pack(side=tk.LEFT, padx=(0, 4))
        self.cb_settlement = ttk.Combobox(top_bar, state="readonly", width=22, font=("Segoe UI", 8))
        self.cb_settlement.pack(side=tk.LEFT, padx=(0, 4))

        set_names = []
        for s in self.world_spec.settlements:
            site_t = getattr(s, "site_type", "plains").capitalize()
            set_names.append(f"{s.name} ({site_t})")
        self.cb_settlement["values"] = set_names
        if set_names:
            self.cb_settlement.current(0)

        btn_tp = tk.Button(
            top_bar,
            text="🚀 Teleport",
            font=("Segoe UI", 8, "bold"),
            bg="#3b82f6",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._on_teleport_click,
        )
        btn_tp.pack(side=tk.LEFT, padx=(0, 14))

        # View Mode Toggle Button
        self.btn_view_mode = tk.Button(
            top_bar,
            text="👁 View: 3D Perspective (V)",
            font=("Segoe UI", 8),
            bg="#334155",
            fg="#f8fafc",
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._toggle_view_mode,
        )
        self.btn_view_mode.pack(side=tk.LEFT, padx=(0, 6))

        # HUD Toggle Button
        self.btn_hud = tk.Button(
            top_bar,
            text="📊 HUD (F3)",
            font=("Segoe UI", 8),
            bg="#334155",
            fg="#f8fafc",
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._toggle_hud,
        )
        self.btn_hud.pack(side=tk.LEFT, padx=(0, 6))

        # Inventory Replenish Button
        btn_inv = tk.Button(
            top_bar,
            text="🎒 Refill Inventory",
            font=("Segoe UI", 8),
            bg="#334155",
            fg="#f8fafc",
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._refill_inventory,
        )
        btn_inv.pack(side=tk.LEFT, padx=(0, 6))

        # Help / Instructions
        btn_help = tk.Button(
            top_bar,
            text="❓ Controls Guide",
            font=("Segoe UI", 8),
            bg="#334155",
            fg="#cbd5e1",
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._show_controls_dialog,
        )
        btn_help.pack(side=tk.RIGHT)

        # Minecraft Anvil Export
        btn_export = tk.Button(
            top_bar,
            text="📥 Export Java (.mca)",
            font=("Segoe UI", 8, "bold"),
            bg="#059669",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._export_anvil,
        )
        btn_export.pack(side=tk.RIGHT, padx=6)

        # 2. Main 3D Viewport Canvas
        self.canvas = tk.Canvas(
            self,
            bg="#729ef5",
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Focus canvas on start
        self.canvas.focus_set()

    def _bind_events(self) -> None:
        # Keyboard controls
        self.bind("<KeyPress>", self._on_key_press)
        self.bind("<KeyRelease>", self._on_key_release)

        # Mouse controls
        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Button-2>", self._on_middle_click)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)

        # Mouse look via drag
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_stop)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<Motion>", self._on_mouse_motion)

    # -------------------------------------------------------------------------
    # Player Teleportation & Settlement Management
    # -------------------------------------------------------------------------
    def _teleport_to_settlement_id(self, settlement_id: str) -> None:
        site = self.world_spec.get_site(settlement_id)
        if not site and self.world_spec.settlements:
            site = self.world_spec.settlements[0]

        if site:
            bx, bz = self.engine.voxel_spec.tile_to_block_center(site.x, site.y)
            by = float(self.engine.voxel_spec.get_interpolated_height(bx, bz) + 2)
            self.engine.player.x = float(bx)
            self.engine.player.y = by
            self.engine.player.z = float(bz)
            self.engine.player.vx = 0.0
            self.engine.player.vy = 0.0
            self.engine.player.vz = 0.0
            self.engine.ensure_chunks_around_player(radius=2)
            self._add_notification(f"🚀 Teleported to {site.name} ({site.site_type})")

    def _on_teleport_click(self) -> None:
        idx = self.cb_settlement.current()
        if 0 <= idx < len(self.world_spec.settlements):
            s = self.world_spec.settlements[idx]
            self._teleport_to_settlement_id(s.id)

    # -------------------------------------------------------------------------
    # Input Handling
    # -------------------------------------------------------------------------
    def _on_key_press(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        self.keys_down.add(key)

        # Hotbar selection 1-9
        if key in "123456789":
            slot = int(key) - 1
            if 0 <= slot < len(HOTBAR_ITEMS):
                self._select_hotbar_slot(slot)

        # Toggle view mode (V or Tab)
        elif key in ("v", "tab"):
            self._toggle_view_mode()

        # Toggle HUD (F3)
        elif key == "f3":
            self._toggle_hud()

        # Jump (Space)
        elif key == "space":
            self.engine.jump()

        # Refill inventory (E)
        elif key == "e":
            self._refill_inventory()

    def _on_key_release(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        self.keys_down.discard(key)

    def _on_drag_start(self, event: tk.Event) -> None:
        self._last_mouse_x = event.x
        self._last_mouse_y = event.y
        self._mouse_drag_active = True

    def _on_drag_stop(self, event: tk.Event) -> None:
        self._mouse_drag_active = False

    def _on_drag_motion(self, event: tk.Event) -> None:
        dx = event.x - self._last_mouse_x
        dy = event.y - self._last_mouse_y
        self._last_mouse_x = event.x
        self._last_mouse_y = event.y

        # Smooth camera rotation
        sensitivity = 0.25
        self.engine.player.yaw = (self.engine.player.yaw + dx * sensitivity) % 360.0
        self.engine.player.pitch = max(-85.0, min(85.0, self.engine.player.pitch + dy * sensitivity))

    def _on_mouse_motion(self, event: tk.Event) -> None:
        # Subtle look parallax if mouse is moved near edges
        pass

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        if event.delta > 0:
            new_slot = (self.hotbar_index - 1) % len(HOTBAR_ITEMS)
        else:
            new_slot = (self.hotbar_index + 1) % len(HOTBAR_ITEMS)
        self._select_hotbar_slot(new_slot)

    def _select_hotbar_slot(self, slot: int) -> None:
        self.hotbar_index = slot
        self.engine.player.selected_block = HOTBAR_ITEMS[slot][0]
        block_name = HOTBAR_ITEMS[slot][1]
        self._add_notification(f"Selected: {block_name}")

    def _toggle_view_mode(self) -> None:
        if self.view_mode == "first_person":
            self.view_mode = "isometric"
            self.btn_view_mode.config(text="👁 View: Isometric 3D (V)")
            self._add_notification("Switched to Isometric Tactical 3D View")
        else:
            self.view_mode = "first_person"
            self.btn_view_mode.config(text="👁 View: 3D Perspective (V)")
            self._add_notification("Switched to First-Person 3D Perspective")

    def _toggle_hud(self) -> None:
        self.show_hud = not self.show_hud

    def _refill_inventory(self) -> None:
        for bid, _, _ in HOTBAR_ITEMS:
            self.engine.player.inventory[bid] = 64
        self._add_notification("🎒 Inventory replenished (64x all blocks)")

    # -------------------------------------------------------------------------
    # Block Breaking & Placing
    # -------------------------------------------------------------------------
    def _on_left_click(self, event: tk.Event) -> None:
        """Left-Click: Break targeted voxel block."""
        res = self.engine.break_targeted_block()
        if res:
            bx, by, bz, bid = res
            bname = BLOCK_NAMES.get(bid, "block").replace("minecraft:", "").replace("_", " ").title()
            self._add_notification(f"⛏ Mined {bname} at ({bx}, {by}, {bz})")
            self._check_settlement_construction_impact()

    def _on_right_click(self, event: tk.Event) -> None:
        """Right-Click: Place selected voxel block against targeted face."""
        res = self.engine.place_block_against_target()
        if res:
            bx, by, bz = res
            bid = self.engine.player.selected_block
            bname = BLOCK_NAMES.get(bid, "block").replace("minecraft:", "").replace("_", " ").title()
            self._add_notification(f"🧱 Placed {bname} at ({bx}, {by}, {bz})")
            self._check_settlement_construction_impact()

    def _on_middle_click(self, event: tk.Event) -> None:
        """Middle-Click: Pick targeted block into hand."""
        hit = self.engine.raycast_block(5.0)
        if hit:
            _, _, bid = hit
            for idx, (h_bid, _, _) in enumerate(HOTBAR_ITEMS):
                if h_bid == bid:
                    self._select_hotbar_slot(idx)
                    return
            self.engine.player.selected_block = bid
            bname = BLOCK_NAMES.get(bid, "block").replace("minecraft:", "").title()
            self._add_notification(f"Picked: {bname}")

    def _check_settlement_construction_impact(self) -> None:
        """Runs Construction Analyzer to detect fortifications or mining impacts."""
        if not self.engine.chunk_deltas:
            return
        records = self.analyzer.analyze_chunk_deltas(self.engine.chunk_deltas)
        for r in records:
            if r.summary:
                self._add_notification(f"🏰 {r.settlement_name}: {r.summary}")

    def _add_notification(self, text: str) -> None:
        self._notifications.append({
            "text": text,
            "created_at": time.time(),
            "duration": 3.0,
        })
        if len(self._notifications) > 6:
            self._notifications.pop(0)

    # -------------------------------------------------------------------------
    # Game Loop & Physics Execution
    # -------------------------------------------------------------------------
    def _game_loop(self) -> None:
        if not self.is_running:
            return

        t_start = time.perf_counter()

        # 1. Gather movement vector from keys
        move_fwd = 0.0
        move_strafe = 0.0

        if "w" in self.keys_down or "up" in self.keys_down:
            move_fwd += 1.0
        if "s" in self.keys_down or "down" in self.keys_down:
            move_fwd -= 1.0
        if "a" in self.keys_down:
            move_strafe -= 1.0
        if "d" in self.keys_down:
            move_strafe += 1.0

        # Keyboard turning (arrow keys left/right)
        if "left" in self.keys_down:
            self.engine.player.yaw = (self.engine.player.yaw - 3.5) % 360.0
        if "right" in self.keys_down:
            self.engine.player.yaw = (self.engine.player.yaw + 3.5) % 360.0

        # Sprinting
        self.engine.player.is_sprinting = ("shift_l" in self.keys_down or "shift_r" in self.keys_down)

        # 2. Physics Simulation Tick (dt = 0.04s)
        self.engine.tick_physics(dt=0.04, move_forward=move_fwd, move_strafe=move_strafe)

        # 3. Render 3D Frame
        self._render_frame()

        # 4. FPS Measurement
        dt = time.perf_counter() - t_start
        self._frame_times.append(dt)
        if len(self._frame_times) > 15:
            self._frame_times.pop(0)
            avg_dt = sum(self._frame_times) / len(self._frame_times)
            if avg_dt > 0.0001:
                self._fps = 1.0 / avg_dt

        # Target ~30 FPS (33ms interval)
        delay = max(10, int((0.033 - dt) * 1000))
        self.after(delay, self._game_loop)

    # -------------------------------------------------------------------------
    # 3D Rendering Pipeline
    # -------------------------------------------------------------------------
    def _render_frame(self) -> None:
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 100 or h < 100:
            return

        self.canvas.delete("all")

        if self.view_mode == "first_person":
            self._render_first_person(w, h)
        else:
            self._render_isometric(w, h)

        # Overlay HUD and Hotbar
        self._render_overlays(w, h)

    def _render_first_person(self, w: int, h: int) -> None:
        cx = w / 2.0
        cy = h / 2.0
        fov = 420.0

        px, py, pz = self.engine.player.get_eye_position()
        yaw_rad = math.radians(self.engine.player.yaw)
        pitch_rad = math.radians(self.engine.player.pitch)

        cos_y, sin_y = math.cos(yaw_rad), math.sin(yaw_rad)
        cos_p, sin_p = math.cos(pitch_rad), math.sin(pitch_rad)

        # Sky Horizon Line based on pitch
        horizon_y = cy + math.tan(pitch_rad) * fov
        self.canvas.create_rectangle(0, 0, w, horizon_y, fill="#78a7ff", outline="")
        self.canvas.create_rectangle(0, horizon_y, w, h, fill="#558833", outline="")

        # Visible Faces Definition: (nx, ny, nz, [4 vertex offsets], face_key)
        FACES = (
            (0, 1, 0, ((0,1,0), (1,1,0), (1,1,1), (0,1,1)), 0),  # Top
            (0, -1, 0, ((0,0,1), (1,0,1), (1,0,0), (0,0,0)), 2), # Bottom
            (1, 0, 0, ((1,0,0), (1,0,1), (1,1,1), (1,1,0)), 1),  # East
            (-1, 0, 0, ((0,0,1), (0,0,0), (0,1,0), (0,1,1)), 1), # West
            (0, 0, 1, ((1,0,1), (0,0,1), (0,1,1), (1,1,1)), 1),  # North
            (0, 0, -1, ((0,0,0), (1,0,0), (1,1,0), (0,1,0)), 1), # South
        )

        r_horiz = 10
        r_vert = 6
        min_x = int(px) - r_horiz
        max_x = int(px) + r_horiz
        min_z = int(pz) - r_horiz
        max_z = int(pz) + r_horiz
        min_y = max(1, int(py) - r_vert)
        max_y = min(254, int(py) + r_vert)

        visible_polys: List[Tuple[float, str, str, List[float]]] = []

        for bx in range(min_x, max_x + 1):
            for bz in range(min_z, max_z + 1):
                for by in range(min_y, max_y + 1):
                    b = self.engine.get_block_at(bx, by, bz)
                    if b == BLOCK_AIR:
                        continue

                    colors = BLOCK_FACE_COLORS.get(b, ("#7a7e80", "#6a6e70", "#545759"))

                    for nx, ny, nz, v_offs, col_idx in FACES:
                        # 1. Neighbor culling: only show face if neighbor is air or transparent water
                        neighbor = self.engine.get_block_at(bx + nx, by + ny, bz + nz)
                        if neighbor != BLOCK_AIR and (neighbor != BLOCK_WATER or b == BLOCK_WATER):
                            continue

                        # 2. Backface culling: face normal towards camera
                        fcx = bx + 0.5 + nx * 0.5
                        fcy = by + 0.5 + ny * 0.5
                        fcz = bz + 0.5 + nz * 0.5
                        dot = (px - fcx) * nx + (py - fcy) * ny + (pz - fcz) * nz
                        if dot <= 0:
                            continue

                        # 3. Project 4 vertices into camera & screen space
                        all_front = True
                        tot_zr = 0.0
                        pts: List[float] = []

                        for ox, oy, oz in v_offs:
                            rel_x = (bx + ox) - px
                            rel_y = (by + oy) - py
                            rel_z = (bz + oz) - pz

                            # Yaw rotation
                            xc = rel_x * cos_y + rel_z * sin_y
                            zc = -rel_x * sin_y + rel_z * cos_y
                            yc = rel_y

                            # Pitch rotation
                            yr = yc * cos_p + zc * sin_p
                            zr = -yc * sin_p + zc * cos_p

                            if zr <= 0.25:
                                all_front = False
                                break

                            tot_zr += zr
                            sx = cx + (xc / zr) * fov
                            sy = cy - (yr / zr) * fov
                            pts.extend([sx, sy])

                        if all_front and len(pts) == 8:
                            avg_z = tot_zr * 0.25
                            fill_col = colors[col_idx]
                            visible_polys.append((avg_z, fill_col, "#2a2b2d", pts))

        # Painter's Algorithm: Sort back-to-front
        visible_polys.sort(key=lambda item: item[0], reverse=True)

        for _, fill_col, outline_col, pts in visible_polys:
            self.canvas.create_polygon(*pts, fill=fill_col, outline=outline_col, width=1)

        # 4. Highlight Targeted Block Outline
        hit = self.engine.raycast_block(5.0)
        if hit:
            (tx, ty, tz), _, _ = hit
            self._render_targeted_block_box(tx, ty, tz, px, py, pz, cos_y, sin_y, cos_p, sin_p, cx, cy, fov)

        # 5. Center Crosshair
        ch_size = 8
        self.canvas.create_line(cx - ch_size, cy, cx + ch_size, cy, fill="#ffffff", width=2)
        self.canvas.create_line(cx, cy - ch_size, cx, cy + ch_size, fill="#ffffff", width=2)

    def _render_targeted_block_box(
        self,
        tx: int, ty: int, tz: int,
        px: float, py: float, pz: float,
        cos_y: float, sin_y: float, cos_p: float, sin_p: float,
        cx: float, cy: float, fov: float,
    ) -> None:
        """Renders cyan 3D wireframe outline around currently targeted block."""
        EDGES = [
            ((0,0,0), (1,0,0)), ((1,0,0), (1,0,1)), ((1,0,1), (0,0,1)), ((0,0,1), (0,0,0)),
            ((0,1,0), (1,1,0)), ((1,1,0), (1,1,1)), ((1,1,1), (0,1,1)), ((0,1,1), (0,1,0)),
            ((0,0,0), (0,1,0)), ((1,0,0), (1,1,0)), ((1,0,1), (1,1,1)), ((0,0,1), (0,1,1)),
        ]

        def project_pt(ox: int, oy: int, oz: int) -> Optional[Tuple[float, float]]:
            rel_x = (tx + ox) - px
            rel_y = (ty + oy) - py
            rel_z = (tz + oz) - pz
            xc = rel_x * cos_y + rel_z * sin_y
            zc = -rel_x * sin_y + rel_z * cos_y
            yc = rel_y
            yr = yc * cos_p + zc * sin_p
            zr = -yc * sin_p + zc * cos_p
            if zr <= 0.2:
                return None
            return (cx + (xc / zr) * fov, cy - (yr / zr) * fov)

        for p1, p2 in EDGES:
            s1 = project_pt(*p1)
            s2 = project_pt(*p2)
            if s1 and s2:
                self.canvas.create_line(s1[0], s1[1], s2[0], s2[1], fill="#00ffff", width=2)

    def _render_isometric(self, w: int, h: int) -> None:
        """Renders 3D Tactical Isometric view with player character representation."""
        cx = w / 2.0
        cy = h / 2.0
        scale = 16.0

        px = self.engine.player.x
        py = self.engine.player.y
        pz = self.engine.player.z

        self.canvas.create_rectangle(0, 0, w, h, fill="#1e293b", outline="")

        r = 8
        min_x = int(px) - r
        max_x = int(px) + r
        min_z = int(pz) - r
        max_z = int(pz) + r
        min_y = max(1, int(py) - 4)
        max_y = min(254, int(py) + 5)

        for bz in range(min_z, max_z + 1):
            for bx in range(min_x, max_x + 1):
                for by in range(min_y, max_y + 1):
                    b = self.engine.get_block_at(bx, by, bz)
                    if b == BLOCK_AIR:
                        continue

                    # Only draw if block above is air
                    if self.engine.get_block_at(bx, by + 1, bz) != BLOCK_AIR:
                        continue

                    dx = bx - px
                    dz = bz - pz
                    dy = by - py

                    # Isometric Projection
                    iso_x = cx + (dx - dz) * scale
                    iso_y = cy + (dx + dz) * (scale * 0.5) - dy * scale

                    colors = BLOCK_FACE_COLORS.get(b, ("#7a7e80", "#6a6e70", "#545759"))

                    # Top Diamond Face
                    diamond = [
                        iso_x, iso_y - scale * 0.5,
                        iso_x + scale, iso_y,
                        iso_x, iso_y + scale * 0.5,
                        iso_x - scale, iso_y,
                    ]
                    self.canvas.create_polygon(*diamond, fill=colors[0], outline="#242526")

        # Draw Player Character Avatar in Isometric View
        self.canvas.create_oval(cx - 6, cy - 14, cx + 6, cy - 2, fill="#e5c07b", outline="#000000")
        self.canvas.create_rectangle(cx - 7, cy - 2, cx + 7, cy + 12, fill="#0284c7", outline="#000000")
        self.canvas.create_line(cx, cy, cx - 12 * math.sin(math.radians(self.engine.player.yaw)), cy + 12 * math.cos(math.radians(self.engine.player.yaw)), fill="#facc15", width=2)

    # -------------------------------------------------------------------------
    # Overlays: Hotbar, HUD, Notifications
    # -------------------------------------------------------------------------
    def _render_overlays(self, w: int, h: int) -> None:
        # 1. Hotbar HUD (Bottom Center)
        slot_w = 46
        slot_h = 46
        tot_w = slot_w * len(HOTBAR_ITEMS)
        start_x = (w - tot_w) / 2.0
        start_y = h - 64

        # Background Tray
        self.canvas.create_rectangle(
            start_x - 4, start_y - 4,
            start_x + tot_w + 4, start_y + slot_h + 4,
            fill="#0f172a", outline="#334155", width=2,
        )

        for i, (bid, bname, bcolor) in enumerate(HOTBAR_ITEMS):
            x0 = start_x + i * slot_w
            y0 = start_y
            x1 = x0 + slot_w
            y1 = y0 + slot_h

            is_sel = (i == self.hotbar_index)
            border_col = "#f59e0b" if is_sel else "#1e293b"
            border_w = 3 if is_sel else 1

            self.canvas.create_rectangle(x0 + 2, y0 + 2, x1 - 2, y1 - 2, fill="#1e293b", outline=border_col, width=border_w)

            # Block Icon Swatch
            self.canvas.create_rectangle(x0 + 10, y0 + 8, x1 - 10, y1 - 16, fill=bcolor, outline="#000000")

            # Slot number & count
            count = self.engine.player.inventory.get(bid, 0)
            self.canvas.create_text(x0 + 6, y0 + 8, text=str(i + 1), font=("Segoe UI", 7, "bold"), fill="#94a3b8", anchor="nw")
            self.canvas.create_text(x1 - 6, y1 - 6, text=str(count), font=("Consolas", 8, "bold"), fill="#ffffff", anchor="se")

        # 2. Floating Action Notifications (Bottom Left, above hotbar)
        now = time.time()
        self._notifications = [n for n in self._notifications if now - n["created_at"] < n["duration"]]
        notif_y = h - 80
        for n in reversed(self._notifications):
            age = now - n["created_at"]
            alpha = max(0.0, 1.0 - (age / n["duration"]))
            fg_col = "#f8fafc" if alpha > 0.3 else "#64748b"

            self.canvas.create_text(
                20, notif_y,
                text=n["text"],
                font=("Segoe UI", 9, "bold"),
                fill=fg_col,
                anchor="w",
            )
            notif_y -= 20

        # 3. Debug HUD (F3 Mode)
        if self.show_hud:
            p = self.engine.player
            tile_x, tile_z = self.engine.voxel_spec.block_to_tile(int(p.x), int(p.z))
            biome_id = self.engine.voxel_spec.grid.biome[self.engine.voxel_spec.grid.index(tile_x, tile_z)]
            biome_name = BIOME_NAMES[biome_id] if 0 <= biome_id < len(BIOME_NAMES) else "Unknown"

            # Target Block Info
            target_str = "None"
            hit = self.engine.raycast_block(5.0)
            if hit:
                (hx, hy, hz), (nx, ny, nz), hbid = hit
                hb_name = BLOCK_NAMES.get(hbid, "block").replace("minecraft:", "")
                target_str = f"{hb_name} at ({hx}, {hy}, {hz}) [Normal: ({nx},{ny},{nz})]"

            # Nearest Settlement
            near_set = "None"
            min_dist = 9999.0
            for s in self.world_spec.settlements:
                sbx, sbz = self.engine.voxel_spec.tile_to_block_center(s.x, s.y)
                d = math.sqrt((p.x - sbx) ** 2 + (p.z - sbz) ** 2)
                if d < min_dist:
                    min_dist = d
                    def_val = getattr(s, "defensibility", 1.0)
                    near_set = f"{s.name} ({int(d)}m away) • Defense: {def_val:.2f}"

            total_deltas = sum(len(d) for d in self.engine.chunk_deltas.values())

            hud_lines = [
                f"MINEMESIS 3D VOXEL SANDBOX v0.5.4 | FPS: {self._fps:.1f}",
                f"XYZ: {p.x:.2f} / {p.y:.2f} / {p.z:.2f}  (Chunk: [{int(p.x)//16}, {int(p.z)//16}])",
                f"Facing: Yaw {p.yaw:.1f}° | Pitch {p.pitch:.1f}°",
                f"Biome: {biome_name} (Tile {tile_x}, {tile_z})",
                f"Targeting: {target_str}",
                f"Modified Blocks: {total_deltas} chunk deltas recorded",
                f"Nearest Settlement: {near_set}",
                f"Controls: [WASD] Move  [Space] Jump  [L-Click] Mine  [R-Click] Place  [1-9] Hotbar  [V] View  [F3] HUD",
            ]

            # Background Box for HUD
            box_h = len(hud_lines) * 16 + 12
            self.canvas.create_rectangle(10, 10, 680, 10 + box_h, fill="#0f172a", outline="#334155", width=1)

            for i, line in enumerate(hud_lines):
                self.canvas.create_text(
                    18, 18 + i * 16,
                    text=line,
                    font=("Consolas", 8),
                    fill="#38bdf8" if i == 0 else "#e2e8f0",
                    anchor="nw",
                )

    # -------------------------------------------------------------------------
    # Dialogs & Export
    # -------------------------------------------------------------------------
    def _export_anvil(self) -> None:
        """Exports current settlement region into Minecraft Java Anvil (.mca) format."""
        try:
            from translators.voxel.minecraft_export import export_settlement_region_to_anvil
            out_dir = Path("releases") / "exports" / "minecraft_sandbox_export"
            s0 = self.world_spec.settlements[0] if self.world_spec.settlements else None
            sid = s0.id if s0 else "set_0"
            out_file = export_settlement_region_to_anvil(self.world_spec, sid, out_dir)
            messagebox.showinfo("Export Success", f"Region exported to Java Anvil format:\n{out_file.resolve()}")
        except Exception as e:
            log_error("Anvil export failed", e)
            messagebox.showerror("Export Error", f"Failed to export region:\n{e}")

    def _show_controls_dialog(self) -> None:
        msg = (
            "🎮 Minemesis 3D Voxel Sandbox Controls:\n\n"
            "• Movement: W, A, S, D (or Arrow Keys)\n"
            "• Jump: Spacebar\n"
            "• Sprint: Hold Shift\n"
            "• Look Around: Click & Drag mouse on screen (or Left/Right arrows)\n"
            "• Mine / Break Block: Left-Click on targeted block\n"
            "• Place Selected Block: Right-Click on targeted face\n"
            "• Pick Block: Middle-Click on targeted block\n"
            "• Hotbar Selection: Number keys 1 - 9 (or Mouse Wheel)\n"
            "• Toggle View: V or Tab (First-Person 3D vs. Isometric 3D)\n"
            "• Toggle HUD: F3 (coordinates, biome, target, settlement defense)\n"
            "• Refill Inventory: E\n"
            "• Settlement Teleport: Select from top dropdown and click 'Teleport'\n\n"
            "Building walls or mining within settlement bounds automatically updates\n"
            "settlement defensibility and economic profiles in real-time!"
        )
        messagebox.showinfo("Voxel Sandbox Controls", msg)

    def _on_close(self) -> None:
        global _active_voxel_window
        self.is_running = False
        _active_voxel_window = None
        self.destroy()


def open_voxel_window(
    parent: Optional[tk.Widget] = None,
    world_spec: Optional[WorldSpec] = None,
    settlement_id: Optional[str] = None,
    spawn_coords: Optional[Tuple[float, float, float]] = None,
) -> VoxelInteractionWindow:
    """
    Entry point to launch the 3D Voxel Sandbox Window from any tab, toolbar, or menu.
    """
    global _active_voxel_window
    if _active_voxel_window is not None and _active_voxel_window.winfo_exists():
        _active_voxel_window.lift()
        _active_voxel_window.focus_force()
        if settlement_id:
            _active_voxel_window._teleport_to_settlement_id(settlement_id)
        return _active_voxel_window

    win = VoxelInteractionWindow(
        parent=parent,
        world_spec=world_spec,
        settlement_id=settlement_id,
        spawn_coords=spawn_coords,
    )
    return win
