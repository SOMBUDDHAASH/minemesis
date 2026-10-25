"""
Viewer V2 Main Application Shell (viewer/app.py).
Provides thin top toolbar, dynamic tab notebook, status bar,
and collapsible right-side persistent Detail Panel (320px).
"""

from __future__ import annotations
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Any, Optional

from viewer.core.bus import bus
from viewer.core.logging import log_error
from viewer.core.session import session
from viewer.core.settings import settings
from viewer.ui.tabs import TAB_REGISTRY, BaseTab
from viewer.ui.theme import theme
from viewer.ui.widgets.entity_link import EntityPill


class DetailPanel(tk.Frame):
    """Persistent collapsible right-side pane (320px) displaying selected entity overview."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        c = theme.colors
        super().__init__(parent, bg=c["panel_bg"], width=320, padx=12, pady=10, **kwargs)
        self.pack_propagate(False)

        # Header with close button
        hdr = tk.Frame(self, bg=c["panel_bg"])
        hdr.pack(fill=tk.X, pady=(0, 8))

        self.lbl_entity_type = tk.Label(hdr, text="INSPECTOR", font=("Segoe UI", 7, "bold"), fg=c["accent"], bg=c["panel_bg"])
        self.lbl_entity_type.pack(side=tk.LEFT)

        btn_close = tk.Button(
            hdr,
            text="✕",
            command=self._hide,
            font=("Segoe UI", 8),
            bg=c["panel_bg"],
            fg=c["fg_muted"],
            relief=tk.FLAT,
            padx=4,
            pady=0,
            cursor="hand2",
        )
        btn_close.pack(side=tk.RIGHT)

        # Content frame
        self.content_frame = tk.Frame(self, bg=c["panel_bg"])
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        self.lbl_title = tk.Label(self.content_frame, text="No entity selected", font=("Segoe UI", 12, "bold"), fg=c["fg"], bg=c["panel_bg"], wraplength=290, justify="left")
        self.lbl_title.pack(anchor="w", pady=(0, 4))

        self.lbl_subtitle = tk.Label(self.content_frame, text="Click any character, event, or settlement to view details.", font=("Segoe UI", 8), fg=c["fg_muted"], bg=c["panel_bg"], wraplength=290, justify="left")
        self.lbl_subtitle.pack(anchor="w", pady=(0, 10))

        self.details_box = tk.Text(
            self.content_frame,
            bg=c["card_bg"],
            fg=c["fg"],
            font=("Segoe UI", 9),
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=8,
            pady=8,
            height=12,
        )
        self.details_box.pack(fill=tk.BOTH, expand=True)
        self.details_box.config(state=tk.DISABLED)

        # Bottom action button
        self.btn_jump = tk.Button(
            self,
            text="Open in Full Tab ↗",
            command=self._on_jump_to_tab,
            bg=c["card_bg"],
            fg=c["accent"],
            font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT,
            pady=6,
            cursor="hand2",
            state=tk.DISABLED,
        )
        self.btn_jump.pack(fill=tk.X, pady=(8, 0))

        self._current_type: Optional[str] = None
        self._current_id: Optional[str] = None

        bus.subscribe("entity:selected", self._on_entity_selected)

    def _hide(self) -> None:
        self.pack_forget()
        settings.set("detail_panel_visible", False)

    def _on_entity_selected(self, entity_type: str, entity_id: str, **kwargs: Any) -> None:
        if not self.winfo_ismapped():
            self.pack(side=tk.RIGHT, fill=tk.Y)
            settings.set("detail_panel_visible", True)

        self._current_type = entity_type
        self._current_id = entity_id
        self._render_details()

    def _render_details(self) -> None:
        if not session.db or not self._current_type or not self._current_id:
            return

        t = self._current_type
        eid = self._current_id
        self.lbl_entity_type.config(text=f"INSPECTOR: {t.upper()}")
        self.btn_jump.config(state=tk.NORMAL)

        self.details_box.config(state=tk.NORMAL)
        self.details_box.delete("1.0", tk.END)

        if t == "character":
            c = session.db.get_character(eid)
            if c:
                name = c.get("display_name", eid)
                self.lbl_title.config(text=name)
                alive = (c.get("death_tick") is None)
                self.lbl_subtitle.config(text=f"{c.get('sex', 'M')} • {c.get('profession', 'Citizen')} • {'Living' if alive else 'Deceased'}")

                self.details_box.insert(tk.END, f"ID: {eid}\n")
                self.details_box.insert(tk.END, f"Full Name: {c.get('first_name')} {c.get('last_name')}\n")
                self.details_box.insert(tk.END, f"Ordinal: {c.get('name_ordinal', 1)}\n")
                self.details_box.insert(tk.END, f"Settlement: {c.get('settlement_id')}\n")
                self.details_box.insert(tk.END, f"Father: {c.get('father_id') or 'None'}\n")
                self.details_box.insert(tk.END, f"Mother: {c.get('mother_id') or 'None'}\n")
                self.details_box.insert(tk.END, f"Spouse: {c.get('spouse_id') or 'None'}\n\n")

                evts = session.db.get_character_events(eid)
                self.details_box.insert(tk.END, f"Recorded Events ({len(evts)}):\n")
                for e in evts[:8]:
                    self.details_box.insert(tk.END, f"• Y{e['year']} #{e['event_id']}: {e['type']}\n")

        elif t == "settlement":
            s = session.db.get_settlement(eid)
            if s:
                self.lbl_title.config(text=s.get("name", eid))
                self.lbl_subtitle.config(text=f"Biome: {s.get('biome')} • Culture: {s.get('culture')}")
                self.details_box.insert(tk.END, f"ID: {eid}\n")
                self.details_box.insert(tk.END, f"Founded Tick: {s.get('founded_tick', 0)}\n\n")
                census = session.db.get_census(settlement_id=eid)
                if census:
                    latest = census[-1]
                    self.details_box.insert(tk.END, f"Current Population: {latest.get('population')}\n")
                    self.details_box.insert(tk.END, f"Food Stores: {int(latest.get('food', 0))}\n")
                    self.details_box.insert(tk.END, f"Settlement Wealth: {int(latest.get('wealth', 0))}\n")

        elif t == "event":
            try:
                e_id = int(eid)
                e = session.db.get_event(e_id)
                if e:
                    self.lbl_title.config(text=f"Event #{e_id}: {e.get('type')}")
                    self.lbl_subtitle.config(text=f"Year {e.get('year')} (Tick {e.get('tick')})")
                    self.details_box.insert(tk.END, f"Description:\n{e.get('description')}\n\n")
                    self.details_box.insert(tk.END, f"Importance: {e.get('importance', 1.0)}\n\n")

                    parts = e.get("participants", [])
                    if parts:
                        self.details_box.insert(tk.END, "Participants:\n")
                        for p in parts:
                            self.details_box.insert(tk.END, f"• {p.get('role')}: {p.get('name_at_time')} ({p.get('character_id')})\n")

                    causes = e.get("causes", [])
                    if causes:
                        self.details_box.insert(tk.END, f"\nCauses: {', '.join([f'#{c}' for c in causes])}\n")
                    conseq = e.get("consequences", [])
                    if conseq:
                        self.details_box.insert(tk.END, f"Consequences: {', '.join([f'#{cq}' for cq in conseq])}\n")
            except ValueError:
                pass

        elif t == "book":
            b = session.db.get_book(eid)
            if b:
                self.lbl_title.config(text=b.get("title", eid))
                self.lbl_subtitle.config(text=f"Penned by {b.get('author_name')} in Year {b.get('year_written')}")
                self.details_box.insert(tk.END, f"Topic / Genre: {b.get('topic')}\n")
                self.details_box.insert(tk.END, f"Settlement: {b.get('settlement_id')}\n")
                self.details_box.insert(tk.END, f"Total Pages: {b.get('page_count', len(b.get('pages', [])))}\n\n")
                pages = b.get("pages", [])
                if pages:
                    self.details_box.insert(tk.END, f"Excerpt:\n{pages[0][:200]}…\n")

        elif t == "religion":
            r = session.db.get_religion(eid)
            if r:
                self.lbl_title.config(text=r.get("name", eid))
                self.lbl_subtitle.config(text=f"Founded Year {r.get('founded_year')} • {r.get('adherent_count', 0)} Adherents")
                self.details_box.insert(tk.END, f"Parent Faith: {r.get('parent_id') or 'None'}\n\n")
                traits = r.get("traits", {})
                if traits:
                    self.details_box.insert(tk.END, "Theological Tenets:\n")
                    for k, v in traits.items():
                        self.details_box.insert(tk.END, f"• {k}: {v}\n")

        elif t == "thread":
            th = session.db.get_thread(eid)
            if th:
                self.lbl_title.config(text=th.get("title", eid))
                self.lbl_subtitle.config(text=f"Category: {th.get('category')} • Years {th.get('start_year')} - {th.get('end_year')}")
                self.details_box.insert(tk.END, f"Connected Events: {th.get('event_count')}\n")

        self.details_box.config(state=tk.DISABLED)

    def _on_jump_to_tab(self) -> None:
        if not self._current_type:
            return
        tab_map = {
            "character": "People",
            "settlement": "Places",
            "book": "Books",
            "religion": "Faith",
            "thread": "Threads",
            "event": "Chronicle",
        }
        target = tab_map.get(self._current_type, "Chronicle")
        bus.publish("tab:switch", tab_name=target, entity_id=self._current_id)


class StoryViewerApp(tk.Tk):
    """Root Application Shell for Minemesis Viewer V2."""

    def __init__(self, initial_file: Optional[str] = None) -> None:
        super().__init__()

        self.title("Minemesis Historical Archive Viewer V2")
        w = settings.get("window_width", 1280)
        h = settings.get("window_height", 820)
        self.geometry(f"{w}x{h}")
        self.minsize(960, 640)

        theme.apply(self)

        self._tabs_by_name: dict[str, BaseTab] = {}
        self._build_ui()
        self._bind_shortcuts()

        bus.subscribe("tab:switch", self._switch_to_tab)
        bus.subscribe("entity:selected", self._on_entity_selected)

        # Open file if passed via command line
        if initial_file:
            self.after(100, lambda: self.load_file(initial_file))

    def _build_ui(self) -> None:
        c = theme.colors

        # 1. Top Toolbar
        self.toolbar = tk.Frame(self, bg=c["panel_bg"], padx=10, pady=6)
        self.toolbar.pack(fill=tk.X)

        self.btn_open = tk.Button(
            self.toolbar,
            text="📂 Open File",
            command=self._on_open_file,
            bg=c["card_bg"],
            fg=c["fg"],
            font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
        )
        self.btn_open.pack(side=tk.LEFT, padx=(0, 8))

        # Navigation History (Back / Forward)
        self.btn_back = tk.Button(
            self.toolbar,
            text="◀",
            command=self._on_back,
            bg=c["card_bg"],
            fg=c["fg_muted"],
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            padx=8,
            pady=3,
            state=tk.DISABLED,
        )
        self.btn_back.pack(side=tk.LEFT, padx=(0, 2))

        self.btn_forward = tk.Button(
            self.toolbar,
            text="▶",
            command=self._on_forward,
            bg=c["card_bg"],
            fg=c["fg_muted"],
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            padx=8,
            pady=3,
            state=tk.DISABLED,
        )
        self.btn_forward.pack(side=tk.LEFT, padx=(0, 12))

        self.lbl_file = tk.Label(
            self.toolbar,
            text="No file opened",
            font=("Segoe UI", 9),
            fg=c["fg_muted"],
            bg=c["panel_bg"],
        )
        self.lbl_file.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Theme toggle & Inspector toggle
        self.btn_theme = tk.Button(
            self.toolbar,
            text="🌓 Theme",
            command=self._toggle_theme,
            bg=c["card_bg"],
            fg=c["fg"],
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            padx=8,
            pady=3,
        )
        self.btn_theme.pack(side=tk.RIGHT, padx=(6, 0))

        self.btn_toggle_panel = tk.Button(
            self.toolbar,
            text="📋 Inspector",
            command=self._toggle_detail_panel,
            bg=c["card_bg"],
            fg=c["fg"],
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            padx=8,
            pady=3,
        )
        self.btn_toggle_panel.pack(side=tk.RIGHT)

        # 2. Main Middle Area (Notebook + Detail Panel)
        self.main_container = tk.Frame(self, bg=c["bg"])
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Detail Panel (Right)
        self.detail_panel = DetailPanel(self.main_container)
        if settings.get("detail_panel_visible", True):
            self.detail_panel.pack(side=tk.RIGHT, fill=tk.Y)

        # Notebook (Left / Center)
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Discover and instantiate all registered tabs
        for order, tab_name, tab_cls in TAB_REGISTRY:
            tab_inst = tab_cls(self.notebook)
            self.notebook.add(tab_inst, text=tab_name)
            self._tabs_by_name[tab_name] = tab_inst

        # 3. Status Bar
        self.status_bar = tk.Frame(self, bg=c["panel_bg"], padx=12, pady=4)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_status = tk.Label(
            self.status_bar,
            text="Minemesis Viewer V2 ready.",
            font=("Segoe UI", 8),
            fg=c["fg_muted"],
            bg=c["panel_bg"],
        )
        self.lbl_status.pack(side=tk.LEFT)

        self.lbl_status_right = tk.Label(
            self.status_bar,
            text="Schema: v1 • Build: viewer-v2",
            font=("Segoe UI", 8),
            fg=c["fg_muted"],
            bg=c["panel_bg"],
        )
        self.lbl_status_right.pack(side=tk.RIGHT)

    def _bind_shortcuts(self) -> None:
        self.bind("<Alt-Left>", lambda e: self._on_back())
        self.bind("<Alt-Right>", lambda e: self._on_forward())
        self.bind("<Control-o>", lambda e: self._on_open_file())
        self.bind("<Control-b>", lambda e: self._toggle_detail_panel())

    def _on_tab_changed(self, event: tk.Event) -> None:
        sel = self.notebook.select()
        if sel:
            tab_widget = self.nametowidget(sel)
            if isinstance(tab_widget, BaseTab):
                tab_widget.on_activate()

    def _switch_to_tab(self, tab_name: str, entity_id: Optional[str] = None, **kwargs: Any) -> None:
        if tab_name in self._tabs_by_name:
            tab_w = self._tabs_by_name[tab_name]
            self.notebook.select(tab_w)
            tab_w.on_activate()

    def _on_entity_selected(self, can_back: bool = False, can_forward: bool = False, **kwargs: Any) -> None:
        self.btn_back.config(state=tk.NORMAL if can_back else tk.DISABLED, fg=theme.colors["fg"] if can_back else theme.colors["fg_muted"])
        self.btn_forward.config(state=tk.NORMAL if can_forward else tk.DISABLED, fg=theme.colors["fg"] if can_forward else theme.colors["fg_muted"])

    def _on_back(self) -> None:
        session.go_back()

    def _on_forward(self) -> None:
        session.go_forward()

    def _toggle_detail_panel(self) -> None:
        if self.detail_panel.winfo_ismapped():
            self.detail_panel.pack_forget()
            settings.set("detail_panel_visible", False)
        else:
            self.detail_panel.pack(side=tk.RIGHT, fill=tk.Y)
            settings.set("detail_panel_visible", True)

    def _toggle_theme(self) -> None:
        new_theme = "light" if theme.current_theme == "dark" else "dark"
        theme.set_theme(new_theme, self)
        settings.set("theme", new_theme)
        # Refresh current tab
        self._on_tab_changed(None)

    def _on_open_file(self) -> None:
        f = filedialog.askopenfilename(
            title="Open Minemesis Run Database",
            filetypes=[("Minemesis Archive", "*.minemesis"), ("All Files", "*.*")],
        )
        if f:
            self.load_file(f)

    def load_file(self, file_path: str | Path) -> None:
        try:
            session.load_file(file_path)
            p = Path(file_path)
            self.lbl_file.config(text=p.name)
            self.title(f"Minemesis Viewer V2 - {p.name}")
            self.lbl_status.config(text=f"Loaded archive: {p.name}")

            # Notify active tab
            self._on_tab_changed(None)
        except Exception as e:
            log_error(f"Could not load run file: {e}", e)
            messagebox.showerror("Error Loading Run", f"Could not load run file:\n{e}")
