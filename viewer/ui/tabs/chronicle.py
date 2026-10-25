"""
Chronicle (Story / Events) Tab for Viewer V2.
Features era/year accordion, major events mode, search filters,
paginated table / card view, and causal why-graph popups.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

from viewer.core.bus import bus
from viewer.core.logging import log_error
from viewer.core.session import session
from viewer.services.causality import causality_service
from viewer.services.narration import narrate_event
from viewer.ui.tabs.base import BaseTab, register_tab
from viewer.ui.theme import theme
from viewer.ui.widgets.entity_link import EntityPill
from viewer.ui.widgets.filter_bar import FilterBar
from viewer.ui.widgets.table import PaginatedTable


@register_tab("Chronicle", order=1)
class ChronicleTab(BaseTab):
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self._view_mode = "cards"  # "cards" or "table"
        self._page = 0
        self._page_size = 50

        # 1. Filter Bar
        self.filter_bar = FilterBar(self)
        self.filter_bar.pack(fill=tk.X)

        # 2. View Toggle Bar
        c = theme.colors
        self.view_bar = tk.Frame(self, bg=c["panel_bg"], padx=10, pady=4)
        self.view_bar.pack(fill=tk.X, pady=(1, 0))

        self.lbl_stats = tk.Label(self.view_bar, text="0 events found", font=("Segoe UI", 8), fg=c["fg_muted"], bg=c["panel_bg"])
        self.lbl_stats.pack(side=tk.LEFT)

        self.btn_toggle_view = tk.Button(
            self.view_bar,
            text="Switch to Table View",
            command=self._toggle_view,
            bg=c["card_bg"],
            fg=c["fg"],
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            padx=8,
            pady=2,
        )
        self.btn_toggle_view.pack(side=tk.RIGHT)

        # 3. Main Container
        self.content_container = tk.Frame(self, bg=c["bg"])
        self.content_container.pack(fill=tk.BOTH, expand=True)

        # Card View (Scrollable Canvas)
        self.card_canvas = tk.Canvas(self.content_container, bg=c["bg"], highlightthickness=0)
        self.card_scrollbar = ttk.Scrollbar(self.content_container, orient=tk.VERTICAL, command=self.card_canvas.yview)
        self.card_frame = tk.Frame(self.card_canvas, bg=c["bg"])

        self.card_frame.bind(
            "<Configure>",
            lambda e: self.card_canvas.configure(scrollregion=self.card_canvas.bbox("all")),
        )
        self.card_window = self.card_canvas.create_window((0, 0), window=self.card_frame, anchor="nw")
        self.card_canvas.configure(yscrollcommand=self.card_scrollbar.set)
        self.card_canvas.bind("<Configure>", lambda e: self.card_canvas.itemconfig(self.card_window, width=e.width))

        # Table View
        cols = [
            {"key": "event_id", "label": "ID", "width": 50},
            {"key": "year", "label": "Year", "width": 50},
            {"key": "type", "label": "Type", "width": 110},
            {"key": "description", "label": "Description", "width": 450},
            {"key": "importance", "label": "Importance", "width": 80},
        ]
        self.table_widget = PaginatedTable(
            self.content_container,
            columns=cols,
            on_select=lambda r: session.select_entity("event", str(r.get("event_id"))),
            on_activate=lambda r: self._open_causal_popup(r.get("event_id")),
        )

        # Show card view by default
        self._show_card_view()

        bus.subscribe("filter:changed", self._on_filter_changed)
        bus.subscribe("session:loaded", lambda **kw: self.refresh())

    def _toggle_view(self) -> None:
        if self._view_mode == "cards":
            self._view_mode = "table"
            self.btn_toggle_view.config(text="Switch to Cards View")
            self._show_table_view()
        else:
            self._view_mode = "cards"
            self.btn_toggle_view.config(text="Switch to Table View")
            self._show_card_view()
        self.refresh()

    def _show_card_view(self) -> None:
        self.table_widget.pack_forget()
        self.card_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.card_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _show_table_view(self) -> None:
        self.card_scrollbar.pack_forget()
        self.card_canvas.pack_forget()
        self.table_widget.pack(fill=tk.BOTH, expand=True)

    def _on_filter_changed(self, **kwargs: Any) -> None:
        self._page = 0
        self.refresh()

    def refresh(self) -> None:
        self.clear_error()
        if not session.db:
            return

        try:
            f = session.filters
            total = session.db.get_event_count(
                era=f.get("era"),
                settlement_id=f.get("settlement"),
                event_types=f.get("event_types"),
                search=f.get("search"),
                major_only=f.get("major_only", False),
            )
            self.lbl_stats.config(text=f"{total} events found")

            events = session.db.get_events(
                limit=150,
                offset=0,
                era=f.get("era"),
                settlement_id=f.get("settlement"),
                event_types=f.get("event_types"),
                search=f.get("search"),
                major_only=f.get("major_only", False),
            )

            if self._view_mode == "table":
                self.table_widget.set_items(events)
            else:
                self._render_cards(events)

        except Exception as e:
            log_error("Error in ChronicleTab.refresh", e)
            self.show_error(f"Failed to load chronicle events: {e}")

    def _render_cards(self, events: list[dict[str, Any]]) -> None:
        for w in self.card_frame.winfo_children():
            w.destroy()

        c = theme.colors
        current_year = -1

        for evt in events:
            y = evt.get("year", 1)
            eid = evt.get("event_id", 0)

            # Year separator if year changes
            if y != current_year:
                current_year = y
                yr_sep = tk.Frame(self.card_frame, bg=c["bg"], pady=6)
                yr_sep.pack(fill=tk.X, padx=12)
                tk.Label(
                    yr_sep,
                    text=f"YEAR {y}",
                    font=("Segoe UI", 9, "bold"),
                    fg=c["accent"],
                    bg=c["bg"],
                ).pack(side=tk.LEFT)
                tk.Frame(yr_sep, bg=c["border"], height=1).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

            card = tk.Frame(self.card_frame, bg=c["panel_bg"], padx=10, pady=8, relief=tk.FLAT)
            card.pack(fill=tk.X, padx=12, pady=2)

            # Top row: Type badge, ID, Why button
            top_row = tk.Frame(card, bg=c["panel_bg"])
            top_row.pack(fill=tk.X)

            type_col = c["accent"]
            if evt.get("importance", 1.0) >= 2.0:
                type_col = c["warning"]
            if evt.get("type") in ("Death", "Raid", "Feud"):
                type_col = c["danger"]

            t_badge = tk.Label(
                top_row,
                text=evt.get("type", "Event").upper(),
                font=("Segoe UI", 7, "bold"),
                bg=c["card_bg"],
                fg=type_col,
                padx=6,
                pady=1,
            )
            t_badge.pack(side=tk.LEFT)

            id_lbl = tk.Label(
                top_row,
                text=f"#{eid}",
                font=("Consolas", 8),
                fg=c["fg_muted"],
                bg=c["panel_bg"],
            )
            id_lbl.pack(side=tk.LEFT, padx=6)

            btn_why = tk.Button(
                top_row,
                text="Why? 🔍",
                command=lambda e_id=eid: self._open_causal_popup(e_id),
                font=("Segoe UI", 7, "bold"),
                bg=c["card_bg"],
                fg=c["accent"],
                relief=tk.FLAT,
                padx=6,
                pady=1,
                cursor="hand2",
            )
            btn_why.pack(side=tk.RIGHT)

            # Middle: Prose description
            prose = narrate_event(evt)
            desc_lbl = tk.Label(
                card,
                text=prose,
                font=("Segoe UI", 9),
                fg=c["fg"],
                bg=c["panel_bg"],
                wraplength=700,
                justify="left",
                anchor="w",
            )
            desc_lbl.pack(fill=tk.X, pady=(4, 4))

            # Bottom: Participant pills
            parts = session.db.get_event_participants(eid) if session.db else []
            if parts:
                p_row = tk.Frame(card, bg=c["panel_bg"])
                p_row.pack(fill=tk.X, pady=(2, 0))
                for p in parts[:5]:
                    cid = p.get("character_id", "")
                    name = p.get("name_at_time", cid)
                    pill = EntityPill(p_row, name, "character", cid)
                    pill.pack(side=tk.LEFT, padx=(0, 4))

            # Bind card click to select event
            def _select(e, e_id=eid):
                session.select_entity("event", str(e_id))

            card.bind("<Button-1>", _select)
            desc_lbl.bind("<Button-1>", _select)

    def _open_causal_popup(self, event_id: int) -> None:
        """Opens popup displaying ancestral causal chain for an event."""
        if not session.db:
            return

        evt = session.db.get_event(event_id)
        if not evt:
            return

        chain = causality_service.get_causal_chain(event_id, max_depth=6)

        c = theme.colors
        pop = tk.Toplevel(self)
        pop.title(f"Causal Chain for Event #{event_id}")
        pop.geometry("620x460")
        pop.configure(bg=c["panel_bg"])
        pop.transient(self.winfo_toplevel())

        tk.Label(
            pop,
            text=f"Causal Why-Graph: Event #{event_id}",
            font=("Segoe UI", 12, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
        ).pack(pady=10)

        txt_frame = tk.Frame(pop, bg=c["panel_bg"], padx=12, pady=6)
        txt_frame.pack(fill=tk.BOTH, expand=True)

        txt = tk.Text(
            txt_frame,
            bg=c["bg"],
            fg=c["fg"],
            relief=tk.FLAT,
            font=("Consolas", 9),
            wrap=tk.WORD,
            padx=8,
            pady=8,
        )
        sb = ttk.Scrollbar(txt_frame, orient=tk.VERTICAL, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        txt.tag_configure("highlight", foreground=c["accent"], font=("Consolas", 9, "bold"))
        txt.tag_configure("arrow", foreground=c["warning"])

        txt.insert(tk.END, f"Target Event: #{event_id} ({evt.get('type')})\n")
        txt.insert(tk.END, f"Description: {evt.get('description')}\n\n")
        txt.insert(tk.END, "Ancestral Causal Chain (Step-by-Step):\n")
        txt.insert(tk.END, "=" * 55 + "\n\n")

        if not chain:
            txt.insert(tk.END, "This event has no prior causal antecedents (root foundational event).\n")
        else:
            for i, ante in enumerate(chain):
                aeid = ante.get("event_id")
                ay = ante.get("year")
                atype = ante.get("type")
                adesc = ante.get("description")
                txt.insert(tk.END, f"[{i+1}] Year {ay} • #{aeid} ({atype})\n", "highlight")
                txt.insert(tk.END, f"    {adesc}\n")
                if i < len(chain) - 1:
                    txt.insert(tk.END, "       ↓ causes\n", "arrow")

        txt.config(state=tk.DISABLED)
