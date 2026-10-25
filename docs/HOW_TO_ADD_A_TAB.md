# How to Add a New Tab in Viewer V2

Minemesis Viewer V2 uses a decoupled dynamic registration pattern. Adding a new tab requires creating **one file** in `viewer/ui/tabs/` — **no modifications to `app.py` or the main window shell are required.**

---

## 3-Step Guide

### Step 1: Create Your Tab File
Create a new file in `viewer/ui/tabs/`, for example `viewer/ui/tabs/custom_tab.py`:

```python
"""
Custom Analysis Tab for Viewer V2.
"""

from __future__ import annotations
import tkinter as tk
from typing import Any

from viewer.core.session import session
from viewer.ui.tabs.base import BaseTab, register_tab
from viewer.ui.theme import theme


# Register the tab with a display name and order position:
# order=0 is Home, order=1 is Chronicle, order=2 is People, etc.
@register_tab("Analytics", order=8)
class AnalyticsTab(BaseTab):
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        c = theme.colors

        # Construct UI elements
        self.lbl_title = tk.Label(
            self,
            text="Civilization Analytics",
            font=("Segoe UI", 14, "bold"),
            fg=c["fg"],
            bg=c["bg"],
        )
        self.lbl_title.pack(anchor="w", padx=16, pady=12)

        self.lbl_info = tk.Label(
            self,
            text="Awaiting database...",
            font=("Segoe UI", 10),
            fg=c["fg_muted"],
            bg=c["bg"],
        )
        self.lbl_info.pack(anchor="w", padx=16)

    def refresh(self) -> None:
        """Called automatically when a new .minemesis database is loaded or selected."""
        self.clear_error()
        if not session.db:
            return

        try:
            # Query the database
            settlements = session.db.get_settlements()
            total_events = session.db.meta.get("total_events", 0)

            self.lbl_info.config(
                text=f"Analyzing {len(settlements)} settlements across {total_events} recorded events."
            )
        except Exception as e:
            # Render a visible red error banner instead of a silent crash
            self.show_error(f"Failed to refresh Analytics tab: {e}")

    def on_activate(self) -> None:
        """Called automatically whenever the user clicks this notebook tab."""
        self.refresh()

    def on_filter_change(self, filters: dict[str, Any]) -> None:
        """Called whenever the user adjusts search or era filters."""
        self.refresh()
```

---

### Step 2: Register in `viewer/ui/tabs/__init__.py`
Add your new tab to the imports in `viewer/ui/tabs/__init__.py`:

```python
from viewer.ui.tabs.custom_tab import AnalyticsTab
```

*(This ensures Python imports the module so the `@register_tab` decorator runs.)*

---

### Step 3: Run the Viewer
Launch the application:
```powershell
python -m viewer
```
Your tab will automatically appear in the top tab notebook at the specified `order` position with full theme styling, error handling, and session state integration!
