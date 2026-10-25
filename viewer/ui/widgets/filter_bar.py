"""
Reusable Filter Bar Widget for Viewer V2.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

from viewer.core.bus import bus
from viewer.core.session import session
from viewer.ui.theme import theme


class FilterBar(tk.Frame):
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        c = theme.colors
        super().__init__(parent, bg=c["panel_bg"], padx=8, pady=6, **kwargs)

        self._settlement_map: dict[str, Optional[str]] = {"All Settlements": None}
        self._era_map: dict[str, Optional[tuple[int, int]]] = {
            "All Time": None,
            "Years 1 - 25": (1, 25),
            "Years 26 - 50": (26, 50),
            "Years 51 - 75": (51, 75),
            "Years 76 - 100": (76, 100),
            "Years 101 - 200": (101, 200),
        }

        # 1. Search Box
        lbl_search = tk.Label(self, text="Search:", font=("Segoe UI", 9, "bold"), bg=c["panel_bg"], fg=c["fg"])
        lbl_search.pack(side=tk.LEFT, padx=(4, 4))

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            self,
            textvariable=self.search_var,
            bg=c["input_bg"],
            fg=c["input_fg"],
            insertbackground=c["fg"],
            relief=tk.FLAT,
            highlightbackground=c["border"],
            highlightthickness=1,
            width=22,
        )
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry.bind("<Return>", self._apply_filters)

        # 2. Era Dropdown
        lbl_era = tk.Label(self, text="Era:", font=("Segoe UI", 9, "bold"), bg=c["panel_bg"], fg=c["fg"])
        lbl_era.pack(side=tk.LEFT, padx=(4, 4))

        self.era_var = tk.StringVar(value="All Time")
        self.era_combo = ttk.Combobox(
            self,
            textvariable=self.era_var,
            values=list(self._era_map.keys()),
            state="readonly",
            width=14,
        )
        self.era_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.era_combo.bind("<<ComboboxSelected>>", self._apply_filters)

        # 3. Settlement Dropdown
        lbl_set = tk.Label(self, text="Settlement:", font=("Segoe UI", 9, "bold"), bg=c["panel_bg"], fg=c["fg"])
        lbl_set.pack(side=tk.LEFT, padx=(4, 4))

        self.set_var = tk.StringVar(value="All Settlements")
        self.set_combo = ttk.Combobox(
            self,
            textvariable=self.set_var,
            values=["All Settlements"],
            state="readonly",
            width=16,
        )
        self.set_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.set_combo.bind("<<ComboboxSelected>>", self._apply_filters)

        # 4. Major Events Only Checkbox
        self.major_var = tk.BooleanVar(value=False)
        self.major_chk = ttk.Checkbutton(
            self,
            text="Major Events Only",
            variable=self.major_var,
            command=self._apply_filters,
        )
        self.major_chk.pack(side=tk.LEFT, padx=(6, 12))

        # 5. Reset Button
        btn_reset = tk.Button(
            self,
            text="Clear",
            command=self._reset_filters,
            bg=c["card_bg"],
            fg=c["fg_muted"],
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            padx=8,
            pady=2,
        )
        btn_reset.pack(side=tk.LEFT)

        bus.subscribe("session:loaded", self._on_session_loaded)

    def _on_session_loaded(self, **kwargs: Any) -> None:
        if session.db:
            settlements = session.db.get_settlements()
            self._settlement_map = {"All Settlements": None}
            for s in settlements:
                self._settlement_map[s["name"]] = s["id"]
            self.set_combo.config(values=list(self._settlement_map.keys()))
            self.set_var.set("All Settlements")

    def _apply_filters(self, event=None) -> None:
        era_tuple = self._era_map.get(self.era_var.get())
        set_id = self._settlement_map.get(self.set_var.get())
        search_txt = self.search_var.get().strip()
        major = self.major_var.get()

        session.update_filters(
            search=search_txt,
            era=era_tuple,
            settlement=set_id,
            major_only=major,
        )

    def _reset_filters(self) -> None:
        self.search_var.set("")
        self.era_var.set("All Time")
        self.set_var.set("All Settlements")
        self.major_var.set(False)
        self._apply_filters()
