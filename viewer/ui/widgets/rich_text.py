"""
Rich Text Widget with Hyperlinked Entity Tags for Viewer V2.
"""

from __future__ import annotations
import tkinter as tk
from typing import Optional

from viewer.core.bus import bus
from viewer.core.session import session
from viewer.ui.theme import theme


class RichTextView(tk.Text):
    """Text widget with embedded clickable entity tags and styling."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        c = theme.colors
        default_kwargs = {
            "bg": c["panel_bg"],
            "fg": c["fg"],
            "insertbackground": c["fg"],
            "font": ("Segoe UI", 9),
            "relief": tk.FLAT,
            "padx": 8,
            "pady": 8,
            "wrap": tk.WORD,
        }
        default_kwargs.update(kwargs)
        super().__init__(parent, **default_kwargs)

        self._tag_counter = 0
        self._configure_default_tags()

    def _configure_default_tags(self) -> None:
        c = theme.colors
        self.tag_configure("bold", font=("Segoe UI", 9, "bold"))
        self.tag_configure("italic", font=("Segoe UI", 9, "italic"))
        self.tag_configure("title", font=("Segoe UI", 12, "bold"), foreground=c["fg"])
        self.tag_configure("muted", foreground=c["fg_muted"], font=("Segoe UI", 8))
        self.tag_configure("warning", foreground=c["danger"], font=("Segoe UI", 9, "bold"))

    def set_content(self, text: str) -> None:
        self.config(state=tk.NORMAL)
        self.delete("1.0", tk.END)
        self.insert(tk.END, text)
        self.config(state=tk.DISABLED)

    def insert_plain(self, text: str, *tags: str) -> None:
        self.insert(tk.END, text, tags)

    def insert_entity_link(
        self,
        display_text: str,
        entity_type: str,
        entity_id: str,
        *,
        is_missing: bool = False,
    ) -> None:
        """Inserts hyperlinked entity text with click bindings."""
        self._tag_counter += 1
        tag_name = f"entity_{self._tag_counter}"

        c = theme.colors
        fg_col = c["danger"] if is_missing else c["accent"]

        self.tag_configure(
            tag_name,
            foreground=fg_col,
            font=("Segoe UI", 9, "bold"),
            underline=1,
        )

        def _on_click(e: tk.Event) -> None:
            session.select_entity(entity_type, entity_id)

        def _on_double_click(e: tk.Event) -> None:
            session.select_entity(entity_type, entity_id)
            target_tab = {
                "character": "People",
                "settlement": "Places",
                "book": "Books",
                "religion": "Faith",
                "thread": "Threads",
                "event": "Chronicle",
            }.get(entity_type, "Chronicle")
            bus.publish("tab:switch", tab_name=target_tab, entity_id=entity_id)

        def _on_enter(e: tk.Event) -> None:
            self.config(cursor="hand2")

        def _on_leave(e: tk.Event) -> None:
            self.config(cursor="")

        self.tag_bind(tag_name, "<Button-1>", _on_click)
        self.tag_bind(tag_name, "<Double-Button-1>", _on_double_click)
        self.tag_bind(tag_name, "<Enter>", _on_enter)
        self.tag_bind(tag_name, "<Leave>", _on_leave)

        self.insert(tk.END, display_text, (tag_name,))
