"""
Narrative Director Control and Intervention Tab for Viewer V2 (Milestone 5).
Displays environmental pressure levers, tension metrics, and director intervention history.
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


@register_tab("Director", order=11)
class DirectorTab(BaseTab):
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        c = theme.colors

        # Left Pane: Director Status, Levers & Metrics
        left_frame = tk.Frame(self.paned, bg=c["panel_bg"], width=320, padx=14, pady=12)
        self.paned.add(left_frame, weight=1)

        tk.Label(
            left_frame,
            text="Narrative Director",
            font=("Segoe UI", 12, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
        ).pack(anchor="w", pady=(0, 6))

        tk.Label(
            left_frame,
            text="Indirect Environmental Pacing Levers",
            font=("Segoe UI", 8),
            fg=c["fg_muted"],
            bg=c["panel_bg"],
        ).pack(anchor="w", pady=(0, 12))

        # Status & Toggle
        self.is_enabled = tk.BooleanVar(value=True)
        self.chk_enable = tk.Checkbutton(
            left_frame,
            text="Enable Director Interventions",
            variable=self.is_enabled,
            font=("Segoe UI", 9, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
            selectcolor=c["bg"],
            activebackground=c["panel_bg"],
            activeforeground=c["fg"],
            command=self._on_toggle,
        )
        self.chk_enable.pack(anchor="w", pady=(0, 14))

        # Pacing Metrics Box
        lbl_box = tk.LabelFrame(
            left_frame,
            text="Tension & Stagnation Metrics",
            font=("Segoe UI", 9, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
            padx=10,
            pady=8,
        )
        lbl_box.pack(fill=tk.X, pady=(0, 14))

        self.lbl_stagnation = tk.Label(lbl_box, text="Stagnation Timer: 0 months", font=("Segoe UI", 9), fg=c["fg"], bg=c["panel_bg"])
        self.lbl_stagnation.pack(anchor="w", pady=2)

        self.lbl_crisis = tk.Label(lbl_box, text="World Crisis Score: Nominal", font=("Segoe UI", 9), fg=c["fg"], bg=c["panel_bg"])
        self.lbl_crisis.pack(anchor="w", pady=2)

        # Environmental Levers Display
        lever_box = tk.LabelFrame(
            left_frame,
            text="Active Environmental Levers",
            font=("Segoe UI", 9, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
            padx=10,
            pady=8,
        )
        lever_box.pack(fill=tk.X, pady=(0, 10))

        self.lbl_scarcity = tk.Label(lever_box, text="Resource Scarcity: x1.00", font=("Segoe UI", 9), fg=c["fg"], bg=c["panel_bg"])
        self.lbl_scarcity.pack(anchor="w", pady=2)

        self.lbl_bandit = tk.Label(lever_box, text="Bandit Raid Pressure: x1.00", font=("Segoe UI", 9), fg=c["fg"], bg=c["panel_bg"])
        self.lbl_bandit.pack(anchor="w", pady=2)

        self.lbl_migration = tk.Label(lever_box, text="Migration Wanderlust: x1.00", font=("Segoe UI", 9), fg=c["fg"], bg=c["panel_bg"])
        self.lbl_migration.pack(anchor="w", pady=2)

        # Right Pane: Director Interventions History
        self.right_frame = tk.Frame(self.paned, bg=c["bg"], padx=14, pady=12)
        self.paned.add(self.right_frame, weight=3)

        tk.Label(
            self.right_frame,
            text="Director Intervention Log",
            font=("Segoe UI", 12, "bold"),
            fg=c["fg"],
            bg=c["bg"],
        ).pack(anchor="w", pady=(0, 4))

        tk.Label(
            self.right_frame,
            text="Chronological record of all indirect environmental lever adjustments.",
            font=("Segoe UI", 8),
            fg=c["fg_muted"],
            bg=c["bg"],
        ).pack(anchor="w", pady=(0, 10))

        cols = [
            {"key": "year", "label": "Year", "width": 60},
            {"key": "lever", "label": "Lever", "width": 140},
            {"key": "magnitude", "label": "Multiplier", "width": 90},
            {"key": "reason", "label": "Pacing Rationale", "width": 260},
            {"key": "summary", "label": "Description", "width": 320},
        ]
        self.interventions_table = PaginatedTable(self.right_frame, columns=cols)
        self.interventions_table.pack(fill=tk.BOTH, expand=True)

        bus.subscribe("session:loaded", lambda **kw: self.refresh())
        bus.subscribe("tab:switch", self._on_tab_switch)

    def _on_tab_switch(self, tab_name: str, **kwargs) -> None:
        if tab_name == "Director":
            self.refresh()

    def _on_toggle(self) -> None:
        state = "ENABLED" if self.is_enabled.get() else "DISABLED"
        self.lbl_crisis.config(text=f"Director Status: {state}")

    def refresh(self) -> None:
        self.clear_error()
        if not session.is_loaded or not session.db:
            self.interventions_table.set_data([])
            return

        try:
            # Query DirectorAction events
            evts = session.db.get_events(event_types=["DirectorAction"], limit=500)
            rows = []
            last_scarcity = 1.0
            last_bandit = 1.0
            last_mig = 1.0

            for e in evts:
                payload = e.get("payload", {})
                lever = payload.get("lever", "environmental")
                mag = payload.get("magnitude", 1.0)
                reason = payload.get("reason", "historical pacing")

                if lever == "resource_scarcity":
                    last_scarcity = mag
                elif lever == "bandit_pressure":
                    last_bandit = mag
                elif lever == "migration_pressure":
                    last_mig = mag

                rows.append({
                    "id": e.get("id"),
                    "year": e.get("year"),
                    "lever": lever,
                    "magnitude": f"x{mag:.2f}",
                    "reason": reason.capitalize(),
                    "summary": e.get("description"),
                })

            self.lbl_scarcity.config(text=f"Resource Scarcity: x{last_scarcity:.2f}")
            self.lbl_bandit.config(text=f"Bandit Raid Pressure: x{last_bandit:.2f}")
            self.lbl_migration.config(text=f"Migration Wanderlust: x{last_mig:.2f}")
            self.lbl_stagnation.config(text=f"Total Interventions: {len(rows)}")

            self.interventions_table.set_data(reversed(rows))

        except Exception as e:
            log_error(f"Error loading Director tab: {e}")
            self.show_error(f"Failed to load director data: {e}")
