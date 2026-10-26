"""
Player Actor and Emergent Reputation Tab for Viewer V2 (Milestone 3).
Displays player identity, command console, active avengers/hunters, allies, and beliefs.
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


@register_tab("Player", order=10)
class PlayerTab(BaseTab):
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        c = theme.colors

        # Left Pane: Player Status & Command Console
        left_frame = tk.Frame(self.paned, bg=c["panel_bg"], width=320, padx=12, pady=12)
        self.paned.add(left_frame, weight=1)

        tk.Label(
            left_frame,
            text="Player Actor: Traveler",
            font=("Segoe UI", 12, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
        ).pack(anchor="w", pady=(0, 6))

        self.lbl_player_info = tk.Label(
            left_frame,
            text="ID: player_0\nProfession: Wanderer\nStatus: Active in World",
            font=("Segoe UI", 9),
            fg=c["fg_muted"],
            bg=c["panel_bg"],
            justify=tk.LEFT,
        )
        self.lbl_player_info.pack(anchor="w", pady=(0, 12))

        # Command Section
        tk.Label(
            left_frame,
            text="Simulation Command Console",
            font=("Segoe UI", 10, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
        ).pack(anchor="w", pady=(6, 4))

        tk.Label(left_frame, text="Target Entity / Settlement ID:", font=("Segoe UI", 8), fg=c["fg_muted"], bg=c["panel_bg"]).pack(anchor="w")
        self.entry_target = tk.Entry(left_frame, font=("Segoe UI", 9), bg=c["bg"], fg=c["fg"], insertbackground=c["fg"])
        self.entry_target.pack(fill=tk.X, pady=(2, 8))
        self.entry_target.insert(0, "char_0")

        # Command Buttons Grid
        btn_frame = tk.Frame(left_frame, bg=c["panel_bg"])
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        actions = [
            ("Kill Target", "#e05252"),
            ("Gift Target", "#4ea8de"),
            ("Help Town", "#48bfe3"),
            ("Save Target", "#52b788"),
            ("Steal Goods", "#f4a261"),
            ("Build Wall", "#7209b7"),
        ]

        for i, (act_name, col) in enumerate(actions):
            btn = tk.Button(
                btn_frame,
                text=act_name,
                font=("Segoe UI", 8, "bold"),
                bg=col,
                fg="#ffffff",
                relief=tk.FLAT,
                padx=6,
                pady=4,
                cursor="hand2",
                command=lambda a=act_name: self._on_command_click(a),
            )
            r = i // 2
            c_idx = i % 2
            btn.grid(row=r, column=c_idx, padx=3, pady=3, sticky="ew")
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        # Output Log Box
        tk.Label(left_frame, text="Command Log:", font=("Segoe UI", 8, "bold"), fg=c["fg_muted"], bg=c["panel_bg"]).pack(anchor="w")
        self.txt_log = tk.Text(left_frame, height=10, font=("Consolas", 8), bg=c["bg"], fg=c["fg"], relief=tk.FLAT, padx=6, pady=6)
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        # Right Pane: Emergent Consequences & Reputation
        self.right_frame = tk.Frame(self.paned, bg=c["bg"], padx=14, pady=12)
        self.paned.add(self.right_frame, weight=3)

        self._build_notebook()

        bus.subscribe("session:loaded", lambda **kw: self.refresh())
        bus.subscribe("tab:switch", self._on_tab_switch)

    def _build_notebook(self) -> None:
        c = theme.colors

        self.sub_notebook = ttk.Notebook(self.right_frame)
        self.sub_notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Active Hunters / Avengers
        self.tab_hunters = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_hunters, text="Active Hunters & Avengers")

        cols_h = [
            {"key": "character", "label": "Hunter", "width": 160},
            {"key": "settlement", "label": "Settlement", "width": 120},
            {"key": "hatred", "label": "Hatred", "width": 80},
            {"key": "status", "label": "Status", "width": 120},
        ]
        self.hunters_table = PaginatedTable(self.tab_hunters, columns=cols_h)
        self.hunters_table.pack(fill=tk.BOTH, expand=True)

        # Tab 2: Devoted Allies
        self.tab_allies = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_allies, text="Devoted Allies & Friends")

        cols_a = [
            {"key": "character", "label": "Ally", "width": 160},
            {"key": "settlement", "label": "Settlement", "width": 120},
            {"key": "loyalty", "label": "Loyalty", "width": 80},
            {"key": "trust", "label": "Trust", "width": 80},
        ]
        self.allies_table = PaginatedTable(self.tab_allies, columns=cols_a)
        self.allies_table.pack(fill=tk.BOTH, expand=True)

        # Tab 3: Player Action History
        self.tab_history = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_history, text="Player History")

        cols_ev = [
            {"key": "year", "label": "Year", "width": 60},
            {"key": "type", "label": "Type", "width": 120},
            {"key": "summary", "label": "Action Details", "width": 380},
        ]
        self.history_table = PaginatedTable(self.tab_history, columns=cols_ev)
        self.history_table.pack(fill=tk.BOTH, expand=True)

    def _on_tab_switch(self, tab_name: str, **kwargs) -> None:
        if tab_name == "Player":
            self.refresh()

    def _on_command_click(self, act_name: str) -> None:
        tgt = self.entry_target.get().strip()
        msg = f"[EXEC] {act_name} -> target '{tgt}' queued.\n"
        self.txt_log.insert(tk.END, msg)
        self.txt_log.see(tk.END)

    def refresh(self) -> None:
        self.clear_error()
        if not session.is_loaded or not session.db:
            self.hunters_table.set_data([])
            self.allies_table.set_data([])
            self.history_table.set_data([])
            return

        try:
            # Query events involving player_0
            all_evts = session.db.get_events(limit=5000)
            player_evts = []
            hunters = []
            allies = []

            for e in all_evts:
                desc = e.get("description", "")
                if "player_0" in desc or "Player" in desc or "Traveler" in desc:
                    player_evts.append({
                        "id": e.get("id"),
                        "year": e.get("year"),
                        "type": e.get("type"),
                        "summary": desc,
                    })

            self.history_table.set_data(list(reversed(player_evts)))

            # Query epistemic cases / grudge cases against player
            epistemic = session.db.get_epistemic_cases(limit=100)
            for ec in epistemic:
                if "player" in ec.get("case_type", "").lower() or "traveler" in ec.get("case_type", "").lower():
                    hunters.append({
                        "character": ec.get("believer_name", "Villager"),
                        "settlement": ec.get("settlement_id", "--"),
                        "hatred": 75.0,
                        "status": "Hunting Blood Vengeance",
                    })

            self.hunters_table.set_data(hunters)
            self.allies_table.set_data(allies)

        except Exception as e:
            log_error(f"Error loading Player tab: {e}")
            self.show_error(f"Failed to load player actor data: {e}")
