"""
Threads (Storylines & Sagas) Tab for Viewer V2.
Displays overarching historical narrative threads and their connected event chains.
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


@register_tab("Threads", order=6)
class ThreadsTab(BaseTab):
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self.selected_thread_id: Optional[str] = None

        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        c = theme.colors

        # Left Pane: Threads List
        left_frame = tk.Frame(self.paned, bg=c["panel_bg"], width=300)
        self.paned.add(left_frame, weight=1)

        tk.Label(
            left_frame,
            text="Historical Storylines",
            font=("Segoe UI", 11, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
            padx=10,
            pady=8,
        ).pack(anchor="w")

        cols = [
            {"key": "title", "label": "Storyline", "width": 170},
            {"key": "category", "label": "Category", "width": 70},
            {"key": "event_count", "label": "Events", "width": 50},
        ]
        self.thread_table = PaginatedTable(
            left_frame,
            columns=cols,
            on_select=self._on_thread_select,
        )
        self.thread_table.pack(fill=tk.BOTH, expand=True)

        # Right Pane: Thread Events Timeline
        self.right_frame = tk.Frame(self.paned, bg=c["bg"], padx=16, pady=12)
        self.paned.add(self.right_frame, weight=3)

        self._build_detail_view()

        bus.subscribe("session:loaded", lambda **kw: self.refresh())
        bus.subscribe("tab:switch", self._on_tab_switch)

    def _build_detail_view(self) -> None:
        c = theme.colors

        self.header_card = tk.Frame(self.right_frame, bg=c["panel_bg"], padx=16, pady=12, relief=tk.FLAT)
        self.header_card.pack(fill=tk.X, pady=(0, 10))

        self.lbl_title = tk.Label(self.header_card, text="Select a Storyline", font=("Segoe UI", 16, "bold"), fg=c["fg"], bg=c["panel_bg"])
        self.lbl_title.pack(anchor="w")

        self.lbl_meta = tk.Label(self.header_card, text="--", font=("Segoe UI", 9), fg=c["fg_muted"], bg=c["panel_bg"])
        self.lbl_meta.pack(anchor="w", pady=(2, 0))

        # Event Chain Table
        cols = [
            {"key": "event_id", "label": "ID", "width": 50},
            {"key": "year", "label": "Year", "width": 50},
            {"key": "type", "label": "Type", "width": 110},
            {"key": "description", "label": "Event Description", "width": 450},
        ]
        self.events_table = PaginatedTable(
            self.right_frame,
            columns=cols,
            on_select=lambda r: session.select_entity("event", str(r.get("event_id"))),
            on_activate=lambda r: bus.publish("tab:switch", tab_name="Chronicle", entity_id=str(r.get("event_id"))),
        )
        self.events_table.pack(fill=tk.BOTH, expand=True)

    def _on_tab_switch(self, tab_name: str, entity_id: str, **kwargs) -> None:
        if tab_name == "Threads" and entity_id.startswith("thread_"):
            self.selected_thread_id = entity_id
            self.refresh()

    def refresh(self) -> None:
        self.clear_error()
        if not session.db:
            return

        try:
            threads = session.db.get_threads()
            self.thread_table.set_items(threads)

            if not self.selected_thread_id and threads:
                self.selected_thread_id = threads[0]["id"]

            if self.selected_thread_id:
                self._display_thread(self.selected_thread_id)

        except Exception as e:
            log_error("Error in ThreadsTab.refresh", e)
            self.show_error(f"Failed to load threads: {e}")

    def _on_thread_select(self, row: dict[str, Any]) -> None:
        tid = row.get("id")
        if tid:
            self.selected_thread_id = tid
            session.select_entity("thread", tid)
            self._display_thread(tid)

    def _display_thread(self, thread_id: str) -> None:
        if not session.db:
            return

        t = session.db.get_thread(thread_id)
        if not t:
            return

        self.lbl_title.config(text=t.get("title", thread_id))
        self.lbl_meta.config(
            text=f"Category: {t.get('category')} • Spans Years {t.get('start_year')} to {t.get('end_year')} • {t.get('event_count', 0)} connected events"
        )

        evts = session.db.get_thread_events(thread_id)
        self.events_table.set_items(evts)
