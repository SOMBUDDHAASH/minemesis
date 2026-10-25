"""
Places (Settlements & Geography) Tab for Viewer V2.
Displays settlement profiles, local libraries, leaders, and economic resource stocks.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

from viewer.core.bus import bus
from viewer.core.logging import log_error
from viewer.core.session import session
from viewer.ui.tabs.base import BaseTab, register_tab
from viewer.ui.theme import theme
from viewer.ui.widgets.chart import CanvasChart
from viewer.ui.widgets.entity_link import EntityPill
from viewer.ui.widgets.table import PaginatedTable


@register_tab("Places", order=3)
class PlacesTab(BaseTab):
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self.selected_set_id: Optional[str] = None

        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        c = theme.colors

        # Left Pane: Settlement List
        left_frame = tk.Frame(self.paned, bg=c["panel_bg"], width=280)
        self.paned.add(left_frame, weight=1)

        tk.Label(
            left_frame,
            text="World Settlements",
            font=("Segoe UI", 11, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
            padx=10,
            pady=8,
        ).pack(anchor="w")

        cols = [
            {"key": "name", "label": "Settlement", "width": 140},
            {"key": "biome", "label": "Biome", "width": 100},
        ]
        self.set_table = PaginatedTable(
            left_frame,
            columns=cols,
            on_select=self._on_set_select,
        )
        self.set_table.pack(fill=tk.BOTH, expand=True)

        # Right Pane: Settlement Profile
        self.right_frame = tk.Frame(self.paned, bg=c["bg"], padx=16, pady=12)
        self.paned.add(self.right_frame, weight=3)

        self._build_profile()

        bus.subscribe("session:loaded", lambda **kw: self.refresh())
        bus.subscribe("tab:switch", self._on_tab_switch)

    def _build_profile(self) -> None:
        c = theme.colors

        # Header Profile Box
        self.profile_box = tk.Frame(self.right_frame, bg=c["panel_bg"], padx=16, pady=12, relief=tk.FLAT)
        self.profile_box.pack(fill=tk.X, pady=(0, 10))

        self.lbl_name = tk.Label(self.profile_box, text="Select a Settlement", font=("Segoe UI", 16, "bold"), fg=c["fg"], bg=c["panel_bg"])
        self.lbl_name.pack(anchor="w")

        self.lbl_details = tk.Label(self.profile_box, text="--", font=("Segoe UI", 9), fg=c["fg_muted"], bg=c["panel_bg"])
        self.lbl_details.pack(anchor="w", pady=(2, 0))

        # Split Subsections: Resource Stock Chart & Settlement Library
        self.sub_notebook = ttk.Notebook(self.right_frame)
        self.sub_notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Resource Stocks Chart
        self.tab_resources = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_resources, text="Resource Stocks Over Time")

        self.chart_resources = CanvasChart(self.tab_resources)
        self.chart_resources.pack(fill=tk.BOTH, expand=True)

        # Tab 2: Settlement Library
        self.tab_library = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_library, text="Local Library & Archives")

        cols = [
            {"key": "title", "label": "Title", "width": 240},
            {"key": "author_name", "label": "Author", "width": 140},
            {"key": "year_written", "label": "Year", "width": 60},
            {"key": "topic", "label": "Genre", "width": 100},
        ]
        self.lib_table = PaginatedTable(
            self.tab_library,
            columns=cols,
            on_select=lambda r: session.select_entity("book", str(r.get("id"))),
            on_activate=lambda r: bus.publish("tab:switch", tab_name="Books", entity_id=str(r.get("id"))),
        )
        self.lib_table.pack(fill=tk.BOTH, expand=True)

    def _on_tab_switch(self, tab_name: str, entity_id: str, **kwargs) -> None:
        if tab_name == "Places" and entity_id.startswith("set_"):
            self.selected_set_id = entity_id
            self.refresh()

    def refresh(self) -> None:
        self.clear_error()
        if not session.db:
            return

        try:
            settlements = session.db.get_settlements()
            self.set_table.set_items(settlements)

            if not self.selected_set_id and settlements:
                self.selected_set_id = settlements[0]["id"]

            if self.selected_set_id:
                self._display_settlement(self.selected_set_id)
        except Exception as e:
            log_error("Error in PlacesTab.refresh", e)
            self.show_error(f"Failed to load places: {e}")

    def _on_set_select(self, row: dict[str, Any]) -> None:
        sid = row.get("id")
        if sid:
            self.selected_set_id = sid
            session.select_entity("settlement", sid)
            self._display_settlement(sid)

    def _display_settlement(self, set_id: str) -> None:
        if not session.db:
            return

        s = session.db.get_settlement(set_id)
        if not s:
            return

        name = s.get("name", set_id)
        biome = s.get("biome", "Temperate Forest")
        culture = s.get("culture", "Common")
        self.lbl_name.config(text=name)
        self.lbl_details.config(text=f"Biome: {biome} • Culture: {culture} • Founded at Tick {s.get('founded_tick', 0)}")

        # Population & Food History
        census = session.db.get_census(settlement_id=set_id)
        pop_pts = [(r["year"], r["population"]) for r in census]
        food_pts = [(r["year"], r["food"]) for r in census]

        series = [
            {"label": "Population", "color": theme.colors["accent"], "points": pop_pts},
            {"label": "Food Stores", "color": theme.colors["success"], "points": food_pts},
        ]
        self.chart_resources.set_line_chart(series)

        # Library Books
        books = session.db.get_books(settlement_id=set_id)
        self.lib_table.set_items(books)
