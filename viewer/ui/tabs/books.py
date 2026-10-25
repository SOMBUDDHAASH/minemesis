"""
Books & Literature Tab for Viewer V2.
Features settlement shelves, full parchment book reader, and Minecraft Book & Quill exporter.
"""

from __future__ import annotations
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Any, Optional

from viewer.core.bus import bus
from viewer.core.logging import log_error
from viewer.core.session import session
from viewer.ui.tabs.base import BaseTab, register_tab
from viewer.ui.theme import theme
from viewer.ui.widgets.table import PaginatedTable


@register_tab("Books", order=4)
class BooksTab(BaseTab):
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self.selected_book_id: Optional[str] = None
        self._current_page = 0
        self._book_pages: list[str] = []

        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        c = theme.colors

        # Left: Books Shelf
        left_frame = tk.Frame(self.paned, bg=c["panel_bg"], width=320)
        self.paned.add(left_frame, weight=1)

        shelf_top = tk.Frame(left_frame, bg=c["panel_bg"], padx=8, pady=6)
        shelf_top.pack(fill=tk.X)

        tk.Label(shelf_top, text="Written Literature", font=("Segoe UI", 11, "bold"), fg=c["fg"], bg=c["panel_bg"]).pack(anchor="w", pady=(0, 4))

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            shelf_top,
            textvariable=self.search_var,
            bg=c["input_bg"],
            fg=c["input_fg"],
            insertbackground=c["fg"],
            relief=tk.FLAT,
            highlightbackground=c["border"],
            highlightthickness=1,
        )
        self.search_entry.pack(fill=tk.X)
        self.search_entry.bind("<KeyRelease>", lambda e: self._load_books())

        cols = [
            {"key": "title", "label": "Title", "width": 160},
            {"key": "author_name", "label": "Author", "width": 100},
            {"key": "year_written", "label": "Year", "width": 50},
        ]
        self.book_table = PaginatedTable(
            left_frame,
            columns=cols,
            on_select=self._on_book_select,
        )
        self.book_table.pack(fill=tk.BOTH, expand=True)

        # Right: Parchment Book Reader
        self.right_frame = tk.Frame(self.paned, bg=c["bg"], padx=20, pady=16)
        self.paned.add(self.right_frame, weight=3)

        self._build_reader()

        bus.subscribe("session:loaded", lambda **kw: self.refresh())
        bus.subscribe("tab:switch", self._on_tab_switch)

    def _build_reader(self) -> None:
        c = theme.colors

        # Top Bar: Title & Minecraft Export Button
        top_bar = tk.Frame(self.right_frame, bg=c["bg"])
        top_bar.pack(fill=tk.X, pady=(0, 10))

        self.lbl_title = tk.Label(top_bar, text="Select a Manuscript", font=("Georgia", 16, "bold"), fg=c["fg"], bg=c["bg"])
        self.lbl_title.pack(side=tk.LEFT)

        btn_mc = tk.Button(
            top_bar,
            text="Export to Minecraft Book ⛏",
            command=self._export_minecraft,
            bg=c["panel_bg"],
            fg=c["accent"],
            font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
        )
        btn_mc.pack(side=tk.RIGHT)

        self.lbl_author = tk.Label(self.right_frame, text="", font=("Georgia", 10, "italic"), fg=c["fg_muted"], bg=c["bg"])
        self.lbl_author.pack(anchor="w", pady=(0, 8))

        # Parchment Frame
        parchment_frame = tk.Frame(self.right_frame, bg=c["parchment_bg"], padx=24, pady=20, relief=tk.FLAT)
        parchment_frame.pack(fill=tk.BOTH, expand=True)

        self.page_text = tk.Text(
            parchment_frame,
            bg=c["parchment_bg"],
            fg=c["parchment_fg"],
            font=("Georgia", 11),
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=12,
            pady=12,
        )
        self.page_text.pack(fill=tk.BOTH, expand=True)

        # Navigation Bar
        nav_bar = tk.Frame(parchment_frame, bg=c["parchment_bg"], pady=8)
        nav_bar.pack(fill=tk.X)

        self.btn_prev = tk.Button(
            nav_bar,
            text="◀ Previous Page",
            command=self._prev_page,
            bg=c["card_bg"],
            fg=c["fg"],
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            padx=10,
            pady=3,
        )
        self.btn_prev.pack(side=tk.LEFT)

        self.lbl_page_num = tk.Label(
            nav_bar,
            text="Page 0 of 0",
            bg=c["parchment_bg"],
            fg=c["parchment_fg"],
            font=("Georgia", 9, "bold"),
        )
        self.lbl_page_num.pack(side=tk.LEFT, expand=True)

        self.btn_next = tk.Button(
            nav_bar,
            text="Next Page ▶",
            command=self._next_page,
            bg=c["card_bg"],
            fg=c["fg"],
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            padx=10,
            pady=3,
        )
        self.btn_next.pack(side=tk.RIGHT)

    def _on_tab_switch(self, tab_name: str, entity_id: str, **kwargs) -> None:
        if tab_name == "Books" and entity_id.startswith("book_"):
            self.selected_book_id = entity_id
            self.refresh()

    def refresh(self) -> None:
        self.clear_error()
        if not session.db:
            return
        self._load_books()
        if self.selected_book_id:
            self._display_book(self.selected_book_id)

    def _load_books(self) -> None:
        if not session.db:
            return
        try:
            q = self.search_var.get().strip()
            books = session.db.get_books(search=q)
            self.book_table.set_items(books)
            if not self.selected_book_id and books:
                self.selected_book_id = books[0]["id"]
        except Exception as e:
            log_error("Error loading books in BooksTab", e)

    def _on_book_select(self, row: dict[str, Any]) -> None:
        bid = row.get("id")
        if bid:
            self.selected_book_id = bid
            session.select_entity("book", bid)
            self._display_book(bid)

    def _display_book(self, book_id: str) -> None:
        if not session.db:
            return

        b = session.db.get_book(book_id)
        if not b:
            return

        self.lbl_title.config(text=b.get("title", "Untitled"))
        self.lbl_author.config(
            text=f"Penned by {b.get('author_name', 'Unknown')} in Year {b.get('year_written', 1)} • Topic: {b.get('topic', 'History')}"
        )

        self._book_pages = b.get("pages", [])
        self._current_page = 0
        self._render_page()

    def _render_page(self) -> None:
        total = len(self._book_pages)
        self.page_text.config(state=tk.NORMAL)
        self.page_text.delete("1.0", tk.END)

        if not self._book_pages:
            self.page_text.insert(tk.END, "[Empty or unrendered manuscript]")
            self.lbl_page_num.config(text="Page 0 of 0")
            self.btn_prev.config(state=tk.DISABLED)
            self.btn_next.config(state=tk.DISABLED)
        else:
            self.page_text.insert(tk.END, self._book_pages[self._current_page])
            self.lbl_page_num.config(text=f"Page {self._current_page + 1} of {total}")
            self.btn_prev.config(state=tk.NORMAL if self._current_page > 0 else tk.DISABLED)
            self.btn_next.config(state=tk.NORMAL if self._current_page < total - 1 else tk.DISABLED)

        self.page_text.config(state=tk.DISABLED)

    def _prev_page(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self._render_page()

    def _next_page(self) -> None:
        if self._current_page < len(self._book_pages) - 1:
            self._current_page += 1
            self._render_page()

    def _export_minecraft(self) -> None:
        if not self.selected_book_id or not session.db:
            return
        b = session.db.get_book(self.selected_book_id)
        if not b:
            return

        pages = b.get("pages", [])
        mc_data = {
            "title": b.get("title", "Book"),
            "author": b.get("author_name", "Minemesis Scholar"),
            "pages": pages,
        }

        save_path = filedialog.asksaveasfilename(
            title="Export Minecraft Book & Quill JSON",
            defaultextension=".json",
            initialfile=f"{b.get('title', 'book').replace(' ', '_').lower()}.json",
            filetypes=[("JSON file", "*.json")],
        )
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(mc_data, f, indent=2)
            messagebox.showinfo("Export Successful", f"Saved Minecraft book data to:\n{save_path}")
