"""
Faith (Religions, Schisms & Myths) Tab for Viewer V2.
Displays theological trees, holy sites, doctrinal traits, myths, and adherent distributions.
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


@register_tab("Faith", order=5)
class FaithTab(BaseTab):
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self.selected_rel_id: Optional[str] = None

        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        c = theme.colors

        # Left Pane: Faith Tree & Roster
        left_frame = tk.Frame(self.paned, bg=c["panel_bg"], width=300)
        self.paned.add(left_frame, weight=1)

        tk.Label(
            left_frame,
            text="Religions & Traditions",
            font=("Segoe UI", 11, "bold"),
            fg=c["fg"],
            bg=c["panel_bg"],
            padx=10,
            pady=8,
        ).pack(anchor="w")

        tree_container = tk.Frame(left_frame, bg=c["panel_bg"])
        tree_container.pack(fill=tk.BOTH, expand=True)

        self.rel_tree = ttk.Treeview(tree_container, columns=["adherents"], show="tree headings", selectmode="browse")
        self.rel_tree.heading("#0", text="Faith Tradition")
        self.rel_tree.heading("adherents", text="Followers")
        self.rel_tree.column("#0", width=180)
        self.rel_tree.column("adherents", width=70, anchor="e")

        sb = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.rel_tree.yview)
        self.rel_tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.rel_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.rel_tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Right Pane: Faith Detail
        self.right_frame = tk.Frame(self.paned, bg=c["bg"], padx=16, pady=12)
        self.paned.add(self.right_frame, weight=3)

        self._build_detail_view()

        bus.subscribe("session:loaded", lambda **kw: self.refresh())
        bus.subscribe("tab:switch", self._on_tab_switch)

    def _build_detail_view(self) -> None:
        c = theme.colors

        # Top Card
        self.header_card = tk.Frame(self.right_frame, bg=c["panel_bg"], padx=16, pady=12, relief=tk.FLAT)
        self.header_card.pack(fill=tk.X, pady=(0, 10))

        self.lbl_name = tk.Label(self.header_card, text="Select a Faith Tradition", font=("Segoe UI", 16, "bold"), fg=c["fg"], bg=c["panel_bg"])
        self.lbl_name.pack(anchor="w")

        self.lbl_meta = tk.Label(self.header_card, text="--", font=("Segoe UI", 9), fg=c["fg_muted"], bg=c["panel_bg"])
        self.lbl_meta.pack(anchor="w", pady=(2, 0))

        # Sub Notebook: Tenets, Holy Sites, Sacred Myths, Adherents Chart
        self.sub_notebook = ttk.Notebook(self.right_frame)
        self.sub_notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Doctrines & Tenets
        self.tab_traits = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_traits, text="Theological Tenets & Virtues")

        self.traits_text = tk.Text(
            self.tab_traits,
            bg=c["panel_bg"],
            fg=c["fg"],
            font=("Segoe UI", 9),
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=8,
            pady=8,
        )
        self.traits_text.pack(fill=tk.BOTH, expand=True)

        # Tab 2: Holy Sites
        self.tab_sites = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_sites, text="Consecrated Holy Sites")

        self.sites_container = tk.Frame(self.tab_sites, bg=c["panel_bg"], padx=12, pady=10)
        self.sites_container.pack(fill=tk.BOTH, expand=True)

        # Tab 3: Sacred Myths
        self.tab_myths = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_myths, text="Sacred Myths & Scripture")

        self.myths_text = tk.Text(
            self.tab_myths,
            bg=c["parchment_bg"],
            fg=c["parchment_fg"],
            font=("Georgia", 10),
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=12,
            pady=12,
        )
        self.myths_text.pack(fill=tk.BOTH, expand=True)

        # Tab 4: Adherent Comparison Chart
        self.tab_chart = tk.Frame(self.sub_notebook, bg=c["bg"], padx=8, pady=8)
        self.sub_notebook.add(self.tab_chart, text="Adherent Distribution")

        self.chart_adherents = CanvasChart(self.tab_chart)
        self.chart_adherents.pack(fill=tk.BOTH, expand=True)

    def _on_tab_switch(self, tab_name: str, entity_id: str, **kwargs) -> None:
        if tab_name == "Faith" and entity_id.startswith("rel_"):
            self.selected_rel_id = entity_id
            self.refresh()

    def refresh(self) -> None:
        self.clear_error()
        if not session.db:
            return

        try:
            religions = session.db.get_religions()
            self.rel_tree.delete(*self.rel_tree.get_children())

            # Build Tree: Root faiths vs Schisms
            roots = [r for r in religions if not r.get("parent_id")]
            children = [r for r in religions if r.get("parent_id")]

            for r in roots:
                rid = r["id"]
                self.rel_tree.insert("", tk.END, iid=rid, text=r["name"], values=[r.get("adherent_count", 0)])

            for c in children:
                cid = c["id"]
                pid = c["parent_id"]
                parent_iid = pid if self.rel_tree.exists(pid) else ""
                self.rel_tree.insert(parent_iid, tk.END, iid=cid, text=c["name"], values=[c.get("adherent_count", 0)])

            # Update Chart
            bar_data = [
                {"label": r["name"], "value": float(r.get("adherent_count", 0)), "color": theme.colors["accent"]}
                for r in religions
            ]
            self.chart_adherents.set_bar_chart(bar_data)

            if not self.selected_rel_id and religions:
                self.selected_rel_id = religions[0]["id"]

            if self.selected_rel_id:
                self._display_religion(self.selected_rel_id)

        except Exception as e:
            log_error("Error in FaithTab.refresh", e)
            self.show_error(f"Failed to load faith data: {e}")

    def _on_tree_select(self, event: tk.Event) -> None:
        sel = self.rel_tree.selection()
        if sel:
            rid = sel[0]
            self.selected_rel_id = rid
            session.select_entity("religion", rid)
            self._display_religion(rid)

    def _display_religion(self, rel_id: str) -> None:
        if not session.db:
            return

        r = session.db.get_religion(rel_id)
        if not r:
            return

        name = r.get("name", rel_id)
        parent_id = r.get("parent_id")
        parent_txt = f" (Schism from {parent_id})" if parent_id else " (Mother Tradition)"
        adherents = r.get("adherent_count", 0)
        f_year = r.get("founded_year", 1)

        self.lbl_name.config(text=name)
        self.lbl_meta.config(text=f"Founded in Year {f_year}{parent_txt} • Followers: {adherents}")

        # Tenets
        self.traits_text.config(state=tk.NORMAL)
        self.traits_text.delete("1.0", tk.END)
        traits = r.get("traits", {})
        if not traits:
            self.traits_text.insert(tk.END, "No specific doctrinal tenets recorded.\n")
        else:
            for k, v in traits.items():
                self.traits_text.insert(tk.END, f"• {k.replace('_', ' ').capitalize()}: {v}\n")
        self.traits_text.config(state=tk.DISABLED)

        # Holy Sites
        for w in self.sites_container.winfo_children():
            w.destroy()
        sites = session.db.get_holy_sites(religion_id=rel_id)
        if not sites:
            tk.Label(self.sites_container, text="No dedicated holy sites consecrated.", font=("Segoe UI", 9), fg=theme.colors["fg_muted"], bg=theme.colors["panel_bg"]).pack(anchor="w")
        else:
            for s in sites:
                row = tk.Frame(self.sites_container, bg=theme.colors["panel_bg"], pady=4)
                row.pack(fill=tk.X)
                pill = EntityPill(row, s["settlement_id"], "settlement", s["settlement_id"])
                pill.pack(side=tk.LEFT)
                tk.Label(row, text=f"• Consecrated Year {s['dedication_year']}", font=("Segoe UI", 8), fg=theme.colors["fg"], bg=theme.colors["panel_bg"]).pack(side=tk.LEFT, padx=6)

        # Sacred Myths
        self.myths_text.config(state=tk.NORMAL)
        self.myths_text.delete("1.0", tk.END)
        myths = session.db.get_myths(religion_id=rel_id)
        if not myths:
            self.myths_text.insert(tk.END, "No written myths or sacred oral texts preserved.\n")
        else:
            for m in myths:
                self.myths_text.insert(tk.END, f"# {m.get('title')}\n")
                self.myths_text.insert(tk.END, f"Recorded Year {m.get('year_recorded', 1)}\n\n")
                self.myths_text.insert(tk.END, f"{m.get('text')}\n\n" + "-" * 40 + "\n\n")
        self.myths_text.config(state=tk.DISABLED)
