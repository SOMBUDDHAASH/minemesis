"""
People (Characters & Epistemics) Tab for Viewer V2.
Features searchable character roster, biographical life page,
Truth vs Belief split view, and personal event timeline.
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


@register_tab("People", order=2)
class PeopleTab(BaseTab):
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self.selected_char_id: Optional[str] = None

        # Split pane: Left = Character Roster, Right = Life Page
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        c = theme.colors

        # --- Left Pane: Character Roster ---
        left_frame = tk.Frame(self.paned, bg=c["panel_bg"], width=320)
        self.paned.add(left_frame, weight=1)

        roster_top = tk.Frame(left_frame, bg=c["panel_bg"], padx=8, pady=6)
        roster_top.pack(fill=tk.X)

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            roster_top,
            textvariable=self.search_var,
            bg=c["input_bg"],
            fg=c["input_fg"],
            insertbackground=c["fg"],
            relief=tk.FLAT,
            highlightbackground=c["border"],
            highlightthickness=1,
        )
        self.search_entry.pack(fill=tk.X, pady=(0, 4))
        self.search_entry.bind("<KeyRelease>", lambda e: self._load_roster())

        self.status_var = tk.StringVar(value="All Statuses")
        self.status_combo = ttk.Combobox(
            roster_top,
            textvariable=self.status_var,
            values=["All Statuses", "Living Only", "Deceased Only"],
            state="readonly",
        )
        self.status_combo.pack(fill=tk.X)
        self.status_combo.bind("<<ComboboxSelected>>", lambda e: self._load_roster())

        cols = [
            {"key": "id", "label": "ID", "width": 60},
            {"key": "display_name", "label": "Name", "width": 140},
            {"key": "settlement_id", "label": "Settlement", "width": 80},
        ]
        self.roster_table = PaginatedTable(
            left_frame,
            columns=cols,
            page_size=50,
            on_select=self._on_char_select,
        )
        self.roster_table.pack(fill=tk.BOTH, expand=True)

        # --- Right Pane: Life Page ---
        self.right_frame = tk.Frame(self.paned, bg=c["bg"], padx=16, pady=12)
        self.paned.add(self.right_frame, weight=3)

        self._build_life_page()

        bus.subscribe("session:loaded", lambda **kw: self.refresh())
        bus.subscribe("tab:switch", self._on_tab_switch)

    def _build_life_page(self) -> None:
        c = theme.colors

        # Biography Card
        self.bio_card = tk.Frame(self.right_frame, bg=c["panel_bg"], padx=16, pady=12, relief=tk.FLAT)
        self.bio_card.pack(fill=tk.X, pady=(0, 10))

        self.lbl_name = tk.Label(self.bio_card, text="Select a Citizen", font=("Segoe UI", 16, "bold"), fg=c["fg"], bg=c["panel_bg"])
        self.lbl_name.pack(anchor="w")

        self.lbl_details = tk.Label(self.bio_card, text="--", font=("Segoe UI", 9), fg=c["fg_muted"], bg=c["panel_bg"])
        self.lbl_details.pack(anchor="w", pady=(2, 6))

        self.family_frame = tk.Frame(self.bio_card, bg=c["panel_bg"])
        self.family_frame.pack(fill=tk.X, pady=(4, 0))

        # Notebook for: Truth vs Belief & Event Timeline
        self.sub_notebook = ttk.Notebook(self.right_frame)
        self.sub_notebook.pack(fill=tk.BOTH, expand=True)

        # Tab A: Truth vs Belief
        self.tab_epistemic = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_epistemic, text="Truth vs Subjective Belief")

        self.epistemic_text = tk.Text(
            self.tab_epistemic,
            bg=c["panel_bg"],
            fg=c["fg"],
            font=("Segoe UI", 9),
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=8,
            pady=8,
        )
        self.epistemic_text.pack(fill=tk.BOTH, expand=True)

        # Tab B: Life Event Timeline
        self.tab_timeline = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_timeline, text="Personal History Timeline")

        cols = [
            {"key": "event_id", "label": "ID", "width": 50},
            {"key": "year", "label": "Year", "width": 50},
            {"key": "type", "label": "Type", "width": 100},
            {"key": "role", "label": "Role", "width": 80},
            {"key": "description", "label": "Event", "width": 400},
        ]
        self.timeline_table = PaginatedTable(
            self.tab_timeline,
            columns=cols,
            on_select=lambda r: session.select_entity("event", str(r.get("event_id"))),
        )
        self.timeline_table.pack(fill=tk.BOTH, expand=True)

    def _on_tab_switch(self, tab_name: str, entity_id: str, **kwargs) -> None:
        if tab_name == "People" and entity_id.startswith("char_"):
            self.selected_char_id = entity_id
            self.refresh()

    def refresh(self) -> None:
        self.clear_error()
        if not session.db:
            return
        self._load_roster()
        if self.selected_char_id:
            self._display_character(self.selected_char_id)

    def _load_roster(self) -> None:
        if not session.db:
            return
        try:
            q = self.search_var.get().strip()
            status_filter = self.status_var.get()
            living_only = (status_filter == "Living Only")
            chars = session.db.get_characters(limit=200, search=q, living_only=living_only)
            self.roster_table.set_items(chars)
        except Exception as e:
            log_error("Error loading roster in PeopleTab", e)

    def _on_char_select(self, row: dict[str, Any]) -> None:
        cid = row.get("id")
        if cid:
            self.selected_char_id = cid
            session.select_entity("character", cid)
            self._display_character(cid)

    def _display_character(self, char_id: str) -> None:
        if not session.db:
            return

        c = session.db.get_character(char_id)
        if not c:
            return

        name = c.get("display_name", char_id)
        alive = (c.get("death_tick") is None)
        age = (c.get("death_tick", 0) - c.get("birth_tick", 0)) // 12 if not alive else (session.db.meta.get("duration_ticks", 0) - c.get("birth_tick", 0)) // 12
        status_txt = f"Living (Age {max(0, age)})" if alive else f"Deceased (Died at age {max(0, age)})"
        prof = c.get("profession", "Citizen")
        settle = c.get("settlement_id", "")

        self.lbl_name.config(text=name)
        self.lbl_details.config(text=f"{status_txt} • {c.get('sex', 'M')} • Profession: {prof} • Settlement: {settle}")

        # Populate Family Links
        for w in self.family_frame.winfo_children():
            w.destroy()

        fam_row = tk.Frame(self.family_frame, bg=theme.colors["panel_bg"])
        fam_row.pack(anchor="w")

        if c.get("father_id"):
            tk.Label(fam_row, text="Father: ", font=("Segoe UI", 8, "bold"), fg=theme.colors["fg_muted"], bg=theme.colors["panel_bg"]).pack(side=tk.LEFT)
            EntityPill(fam_row, c["father_id"], "character", c["father_id"]).pack(side=tk.LEFT, padx=(0, 6))

        if c.get("mother_id"):
            tk.Label(fam_row, text="Mother: ", font=("Segoe UI", 8, "bold"), fg=theme.colors["fg_muted"], bg=theme.colors["panel_bg"]).pack(side=tk.LEFT)
            EntityPill(fam_row, c["mother_id"], "character", c["mother_id"]).pack(side=tk.LEFT, padx=(0, 6))

        if c.get("spouse_id"):
            tk.Label(fam_row, text="Spouse: ", font=("Segoe UI", 8, "bold"), fg=theme.colors["fg_muted"], bg=theme.colors["panel_bg"]).pack(side=tk.LEFT)
            EntityPill(fam_row, c["spouse_id"], "character", c["spouse_id"]).pack(side=tk.LEFT, padx=(0, 6))

        # Populate Epistemic Ledger (Truth vs Belief)
        self.epistemic_text.config(state=tk.NORMAL)
        self.epistemic_text.delete("1.0", tk.END)

        cases = session.db.get_character_epistemic_cases(char_id)
        if not cases:
            self.epistemic_text.insert(
                tk.END,
                "No subjective belief divergence or grievances recorded for this citizen in the epistemic ledger.\n",
            )
        else:
            for case in cases:
                is_believer = (case.get("believer_character_id") == char_id)
                role = "Subjective Believer" if is_believer else "Subject of Grievance"
                self.epistemic_text.insert(
                    tk.END,
                    f"Case: {case.get('case_type')} (Year {case.get('year')}) [{role}]\n",
                    "bold",
                )
                self.epistemic_text.insert(tk.END, f"  Objective Ground Truth:\n    {case.get('ground_truth')}\n")
                self.epistemic_text.insert(
                    tk.END,
                    f"  Subjective Belief ({case.get('source_type')} - {int(case.get('confidence', 1.0) * 100)}% Confidence):\n    {case.get('belief_summary')}\n\n",
                )

        self.epistemic_text.config(state=tk.DISABLED)

        # Populate Life Event Timeline
        evts = session.db.get_character_events(char_id)
        self.timeline_table.set_items(evts)
