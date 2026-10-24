"""
Minemesis Story Viewer - Main Tkinter Application.

Milestone 0.5.2 Read-Only Presentation Layer.
Strict Boundary Rule: minemesis never imports viewer.
"""

from __future__ import annotations
import math
import os
import random
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from typing import Any, Callable, Mapping, Optional, Sequence

from viewer.model import RunData, EventProxy, EventLogProxy, SCHEMA_VERSION
from viewer.formatter import (
    format_event_sentence,
    format_because_clause,
    format_character_name,
    format_settlement_name,
    get_event_category_color,
)
from viewer.threads import extract_story_threads, StoryThread
from viewer.export import export_story_to_text, export_story_to_html


BUILD_TAG = "m0.5.2"
BUILD_COMMIT = "e322da2"
BUILD_TIME = "2026-10-24"

SHOWCASE_SEEDS = [42, 2029, 2030, 2043, 2011]


class StoryViewerApp:
    def __init__(self, root: tk.Tk, initial_file: Optional[str] = None):
        self.root = root
        self.root.title(f"Minemesis Story Viewer - Milestone {BUILD_TAG}")
        self.root.geometry("1240x820")
        self.root.minsize(1020, 700)

        # Application state
        self.run_data: Optional[RunData] = None
        self.event_log_proxy: Optional[EventLogProxy] = None
        self.threads: list[StoryThread] = []
        self.is_simulating: bool = False

        # Book reader state
        self.current_book_index: int = 0
        self.current_book_page: int = 0

        # Styles
        self._setup_styles()

        # Build UI layout
        self._build_top_controls()
        self._build_tabs()
        self._build_status_bar()

        # Bindings
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if initial_file and os.path.exists(initial_file):
            self.load_run_file(initial_file)
        else:
            # Default: run seed 42 in background on startup
            self.root.after(100, lambda: self._start_simulation(seed=42, years=100))

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TNotebook", tabposition="n", padding=2)
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[10, 4])
        style.configure("Toolbar.TFrame", background="#EAECEE")
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 9))

    # =========================================================================
    # UI CONSTRUCTION
    # =========================================================================

    def _build_top_controls(self):
        toolbar = ttk.Frame(self.root, style="Toolbar.TFrame", padding=6)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # Seed selection
        ttk.Label(toolbar, text="Seed:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(4, 2))
        self.seed_var = tk.StringVar(value="42")
        self.seed_combo = ttk.Combobox(toolbar, textvariable=self.seed_var, width=8, values=[str(s) for s in SHOWCASE_SEEDS])
        self.seed_combo.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_random = ttk.Button(toolbar, text="🎲 Random", width=9, command=self._on_random_seed)
        self.btn_random.pack(side=tk.LEFT, padx=(0, 10))

        # Years
        ttk.Label(toolbar, text="Years:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(4, 2))
        self.years_var = tk.StringVar(value="100")
        self.years_entry = ttk.Entry(toolbar, textvariable=self.years_var, width=5)
        self.years_entry.pack(side=tk.LEFT, padx=(0, 10))

        # Toggles
        self.toggle_religion = tk.BooleanVar(value=True)
        self.chk_religion = ttk.Checkbutton(toolbar, text="Religion", variable=self.toggle_religion)
        self.chk_religion.pack(side=tk.LEFT, padx=(0, 6))

        self.toggle_lore = tk.BooleanVar(value=True)
        self.chk_lore = ttk.Checkbutton(toolbar, text="Lore & Books", variable=self.toggle_lore)
        self.chk_lore.pack(side=tk.LEFT, padx=(0, 12))

        # Run Button
        self.btn_run = ttk.Button(toolbar, text="▶ Run Simulation", command=self._on_run_click)
        self.btn_run.pack(side=tk.LEFT, padx=(0, 12))

        # Progress bar
        self.progress_bar = ttk.Progressbar(toolbar, orient=tk.HORIZONTAL, length=120, mode="determinate")
        self.progress_bar.pack(side=tk.LEFT, padx=(0, 12))

        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # File Operations
        self.btn_open = ttk.Button(toolbar, text="📂 Open Run...", command=self._on_open_file)
        self.btn_open.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_save = ttk.Button(toolbar, text="💾 Save Run...", command=self._on_save_file)
        self.btn_save.pack(side=tk.LEFT, padx=(0, 4))

        # Export dropdown
        self.btn_export = ttk.Menubutton(toolbar, text="📄 Export Story ▾")
        export_menu = tk.Menu(self.btn_export, tearoff=0)
        export_menu.add_command(label="Export Chronicle as Plain Text (.txt)...", command=self._on_export_text)
        export_menu.add_command(label="Export Chronicle as HTML Document (.html)...", command=self._on_export_html)
        self.btn_export["menu"] = export_menu
        self.btn_export.pack(side=tk.LEFT, padx=(0, 4))

    def _build_tabs(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Create 8 tabs
        self.tab_story = ttk.Frame(self.notebook)
        self.tab_why = ttk.Frame(self.notebook)
        self.tab_threads = ttk.Frame(self.notebook)
        self.tab_people = ttk.Frame(self.notebook)
        self.tab_world = ttk.Frame(self.notebook)
        self.tab_books = ttk.Frame(self.notebook)
        self.tab_religion = ttk.Frame(self.notebook)
        self.tab_changes = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_story, text=" 📜 Story ")
        self.notebook.add(self.tab_why, text=" 🔍 Why (Causality) ")
        self.notebook.add(self.tab_threads, text=" ⚔ Threads ")
        self.notebook.add(self.tab_people, text=" 👤 People & Truth ")
        self.notebook.add(self.tab_world, text=" 🌍 World & Census ")
        self.notebook.add(self.tab_books, text=" 📖 Books ")
        self.notebook.add(self.tab_religion, text=" 🕊 Religion ")
        self.notebook.add(self.tab_changes, text=" ℹ Changes ")

        self._build_story_tab()
        self._build_why_tab()
        self._build_threads_tab()
        self._build_people_tab()
        self._build_world_tab()
        self._build_books_tab()
        self._build_religion_tab()
        self._build_changes_tab()

    def _build_status_bar(self):
        self.status_bar = ttk.Frame(self.root, padding=4)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ttk.Label(self.status_bar, text="Ready", style="Status.TLabel")
        self.status_label.pack(side=tk.LEFT, padx=4)

        self.info_label = ttk.Label(self.status_bar, text=f"Milestone {BUILD_TAG} (Build {BUILD_COMMIT})", style="Status.TLabel")
        self.info_label.pack(side=tk.RIGHT, padx=4)

    # -------------------------------------------------------------------------
    # TAB 1: STORY
    # -------------------------------------------------------------------------
    def _build_story_tab(self):
        # Filter bar
        filt_frame = ttk.Frame(self.tab_story, padding=4)
        filt_frame.pack(side=tk.TOP, fill=tk.X)

        self.filter_hide_demographics = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            filt_frame,
            text="Hide Routine Demographics",
            variable=self.filter_hide_demographics,
            command=self._apply_story_filters,
        ).pack(side=tk.LEFT, padx=(2, 8))

        self.filter_tally_conflicts = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            filt_frame,
            text="Tally Raids & Feuds Only",
            variable=self.filter_tally_conflicts,
            command=self._apply_story_filters,
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(filt_frame, text="Settlement:").pack(side=tk.LEFT, padx=(4, 2))
        self.filter_settlement = ttk.Combobox(filt_frame, width=16, state="readonly", values=["All Settlements"])
        self.filter_settlement.current(0)
        self.filter_settlement.bind("<<ComboboxSelected>>", lambda e: self._apply_story_filters())
        self.filter_settlement.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(filt_frame, text="Type:").pack(side=tk.LEFT, padx=(4, 2))
        self.filter_type = ttk.Combobox(filt_frame, width=16, state="readonly", values=["All Types"])
        self.filter_type.current(0)
        self.filter_type.bind("<<ComboboxSelected>>", lambda e: self._apply_story_filters())
        self.filter_type.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(filt_frame, text="Search:").pack(side=tk.LEFT, padx=(4, 2))
        self.story_search_var = tk.StringVar()
        self.story_search_entry = ttk.Entry(filt_frame, textvariable=self.story_search_var, width=14)
        self.story_search_entry.bind("<Return>", lambda e: self._apply_story_filters())
        self.story_search_entry.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(filt_frame, text="Jump to Year:").pack(side=tk.LEFT, padx=(4, 2))
        self.story_year_jump_var = tk.StringVar()
        self.story_year_jump = ttk.Entry(filt_frame, textvariable=self.story_year_jump_var, width=5)
        self.story_year_jump.bind("<Return>", lambda e: self._jump_to_year())
        self.story_year_jump.pack(side=tk.LEFT, padx=(0, 8))

        self.filter_raw_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            filt_frame,
            text="Raw Mode",
            variable=self.filter_raw_mode,
            command=self._apply_story_filters,
        ).pack(side=tk.RIGHT, padx=4)

        # Scrolled Text view
        self.story_text = scrolledtext.ScrolledText(
            self.tab_story,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            padx=10,
            pady=10,
            background="#FFFFFF",
            relief=tk.FLAT,
        )
        self.story_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Tag styles for categories
        self.story_text.tag_configure("year_hdr", font=("Segoe UI", 12, "bold"), foreground="#1A5276", spacing1=8, spacing3=4)
        self.story_text.tag_configure("conflict", foreground="#922B21")
        self.story_text.tag_configure("flourishing", foreground="#1E8449")
        self.story_text.tag_configure("religion", foreground="#2874A6")
        self.story_text.tag_configure("literature", foreground="#6C3483")
        self.story_text.tag_configure("famine", foreground="#B9770E")
        self.story_text.tag_configure("civic", foreground="#2C3E50")
        self.story_text.tag_configure("because", font=("Segoe UI", 9, "italic"), foreground="#707B7C", lmargin1=24, lmargin2=24)
        self.story_text.tag_configure("raw", font=("Consolas", 9), foreground="#2C3E50")

    def _jump_to_year(self):
        val = self.story_year_jump_var.get().strip()
        if not val:
            return
        try:
            target_year = int(val)
            header_pattern = f"=== YEAR {target_year:02d} ==="
            pos = self.story_text.search(header_pattern, "1.0", tk.END)
            if pos:
                self.story_text.see(pos)
                self.story_text.tag_add("highlight", pos, f"{pos} lineend")
                self.story_text.tag_configure("highlight", background="#FCF3CF")
                self.root.after(2000, lambda: self.story_text.tag_remove("highlight", "1.0", tk.END))
        except ValueError:
            pass

    # -------------------------------------------------------------------------
    # TAB 2: WHY (CAUSALITY)
    # -------------------------------------------------------------------------
    def _build_why_tab(self):
        paned = ttk.PanedWindow(self.tab_why, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Left pane: Event selection
        left_frame = ttk.Frame(paned, padding=4)
        paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Select Event to Trace Causality:", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4))
        
        # Search box in left pane
        why_search_frame = ttk.Frame(left_frame)
        why_search_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(why_search_frame, text="Filter:").pack(side=tk.LEFT)
        self.why_search_var = tk.StringVar()
        self.why_search_entry = ttk.Entry(why_search_frame, textvariable=self.why_search_var)
        self.why_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.why_search_entry.bind("<KeyRelease>", lambda e: self._filter_why_events())

        columns = ("id", "year", "type", "description")
        self.why_tree = ttk.Treeview(left_frame, columns=columns, show="headings", selectmode="browse")
        self.why_tree.heading("id", text="ID")
        self.why_tree.heading("year", text="Year")
        self.why_tree.heading("type", text="Type")
        self.why_tree.heading("description", text="Description")
        self.why_tree.column("id", width=45, anchor=tk.CENTER)
        self.why_tree.column("year", width=45, anchor=tk.CENTER)
        self.why_tree.column("type", width=95)
        self.why_tree.column("description", width=220)

        why_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.why_tree.yview)
        self.why_tree.configure(yscrollcommand=why_scroll.set)
        self.why_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        why_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.why_tree.bind("<<TreeviewSelect>>", self._on_why_select_event)

        # Right pane: Causal DAG inspection
        right_frame = ttk.Frame(paned, padding=6)
        paned.add(right_frame, weight=2)

        ttk.Label(right_frame, text="Causal Chain Breakdown:", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4))

        self.why_details_text = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            padx=10,
            pady=10,
            background="#FFFFFF",
            relief=tk.FLAT,
        )
        self.why_details_text.pack(fill=tk.BOTH, expand=True)

        self.why_details_text.tag_configure("title", font=("Segoe UI", 11, "bold"), foreground="#1B2631")
        self.why_details_text.tag_configure("section", font=("Segoe UI", 10, "bold"), foreground="#2C3E50", spacing1=8, spacing3=2)
        self.why_details_text.tag_configure("cause_line", foreground="#78281F", lmargin1=16, lmargin2=24)
        self.why_details_text.tag_configure("effect_line", foreground="#145A32", lmargin1=16, lmargin2=24)
        self.why_details_text.tag_configure("root_badge", font=("Segoe UI", 9, "bold"), foreground="#B03A2E")

    def _filter_why_events(self):
        query = self.why_search_var.get().strip().lower()
        if not self.run_data:
            return
        self.why_tree.delete(*self.why_tree.get_children())
        for e in self.run_data.events:
            desc = format_event_sentence(EventProxy(
                id=e["id"], tick=e["tick"], location=e.get("location",""), type_val=e.get("type",""),
                participants=tuple((p[0], p[1]) for p in e.get("participants", ())),
                causes=tuple(e.get("causes", ())), intent_val=e.get("intent", ""), scale_val=e.get("scale", ""),
                payload=dict(e.get("payload", {})),
            ), self.run_data.characters, self.run_data.settlements)

            if not query or query in desc.lower() or query in e.get("type", "").lower() or query == str(e["id"]):
                y = (e["tick"] // 12) + 1
                self.why_tree.insert("", tk.END, iid=str(e["id"]), values=(e["id"], y, e.get("type", ""), desc))

    def _on_why_select_event(self, event=None):
        sel = self.why_tree.selection()
        if not sel or not self.run_data:
            return
        event_id = int(sel[0])
        self.inspect_event_causality(event_id)

    def inspect_event_causality(self, event_id: int):
        if not self.run_data or not self.event_log_proxy:
            return
        evt = self.event_log_proxy.get(event_id)
        if not evt:
            return

        self.why_details_text.delete("1.0", tk.END)

        sentence = format_event_sentence(evt, self.run_data.characters, self.run_data.settlements)
        year = (evt.tick // 12) + 1

        self.why_details_text.insert(tk.END, f"Event #{evt.id} (Year {year:02d}, Tick {evt.tick})\n", "title")
        self.why_details_text.insert(tk.END, f"{sentence}\n\n")

        self.why_details_text.insert(tk.END, "Event Metadata:\n", "section")
        self.why_details_text.insert(tk.END, f"  • Type: {evt.type.value}\n")
        self.why_details_text.insert(tk.END, f"  • Intent: {evt.intent.value} | Scale: {evt.scale_val}\n")
        self.why_details_text.insert(tk.END, f"  • Location: {format_settlement_name(evt.location, self.run_data.settlements)}\n")
        
        parts_str = ", ".join(f"{role}: {format_character_name(cid, self.run_data.characters)}" for role, cid in evt.participants)
        self.why_details_text.insert(tk.END, f"  • Participants: {parts_str or 'None'}\n\n")

        # 1. Backward Antecedent Causes (Trace to roots)
        self.why_details_text.insert(tk.END, "◄ Backward Causal Chain (Why Did This Happen?):\n", "section")
        if not evt.causes:
            self.why_details_text.insert(tk.END, "  [ROOT EVENT] This event had no recorded antecedents; it is an unprovoked root cause.\n", "root_badge")
        else:
            visited = set()
            def trace_ancestors(e_curr: EventProxy, depth: int):
                for c_id in e_curr.causes:
                    c_evt = self.event_log_proxy.get(c_id)
                    if c_evt and c_id not in visited:
                        visited.add(c_id)
                        c_sent = format_event_sentence(c_evt, self.run_data.characters, self.run_data.settlements)
                        c_year = (c_evt.tick // 12) + 1
                        indent = "  " * depth
                        root_mark = " [ROOT]" if not c_evt.causes else ""
                        self.why_details_text.insert(tk.END, f"{indent}↳ Caused by #{c_evt.id} (Year {c_year:02d}): {c_sent}{root_mark}\n", "cause_line")
                        trace_ancestors(c_evt, depth + 1)
            trace_ancestors(evt, 1)

        self.why_details_text.insert(tk.END, "\n")

        # 2. Forward Consequences (What Did This Cause?)
        self.why_details_text.insert(tk.END, "► Forward Consequences (What Did This Event Trigger?):\n", "section")
        consequences = [e for e in self.event_log_proxy.all_events() if evt.id in e.causes]
        if not consequences:
            self.why_details_text.insert(tk.END, "  This event produced no downstream consequences.\n")
        else:
            for cons in consequences:
                cons_sent = format_event_sentence(cons, self.run_data.characters, self.run_data.settlements)
                cons_year = (cons.tick // 12) + 1
                self.why_details_text.insert(tk.END, f"  • Triggered #{cons.id} (Year {cons_year:02d}): {cons_sent}\n", "effect_line")

    # -------------------------------------------------------------------------
    # TAB 3: THREADS
    # -------------------------------------------------------------------------
    def _build_threads_tab(self):
        paned = ttk.PanedWindow(self.tab_threads, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Left pane: Thread list
        left_frame = ttk.Frame(paned, padding=4)
        paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Identified Conflict Storylines (≥3 Events):", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4))

        cols = ("title", "span", "events", "depth")
        self.threads_tree = ttk.Treeview(left_frame, columns=cols, show="headings", selectmode="browse")
        self.threads_tree.heading("title", text="Storyline Title")
        self.threads_tree.heading("span", text="Timespan")
        self.threads_tree.heading("events", text="Events")
        self.threads_tree.heading("depth", text="Depth")
        self.threads_tree.column("title", width=180)
        self.threads_tree.column("span", width=90, anchor=tk.CENTER)
        self.threads_tree.column("events", width=50, anchor=tk.CENTER)
        self.threads_tree.column("depth", width=50, anchor=tk.CENTER)

        thr_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.threads_tree.yview)
        self.threads_tree.configure(yscrollcommand=thr_scroll.set)
        self.threads_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        thr_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.threads_tree.bind("<<TreeviewSelect>>", self._on_thread_select)

        # Right pane: Narrative Breakdown
        right_frame = ttk.Frame(paned, padding=6)
        paned.add(right_frame, weight=2)

        ttk.Label(right_frame, text="Storyline Narrative & Chronology:", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4))

        self.thread_detail_text = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            padx=10,
            pady=10,
            background="#FFFFFF",
            relief=tk.FLAT,
        )
        self.thread_detail_text.pack(fill=tk.BOTH, expand=True)

        self.thread_detail_text.tag_configure("title", font=("Segoe UI", 12, "bold"), foreground="#900C3F")
        self.thread_detail_text.tag_configure("meta", font=("Segoe UI", 9, "italic"), foreground="#5D6D7E", spacing3=6)
        self.thread_detail_text.tag_configure("step_hdr", font=("Segoe UI", 10, "bold"), foreground="#1B2631", spacing1=6)
        self.thread_detail_text.tag_configure("step_body", foreground="#2C3E50")
        self.thread_detail_text.tag_configure("step_cause", font=("Segoe UI", 9, "italic"), foreground="#78281F", lmargin1=16, lmargin2=24)

    def _on_thread_select(self, event=None):
        sel = self.threads_tree.selection()
        if not sel:
            return
        t_id = sel[0]
        thread = next((t for t in self.threads if t.thread_id == t_id), None)
        if not thread or not self.run_data or not self.event_log_proxy:
            return

        self.thread_detail_text.delete("1.0", tk.END)
        self.thread_detail_text.insert(tk.END, f"{thread.title}\n", "title")
        self.thread_detail_text.insert(
            tk.END,
            f"Timespan: {thread.year_span} | Events: {thread.event_count} | Longest Causal Depth: {thread.longest_chain_depth}\n\n",
            "meta"
        )

        for idx, e_id in enumerate(thread.event_ids, 1):
            evt = self.event_log_proxy.get(e_id)
            if not evt:
                continue
            y = (evt.tick // 12) + 1
            sent = format_event_sentence(evt, self.run_data.characters, self.run_data.settlements)
            self.thread_detail_text.insert(tk.END, f"Episode {idx:02d} [Year {y:02d}]: {evt.type.value}\n", "step_hdr")
            self.thread_detail_text.insert(tk.END, f"  {sent}\n", "step_body")

            cause_clause = format_because_clause(evt, self.event_log_proxy, self.run_data.characters, self.run_data.settlements)
            if cause_clause:
                self.thread_detail_text.insert(tk.END, f"  [{cause_clause}]\n", "step_cause")
            self.thread_detail_text.insert(tk.END, "\n")

    # -------------------------------------------------------------------------
    # TAB 4: PEOPLE & TRUTH
    # -------------------------------------------------------------------------
    def _build_people_tab(self):
        paned = ttk.PanedWindow(self.tab_people, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Left pane: Character roster
        left_frame = ttk.Frame(paned, padding=4)
        paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Characters Roster:", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4))

        p_filt = ttk.Frame(left_frame)
        p_filt.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(p_filt, text="Filter:").pack(side=tk.LEFT)
        self.people_filter_var = tk.StringVar()
        self.people_filter_entry = ttk.Entry(p_filt, textvariable=self.people_filter_var)
        self.people_filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.people_filter_entry.bind("<KeyRelease>", lambda e: self._filter_people_list())

        cols = ("name", "status", "age", "settlement")
        self.people_tree = ttk.Treeview(left_frame, columns=cols, show="headings", selectmode="browse")
        self.people_tree.heading("name", text="Name")
        self.people_tree.heading("status", text="Status")
        self.people_tree.heading("age", text="Age")
        self.people_tree.heading("settlement", text="Home")
        self.people_tree.column("name", width=130)
        self.people_tree.column("status", width=60, anchor=tk.CENTER)
        self.people_tree.column("age", width=40, anchor=tk.CENTER)
        self.people_tree.column("settlement", width=100)

        p_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.people_tree.yview)
        self.people_tree.configure(yscrollcommand=p_scroll.set)
        self.people_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        p_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.people_tree.bind("<<TreeviewSelect>>", self._on_person_select)

        # Right pane: Details and TRUTH VS BELIEF
        right_frame = ttk.Frame(paned, padding=6)
        paned.add(right_frame, weight=2)

        ttk.Label(right_frame, text="Character Biography & Truth vs. Belief Audit:", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4))

        self.person_details_text = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            padx=10,
            pady=10,
            background="#FFFFFF",
            relief=tk.FLAT,
        )
        self.person_details_text.pack(fill=tk.BOTH, expand=True)

        self.person_details_text.tag_configure("char_name", font=("Segoe UI", 13, "bold"), foreground="#1B2631")
        self.person_details_text.tag_configure("sec_hdr", font=("Segoe UI", 10, "bold"), foreground="#2C3E50", spacing1=8, spacing3=2)
        self.person_details_text.tag_configure("truth_hdr", font=("Segoe UI", 10, "bold"), foreground="#196F3D")
        self.person_details_text.tag_configure("belief_hdr", font=("Segoe UI", 10, "bold"), foreground="#884EA0")
        self.person_details_text.tag_configure("divergence", background="#FADBD8", foreground="#78281F", font=("Segoe UI", 9, "bold"))
        self.person_details_text.tag_configure("accord", background="#D5F5E3", foreground="#1E8449")

    def _filter_people_list(self):
        query = self.people_filter_var.get().strip().lower()
        if not self.run_data:
            return
        self.people_tree.delete(*self.people_tree.get_children())
        for cid, c in sorted(self.run_data.characters.items(), key=lambda kv: kv[1].get("full_name", "")):
            fname = c.get("full_name") or f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
            sname = format_settlement_name(c.get("settlement_id", ""), self.run_data.settlements)
            status = "Alive" if c.get("alive") else "Dead"
            age = c.get("age_years", 0)

            if not query or query in fname.lower() or query in sname.lower() or query in status.lower():
                self.people_tree.insert("", tk.END, iid=cid, values=(fname, status, age, sname))

    def _on_person_select(self, event=None):
        sel = self.people_tree.selection()
        if not sel or not self.run_data:
            return
        cid = sel[0]
        c = self.run_data.characters.get(cid)
        if not c:
            return

        self.person_details_text.delete("1.0", tk.END)

        full_name = c.get("full_name") or f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
        status_str = "Living" if c.get("alive") else f"Deceased (Tick {c.get('death_tick', '?')})"

        self.person_details_text.insert(tk.END, f"{full_name} ({status_str})\n", "char_name")
        self.person_details_text.insert(tk.END, f"Settlement: {format_settlement_name(c.get('settlement_id', ''), self.run_data.settlements)} | Sex: {c.get('sex', '?')} | Age: {c.get('age_years', 0)} years\n\n")

        # Family
        self.person_details_text.insert(tk.END, "Family & Kinship:\n", "sec_hdr")
        father = format_character_name(c.get("father_id", ""), self.run_data.characters)
        mother = format_character_name(c.get("mother_id", ""), self.run_data.characters)
        spouse = format_character_name(c.get("spouse_id", ""), self.run_data.characters)
        kids = [format_character_name(k, self.run_data.characters) for k in c.get("children_ids", ())]
        
        self.person_details_text.insert(tk.END, f"  • Parents: {father} & {mother}\n")
        self.person_details_text.insert(tk.END, f"  • Spouse: {spouse or 'Unmarried'}\n")
        self.person_details_text.insert(tk.END, f"  • Children: {', '.join(kids) if kids else 'None'}\n\n")

        # Psychology
        self.person_details_text.insert(tk.END, "Psychological Profile:\n", "sec_hdr")
        self.person_details_text.insert(tk.END, f"  • Suspicion: {c.get('suspicion', 0.0):.2f}\n")
        self.person_details_text.insert(tk.END, f"  • Forgiveness: {c.get('forgiveness', 0.0):.2f}\n\n")

        # TRUTH VS BELIEF AUDIT
        self.person_details_text.insert(tk.END, "TRUTH VS. BELIEF AUDIT (Epistemic Reality vs. Subjective Mind):\n", "sec_hdr")
        c_beliefs = self.run_data.beliefs.get(cid, {})

        if not c_beliefs:
            self.person_details_text.insert(tk.END, "  This character holds no recorded historical event beliefs.\n")
        else:
            self.person_details_text.insert(
                tk.END,
                f"  This character holds {len(c_beliefs)} event beliefs. Comparing mind to reality:\n\n"
            )

            # Iterate through beliefs
            divergence_count = 0
            for e_id_str, b_dict in c_beliefs.items():
                e_id = int(e_id_str)
                real_evt = self.event_log_proxy.get(e_id) if self.event_log_proxy else None

                b_type = b_dict.get("believed_type", "")
                b_intent = b_dict.get("believed_intent", "")
                b_actor = format_character_name(b_dict.get("believed_actor", ""), self.run_data.characters)
                b_conf = b_dict.get("confidence", 1.0)
                b_src = b_dict.get("source", "")

                r_type = real_evt.type.value if real_evt else "Unknown"
                r_intent = real_evt.intent.value if real_evt else "Unknown"
                r_actor = format_character_name(real_evt.participants_dict.get("actor", "") or real_evt.participants_dict.get("aggressor", ""), self.run_data.characters) if real_evt else "None"

                is_divergent = (b_type != r_type) or (b_intent != r_intent) or (b_dict.get("believed_actor") and b_dict.get("believed_actor") != real_evt.participants_dict.get("actor") if real_evt else False)
                if is_divergent:
                    divergence_count += 1

                flag_tag = "divergence" if is_divergent else "accord"
                flag_text = " [DIVERGENCE / MISTRUTH]" if is_divergent else " [TRUE WITNESS]"

                self.person_details_text.insert(tk.END, f"  • Event #{e_id}{flag_text}\n", flag_tag)
                self.person_details_text.insert(
                    tk.END,
                    f"      Belief ({b_src}, conf: {b_conf:.2f}): Considers it a '{b_type}' with '{b_intent}' intent by {b_actor}.\n",
                    "belief_hdr"
                )
                self.person_details_text.insert(
                    tk.END,
                    f"      Reality: Was actually a '{r_type}' with '{r_intent}' intent by {r_actor}.\n\n",
                    "truth_hdr"
                )

            if divergence_count > 0:
                self.person_details_text.insert(
                    tk.END,
                    f"  Summary: {divergence_count} of {len(c_beliefs)} beliefs diverge from ground truth reality, driving suspicion and grudges.\n",
                    "divergence"
                )

    # -------------------------------------------------------------------------
    # TAB 5: WORLD & CENSUS
    # -------------------------------------------------------------------------
    def _build_world_tab(self):
        # Upper: Metrics Summary Cards
        metric_frame = ttk.Frame(self.tab_world, padding=6)
        metric_frame.pack(side=tk.TOP, fill=tk.X)

        self.lbl_world_summary = ttk.Label(
            metric_frame,
            text="Simulate a run or open a file to view demographic and world balance analytics.",
            font=("Segoe UI", 10, "bold"),
            foreground="#1F618D",
        )
        self.lbl_world_summary.pack(anchor=tk.W, pady=2)

        # Middle: Population Canvas Chart
        chart_frame = ttk.LabelFrame(self.tab_world, text="Settlement Demographics & Population Over Time (100 Years)", padding=6)
        chart_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=4)

        self.pop_canvas = tk.Canvas(chart_frame, bg="#FFFFFF", highlightthickness=0)
        self.pop_canvas.pack(fill=tk.BOTH, expand=True)
        self.pop_canvas.bind("<Configure>", lambda e: self._draw_population_chart())

        # Lower Split: Collapses/Migrations and Event Share
        lower_paned = ttk.PanedWindow(self.tab_world, orient=tk.HORIZONTAL)
        lower_paned.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Left lower: Crisis & Collapses
        crisis_frame = ttk.LabelFrame(lower_paned, text="Settlement Crises, Famines, & Collapses", padding=4)
        lower_paned.add(crisis_frame, weight=1)

        cols_c = ("year", "settlement", "crisis")
        self.crisis_tree = ttk.Treeview(crisis_frame, columns=cols_c, show="headings")
        self.crisis_tree.heading("year", text="Year")
        self.crisis_tree.heading("settlement", text="Location")
        self.crisis_tree.heading("crisis", text="Event Description")
        self.crisis_tree.column("year", width=50, anchor=tk.CENTER)
        self.crisis_tree.column("settlement", width=110)
        self.crisis_tree.column("crisis", width=240)
        self.crisis_tree.pack(fill=tk.BOTH, expand=True)

        # Right lower: Event Share Balance Table
        share_frame = ttk.LabelFrame(lower_paned, text="Event Type Share (% Balance Audit)", padding=4)
        lower_paned.add(share_frame, weight=1)

        cols_s = ("type", "count", "percent")
        self.share_tree = ttk.Treeview(share_frame, columns=cols_s, show="headings")
        self.share_tree.heading("type", text="Event Type")
        self.share_tree.heading("count", text="Count")
        self.share_tree.heading("percent", text="Share (%)")
        self.share_tree.column("type", width=140)
        self.share_tree.column("count", width=60, anchor=tk.CENTER)
        self.share_tree.column("percent", width=70, anchor=tk.CENTER)
        self.share_tree.pack(fill=tk.BOTH, expand=True)

    def _draw_population_chart(self):
        self.pop_canvas.delete("all")
        if not self.run_data or not self.run_data.census:
            return

        w = self.pop_canvas.winfo_width()
        h = self.pop_canvas.winfo_height()
        if w < 100 or h < 100:
            return

        margin_left = 50
        margin_right = 30
        margin_top = 30
        margin_bottom = 40

        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        census = self.run_data.census
        num_years = len(census)
        if num_years < 2:
            return

        max_pop = max((c["total_population"] for c in census), default=100)
        max_pop = max(max_pop, 50)
        # Round up max_pop to neat multiple of 20
        y_max = int(math.ceil(max_pop / 20.0) * 20)

        # Axes
        self.pop_canvas.create_line(margin_left, margin_top + chart_h, margin_left + chart_w, margin_top + chart_h, fill="#BDC3C7", width=2)
        self.pop_canvas.create_line(margin_left, margin_top, margin_left, margin_top + chart_h, fill="#BDC3C7", width=2)

        # Grid lines and Y labels
        for y_val in range(0, y_max + 1, max(20, y_max // 5)):
            y_pos = margin_top + chart_h - (y_val / y_max) * chart_h
            self.pop_canvas.create_line(margin_left, y_pos, margin_left + chart_w, y_pos, fill="#EAEDED", dash=(2, 4))
            self.pop_canvas.create_text(margin_left - 8, y_pos, text=str(y_val), anchor=tk.E, font=("Segoe UI", 8), fill="#7F8C8D")

        # X labels
        for x_year in range(10, num_years + 1, 20):
            x_pos = margin_left + (x_year / num_years) * chart_w
            self.pop_canvas.create_line(x_pos, margin_top + chart_h, x_pos, margin_top + chart_h + 4, fill="#BDC3C7")
            self.pop_canvas.create_text(x_pos, margin_top + chart_h + 14, text=f"Y{x_year}", font=("Segoe UI", 8), fill="#7F8C8D")

        # Settlement lines
        colors = ["#2980B9", "#27AE60", "#E67E22", "#8E44AD", "#C0392B"]
        settlements = list(self.run_data.settlements.keys())

        # Legend
        legend_x = margin_left + 10
        self.pop_canvas.create_line(legend_x, margin_top - 12, legend_x + 18, margin_top - 12, fill="#2C3E50", width=3)
        self.pop_canvas.create_text(legend_x + 22, margin_top - 12, text="Total World Pop", anchor=tk.W, font=("Segoe UI", 8, "bold"), fill="#2C3E50")
        legend_x += 120

        for idx, s_id in enumerate(settlements):
            col = colors[idx % len(colors)]
            s_name = format_settlement_name(s_id, self.run_data.settlements)
            self.pop_canvas.create_line(legend_x, margin_top - 12, legend_x + 18, margin_top - 12, fill=col, width=2)
            self.pop_canvas.create_text(legend_x + 22, margin_top - 12, text=s_name, anchor=tk.W, font=("Segoe UI", 8), fill=col)
            legend_x += 110

        # Plot settlement points
        for idx, s_id in enumerate(settlements):
            col = colors[idx % len(colors)]
            coords = []
            for c_entry in census:
                y_idx = c_entry["year"]
                pop = c_entry["populations"].get(s_id, 0)
                px = margin_left + (y_idx / num_years) * chart_w
                py = margin_top + chart_h - (pop / y_max) * chart_h
                coords.extend([px, py])
            if len(coords) >= 4:
                self.pop_canvas.create_line(*coords, fill=col, width=2, smooth=True)

        # Plot total population line
        tot_coords = []
        for c_entry in census:
            y_idx = c_entry["year"]
            t_pop = c_entry["total_population"]
            px = margin_left + (y_idx / num_years) * chart_w
            py = margin_top + chart_h - (t_pop / y_max) * chart_h
            tot_coords.extend([px, py])
        if len(tot_coords) >= 4:
            self.pop_canvas.create_line(*tot_coords, fill="#2C3E50", width=3, smooth=True)

    # -------------------------------------------------------------------------
    # TAB 6: BOOKS
    # -------------------------------------------------------------------------
    def _build_books_tab(self):
        paned = ttk.PanedWindow(self.tab_books, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Left: Library list
        left_frame = ttk.Frame(paned, padding=4)
        paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Penned Manuscripts & Chronicles:", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4))

        cols = ("title", "author", "year", "genre")
        self.books_tree = ttk.Treeview(left_frame, columns=cols, show="headings", selectmode="browse")
        self.books_tree.heading("title", text="Book Title")
        self.books_tree.heading("author", text="Author")
        self.books_tree.heading("year", text="Year")
        self.books_tree.heading("genre", text="Genre")
        self.books_tree.column("title", width=160)
        self.books_tree.column("author", width=100)
        self.books_tree.column("year", width=40, anchor=tk.CENTER)
        self.books_tree.column("genre", width=80)

        b_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.books_tree.yview)
        self.books_tree.configure(yscrollcommand=b_scroll.set)
        self.books_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        b_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.books_tree.bind("<<TreeviewSelect>>", self._on_book_select)

        # Right: Book Reader View
        right_frame = ttk.Frame(paned, padding=6)
        paned.add(right_frame, weight=2)

        ttk.Label(right_frame, text="Manuscript Reader (Minecraft Book Layout):", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4))

        # Reader frame mimicking a parchment page
        self.reader_meta_lbl = ttk.Label(right_frame, text="Select a book from the library to read.", font=("Segoe UI", 9, "italic"))
        self.reader_meta_lbl.pack(anchor=tk.W, pady=(0, 4))

        # Page container
        page_box = tk.Frame(right_frame, bg="#FDFEFE", bd=2, relief=tk.GROOVE, padx=12, pady=12)
        page_box.pack(fill=tk.BOTH, expand=True, pady=4)

        self.reader_title_lbl = tk.Label(page_box, text="", font=("Georgia", 14, "bold"), bg="#FDFEFE", fg="#17202A")
        self.reader_title_lbl.pack(anchor=tk.N, pady=(0, 4))

        self.reader_page_text = tk.Label(
            page_box,
            text="",
            font=("Georgia", 11),
            bg="#FDFEFE",
            fg="#2C3E50",
            wraplength=480,
            justify=tk.LEFT,
        )
        self.reader_page_text.pack(fill=tk.BOTH, expand=True, pady=8)

        # Page nav controls
        nav_frame = ttk.Frame(right_frame)
        nav_frame.pack(fill=tk.X, pady=4)

        self.btn_prev_page = ttk.Button(nav_frame, text="◀ Prev Page", width=12, command=self._on_prev_page)
        self.btn_prev_page.pack(side=tk.LEFT, padx=4)

        self.lbl_page_num = ttk.Label(nav_frame, text="Page 0 / 0", font=("Segoe UI", 9, "bold"))
        self.lbl_page_num.pack(side=tk.LEFT, expand=True)

        self.btn_next_page = ttk.Button(nav_frame, text="Next Page ▶", width=12, command=self._on_next_page)
        self.btn_next_page.pack(side=tk.RIGHT, padx=4)

        # Historiographical disclosure box
        self.reader_bias_lbl = ttk.Label(
            right_frame,
            text="",
            font=("Segoe UI", 9, "italic"),
            foreground="#6C3483",
            wraplength=500,
        )
        self.reader_bias_lbl.pack(fill=tk.X, pady=(4, 0))

    def _on_book_select(self, event=None):
        sel = self.books_tree.selection()
        if not sel or not self.run_data:
            return
        book_id = sel[0]
        b = next((bk for bk in self.run_data.books if bk.get("id") == book_id), None)
        if not b:
            return

        self.current_book_index = next((i for i, bk in enumerate(self.run_data.books) if bk.get("id") == book_id), 0)
        self.current_book_page = 0
        self._render_current_book_page()

    def _render_current_book_page(self):
        if not self.run_data or not self.run_data.books:
            return
        b = self.run_data.books[self.current_book_index]
        pages = b.get("pages", [])
        total_pages = len(pages)

        self.reader_meta_lbl.config(
            text=f"Author: {b.get('author_name', 'Unknown')} ({b.get('author_literacy', 'Unknown')}) | Penned: Year {b.get('creation_year', 0)} | Settlement: {format_settlement_name(b.get('settlement_id', ''), self.run_data.settlements)}"
        )
        self.reader_title_lbl.config(text=b.get("title", "Untitled Manuscript"))

        if total_pages == 0:
            self.reader_page_text.config(text="[This book contains no recorded pages.]")
            self.lbl_page_num.config(text="Page 0 / 0")
        else:
            p_idx = max(0, min(self.current_book_page, total_pages - 1))
            self.current_book_page = p_idx
            self.reader_page_text.config(text=pages[p_idx])
            self.lbl_page_num.config(text=f"Page {p_idx + 1} of {total_pages}")

        bias = b.get("perspective_bias", "Unbiased chronicle")
        self.reader_bias_lbl.config(text=f"Historiographical Disclosure: Authorial perspective reflects: {bias}.")

    def _on_prev_page(self):
        if self.current_book_page > 0:
            self.current_book_page -= 1
            self._render_current_book_page()

    def _on_next_page(self):
        if not self.run_data or not self.run_data.books:
            return
        b = self.run_data.books[self.current_book_index]
        if self.current_book_page < len(b.get("pages", [])) - 1:
            self.current_book_page += 1
            self._render_current_book_page()

    # -------------------------------------------------------------------------
    # TAB 7: RELIGION
    # -------------------------------------------------------------------------
    def _build_religion_tab(self):
        paned = ttk.PanedWindow(self.tab_religion, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Upper: Faiths & Tenets
        upper_frame = ttk.LabelFrame(paned, text="Theological Doctrines & Sacred Geography", padding=6)
        paned.add(upper_frame, weight=1)

        self.religion_overview_text = scrolledtext.ScrolledText(
            upper_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            padx=10,
            pady=10,
            background="#FFFFFF",
            relief=tk.FLAT,
        )
        self.religion_overview_text.pack(fill=tk.BOTH, expand=True)

        # Lower: Religious Events log (Schisms, Syncretisms, Reforms, Holy Sites)
        lower_frame = ttk.LabelFrame(paned, text="Religious History & Evolution Events", padding=4)
        paned.add(lower_frame, weight=1)

        cols = ("year", "type", "description")
        self.rel_events_tree = ttk.Treeview(lower_frame, columns=cols, show="headings")
        self.rel_events_tree.heading("year", text="Year")
        self.rel_events_tree.heading("type", text="Type")
        self.rel_events_tree.heading("description", text="Religious Event Description")
        self.rel_events_tree.column("year", width=50, anchor=tk.CENTER)
        self.rel_events_tree.column("type", width=120)
        self.rel_events_tree.column("description", width=400)
        self.rel_events_tree.pack(fill=tk.BOTH, expand=True)

    # -------------------------------------------------------------------------
    # TAB 8: CHANGES (Release Notes & Standing Rule)
    # -------------------------------------------------------------------------
    def _build_changes_tab(self):
        txt = scrolledtext.ScrolledText(
            self.tab_changes,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            padx=16,
            pady=16,
            background="#FFFFFF",
            relief=tk.FLAT,
        )
        txt.pack(fill=tk.BOTH, expand=True)

        txt.tag_configure("h1", font=("Segoe UI", 14, "bold"), foreground="#1B2631", spacing3=6)
        txt.tag_configure("h2", font=("Segoe UI", 11, "bold"), foreground="#2C3E50", spacing1=8, spacing3=4)
        txt.tag_configure("bullet", lmargin1=16, lmargin2=28)
        txt.tag_configure("highlight", font=("Segoe UI", 10, "bold"), foreground="#196F3D")

        txt.insert(tk.END, f"Minemesis Story Viewer - Release Notes (Milestone {BUILD_TAG})\n", "h1")
        txt.insert(tk.END, f"Build Commit: {BUILD_COMMIT} | Build Date: {BUILD_TIME} | Schema: v{SCHEMA_VERSION}\n\n")

        txt.insert(tk.END, "What changed in this build (Plain-English Summary):\n", "h2")
        txt.insert(tk.END, "1. Reconciled all event numbers and population figures so birth, death, and census accounts match reality exactly.\n", "bullet")
        txt.insert(tk.END, "2. Hardened determinism so running any seed yields identical output regardless of process memory or hashing salts.\n", "bullet")
        txt.insert(tk.END, "3. Eliminated repetitive festival and routine conversion spam so genuine feuds and raids stand out prominently.\n", "bullet")
        txt.insert(tk.END, "4. Re-anchored book creation in author beliefs, ensuring books reflect subjective character biases rather than omniscient truth.\n", "bullet")
        txt.insert(tk.END, "5. Built this standalone Story Viewer application to explore causal roots, feuds, books, and beliefs with one click.\n\n", "bullet")

        txt.insert(tk.END, "3 Things to look for in the viewer:\n", "h2")
        txt.insert(tk.END, "1. In the Story tab, look for indented '↳ because: [...]' lines explaining the causal grievances behind violence.\n", "bullet")
        txt.insert(tk.END, "2. In the People tab, check the 'Truth vs. Belief Audit' to see how false rumors spark deadly grudges.\n", "bullet")
        txt.insert(tk.END, "3. In the World tab, inspect the event share table and population graph over 100 years of civilization.\n\n", "bullet")

        txt.insert(tk.END, "Standing Rule Compliance:\n", "h2")
        txt.insert(tk.END, "• The viewer is an independent, read-only presentation layer in `viewer/`.\n", "bullet")
        txt.insert(tk.END, "• `minemesis` never imports `viewer` (enforced by automated boundary tests).\n", "bullet")
        txt.insert(tk.END, "• The viewer draws zero RNG numbers from the simulation, preserving strict determinism.\n", "bullet")

    # =========================================================================
    # ACTIONS & SIMULATION RUNNER
    # =========================================================================

    def _on_random_seed(self):
        new_seed = random.randint(100, 9999)
        self.seed_var.set(str(new_seed))

    def _on_run_click(self):
        if self.is_simulating:
            return
        try:
            seed = int(self.seed_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Input", "Seed must be an integer.")
            return

        try:
            years = int(self.years_var.get().strip())
            if years <= 0 or years > 500:
                messagebox.showerror("Invalid Input", "Years must be between 1 and 500.")
                return
        except ValueError:
            messagebox.showerror("Invalid Input", "Years must be an integer.")
            return

        self._start_simulation(seed, years)

    def _start_simulation(self, seed: int, years: int):
        self.is_simulating = True
        self.btn_run.config(state=tk.DISABLED)
        self.btn_random.config(state=tk.DISABLED)
        self.status_label.config(text=f"Simulating Seed {seed} for {years} years...")
        self.progress_bar.config(value=0, maximum=years)

        enable_rel = self.toggle_religion.get()
        enable_lore = self.toggle_lore.get()

        def worker():
            try:
                # Import simulation inside worker to maintain isolation
                from minemesis.systems.simulation import Simulation

                sim = Simulation(
                    seed=seed,
                    enable_religion=enable_rel,
                    enable_lore=enable_lore,
                )

                # Run step by step to update progress
                total_ticks = years * 12
                for tick_idx in range(total_ticks):
                    if len(sim.living_characters) == 0:
                        break
                    sim.step_month()
                    if (tick_idx + 1) % 12 == 0:
                        completed_years = (tick_idx + 1) // 12
                        self.root.after(0, self._update_sim_progress, completed_years, years)

                # Capture RunData
                build_info = {
                    "tag": BUILD_TAG,
                    "commit": BUILD_COMMIT,
                    "date": BUILD_TIME,
                }
                run_data = RunData.from_simulation(sim, years=years, build_info=build_info)
                self.root.after(0, self._on_simulation_complete, run_data)
            except Exception as ex:
                self.root.after(0, self._on_simulation_error, str(ex))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _update_sim_progress(self, current_year: int, total_years: int):
        self.progress_bar.config(value=current_year)
        self.status_label.config(text=f"Simulating: Year {current_year} of {total_years}...")

    def _on_simulation_complete(self, run_data: RunData):
        self.is_simulating = False
        self.btn_run.config(state=tk.NORMAL)
        self.btn_random.config(state=tk.NORMAL)
        self.progress_bar.config(value=self.progress_bar["maximum"])
        self.status_label.config(text=f"Simulation complete: Seed {run_data.seed} ({len(run_data.events)} events logged)")

        self.set_run_data(run_data)

    def _on_simulation_error(self, err_msg: str):
        self.is_simulating = False
        self.btn_run.config(state=tk.NORMAL)
        self.btn_random.config(state=tk.NORMAL)
        self.status_label.config(text="Simulation failed.")
        messagebox.showerror("Simulation Error", f"An error occurred during simulation:\n{err_msg}")

    # =========================================================================
    # DATA POPULATION
    # =========================================================================

    def set_run_data(self, run_data: RunData):
        self.run_data = run_data
        self.event_log_proxy = run_data.get_event_log_proxy()

        # Update settlement dropdown in story tab
        s_names = ["All Settlements"] + [format_settlement_name(sid, run_data.settlements) for sid in sorted(run_data.settlements.keys())]
        self.filter_settlement["values"] = s_names
        self.filter_settlement.current(0)

        # Update event types in story tab
        e_types = ["All Types"] + sorted(list(run_data.event_share.keys()))
        self.filter_type["values"] = e_types
        self.filter_type.current(0)

        # Extract conflict storylines
        self.threads = extract_story_threads(
            event_log=self.event_log_proxy,
            characters=run_data.characters,
            settlements=run_data.settlements,
            min_events=3,
        )

        # Refresh all views
        self._apply_story_filters()
        self._populate_why_tab()
        self._populate_threads_tab()
        self._populate_people_tab()
        self._populate_world_tab()
        self._populate_books_tab()
        self._populate_religion_tab()

    def _apply_story_filters(self):
        if not self.run_data or not self.event_log_proxy:
            return

        hide_demographics = self.filter_hide_demographics.get()
        tally_conflicts = self.filter_tally_conflicts.get()
        sel_settle = self.filter_settlement.get()
        sel_type = self.filter_type.get()
        search_query = self.story_search_var.get().strip().lower()
        raw_mode = self.filter_raw_mode.get()

        self.story_text.delete("1.0", tk.END)

        filtered_events = []
        for e in self.event_log_proxy.all_events():
            t_val = e.type.value

            # Filter demographics
            if hide_demographics:
                if t_val in ("Birth", "Marriage"):
                    continue
                if t_val == "Death" and e.payload.get("cause") in ("old_age", "natural_causes", "illness", "fever"):
                    continue

            # Tally conflicts
            if tally_conflicts:
                if t_val not in ("Feud", "Raid", "Death", "Peace", "SuccessionCrisis", "SettlementCollapse"):
                    continue

            # Settlement filter
            if sel_settle != "All Settlements":
                sname = format_settlement_name(e.location, self.run_data.settlements)
                if sname != sel_settle:
                    continue

            # Type filter
            if sel_type != "All Types":
                if t_val != sel_type:
                    continue

            sentence = format_event_sentence(e, self.run_data.characters, self.run_data.settlements)
            if search_query:
                if (search_query not in sentence.lower() and
                    search_query not in t_val.lower() and
                    search_query != str(e.id)):
                    continue

            filtered_events.append((e, sentence))

        # Group by year
        current_year = -1
        for e, sentence in filtered_events:
            year = (e.tick // 12) + 1
            if year != current_year:
                current_year = year
                self.story_text.insert(tk.END, f"\n=== YEAR {current_year:02d} ===\n", "year_hdr")

            if raw_mode:
                self.story_text.insert(
                    tk.END,
                    f"  [#{e.id:04d} Y{year:02d} T{e.tick:04d}] {e.type.value} @ {e.location} causes={list(e.causes)}: {sentence}\n",
                    "raw"
                )
            else:
                tag = "civic"
                t_val = e.type.value
                if t_val in ("Feud", "Raid", "SuccessionCrisis", "SettlementCollapse"):
                    tag = "conflict"
                elif t_val in ("Peace", "Marriage", "Birth"):
                    tag = "flourishing"
                elif t_val in ("Conversion", "Revelation", "HolySiteDiscovered", "HolySiteElevated", "ReligiousSchism", "Pilgrimage"):
                    tag = "religion"
                elif t_val in ("BookWritten", "ArchiveDamaged"):
                    tag = "literature"
                elif t_val in ("Famine",):
                    tag = "famine"

                self.story_text.insert(tk.END, f"  • {sentence}\n", tag)
                because_clause = format_because_clause(e, self.event_log_proxy, self.run_data.characters, self.run_data.settlements)
                if because_clause:
                    self.story_text.insert(tk.END, f"      [↳ {because_clause}]\n", "because")

    def _populate_why_tab(self):
        self.why_tree.delete(*self.why_tree.get_children())
        self.why_details_text.delete("1.0", tk.END)
        self._filter_why_events()

    def _populate_threads_tab(self):
        self.threads_tree.delete(*self.threads_tree.get_children())
        self.thread_detail_text.delete("1.0", tk.END)

        for t in self.threads:
            self.threads_tree.insert(
                "",
                tk.END,
                iid=t.thread_id,
                values=(t.title, t.year_span, t.event_count, t.longest_chain_depth),
            )

        if self.threads:
            self.threads_tree.selection_set(self.threads[0].thread_id)
            self._on_thread_select()

    def _populate_people_tab(self):
        self.people_tree.delete(*self.people_tree.get_children())
        self.person_details_text.delete("1.0", tk.END)
        self._filter_people_list()
        all_cids = list(self.run_data.characters.keys())
        if all_cids:
            self.people_tree.selection_set(all_cids[0])
            self._on_person_select()

    def _populate_world_tab(self):
        # Summary
        census = self.run_data.census
        init_pop = census[0]["total_population"] if census else 0
        final_pop = census[-1]["total_population"] if census else 0
        living_count = sum(1 for c in self.run_data.characters.values() if c.get("alive"))
        total_births = sum(1 for e in self.run_data.events if e.get("type") == "Birth")
        total_deaths = sum(1 for e in self.run_data.events if e.get("type") == "Death")

        summary_text = (
            f"Seed {self.run_data.seed} | {self.run_data.years} Years Simulated | "
            f"Initial Pop: {init_pop} ➔ Final Living: {living_count} (Census: {final_pop}) | "
            f"Total Births: {total_births} | Total Deaths: {total_deaths} | Total Events: {len(self.run_data.events)}"
        )
        self.lbl_world_summary.config(text=summary_text)

        # Crises list
        self.crisis_tree.delete(*self.crisis_tree.get_children())
        for e in self.run_data.events:
            t = e.get("type")
            if t in ("SettlementCollapse", "Famine", "SuccessionCrisis", "Migration"):
                y = (e["tick"] // 12) + 1
                s_name = format_settlement_name(e.get("location", ""), self.run_data.settlements)
                sent = format_event_sentence(
                    EventProxy(id=e["id"], tick=e["tick"], location=e.get("location",""), type_val=t,
                               participants=tuple((p[0],p[1]) for p in e.get("participants", ())),
                               causes=tuple(e.get("causes", ())), intent_val="", scale_val="", payload=dict(e.get("payload",{}))),
                    self.run_data.characters,
                    self.run_data.settlements,
                )
                self.crisis_tree.insert("", tk.END, values=(y, s_name, sent))

        # Event share table
        self.share_tree.delete(*self.share_tree.get_children())
        from collections import Counter
        counts = Counter(e.get("type") for e in self.run_data.events)
        total = len(self.run_data.events) or 1
        for ev_type, count in counts.most_common():
            pct = round((count / total) * 100, 2)
            self.share_tree.insert("", tk.END, values=(ev_type, count, f"{pct}%"))

        # Redraw chart
        self._draw_population_chart()

    def _populate_books_tab(self):
        self.books_tree.delete(*self.books_tree.get_children())
        for b in self.run_data.books:
            self.books_tree.insert(
                "",
                tk.END,
                iid=b.get("id"),
                values=(
                    b.get("title", "Untitled"),
                    b.get("author_name", "Unknown"),
                    b.get("creation_year", 0),
                    b.get("genre", "Chronicle"),
                ),
            )
        if self.run_data.books:
            self.books_tree.selection_set(self.run_data.books[0].get("id"))
            self._on_book_select()
        else:
            self.reader_meta_lbl.config(text="No books penned in this simulation run (Lore disabled or early years).")
            self.reader_title_lbl.config(text="")
            self.reader_page_text.config(text="")
            self.lbl_page_num.config(text="Page 0 / 0")
            self.reader_bias_lbl.config(text="")

    def _populate_religion_tab(self):
        self.religion_overview_text.delete("1.0", tk.END)
        self.rel_events_tree.delete(*self.rel_events_tree.get_children())

        # Collect religious events
        rel_events = []
        for e in self.run_data.events:
            t = e.get("type")
            if t in (
                "Conversion", "Revelation", "HolySiteDiscovered", "HolySiteElevated",
                "ReligiousSchism", "ReligiousReform", "ReligiousSyncretism", "HeresyDeclared",
                "DoctrinalBorrowing", "FolkTraditionAbsorbed", "SaintCanonized", "Pilgrimage"
            ):
                y = (e["tick"] // 12) + 1
                sent = format_event_sentence(
                    EventProxy(id=e["id"], tick=e["tick"], location=e.get("location",""), type_val=t,
                               participants=tuple((p[0],p[1]) for p in e.get("participants", ())),
                               causes=tuple(e.get("causes", ())), intent_val="", scale_val="", payload=dict(e.get("payload",{}))),
                    self.run_data.characters,
                    self.run_data.settlements,
                )
                self.rel_events_tree.insert("", tk.END, values=(y, t, sent))
                rel_events.append((y, t, sent))

        # Theological overview
        self.religion_overview_text.insert(
            tk.END,
            f"Religious Analytics & Theological Profile (Seed {self.run_data.seed}):\n\n",
            "Header.TLabel"
        )
        self.religion_overview_text.insert(
            tk.END,
            f"Total Religious Evolution Events Recorded: {len(rel_events)}\n\n"
        )
        self.religion_overview_text.insert(
            tk.END,
            "Settlements & Active Faiths:\n"
        )
        for s_id, s in self.run_data.settlements.items():
            s_name = format_settlement_name(s_id, self.run_data.settlements)
            # Find conversions in this settlement
            settle_convs = [e for e in self.run_data.events if e.get("type") == "Conversion" and e.get("location") == s_id]
            self.religion_overview_text.insert(
                tk.END,
                f"  • {s_name} ({s_id}): {len(settle_convs)} notable spiritual conversions recorded.\n"
            )

    # =========================================================================
    # FILE OPERATIONS & EXPORT
    # =========================================================================

    def _on_open_file(self):
        file_path = filedialog.askopenfilename(
            title="Open Minemesis Run Data",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if file_path:
            self.load_run_file(file_path)

    def load_run_file(self, file_path: str):
        try:
            run_data = RunData.load_from_json(file_path)
            self.seed_var.set(str(run_data.seed))
            self.years_var.set(str(run_data.years))
            self.toggle_religion.set(run_data.toggles.get("religion", True))
            self.toggle_lore.set(run_data.toggles.get("lore", True))
            self.set_run_data(run_data)
            self.status_label.config(text=f"Loaded: {os.path.basename(file_path)}")
        except Exception as ex:
            messagebox.showerror("Load Failed", f"Could not load run file:\n{ex}")

    def _on_save_file(self):
        if not self.run_data:
            messagebox.showwarning("No Data", "No simulation run data available to save.")
            return
        file_path = filedialog.asksaveasfilename(
            title="Save Minemesis Run Data",
            defaultextension=".json",
            initialfile=f"minemesis_run_seed{self.run_data.seed}.json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if file_path:
            try:
                self.run_data.save_to_json(file_path)
                messagebox.showinfo("Saved", f"Run data successfully saved to:\n{file_path}")
            except Exception as ex:
                messagebox.showerror("Save Failed", f"Could not save file:\n{ex}")

    def _on_export_text(self):
        if not self.run_data or not self.event_log_proxy:
            messagebox.showwarning("No Data", "No simulation run data available to export.")
            return
        file_path = filedialog.asksaveasfilename(
            title="Export Story as Plain Text",
            defaultextension=".txt",
            initialfile=f"chronicle_seed{self.run_data.seed}.txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if file_path:
            try:
                txt = export_story_to_text(
                    events=self.event_log_proxy.all_events(),
                    event_log=self.event_log_proxy,
                    characters=self.run_data.characters,
                    settlements=self.run_data.settlements,
                    title=f"Minemesis Chronicle - Seed {self.run_data.seed}",
                )
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(txt)
                messagebox.showinfo("Exported", f"Story text successfully exported to:\n{file_path}")
            except Exception as ex:
                messagebox.showerror("Export Failed", f"Could not export text:\n{ex}")

    def _on_export_html(self):
        if not self.run_data or not self.event_log_proxy:
            messagebox.showwarning("No Data", "No simulation run data available to export.")
            return
        file_path = filedialog.asksaveasfilename(
            title="Export Story as HTML Document",
            defaultextension=".html",
            initialfile=f"chronicle_seed{self.run_data.seed}.html",
            filetypes=[("HTML Files", "*.html"), ("All Files", "*.*")],
        )
        if file_path:
            try:
                html_doc = export_story_to_html(
                    events=self.event_log_proxy.all_events(),
                    event_log=self.event_log_proxy,
                    characters=self.run_data.characters,
                    settlements=self.run_data.settlements,
                    title=f"Minemesis Chronicle - Seed {self.run_data.seed}",
                )
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html_doc)
                messagebox.showinfo("Exported", f"Story HTML successfully exported to:\n{file_path}")
            except Exception as ex:
                messagebox.showerror("Export Failed", f"Could not export HTML:\n{ex}")

    def _on_close(self):
        self.root.destroy()
