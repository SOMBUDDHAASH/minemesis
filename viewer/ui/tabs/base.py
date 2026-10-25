"""
Base Tab Class and Tab Registry for Viewer V2.
Allows dynamic tab discovery and registration via @register_tab decorator.
"""

from __future__ import annotations
import tkinter as tk
from typing import Any, Callable, Optional, Type

from viewer.core.logging import create_error_banner
from viewer.ui.theme import theme

# Registry: list of (order, tab_name, TabClass)
TAB_REGISTRY: list[tuple[int, str, type[BaseTab]]] = []


def register_tab(name: str, order: int = 100):
    """Decorator to register a new tab in the viewer notebook."""
    def decorator(cls: type[BaseTab]):
        TAB_REGISTRY.append((order, name, cls))
        TAB_REGISTRY.sort(key=lambda t: t[0])
        return cls
    return decorator


class BaseTab(tk.Frame):
    """Abstract base class for all Viewer V2 tabs."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        c = theme.colors
        super().__init__(parent, bg=c["bg"], **kwargs)
        self._error_banner: Optional[tk.Frame] = None

    def refresh(self) -> None:
        """Called when database data is reloaded or active tab updates."""
        pass

    def on_activate(self) -> None:
        """Called when user switches to this tab."""
        self.refresh()

    def on_filter_change(self, filters: dict[str, Any]) -> None:
        """Called when global filter state changes."""
        pass

    def show_error(self, msg: str, details: Optional[str] = None) -> None:
        """Renders a visible modern red error banner at the top of the tab."""
        self.clear_error()
        self._error_banner = create_error_banner(self, msg, details)
        self._error_banner.pack(side=tk.TOP, fill=tk.X, padx=10, pady=6)

    def clear_error(self) -> None:
        if self._error_banner:
            self._error_banner.destroy()
            self._error_banner = None
