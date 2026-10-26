"""
World & Census Tab for Viewer V2.
Displays population charts over time, vital rates (births/deaths), and settlement comparisons.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Any

from viewer.core.bus import bus
from viewer.core.logging import log_error
from viewer.core.session import session
from viewer.services.census import census_service
from viewer.ui.tabs.base import BaseTab, register_tab
from viewer.ui.theme import theme
from viewer.ui.widgets.chart import CanvasChart


@register_tab("World & Census", order=7)
class WorldTab(BaseTab):
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        c = theme.colors

        # Top Summary Header
        self.summary_card = tk.Frame(self, bg=c["panel_bg"], padx=16, pady=10)
        self.summary_card.pack(fill=tk.X, padx=12, pady=(10, 8))

        self.lbl_title = tk.Label(self.summary_card, text="World Demographics & Census Dynamics", font=("Segoe UI", 12, "bold"), fg=c["fg"], bg=c["panel_bg"])
        self.lbl_title.pack(anchor="w")

        self.lbl_stats = tk.Label(self.summary_card, text="--", font=("Segoe UI", 8), fg=c["fg_muted"], bg=c["panel_bg"])
        self.lbl_stats.pack(anchor="w", pady=(2, 0))

        # Sub Notebook for charts
        self.sub_notebook = ttk.Notebook(self)
        self.sub_notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        # Chart 1: Total & Settlement Population
        self.tab_pop = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_pop, text="Population Over Time")
        self.chart_pop = CanvasChart(self.tab_pop)
        self.chart_pop.pack(fill=tk.BOTH, expand=True)

        # Chart 2: Vital Rates (Births vs Deaths)
        self.tab_vitals = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_vitals, text="Annual Births & Deaths")
        self.chart_vitals = CanvasChart(self.tab_vitals)
        self.chart_vitals.pack(fill=tk.BOTH, expand=True)

        # Chart 3: Settlement Distribution
        self.tab_dist = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_dist, text="Settlement Comparison")
        self.chart_dist = CanvasChart(self.tab_dist)
        self.chart_dist.pack(fill=tk.BOTH, expand=True)

        # Tab 4: 2D Macro World Map & Replay Controller (Milestone 6)
        self.tab_map = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_map, text="Macro World Map & Replay")
        self._build_macro_map_tab()

        bus.subscribe("session:loaded", lambda **kw: self.refresh())

    def _build_macro_map_tab(self) -> None:
        c = theme.colors
        top_bar = tk.Frame(self.tab_map, bg=c["panel_bg"], padx=10, pady=6)
        top_bar.pack(fill=tk.X, pady=(0, 6))

        tk.Label(top_bar, text="Target Replay Year:", font=("Segoe UI", 9, "bold"), fg=c["fg"], bg=c["panel_bg"]).pack(side=tk.LEFT, padx=(0, 6))
        self.entry_replay_year = tk.Entry(top_bar, font=("Segoe UI", 9), width=8, bg=c["bg"], fg=c["fg"], insertbackground=c["fg"])
        self.entry_replay_year.pack(side=tk.LEFT, padx=(0, 10))
        self.entry_replay_year.insert(0, "50")

        self.btn_replay = tk.Button(
            top_bar,
            text="Replay Simulation",
            font=("Segoe UI", 8, "bold"),
            bg=c["accent"],
            fg="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._on_replay_click,
        )
        self.btn_replay.pack(side=tk.LEFT)

        self.lbl_replay_status = tk.Label(top_bar, text="Pure keyed deterministic forward replay", font=("Segoe UI", 8), fg=c["fg_muted"], bg=c["panel_bg"])
        self.lbl_replay_status.pack(side=tk.LEFT, padx=12)

        self.canvas_map = tk.Canvas(self.tab_map, bg="#121824", highlightthickness=0)
        self.canvas_map.pack(fill=tk.BOTH, expand=True)

    def _on_replay_click(self) -> None:
        try:
            yr = int(self.entry_replay_year.get().strip())
            self.lbl_replay_status.config(text=f"Replaying deterministic simulation to Year {yr}...")
            self.update_idletasks()
            w_seed = int(session.db.meta.get("world_seed", 42)) if session.db else 42
            h_seed = int(session.db.meta.get("history_seed", 1337)) if session.db else 1337
            from minemesis.core.save_load import replay_to_year
            sim = replay_to_year(world_seed=w_seed, history_seed=h_seed, target_year=yr)
            self.lbl_replay_status.config(
                text=f"Replay to Year {yr} complete: {sim.get_total_living_population()} pop, {len(sim.event_log)} events."
            )
        except Exception as e:
            self.lbl_replay_status.config(text=f"Replay error: {e}")

    def _render_macro_map(self) -> None:
        if not session.db:
            return
        w_seed = int(session.db.meta.get("world_seed", 42))
        from minemesis.core.save_load import reconstruct_macro_world_map
        map_data = reconstruct_macro_world_map(world_seed=w_seed)

        self.canvas_map.delete("all")
        cw = max(400, self.canvas_map.winfo_width())
        ch = max(300, self.canvas_map.winfo_height())
        scale_x = cw / 1100.0
        scale_y = ch / 1100.0

        # Draw road / connection lines
        for conn in map_data["connections"]:
            s1 = next((s for s in map_data["settlements"] if s["id"] == conn["from"]), None)
            s2 = next((s for s in map_data["settlements"] if s["id"] == conn["to"]), None)
            if s1 and s2:
                x1, y1 = 50 + s1["x"] * scale_x, 50 + s1["y"] * scale_y
                x2, y2 = 50 + s2["x"] * scale_x, 50 + s2["y"] * scale_y
                self.canvas_map.create_line(x1, y1, x2, y2, fill="#2a3b5c", width=1.5, dash=(4, 4))

        # Draw settlement nodes
        biome_colors = {
            "Plains": "#48bb78",
            "Forest": "#2f855a",
            "Mountains": "#a0aec0",
            "Coast": "#3182ce",
            "Desert": "#d69e2e",
        }

        for s in map_data["settlements"]:
            x = 50 + s["x"] * scale_x
            y = 50 + s["y"] * scale_y
            col = biome_colors.get(s["biome"], "#38bdf8")
            self.canvas_map.create_oval(x - 8, y - 8, x + 8, y + 8, fill=col, outline="#ffffff", width=1.5)
            self.canvas_map.create_text(x, y - 14, text=s["name"], fill="#e2e8f0", font=("Segoe UI", 9, "bold"))
            self.canvas_map.create_text(x, y + 14, text=f"{s['biome']}", fill="#94a3b8", font=("Segoe UI", 7))

    def refresh(self) -> None:
        self.clear_error()
        if not session.db:
            return

        try:
            # 1. Population Series
            pop_hist = census_service.get_population_history()
            colors = ["#38bdf8", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#f472b6"]
            series = []

            # Add Total series first
            if "__total__" in pop_hist:
                series.append({
                    "label": "Total Pop",
                    "color": "#ffffff",
                    "points": pop_hist["__total__"],
                })

            col_idx = 0
            for sid, pts in pop_hist.items():
                if sid == "__total__":
                    continue
                s_name = sid.replace("set_", "").capitalize()
                series.append({
                    "label": s_name,
                    "color": colors[col_idx % len(colors)],
                    "points": pts,
                })
                col_idx += 1

            self.chart_pop.set_line_chart(series)

            # 2. Vital Rates
            vitals = census_service.get_vital_rates()
            v_series = [
                {"label": "Births", "color": theme.colors["success"], "points": vitals["births"]},
                {"label": "Deaths", "color": theme.colors["danger"], "points": vitals["deaths"]},
            ]
            self.chart_vitals.set_line_chart(v_series)

            # 3. Settlement Comparison (Latest Year)
            census = session.db.get_census()
            if census:
                latest_year = max([r["year"] for r in census])
                bar_cats = []
                for r in census:
                    if r["year"] == latest_year:
                        bar_cats.append({
                            "label": r["settlement_id"].replace("set_", "").capitalize(),
                            "value": float(r["population"]),
                            "color": theme.colors["accent"],
                        })
                self.chart_dist.set_bar_chart(bar_cats)

                tot_births = sum([b[1] for b in vitals["births"]])
                tot_deaths = sum([d[1] for d in vitals["deaths"]])
                self.lbl_stats.config(
                    text=f"Year {latest_year} Census: {len(bar_cats)} Settlements Active • Cumulative Births: {tot_births} • Cumulative Deaths: {tot_deaths}"
                )

            # 4. Render 2D Macro World Map
            self._render_macro_map()

        except Exception as e:
            log_error("Error in WorldTab.refresh", e)
            self.show_error(f"Failed to load census data: {e}")
