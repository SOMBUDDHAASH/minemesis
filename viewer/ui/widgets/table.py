"""
Virtualized Paginated Table Widget for Viewer V2.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Optional, Sequence

from viewer.ui.theme import theme


class PaginatedTable(tk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        columns: Sequence[dict[str, Any]],
        page_size: int = 50,
        on_select: Optional[Callable[[dict[str, Any]], None]] = None,
        on_activate: Optional[Callable[[dict[str, Any]], None]] = None,
        **kwargs,
    ) -> None:
        c = theme.colors
        super().__init__(parent, bg=c["bg"], **kwargs)

        self.columns_def = columns
        self.page_size = page_size
        self.on_select = on_select
        self.on_activate = on_activate

        self.current_page = 0
        self.total_rows = 0
        self._all_items: list[dict[str, Any]] = []

        # Treeview container
        tree_frame = tk.Frame(self, bg=c["panel_bg"])
        tree_frame.pack(fill=tk.BOTH, expand=True)

        col_ids = [c["key"] for c in columns]
        self.tree = ttk.Treeview(tree_frame, columns=col_ids, show="headings", selectmode="browse")

        # Scrollbar
        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for col in columns:
            self.tree.heading(col["key"], text=col["label"])
            self.tree.column(col["key"], width=col.get("width", 100), anchor=col.get("anchor", tk.W))

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_activate)

        # Pagination toolbar
        self.page_frame = tk.Frame(self, bg=c["panel_bg"], pady=4, padx=6)
        self.page_frame.pack(fill=tk.X)

        self.btn_prev = tk.Button(
            self.page_frame,
            text="◀ Prev",
            command=self._prev_page,
            bg=c["card_bg"],
            fg=c["fg"],
            relief=tk.FLAT,
            padx=8,
            pady=2,
            font=("Segoe UI", 8),
        )
        self.btn_prev.pack(side=tk.LEFT)

        self.lbl_page = tk.Label(
            self.page_frame,
            text="Page 1 of 1 (0 items)",
            bg=c["panel_bg"],
            fg=c["fg_muted"],
            font=("Segoe UI", 8),
        )
        self.lbl_page.pack(side=tk.LEFT, padx=12)

        self.btn_next = tk.Button(
            self.page_frame,
            text="Next ▶",
            command=self._next_page,
            bg=c["card_bg"],
            fg=c["fg"],
            relief=tk.FLAT,
            padx=8,
            pady=2,
            font=("Segoe UI", 8),
        )
        self.btn_next.pack(side=tk.LEFT)

    def set_items(self, items: list[dict[str, Any]]) -> None:
        self._all_items = items
        self.total_rows = len(items)
        self.current_page = 0
        self._render_current_page()

    def _render_current_page(self) -> None:
        self.tree.delete(*self.tree.get_children())
        total_pages = max(1, (self.total_rows + self.page_size - 1) // self.page_size)
        start_idx = self.current_page * self.page_size
        end_idx = min(self.total_rows, start_idx + self.page_size)

        for i in range(start_idx, end_idx):
            item = self._all_items[i]
            row_vals = [item.get(col["key"], "") for col in self.columns_def]
            self.tree.insert("", tk.END, iid=str(i), values=row_vals)

        self.lbl_page.config(
            text=f"Page {self.current_page + 1} of {total_pages} ({self.total_rows} total)"
        )
        self.btn_prev.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
        self.btn_next.config(state=tk.NORMAL if self.current_page < total_pages - 1 else tk.DISABLED)

    def _prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self._render_current_page()

    def _next_page(self) -> None:
        total_pages = max(1, (self.total_rows + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._render_current_page()

    def _on_tree_select(self, event: tk.Event) -> None:
        sel = self.tree.selection()
        if sel and self.on_select:
            idx = int(sel[0])
            if 0 <= idx < len(self._all_items):
                self.on_select(self._all_items[idx])

    def _on_tree_activate(self, event: tk.Event) -> None:
        sel = self.tree.selection()
        if sel and self.on_activate:
            idx = int(sel[0])
            if 0 <= idx < len(self._all_items):
                self.on_activate(self._all_items[idx])
