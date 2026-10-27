"""
Map Tab for Minemesis Viewer V2.

Interactive 2D Continental Geography and Settlement Catchment Explorer:
- Renders 300x300 continental geography using fast Tkinter PhotoImage PPM format.
- Biome color-coding with elevation relief shading.
- River networks, A* road networks, and settlement markers.
- Interactive Zoom (1x to 4x), Pan, and Tile Inspector (Elevation, Biome, River, Travel Cost).
- Settlement Catchment Breakdown (Farmland, Forest, Ore, Fish, Stone, Defensibility).
- Minecraft Java (.mca) Region Export Controls.
"""

from __future__ import annotations
import math
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Optional

from viewer.core.bus import bus
from viewer.core.logging import log_error
from viewer.core.session import session
from viewer.ui.tabs.base import BaseTab, register_tab
from viewer.ui.theme import theme
from minemesis.terrain.terrain_engine import (
    generate_terrain,
    TerrainGrid,
    BIOME_NAMES,
    BIOME_OCEAN,
    BIOME_BEACH,
    BIOME_GRASSLAND,
    BIOME_FOREST,
    BIOME_TAIGA,
    BIOME_SNOW,
    BIOME_DESERT,
    BIOME_SWAMP,
    BIOME_HILLS,
    BIOME_MOUNTAIN,
    SEA_LEVEL,
)
from minemesis.terrain.catchment import place_settlements, analyze_catchment
from minemesis.terrain.roads import generate_road_network
from minemesis.systems.world_spec import SettlementSite


# Biome RGB Palette
BIOME_PALETTE = {
    BIOME_OCEAN: (28, 64, 120),
    BIOME_BEACH: (224, 204, 140),
    BIOME_GRASSLAND: (92, 175, 75),
    BIOME_FOREST: (34, 118, 52),
    BIOME_TAIGA: (42, 90, 72),
    BIOME_SNOW: (230, 242, 252),
    BIOME_DESERT: (226, 186, 108),
    BIOME_SWAMP: (68, 88, 58),
    BIOME_HILLS: (138, 148, 118),
    BIOME_MOUNTAIN: (115, 115, 122),
}


@register_tab("Map", order=2)
class MapTab(BaseTab):
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self.world_seed = 42
        self.grid: Optional[TerrainGrid] = None
        self.settlements: list[SettlementSite] = []
        self.roads: list[WorldRoad] = []
        self.zoom_level = 2
        self.photo_base: Optional[tk.PhotoImage] = None
        self.photo_display: Optional[tk.PhotoImage] = None
        self.selected_settlement_id: Optional[str] = None

        c = theme.colors

        # Top Control Bar
        top_bar = tk.Frame(self, bg=c["panel_bg"], padx=12, pady=8)
        top_bar.pack(fill=tk.X, padx=12, pady=(10, 6))

        tk.Label(top_bar, text="World Seed:", font=("Segoe UI", 9, "bold"), fg=c["fg"], bg=c["panel_bg"]).pack(side=tk.LEFT, padx=(0, 6))
        self.entry_seed = tk.Entry(top_bar, font=("Segoe UI", 9), width=10, bg=c["bg"], fg=c["fg"], insertbackground=c["fg"])
        self.entry_seed.pack(side=tk.LEFT, padx=(0, 8))
        self.entry_seed.insert(0, "42")

        self.btn_load_seed = tk.Button(
            top_bar,
            text="Generate / View",
            font=("Segoe UI", 8, "bold"),
            bg=c["accent"],
            fg="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._on_generate_click,
        )
        self.btn_load_seed.pack(side=tk.LEFT, padx=(0, 16))

        # Zoom Controls
        tk.Label(top_bar, text="Zoom:", font=("Segoe UI", 9, "bold"), fg=c["fg"], bg=c["panel_bg"]).pack(side=tk.LEFT, padx=(0, 6))
        self.btn_zoom_out = tk.Button(
            top_bar,
            text=" - ",
            font=("Segoe UI", 8, "bold"),
            bg=c["card_bg"],
            fg=c["fg"],
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._zoom_out,
        )
        self.btn_zoom_out.pack(side=tk.LEFT, padx=2)

        self.lbl_zoom = tk.Label(top_bar, text="2x", font=("Segoe UI", 9), fg=c["fg"], bg=c["panel_bg"], width=4)
        self.lbl_zoom.pack(side=tk.LEFT, padx=2)

        self.btn_zoom_in = tk.Button(
            top_bar,
            text=" + ",
            font=("Segoe UI", 8, "bold"),
            bg=c["card_bg"],
            fg=c["fg"],
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2",
            command=self._zoom_in,
        )
        self.btn_zoom_in.pack(side=tk.LEFT, padx=(2, 16))

        # Layer Checkboxes
        self.var_show_rivers = tk.BooleanVar(value=True)
        self.chk_rivers = tk.Checkbutton(
            top_bar,
            text="Rivers",
            variable=self.var_show_rivers,
            font=("Segoe UI", 8),
            fg=c["fg"],
            bg=c["panel_bg"],
            selectcolor=c["bg"],
            activebackground=c["panel_bg"],
            activeforeground=c["fg"],
            command=self._render_map_view,
        )
        self.chk_rivers.pack(side=tk.LEFT, padx=4)

        self.var_show_roads = tk.BooleanVar(value=True)
        self.chk_roads = tk.Checkbutton(
            top_bar,
            text="Roads",
            variable=self.var_show_roads,
            font=("Segoe UI", 8),
            fg=c["fg"],
            bg=c["panel_bg"],
            selectcolor=c["bg"],
            activebackground=c["panel_bg"],
            activeforeground=c["fg"],
            command=self._render_map_view,
        )
        self.chk_roads.pack(side=tk.LEFT, padx=4)

        self.var_show_settlements = tk.BooleanVar(value=True)
        self.chk_settlements = tk.Checkbutton(
            top_bar,
            text="Settlements",
            variable=self.var_show_settlements,
            font=("Segoe UI", 8),
            fg=c["fg"],
            bg=c["panel_bg"],
            selectcolor=c["bg"],
            activebackground=c["panel_bg"],
            activeforeground=c["fg"],
            command=self._render_map_view,
        )
        self.chk_settlements.pack(side=tk.LEFT, padx=4)

        # Status tile info readout in top bar
        self.lbl_hover_info = tk.Label(
            top_bar,
            text="Hover over map to inspect coordinates & biome",
            font=("Consolas", 8),
            fg=c["fg_muted"],
            bg=c["panel_bg"],
        )
        self.lbl_hover_info.pack(side=tk.RIGHT, padx=6)

        # Main Split Content: Left Canvas, Right Inspector
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        # Left Container: Canvas with scrollbars
        self.frame_canvas = tk.Frame(self.paned, bg=c["bg"])
        self.paned.add(self.frame_canvas, weight=3)

        self.h_scroll = tk.Scrollbar(self.frame_canvas, orient=tk.HORIZONTAL)
        self.v_scroll = tk.Scrollbar(self.frame_canvas, orient=tk.VERTICAL)
        self.canvas = tk.Canvas(
            self.frame_canvas,
            bg="#0d1117",
            xscrollcommand=self.h_scroll.set,
            yscrollcommand=self.v_scroll.set,
            highlightthickness=0,
        )
        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<Motion>", self._on_canvas_motion)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        # Right Container: Settlement & Catchment Inspector + Minecraft Exporter
        self.frame_inspector = tk.Frame(self.paned, bg=c["panel_bg"], padx=14, pady=12)
        self.paned.add(self.frame_inspector, weight=1)
        self._build_inspector_ui()

        bus.subscribe("session:loaded", lambda **kw: self.refresh())

    def _build_inspector_ui(self) -> None:
        c = theme.colors
        tk.Label(
            self.frame_inspector,
            text="Settlement & Catchment",
            font=("Segoe UI", 11, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
        ).pack(anchor="w")

        tk.Label(
            self.frame_inspector,
            text="Select a settlement to inspect 12-tile catchment endowments:",
            font=("Segoe UI", 8),
            fg=c["fg_muted"],
            bg=c["panel_bg"],
            wraplength=260,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(2, 8))

        # Settlement Dropdown
        self.cb_settlement = ttk.Combobox(self.frame_inspector, state="readonly", font=("Segoe UI", 9))
        self.cb_settlement.pack(fill=tk.X, pady=(0, 10))
        self.cb_settlement.bind("<<ComboboxSelected>>", self._on_settlement_selected)

        # Info Box Card
        self.card_info = tk.Frame(self.frame_inspector, bg=c["card_bg"], padx=10, pady=10)
        self.card_info.pack(fill=tk.X, pady=(0, 12))

        self.lbl_card_title = tk.Label(self.card_info, text="No Settlement Selected", font=("Segoe UI", 9, "bold"), fg=c["fg"], bg=c["card_bg"])
        self.lbl_card_title.pack(anchor="w")

        self.lbl_card_body = tk.Label(
            self.card_info,
            text="Coordinates: --\nBiome: --\nDefensibility: --",
            font=("Segoe UI", 8),
            fg=c["fg_muted"],
            bg=c["card_bg"],
            justify=tk.LEFT,
        )
        self.lbl_card_body.pack(anchor="w", pady=(4, 6))

        self.lbl_endowments = tk.Label(
            self.card_info,
            text="Catchment Resources (Radius 12):\n • Farmland: --\n • Forest: --\n • Ore: --\n • Fish: --\n • Stone: --",
            font=("Segoe UI", 8),
            fg=c["fg"],
            bg=c["card_bg"],
            justify=tk.LEFT,
        )
        self.lbl_endowments.pack(anchor="w")

        # Playable 3D Voxel Sandbox Section
        tk.Label(
            self.frame_inspector,
            text="Interactive 3D Voxel Sandbox",
            font=("Segoe UI", 10, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
        ).pack(anchor="w", pady=(12, 4))

        self.btn_play_voxel = tk.Button(
            self.frame_inspector,
            text="🎮 Explore in 3D Voxel Mode",
            font=("Segoe UI", 9, "bold"),
            bg="#059669",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=6,
            cursor="hand2",
            command=self._launch_settlement_in_voxel,
        )
        self.btn_play_voxel.pack(fill=tk.X, pady=(2, 8))

        # Minecraft Voxel Export Section
        tk.Label(
            self.frame_inspector,
            text="Minecraft Java Voxel Export",
            font=("Segoe UI", 10, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
        ).pack(anchor="w", pady=(8, 4))

        tk.Label(
            self.frame_inspector,
            text="Export to Anvil (.mca) Java format (1 tile = 8 blocks):",
            font=("Segoe UI", 8),
            fg=c["fg_muted"],
            bg=c["panel_bg"],
            wraplength=260,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(0, 8))

        self.btn_export_region = tk.Button(
            self.frame_inspector,
            text="Export Settlement Region (400x400)",
            font=("Segoe UI", 8, "bold"),
            bg=c["accent"],
            fg="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._export_settlement_region,
        )
        self.btn_export_region.pack(fill=tk.X, pady=3)

        self.btn_export_world = tk.Button(
            self.frame_inspector,
            text="Export Full World (2400x2400)",
            font=("Segoe UI", 8),
            bg=c["card_bg"],
            fg=c["fg"],
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._export_full_world,
        )
        self.btn_export_world.pack(fill=tk.X, pady=3)

        self.lbl_export_status = tk.Label(
            self.frame_inspector,
            text="Ready to export",
            font=("Segoe UI", 8),
            fg=c["fg_muted"],
            bg=c["panel_bg"],
            wraplength=260,
            justify=tk.LEFT,
        )
        self.lbl_export_status.pack(anchor="w", pady=(6, 0))

    def _on_generate_click(self) -> None:
        try:
            val = int(self.entry_seed.get().strip())
            self.world_seed = val
            self.load_map_data(val)
        except ValueError:
            messagebox.showerror("Invalid Seed", "Please enter a valid integer seed.")

    def _zoom_in(self) -> None:
        if self.zoom_level < 4:
            self.zoom_level += 1
            self.lbl_zoom.config(text=f"{self.zoom_level}x")
            self._render_map_view()

    def _zoom_out(self) -> None:
        if self.zoom_level > 1:
            self.zoom_level -= 1
            self.lbl_zoom.config(text=f"{self.zoom_level}x")
            self._render_map_view()

    def load_map_data(self, world_seed: int) -> None:
        """Generates or retrieves terrain grid, settlements, and roads."""
        self.world_seed = world_seed
        self.grid = generate_terrain(world_seed=self.world_seed, width=300, height=300)
        self.settlements = place_settlements(grid=self.grid, world_seed=self.world_seed, settlement_count=10, min_spacing=28)
        self.roads = generate_road_network(grid=self.grid, settlements=self.settlements)

        # Update settlement dropdown
        names = [
            f"{s.name} ({getattr(s, 'site_type', getattr(s, 'biome', 'plains')).capitalize()})"
            for s in self.settlements
        ]
        self.cb_settlement["values"] = names
        if names:
            self.cb_settlement.current(0)
            self._on_settlement_selected()

        self._create_base_ppm()
        self._render_map_view()

    def _create_base_ppm(self) -> None:
        """Builds 300x300 PPM binary buffer for high-speed rendering."""
        if not self.grid:
            return

        w, h = self.grid.width, self.grid.height
        raw_pixels = bytearray(w * h * 3)

        for y in range(h):
            row_offset = y * w * 3
            grid_row = y * w
            for x in range(w):
                idx = grid_row + x
                elev = self.grid.elevation[idx]
                biome = self.grid.biome[idx]
                has_river = (self.grid.river_flow[idx] > 0)
                is_lake = bool(self.grid.lake_flag[idx])

                # Determine base RGB
                if has_river and elev > SEA_LEVEL:
                    r, g, b = (35, 125, 220)
                elif is_lake:
                    r, g, b = (25, 80, 150)
                else:
                    r, g, b = BIOME_PALETTE.get(biome, (100, 100, 100))

                # Subtle hillshading relief
                if biome not in (BIOME_OCEAN, BIOME_BEACH) and not has_river and not is_lake:
                    shade = 0.82 + (elev / 255.0) * 0.36
                    r = min(255, int(r * shade))
                    g = min(255, int(g * shade))
                    b = min(255, int(b * shade))

                px_idx = row_offset + x * 3
                raw_pixels[px_idx] = r
                raw_pixels[px_idx + 1] = g
                raw_pixels[px_idx + 2] = b

        ppm_header = f"P6\n{w} {h}\n255\n".encode("ascii")
        self.photo_base = tk.PhotoImage(data=ppm_header + raw_pixels, format="PPM")

    def _render_map_view(self) -> None:
        """Renders scaled image, rivers, roads, and settlement markers onto Canvas."""
        if not self.photo_base:
            return

        self.canvas.delete("all")
        z = self.zoom_level
        self.photo_display = self.photo_base.zoom(z, z)

        # Draw background image
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_display)

        # Draw Roads
        if self.var_show_roads.get() and self.roads:
            for road in self.roads:
                coords = []
                r_path = road.get("path", []) if isinstance(road, dict) else getattr(road, "path", [])
                for rx, ry in r_path:
                    coords.extend([rx * z + (z // 2), ry * z + (z // 2)])
                if len(coords) >= 4:
                    self.canvas.create_line(coords, fill="#fbbf24", width=max(1, z), joinstyle=tk.ROUND, capstyle=tk.ROUND)

        # Draw Settlements
        if self.var_show_settlements.get() and self.settlements:
            for s in self.settlements:
                sx = s.x * z + (z // 2)
                sy = s.y * z + (z // 2)
                r = max(4, 3 * z)

                is_selected = (self.selected_settlement_id == s.id)
                fill_col = "#ef4444" if not is_selected else "#f59e0b"
                outline_col = "#ffffff" if is_selected else "#000000"

                self.canvas.create_oval(sx - r, sy - r, sx + r, sy + r, fill=fill_col, outline=outline_col, width=2)
                self.canvas.create_text(
                    sx,
                    sy - r - 6,
                    text=s.name,
                    fill="#ffffff",
                    font=("Segoe UI", max(7, 6 + z), "bold"),
                )

        total_w = 300 * z
        total_h = 300 * z
        self.canvas.config(scrollregion=(0, 0, total_w, total_h))

    def _on_canvas_motion(self, event: tk.Event) -> None:
        """Inspects tile under mouse cursor."""
        if not self.grid:
            return

        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        z = self.zoom_level

        tile_x = int(cx // z)
        tile_y = int(cy // z)

        if self.grid.in_bounds(tile_x, tile_y):
            idx = self.grid.index(tile_x, tile_y)
            elev = self.grid.elevation[idx]
            b_id = self.grid.biome[idx]
            b_name = BIOME_NAMES[b_id] if b_id < len(BIOME_NAMES) else "Unknown"
            flow = self.grid.river_flow[idx]
            cost = self.grid.travel_cost[idx]
            river_str = f"River flow: {flow}" if flow > 0 else "No river"

            self.lbl_hover_info.config(
                text=f"X:{tile_x:03d} Y:{tile_y:03d} | Biome: {b_name} | Elev: {elev}m | {river_str} | Travel Cost: {cost}"
            )

    def _on_canvas_click(self, event: tk.Event) -> None:
        """Selects nearest settlement on click."""
        if not self.settlements:
            return

        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        z = self.zoom_level

        tile_x = cx / z
        tile_y = cy / z

        # Find closest settlement within 12 tiles
        closest = None
        min_d = 12.0
        for s in self.settlements:
            d = math.sqrt((s.x - tile_x) ** 2 + (s.y - tile_y) ** 2)
            if d < min_d:
                min_d = d
                closest = s

        if closest:
            self.selected_settlement_id = closest.id
            for i, s in enumerate(self.settlements):
                if s.id == closest.id:
                    self.cb_settlement.current(i)
                    self._on_settlement_selected()
                    break

    def _on_settlement_selected(self, event: Optional[tk.Event] = None) -> None:
        idx = self.cb_settlement.current()
        if idx < 0 or idx >= len(self.settlements):
            return

        s = self.settlements[idx]
        self.selected_settlement_id = s.id

        def_val = getattr(s, "defensibility", getattr(s, "defensibility_score", 1.0))
        biome_str = getattr(s, "site_type", getattr(s, "biome", "Plains")).capitalize()

        self.lbl_card_title.config(text=f"{s.name}")
        self.lbl_card_body.config(
            text=f"ID: {s.id}\nLocation: Tile ({s.x}, {s.y})\nType: {biome_str}\nDefensibility: {def_val:.1f}"
        )

        # Analyze Catchment
        if self.grid:
            catchment = analyze_catchment(self.grid, s.x, s.y, radius=12)
            self.lbl_endowments.config(
                text=(
                    f"Catchment Resources (Radius 12):\n"
                    f" • Farmland:   {catchment.get('farmland', 0.0):.1f}\n"
                    f" • Forest:     {catchment.get('forest', 0.0):.1f}\n"
                    f" • Ore:        {catchment.get('ore_richness', 0.0):.1f}\n"
                    f" • Fish:       {catchment.get('fish_potential', 0.0):.1f}\n"
                    f" • Stone:      {catchment.get('stone', 0.0):.1f}\n"
                    f" • Defense:    {catchment.get('defensibility', 0.0):.1f}"
                )
            )

        self._render_map_view()

    def _launch_settlement_in_voxel(self) -> None:
        """Launches the 3D Voxel Sandbox positioned directly at the selected settlement."""
        idx = self.cb_settlement.current()
        if 0 <= idx < len(self.settlements):
            s = self.settlements[idx]
            bus.publish("voxel:launch", settlement_id=s.id)
        else:
            bus.publish("voxel:launch")

    def _export_settlement_region(self) -> None:
        """Triggers Milestone T1 Voxel Exporter for cropped settlement region."""
        idx = self.cb_settlement.current()
        if idx < 0 or idx >= len(self.settlements):
            messagebox.showinfo("Export", "Please select a settlement first.")
            return

        s = self.settlements[idx]
        self.lbl_export_status.config(text=f"Exporting 400x400 voxel region for {s.name}...")
        self.update_idletasks()

        try:
            from translators.voxel.minecraft_export import export_settlement_region_to_anvil
            from minemesis.systems.world_spec import WorldSpec

            spec = WorldSpec(
                world_seed=self.world_seed,
                map_width=300,
                map_height=300,
                settlements=tuple(self.settlements),
                roads=tuple(self.roads),
                generator_version="T1",
            )

            out_dir = Path("releases") / "exports" / f"minecraft_region_{s.id}"
            out_file = export_settlement_region_to_anvil(
                world_spec=spec,
                settlement_id=s.id,
                output_dir=out_dir,
            )
            self.lbl_export_status.config(text=f"Exported: {out_file.name} (Java 1.20/1.21 Anvil format)")
            messagebox.showinfo("Export Successful", f"Settlement region successfully exported to:\n{out_file.resolve()}")
        except Exception as e:
            log_error("Failed to export settlement region", e)
            self.lbl_export_status.config(text=f"Export failed: {e}")
            messagebox.showerror("Export Failed", f"Error exporting region:\n{e}")

    def _export_full_world(self) -> None:
        """Triggers Milestone T1 Voxel Exporter for full 2400x2400 block continent."""
        self.lbl_export_status.config(text="Exporting full 2400x2400 world (this takes ~3-5 seconds)...")
        self.update_idletasks()

        try:
            from translators.voxel.minecraft_export import export_full_world_to_anvil
            from minemesis.systems.world_spec import WorldSpec

            spec = WorldSpec(
                world_seed=self.world_seed,
                map_width=300,
                map_height=300,
                settlements=tuple(self.settlements),
                roads=tuple(self.roads),
                generator_version="T1",
            )

            out_dir = Path("releases") / "exports" / "minecraft_full_world"
            out_files = export_full_world_to_anvil(
                world_spec=spec,
                output_dir=out_dir,
            )
            self.lbl_export_status.config(text=f"Exported {len(out_files)} Anvil (.mca) region files!")
            messagebox.showinfo("Export Successful", f"Full world successfully exported {len(out_files)} region files to:\n{out_dir.resolve()}")
        except Exception as e:
            log_error("Failed to export full world", e)
            self.lbl_export_status.config(text=f"Export failed: {e}")
            messagebox.showerror("Export Failed", f"Error exporting world:\n{e}")

    def refresh(self) -> None:
        """Loads map from current session database or defaults."""
        self.clear_error()
        if session.db:
            w_seed = int(session.db.meta.get("world_seed", 42))
            self.entry_seed.delete(0, tk.END)
            self.entry_seed.insert(0, str(w_seed))
            self.load_map_data(w_seed)
        else:
            self.load_map_data(42)
