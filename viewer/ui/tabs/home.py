"""
Home Tab for Viewer V2.
Displays Run Overview, Headline Metrics, Key People, Major Events,
Name Integrity Audit status badge, and standalone Simulation Launcher.
"""

from __future__ import annotations
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Any, Optional

from viewer.core.bus import bus
from viewer.core.logging import log_error
from viewer.core.session import session
from viewer.ui.tabs.base import BaseTab, register_tab
from viewer.ui.theme import theme
from viewer.ui.widgets.entity_link import EntityPill


@register_tab("Home", order=0)
class HomeTab(BaseTab):
    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        self.canvas = tk.Canvas(self, bg=theme.colors["bg"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=theme.colors["bg"])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_ui()
        bus.subscribe("session:loaded", lambda **kw: self.refresh())

    def _build_ui(self) -> None:
        c = theme.colors
        pad_x = 24

        # Header Frame
        hdr = tk.Frame(self.scrollable_frame, bg=c["bg"], pady=16)
        hdr.pack(fill=tk.X, padx=pad_x)

        title_lbl = tk.Label(hdr, text="Minemesis Historical Archive", font=("Segoe UI", 18, "bold"), fg=c["fg"], bg=c["bg"])
        title_lbl.pack(side=tk.LEFT)

        btn_new_run = tk.Button(
            hdr,
            text="+ Run New Simulation",
            command=self._open_new_run_dialog,
            bg=c["accent"],
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
        )
        btn_new_run.pack(side=tk.RIGHT)

        # Meta & Audit Status Bar
        self.status_bar = tk.Frame(self.scrollable_frame, bg=c["panel_bg"], padx=14, pady=10, relief=tk.FLAT)
        self.status_bar.pack(fill=tk.X, padx=pad_x, pady=(0, 16))

        self.lbl_meta = tk.Label(
            self.status_bar,
            text="No active run loaded. Click 'Run New Simulation' or open a .minemesis file.",
            font=("Segoe UI", 9),
            fg=c["fg_muted"],
            bg=c["panel_bg"],
        )
        self.lbl_meta.pack(side=tk.LEFT)

        self.btn_audit = tk.Button(
            self.status_bar,
            text="Audit: Unknown",
            font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT,
            padx=8,
            pady=3,
            state=tk.DISABLED,
        )
        self.btn_audit.pack(side=tk.RIGHT)

        # Metrics Grid (Cards)
        self.metrics_frame = tk.Frame(self.scrollable_frame, bg=c["bg"])
        self.metrics_frame.pack(fill=tk.X, padx=pad_x, pady=(0, 20))

        self.card_pop = self._create_metric_card(self.metrics_frame, "Total Population", "--", 0)
        self.card_events = self._create_metric_card(self.metrics_frame, "Total Events", "--", 1)
        self.card_chars = self._create_metric_card(self.metrics_frame, "Total Citizens", "--", 2)
        self.card_books = self._create_metric_card(self.metrics_frame, "Penned Books", "--", 3)
        self.card_faiths = self._create_metric_card(self.metrics_frame, "Religions", "--", 4)

        # Content Split: Key People & Headline Events
        content_frame = tk.Frame(self.scrollable_frame, bg=c["bg"])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=pad_x, pady=(0, 24))

        # Left: Key People (Settlement Leaders)
        left_box = tk.Frame(content_frame, bg=c["panel_bg"], padx=16, pady=14, relief=tk.FLAT)
        left_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        tk.Label(left_box, text="Current Chiefs & Leaders", font=("Segoe UI", 11, "bold"), fg=c["fg"], bg=c["panel_bg"]).pack(anchor="w", pady=(0, 10))
        self.leaders_container = tk.Frame(left_box, bg=c["panel_bg"])
        self.leaders_container.pack(fill=tk.BOTH, expand=True)

        # Right: Headline Events
        right_box = tk.Frame(content_frame, bg=c["panel_bg"], padx=16, pady=14, relief=tk.FLAT)
        right_box.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        tk.Label(right_box, text="Major Historical Milestones", font=("Segoe UI", 11, "bold"), fg=c["fg"], bg=c["panel_bg"]).pack(anchor="w", pady=(0, 10))
        self.events_container = tk.Frame(right_box, bg=c["panel_bg"])
        self.events_container.pack(fill=tk.BOTH, expand=True)

    def _create_metric_card(self, parent: tk.Widget, title: str, value: str, col: int) -> dict[str, Any]:
        c = theme.colors
        card = tk.Frame(parent, bg=c["panel_bg"], padx=14, pady=12, relief=tk.FLAT)
        card.grid(row=0, column=col, sticky="nsew", padx=6)
        parent.grid_columnconfigure(col, weight=1)

        lbl_t = tk.Label(card, text=title.upper(), font=("Segoe UI", 7, "bold"), fg=c["fg_muted"], bg=c["panel_bg"])
        lbl_t.pack(anchor="w")

        lbl_v = tk.Label(card, text=value, font=("Segoe UI", 16, "bold"), fg=c["accent"], bg=c["panel_bg"])
        lbl_v.pack(anchor="w", pady=(4, 0))
        return {"frame": card, "title": lbl_t, "value": lbl_v}

    def refresh(self) -> None:
        self.clear_error()
        if not session.db:
            return

        try:
            m = session.db.meta
            w_seed = m.get("world_seed", 0)
            h_seed = m.get("history_seed", 0)
            p_code = m.get("pair_code", f"{w_seed}:{h_seed}")
            ticks = m.get("duration_ticks", 0)
            years = ticks // 12
            gen_at = m.get("generated_at", "")[:10]

            self.lbl_meta.config(
                text=f"Seed Pair: {p_code} (World {w_seed} / History {h_seed})  •  Duration: {years} Years ({ticks} ticks)  •  Generated: {gen_at}"
            )

            # Name Audit Badge
            issues = session.db.get_name_audit_issues()
            if not issues:
                self.btn_audit.config(
                    text="✓ Name Integrity: 100% (0 Issues)",
                    bg="#065f46",
                    fg="#a7f3d0",
                    state=tk.NORMAL,
                    command=lambda: messagebox.showinfo("Name Integrity", "All characters and historical participants resolved with 100% valid names!"),
                )
            else:
                self.btn_audit.config(
                    text=f"⚠ Name Issues: {len(issues)} Detected",
                    bg="#7f1d1d",
                    fg="#fecaca",
                    state=tk.NORMAL,
                    command=lambda: messagebox.showwarning("Name Issues", f"{len(issues)} issues detected in name_audit table:\n" + "\n".join([f"- {i['character_id']}: {i['issue_type']}" for i in issues[:10]])),
                )

            # Counts
            counts = session.db.get_row_counts()
            settlements = session.db.get_settlements()

            # Calculate total living population
            census = session.db.get_census()
            latest_year = max([r["year"] for r in census]) if census else 0
            living_pop = sum([r["population"] for r in census if r["year"] == latest_year])

            self.card_pop["value"].config(text=str(living_pop))
            self.card_events["value"].config(text=str(counts.get("events", 0)))
            self.card_chars["value"].config(text=str(counts.get("characters", 0)))
            self.card_books["value"].config(text=str(counts.get("books", 0)))
            self.card_faiths["value"].config(text=str(counts.get("religions", 0)))

            # Populate Leaders
            for w in self.leaders_container.winfo_children():
                w.destroy()

            chars = session.db.get_characters(limit=6, living_only=True)
            for c_obj in chars:
                row = tk.Frame(self.leaders_container, bg=theme.colors["panel_bg"], pady=4)
                row.pack(fill=tk.X)
                pill = EntityPill(row, c_obj["display_name"], "character", c_obj["id"])
                pill.pack(side=tk.LEFT)
                desc = tk.Label(
                    row,
                    text=f"• Age {c_obj['birth_tick'] // 12 if c_obj.get('birth_tick') else 30} • {c_obj.get('profession', 'Citizen')}",
                    font=("Segoe UI", 8),
                    fg=theme.colors["fg_muted"],
                    bg=theme.colors["panel_bg"],
                )
                desc.pack(side=tk.LEFT, padx=6)

            # Populate Headline Events
            for w in self.events_container.winfo_children():
                w.destroy()

            major_evts = session.db.get_events(limit=6, major_only=True)
            for e_obj in major_evts:
                row = tk.Frame(self.events_container, bg=theme.colors["panel_bg"], pady=4)
                row.pack(fill=tk.X)
                yr_lbl = tk.Label(
                    row,
                    text=f"Year {e_obj['year']}:",
                    font=("Segoe UI", 8, "bold"),
                    fg=theme.colors["accent"],
                    bg=theme.colors["panel_bg"],
                )
                yr_lbl.pack(side=tk.LEFT, padx=(0, 6))

                txt = e_obj.get("description", "")
                if len(txt) > 65:
                    txt = txt[:62] + "…"
                desc_lbl = tk.Label(
                    row,
                    text=txt,
                    font=("Segoe UI", 8),
                    fg=theme.colors["fg"],
                    bg=theme.colors["panel_bg"],
                    anchor="w",
                )
                desc_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        except Exception as e:
            log_error("Error refreshing HomeTab", e)
            self.show_error(f"Failed to refresh Home tab: {e}")

    def _open_new_run_dialog(self) -> None:
        """Opens modal dialog to run simulation in subprocess without blocking UI."""
        c = theme.colors
        dlg = tk.Toplevel(self)
        dlg.title("Run New Simulation")
        dlg.geometry("440x360")
        dlg.resizable(False, False)
        dlg.configure(bg=c["panel_bg"])
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        tk.Label(dlg, text="Configure Simulation Run", font=("Segoe UI", 12, "bold"), fg=c["fg"], bg=c["panel_bg"]).pack(pady=(16, 12))

        form = tk.Frame(dlg, bg=c["panel_bg"], padx=20)
        form.pack(fill=tk.BOTH, expand=True)

        tk.Label(form, text="World Seed:", font=("Segoe UI", 9, "bold"), fg=c["fg"], bg=c["panel_bg"]).grid(row=0, column=0, sticky="w", pady=6)
        world_entry = tk.Entry(form, bg=c["input_bg"], fg=c["input_fg"], relief=tk.FLAT, highlightthickness=1, highlightbackground=c["border"])
        world_entry.insert(0, "42")
        world_entry.grid(row=0, column=1, sticky="ew", pady=6, padx=(10, 0))

        tk.Label(form, text="History Seed:", font=("Segoe UI", 9, "bold"), fg=c["fg"], bg=c["panel_bg"]).grid(row=1, column=0, sticky="w", pady=6)
        hist_entry = tk.Entry(form, bg=c["input_bg"], fg=c["input_fg"], relief=tk.FLAT, highlightthickness=1, highlightbackground=c["border"])
        hist_entry.insert(0, "1337")
        hist_entry.grid(row=1, column=1, sticky="ew", pady=6, padx=(10, 0))

        tk.Label(form, text="Simulated Years:", font=("Segoe UI", 9, "bold"), fg=c["fg"], bg=c["panel_bg"]).grid(row=2, column=0, sticky="w", pady=6)
        years_entry = tk.Entry(form, bg=c["input_bg"], fg=c["input_fg"], relief=tk.FLAT, highlightthickness=1, highlightbackground=c["border"])
        years_entry.insert(0, "30")
        years_entry.grid(row=2, column=1, sticky="ew", pady=6, padx=(10, 0))

        form.grid_columnconfigure(1, weight=1)

        prog_bar = ttk.Progressbar(dlg, mode="indeterminate")
        status_lbl = tk.Label(dlg, text="Ready", font=("Segoe UI", 8), fg=c["fg_muted"], bg=c["panel_bg"])
        status_lbl.pack(pady=(10, 4))

        def _start_sim():
            try:
                w_s = int(world_entry.get().strip())
                h_s = int(hist_entry.get().strip())
                yrs = int(years_entry.get().strip())
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid integers for seeds and years.")
                return

            out_file = filedialog.asksaveasfilename(
                title="Select .minemesis Output File",
                defaultextension=".minemesis",
                filetypes=[("Minemesis Run Archive", "*.minemesis")],
            )
            if not out_file:
                return

            prog_bar.pack(fill=tk.X, padx=24, pady=4)
            prog_bar.start()
            status_lbl.config(text="Simulating in background... Please wait.")
            btn_run.config(state=tk.DISABLED)

            def _worker():
                cmd = [
                    sys.executable,
                    "-m",
                    "viewer",
                    "--simulate",
                    "--world-seed",
                    str(w_s),
                    "--history-seed",
                    str(h_s),
                    "--years",
                    str(yrs),
                    "--out",
                    out_file,
                ]
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    self.after(0, lambda: _on_sim_done(out_file))
                except Exception as ex:
                    self.after(0, lambda: _on_sim_error(str(ex)))

            def _on_sim_done(saved_path: str):
                prog_bar.stop()
                dlg.destroy()
                session.load_file(saved_path)
                messagebox.showinfo("Simulation Complete", f"Successfully generated and loaded {yrs}-year history!")

            def _on_sim_error(err_msg: str):
                prog_bar.stop()
                prog_bar.pack_forget()
                btn_run.config(state=tk.NORMAL)
                status_lbl.config(text="Error occurred.")
                messagebox.showerror("Simulation Failed", f"Failed to run simulation:\n{err_msg}")

            threading.Thread(target=_worker, daemon=True).start()

        btn_run = tk.Button(
            dlg,
            text="Generate World & History",
            command=_start_sim,
            bg=c["accent"],
            fg="#ffffff",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=14,
            pady=8,
            cursor="hand2",
        )
        btn_run.pack(pady=14)
