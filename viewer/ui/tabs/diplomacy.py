"""
Diplomacy and Geopolitics Tab for Viewer V2 (Milestone 2).
Displays inter-settlement diplomatic stances, alliances, war campaigns, and treaties.
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
from viewer.ui.widgets.table import PaginatedTable


@register_tab("Diplomacy", order=9)
class DiplomacyTab(BaseTab):
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self.selected_pair: Optional[str] = None

        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        c = theme.colors

        # Left Pane: Diplomatic Relations List
        left_frame = tk.Frame(self.paned, bg=c["panel_bg"], width=350)
        self.paned.add(left_frame, weight=1)

        tk.Label(
            left_frame,
            text="Inter-Settlement Geopolitics",
            font=("Segoe UI", 11, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
            padx=10,
            pady=8,
        ).pack(anchor="w")

        cols = [
            {"key": "pair", "label": "Settlements", "width": 180},
            {"key": "stance", "label": "Stance", "width": 90},
            {"key": "score", "label": "Score", "width": 60},
        ]
        self.relations_table = PaginatedTable(
            left_frame,
            columns=cols,
            on_select=self._on_pair_select,
        )
        self.relations_table.pack(fill=tk.BOTH, expand=True)

        # Right Pane: Detailed Stance & History
        self.right_frame = tk.Frame(self.paned, bg=c["bg"], padx=16, pady=12)
        self.paned.add(self.right_frame, weight=3)

        self._build_profile()

        bus.subscribe("session:loaded", lambda **kw: self.refresh())
        bus.subscribe("tab:switch", self._on_tab_switch)

    def _build_profile(self) -> None:
        c = theme.colors

        # Header Box
        self.profile_box = tk.Frame(self.right_frame, bg=c["panel_bg"], padx=16, pady=12, relief=tk.FLAT)
        self.profile_box.pack(fill=tk.X, pady=(0, 10))

        self.lbl_title = tk.Label(
            self.profile_box,
            text="Select a Settlement Pair",
            font=("Segoe UI", 16, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
        )
        self.lbl_title.pack(anchor="w")

        self.lbl_details = tk.Label(
            self.profile_box,
            text="Diplomatic treaties, wars, and alliance records will appear here.",
            font=("Segoe UI", 9),
            fg=c["fg_muted"],
            bg=c["panel_bg"],
        )
        self.lbl_details.pack(anchor="w", pady=(2, 0))

        # Sub-tabs: Treaties & Wars
        self.sub_notebook = ttk.Notebook(self.right_frame)
        self.sub_notebook.pack(fill=tk.BOTH, expand=True)

        # Sub-tab 1: Diplomatic Events
        self.tab_events = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_events, text="Treaties, Alliances & Wars")

        evt_cols = [
            {"key": "year", "label": "Year", "width": 60},
            {"key": "type", "label": "Type", "width": 120},
            {"key": "summary", "label": "Summary", "width": 380},
        ]
        self.events_table = PaginatedTable(self.tab_events, columns=evt_cols)
        self.events_table.pack(fill=tk.BOTH, expand=True)

    def _on_tab_switch(self, tab_name: str, **kwargs) -> None:
        if tab_name == "Diplomacy":
            self.refresh()

    def refresh(self) -> None:
        self.clear_error()
        if not session.is_loaded or not session.db:
            self.relations_table.set_data([])
            self.events_table.set_data([])
            return

        try:
            settlements = session.db.get_settlements()
            set_dict = {s["id"]: s.get("name", s["id"]) for s in settlements}
            s_ids = sorted(set_dict.keys())

            # Query diplomatic events
            evts = session.db.get_events(
                event_types=["AllianceFormed", "WarDeclared", "TreatySigned", "TradeRouteFounded", "TradeRouteBroken", "Raid"],
                limit=1000,
            )

            # Build pairwise relation summary
            pair_rows = []
            for i in range(len(s_ids)):
                for j in range(i + 1, len(s_ids)):
                    s1 = s_ids[i]
                    s2 = s_ids[j]
                    n1 = set_dict[s1]
                    n2 = set_dict[s2]

                    # Infer current stance from latest event
                    stance = "Neutral"
                    score = 0
                    relevant = []
                    for e in evts:
                        loc = e.get("location", "")
                        desc = e.get("description", "")
                        etype = e.get("type", "")
                        if (s1 in loc or n1 in desc) and (s2 in loc or n2 in desc):
                            relevant.append(e)

                    if relevant:
                        last_e = relevant[-1]
                        letype = last_e.get("type")
                        if letype == "AllianceFormed":
                            stance = "Alliance"
                            score = 65
                        elif letype == "WarDeclared":
                            stance = "War"
                            score = -75
                        elif letype == "TreatySigned":
                            stance = "Friendly"
                            score = 25
                        elif letype == "TradeRouteFounded":
                            stance = "Friendly"
                            score = 30
                        elif letype in ("Raid", "TradeRouteBroken"):
                            stance = "Suspicious"
                            score = -25

                    pair_rows.append({
                        "id": f"{s1}__{s2}",
                        "s1": s1,
                        "s2": s2,
                        "pair": f"{n1} & {n2}",
                        "stance": stance,
                        "score": score,
                        "_events": relevant,
                    })

            pair_rows.sort(key=lambda r: (0 if r["stance"] == "War" else (1 if r["stance"] == "Alliance" else 2), r["pair"]))
            self.relations_table.set_data(pair_rows)

            if pair_rows and not self.selected_pair:
                self._load_pair(pair_rows[0])
            elif self.selected_pair:
                match = next((r for r in pair_rows if r["id"] == self.selected_pair), None)
                if match:
                    self._load_pair(match)

        except Exception as e:
            log_error(f"Error loading Diplomacy: {e}")
            self.show_error(f"Failed to load diplomacy data: {e}")

    def _on_pair_select(self, row: dict[str, Any]) -> None:
        self.selected_pair = row.get("id")
        self._load_pair(row)

    def _load_pair(self, row: dict[str, Any]) -> None:
        pair_name = row.get("pair", "Unknown")
        stance = row.get("stance", "Neutral")
        score = row.get("score", 0)
        evts = row.get("_events", [])

        self.lbl_title.config(text=pair_name)
        self.lbl_details.config(
            text=f"Current Diplomatic Stance: {stance.upper()}  |  Diplomatic Trust Score: {score}  |  Recorded Events: {len(evts)}"
        )

        evt_rows = []
        for e in reversed(evts):
            evt_rows.append({
                "id": e.get("id"),
                "year": e.get("year"),
                "type": e.get("type"),
                "summary": e.get("description"),
            })
        self.events_table.set_data(evt_rows)
