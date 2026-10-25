"""
Standardized Clickable Entity Pill Widget for Viewer V2.
Single-click: opens entity in persistent Detail Panel.
Double-click: navigates to entity's full tab.
"""

from __future__ import annotations
import tkinter as tk
from typing import Optional

from viewer.core.bus import bus
from viewer.core.session import session
from viewer.ui.theme import theme


class EntityPill(tk.Label):
    """Clickable pill for Characters, Settlements, Religions, Books, Threads, Events."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str,
        entity_type: str,
        entity_id: str,
        *,
        is_warning: bool = False,
        **kwargs,
    ) -> None:
        c = theme.colors
        bg_col = "#7f1d1d" if is_warning else c["tag_bg"]
        fg_col = "#fca5a5" if is_warning else c["accent"]

        super().__init__(
            parent,
            text=text,
            bg=bg_col,
            fg=fg_col,
            font=("Segoe UI", 8, "bold"),
            padx=6,
            pady=2,
            relief=tk.FLAT,
            cursor="hand2",
            **kwargs,
        )

        self.entity_type = entity_type
        self.entity_id = entity_id

        self.bind("<Button-1>", self._on_single_click)
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_single_click(self, event: tk.Event) -> None:
        session.select_entity(self.entity_type, self.entity_id)

    def _on_double_click(self, event: tk.Event) -> None:
        session.select_entity(self.entity_type, self.entity_id)
        # Notify app to switch tab
        target_tab = {
            "character": "People",
            "settlement": "Places",
            "book": "Books",
            "religion": "Faith",
            "thread": "Threads",
            "event": "Chronicle",
        }.get(self.entity_type, "Chronicle")
        bus.publish("tab:switch", tab_name=target_tab, entity_id=self.entity_id)

    def _on_enter(self, event: tk.Event) -> None:
        self.config(bg=theme.colors["border"])

    def _on_leave(self, event: tk.Event) -> None:
        self.config(bg=theme.colors["tag_bg"])
