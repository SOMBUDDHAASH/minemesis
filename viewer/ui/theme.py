"""
Modern Theme and Styling Engine for Viewer V2.
Provides dark and light palettes, typography, and TTK style configurations.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Any

PALETTES = {
    "dark": {
        "bg": "#0f1115",
        "panel_bg": "#161920",
        "card_bg": "#1e222b",
        "card_hover": "#262b37",
        "border": "#2b303d",
        "fg": "#f1f5f9",
        "fg_muted": "#94a3b8",
        "accent": "#38bdf8",
        "accent_hover": "#0ea5e9",
        "success": "#34d399",
        "warning": "#fbbf24",
        "danger": "#f87171",
        "tag_bg": "#1e293b",
        "input_bg": "#1a1d24",
        "input_fg": "#f8fafc",
        "parchment_bg": "#231f1a",
        "parchment_fg": "#e2d9cc",
    },
    "light": {
        "bg": "#f8fafc",
        "panel_bg": "#ffffff",
        "card_bg": "#f1f5f9",
        "card_hover": "#e2e8f0",
        "border": "#cbd5e1",
        "fg": "#0f172a",
        "fg_muted": "#64748b",
        "accent": "#0284c7",
        "accent_hover": "#0369a1",
        "success": "#059669",
        "warning": "#d97706",
        "danger": "#dc2626",
        "tag_bg": "#e2e8f0",
        "input_bg": "#ffffff",
        "input_fg": "#0f172a",
        "parchment_bg": "#fef9ee",
        "parchment_fg": "#292524",
    },
}

FONTS = {
    "title": ("Segoe UI", 16, "bold"),
    "subtitle": ("Segoe UI", 12, "bold"),
    "h3": ("Segoe UI", 10, "bold"),
    "body": ("Segoe UI", 9),
    "body_bold": ("Segoe UI", 9, "bold"),
    "small": ("Segoe UI", 8),
    "mono": ("Consolas", 9),
    "book_title": ("Georgia", 14, "bold"),
    "book_body": ("Georgia", 10),
}


class ThemeManager:
    def __init__(self) -> None:
        self.current_theme = "dark"

    @property
    def colors(self) -> dict[str, str]:
        return PALETTES.get(self.current_theme, PALETTES["dark"])

    def set_theme(self, theme_name: str, root: tk.Tk) -> None:
        if theme_name in PALETTES:
            self.current_theme = theme_name
            self.apply(root)

    def apply(self, root: tk.Tk) -> None:
        c = self.colors
        root.config(bg=c["bg"])

        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Configure generic TTK styles
        style.configure(".", background=c["bg"], foreground=c["fg"], font=FONTS["body"])
        style.configure("TFrame", background=c["bg"])
        style.configure("Panel.TFrame", background=c["panel_bg"])
        style.configure("Card.TFrame", background=c["card_bg"], relief="flat")

        style.configure("TLabel", background=c["bg"], foreground=c["fg"])
        style.configure("Panel.TLabel", background=c["panel_bg"], foreground=c["fg"])
        style.configure("Muted.TLabel", background=c["bg"], foreground=c["fg_muted"], font=FONTS["small"])
        style.configure("Title.TLabel", font=FONTS["title"], foreground=c["fg"], background=c["bg"])
        style.configure("Subtitle.TLabel", font=FONTS["subtitle"], foreground=c["fg"], background=c["bg"])

        # Buttons
        style.configure(
            "TButton",
            background=c["panel_bg"],
            foreground=c["fg"],
            font=FONTS["body"],
            padding=(8, 4),
            relief="flat",
        )
        style.map(
            "TButton",
            background=[("active", c["card_hover"]), ("pressed", c["border"])],
            foreground=[("active", c["accent"])],
        )

        style.configure(
            "Accent.TButton",
            background=c["accent"],
            foreground="#ffffff",
            font=FONTS["body_bold"],
            padding=(10, 4),
        )
        style.map("Accent.TButton", background=[("active", c["accent_hover"])])

        # Notebook tabs
        style.configure(
            "TNotebook",
            background=c["panel_bg"],
            tabmargins=[2, 4, 2, 0],
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            background=c["bg"],
            foreground=c["fg_muted"],
            padding=[12, 6],
            font=FONTS["body_bold"],
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", c["panel_bg"])],
            foreground=[("selected", c["accent"])],
        )

        # Treeview (table)
        style.configure(
            "Treeview",
            background=c["panel_bg"],
            foreground=c["fg"],
            fieldbackground=c["panel_bg"],
            font=FONTS["body"],
            rowheight=26,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=c["card_bg"],
            foreground=c["fg"],
            font=FONTS["h3"],
            padding=(4, 4),
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", c["accent"])],
            foreground=[("selected", "#ffffff")],
        )

        # Combobox
        style.configure(
            "TCombobox",
            fieldbackground=c["input_bg"],
            background=c["panel_bg"],
            foreground=c["input_fg"],
            padding=4,
        )

        # Checkbutton
        style.configure(
            "TCheckbutton",
            background=c["bg"],
            foreground=c["fg"],
            font=FONTS["body"],
        )


theme = ThemeManager()
