"""
Lightweight Canvas-Based Chart Widget for Viewer V2 (Zero Dependencies).
Renders crisp Line Charts and Bar Charts directly onto a Tkinter Canvas.
"""

from __future__ import annotations
import tkinter as tk
from typing import Optional, Sequence

from viewer.ui.theme import theme


class CanvasChart(tk.Frame):
    """Native Canvas-based chart supporting line charts and bar charts."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        c = theme.colors
        super().__init__(parent, bg=c["panel_bg"], **kwargs)

        self.canvas = tk.Canvas(
            self,
            bg=c["panel_bg"],
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_resize)

        self._chart_type: str = "line"
        self._series: list[dict] = []  # [{"label": str, "color": str, "points": [(x, y)]}]
        self._categories: list[dict] = []  # [{"label": str, "value": float, "color": str}]

    def _on_resize(self, event: tk.Event) -> None:
        self.redraw()

    def set_line_chart(self, series: Sequence[dict]) -> None:
        """series = [{'label': 'Total Pop', 'color': '#38bdf8', 'points': [(1, 100), (2, 110)]}]"""
        self._chart_type = "line"
        self._series = list(series)
        self.redraw()

    def set_bar_chart(self, categories: Sequence[dict]) -> None:
        """categories = [{'label': 'Oakhaven', 'value': 45, 'color': '#38bdf8'}]"""
        self._chart_type = "bar"
        self._categories = list(categories)
        self.redraw()

    def redraw(self) -> None:
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 100 or h < 80:
            return

        if self._chart_type == "line":
            self._render_line_chart(w, h)
        elif self._chart_type == "bar":
            self._render_bar_chart(w, h)

    def _render_line_chart(self, w: int, h: int) -> None:
        c = theme.colors
        margin_left = 50
        margin_right = 30
        margin_top = 20
        margin_bottom = 40

        plot_w = max(10, w - margin_left - margin_right)
        plot_h = max(10, h - margin_top - margin_bottom)

        # Collect all points
        all_x = []
        all_y = []
        for s in self._series:
            for x, y in s.get("points", []):
                all_x.append(x)
                all_y.append(y)

        if not all_x:
            self.canvas.create_text(
                w // 2, h // 2, text="No chart data available", fill=c["fg_muted"], font=("Segoe UI", 10)
            )
            return

        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = 0, max(all_y)
        if max_x == min_x:
            max_x = min_x + 1
        if max_y == min_y:
            max_y = 10

        # Draw grid lines & Y labels
        num_y_ticks = 4
        for i in range(num_y_ticks + 1):
            y_val = min_y + (max_y - min_y) * (i / num_y_ticks)
            py = margin_top + plot_h - (i / num_y_ticks) * plot_h
            self.canvas.create_line(
                margin_left, py, margin_left + plot_w, py, fill=c["border"], dash=(2, 4)
            )
            self.canvas.create_text(
                margin_left - 8,
                py,
                text=f"{int(y_val)}",
                fill=c["fg_muted"],
                anchor="e",
                font=("Segoe UI", 7),
            )

        # Draw X labels
        num_x_ticks = min(5, max_x - min_x)
        if num_x_ticks > 0:
            for i in range(num_x_ticks + 1):
                x_val = min_x + (max_x - min_x) * (i / num_x_ticks)
                px = margin_left + (i / num_x_ticks) * plot_w
                self.canvas.create_line(px, margin_top, px, margin_top + plot_h, fill=c["border"], dash=(2, 4))
                self.canvas.create_text(
                    px,
                    margin_top + plot_h + 12,
                    text=f"Y{int(x_val)}",
                    fill=c["fg_muted"],
                    anchor="n",
                    font=("Segoe UI", 7),
                )

        # Draw series lines
        legend_x = margin_left + 10
        for s in self._series:
            pts = s.get("points", [])
            col = s.get("color", c["accent"])
            lbl = s.get("label", "")

            coords = []
            for x, y in pts:
                px = margin_left + ((x - min_x) / (max_x - min_x)) * plot_w
                py = margin_top + plot_h - ((y - min_y) / (max_y - min_y)) * plot_h
                coords.extend([px, py])

            if len(coords) >= 4:
                self.canvas.create_line(coords, fill=col, width=2, smooth=False)

            # Draw legend entry
            if lbl:
                self.canvas.create_line(legend_x, margin_top - 8, legend_x + 16, margin_top - 8, fill=col, width=2)
                self.canvas.create_text(
                    legend_x + 22,
                    margin_top - 8,
                    text=lbl,
                    fill=c["fg"],
                    anchor="w",
                    font=("Segoe UI", 8),
                )
                legend_x += len(lbl) * 7 + 40

    def _render_bar_chart(self, w: int, h: int) -> None:
        c = theme.colors
        margin_left = 60
        margin_right = 20
        margin_top = 20
        margin_bottom = 40

        plot_w = max(10, w - margin_left - margin_right)
        plot_h = max(10, h - margin_top - margin_bottom)

        if not self._categories:
            self.canvas.create_text(
                w // 2, h // 2, text="No chart data available", fill=c["fg_muted"], font=("Segoe UI", 10)
            )
            return

        max_val = max([item["value"] for item in self._categories] + [10])
        bar_count = len(self._categories)
        bar_width = min(40, max(8, int((plot_w / max(1, bar_count)) * 0.6)))
        gap = plot_w / max(1, bar_count)

        # Baseline
        self.canvas.create_line(
            margin_left, margin_top + plot_h, margin_left + plot_w, margin_top + plot_h, fill=c["border"]
        )

        for i, item in enumerate(self._categories):
            cx = margin_left + (i + 0.5) * gap
            val = item["value"]
            bar_h = (val / max_val) * plot_h
            bx0 = cx - bar_width / 2
            bx1 = cx + bar_width / 2
            by1 = margin_top + plot_h
            by0 = by1 - bar_h

            col = item.get("color", c["accent"])
            self.canvas.create_rectangle(bx0, by0, bx1, by1, fill=col, outline="")

            # Value label
            self.canvas.create_text(
                cx, by0 - 6, text=str(int(val)), fill=c["fg"], font=("Segoe UI", 7, "bold"), anchor="s"
            )

            # Category label
            lbl = item.get("label", "")
            if len(lbl) > 10:
                lbl = lbl[:9] + "…"
            self.canvas.create_text(
                cx, by1 + 10, text=lbl, fill=c["fg_muted"], font=("Segoe UI", 7), anchor="n"
            )
