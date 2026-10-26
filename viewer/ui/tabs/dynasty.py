"""
Dynasties and Kinship Tab for Viewer V2 (Milestone 1).
Displays family houses, prestige standings, lineage trees, and vendetta lines.
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
from viewer.ui.widgets.entity_link import EntityPill
from viewer.ui.widgets.table import PaginatedTable


@register_tab("Dynasties", order=8)
class DynastyTab(BaseTab):
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self.selected_dynasty_id: Optional[str] = None
        self._dynasties_data: list[dict[str, Any]] = []

        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        c = theme.colors

        # Left Pane: Dynasty Rankings
        left_frame = tk.Frame(self.paned, bg=c["panel_bg"], width=320)
        self.paned.add(left_frame, weight=1)

        tk.Label(
            left_frame,
            text="Noble Houses & Dynasties",
            font=("Segoe UI", 11, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
            padx=10,
            pady=8,
        ).pack(anchor="w")

        cols = [
            {"key": "surname", "label": "House", "width": 120},
            {"key": "living", "label": "Living", "width": 55},
            {"key": "total", "label": "Total", "width": 55},
            {"key": "prestige", "label": "Prestige", "width": 65},
        ]
        self.dynasty_table = PaginatedTable(
            left_frame,
            columns=cols,
            on_select=self._on_dynasty_select,
        )
        self.dynasty_table.pack(fill=tk.BOTH, expand=True)

        # Right Pane: House Details
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
            text="Select a Dynasty",
            font=("Segoe UI", 16, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
        )
        self.lbl_title.pack(anchor="w")

        self.lbl_details = tk.Label(
            self.profile_box,
            text="Lineage metrics and family standings will appear here.",
            font=("Segoe UI", 9),
            fg=c["fg_muted"],
            bg=c["panel_bg"],
        )
        self.lbl_details.pack(anchor="w", pady=(2, 0))

        # Sub-tabs: Living Members & Feud Lines
        self.sub_notebook = ttk.Notebook(self.right_frame)
        self.sub_notebook.pack(fill=tk.BOTH, expand=True)

        # Sub-tab 1: House Members
        self.tab_members = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_members, text="Family Members")

        member_cols = [
            {"key": "name", "label": "Name", "width": 160},
            {"key": "status", "label": "Status", "width": 70},
            {"key": "settlement", "label": "Settlement", "width": 110},
            {"key": "profession", "label": "Profession", "width": 100},
            {"key": "father", "label": "Father", "width": 120},
            {"key": "mother", "label": "Mother", "width": 120},
        ]
        self.member_table = PaginatedTable(self.tab_members, columns=member_cols)
        self.member_table.pack(fill=tk.BOTH, expand=True)

        # Sub-tab 2: Vendetta / Feud History
        self.tab_feuds = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_feuds, text="Active & Historic Feuds")

        feud_cols = [
            {"key": "year", "label": "Year", "width": 60},
            {"key": "event_type", "label": "Event", "width": 100},
            {"key": "summary", "label": "Summary", "width": 380},
        ]
        self.feud_table = PaginatedTable(self.tab_feuds, columns=feud_cols)
        self.feud_table.pack(fill=tk.BOTH, expand=True)

    def _on_tab_switch(self, tab_name: str, **kwargs) -> None:
        if tab_name == "Dynasties":
            self.refresh()

    def refresh(self) -> None:
        self.clear_error()
        if not session.is_loaded or not session.db:
            self.dynasty_table.set_data([])
            self.member_table.set_data([])
            self.feud_table.set_data([])
            return

        try:
            # Query all characters
            chars = session.db.get_characters(limit=100000)
            books = session.db.get_books(limit=10000)

            # Group characters by family / surname
            families: dict[str, dict[str, Any]] = {}
            for c in chars:
                sur = c.get("last_name") or "Unknown"
                if sur not in families:
                    families[sur] = {
                        "surname": sur,
                        "members": [],
                        "living": 0,
                        "total": 0,
                        "books": 0,
                        "settlements": set(),
                    }
                fam = families[sur]
                fam["members"].append(c)
                fam["total"] += 1
                if c.get("alive"):
                    fam["living"] += 1
                set_name = c.get("settlement_name") or c.get("settlement_id") or ""
                if set_name:
                    fam["settlements"].add(set_name)

            for b in books:
                aname = b.get("author_name") or ""
                parts = aname.split()
                if len(parts) >= 2:
                    sur = parts[-1]
                    if sur in families:
                        families[sur]["books"] += 1

            # Build list
            table_rows = []
            for sur, f in families.items():
                prestige = round(f["living"] * 2.5 + f["books"] * 8.0 + f["total"] * 0.5, 1)
                table_rows.append({
                    "id": sur,
                    "surname": f"House {sur}",
                    "living": f["living"],
                    "total": f["total"],
                    "prestige": prestige,
                    "settlements": ", ".join(sorted(f["settlements"])[:2]),
                    "_raw": f,
                })

            table_rows.sort(key=lambda r: (r["prestige"], r["living"]), reverse=True)
            self._dynasties_data = table_rows
            self.dynasty_table.set_data(table_rows)

            if table_rows and not self.selected_dynasty_id:
                self._load_dynasty(table_rows[0])
            elif self.selected_dynasty_id:
                match = next((r for r in table_rows if r["id"] == self.selected_dynasty_id), None)
                if match:
                    self._load_dynasty(match)

        except Exception as e:
            log_error(f"Error loading Dynasties: {e}")
            self.show_error(f"Failed to load dynasty data: {e}")

    def _on_dynasty_select(self, row: dict[str, Any]) -> None:
        self.selected_dynasty_id = row.get("id")
        self._load_dynasty(row)

    def _load_dynasty(self, row: dict[str, Any]) -> None:
        raw = row.get("_raw", {})
        sur = raw.get("surname", "Unknown")
        members = raw.get("members", [])
        living = raw.get("living", 0)
        total = raw.get("total", 0)
        prestige = row.get("prestige", 0)
        sets = row.get("settlements", "Unknown")

        self.lbl_title.config(text=f"House of {sur}")
        self.lbl_details.config(
            text=f"Prestige Score: {prestige}  |  Living: {living}  |  Total Recorded: {total}  |  Primary Lands: {sets}"
        )

        # Populate members table
        member_rows = []
        for m in members:
            status = "Living" if m.get("alive") else f"Died Y{m.get('death_year', '?')}"
            member_rows.append({
                "id": m.get("id"),
                "name": f"{m.get('first_name', '')} {m.get('last_name', '')}".strip(),
                "status": status,
                "settlement": m.get("settlement_name") or m.get("settlement_id") or "--",
                "profession": m.get("profession") or "Citizen",
                "father": m.get("father_id") or "--",
                "mother": m.get("mother_id") or "--",
            })
        member_rows.sort(key=lambda x: (0 if x["status"] == "Living" else 1, x["name"]))
        self.member_table.set_data(member_rows)

        # Populate feuds involving this surname
        if session.is_loaded and session.db:
            try:
                feud_evts = session.db.get_events(event_types=["Feud", "Death", "Peace"], limit=200)
                feud_rows = []
                for fe in feud_evts:
                    desc = fe.get("description", "")
                    if sur.lower() in desc.lower():
                        feud_rows.append({
                            "id": fe.get("id"),
                            "year": fe.get("year"),
                            "event_type": fe.get("type"),
                            "summary": desc,
                        })
                self.feud_table.set_data(feud_rows)
            except Exception as e:
                log_error(f"Error loading dynasty feud events: {e}")
                self.feud_table.set_data([])
