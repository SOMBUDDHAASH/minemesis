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

        bus.subscribe("session:loaded", lambda **kw: self.refresh())

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

        except Exception as e:
            log_error("Error in WorldTab.refresh", e)
            self.show_error(f"Failed to load census data: {e}")
