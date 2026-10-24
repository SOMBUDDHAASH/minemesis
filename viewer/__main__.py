"""
CLI Entry Point for Minemesis Story Viewer.

Supports:
- GUI launch (default)
- --version : prints build tag, commit, timestamp, and seed 42 5-year digest
- --selftest: runs headless validation of simulation, formatting, and causal integrity
- --open <file>: loads a saved run JSON directly into the viewer
"""

from __future__ import annotations
import argparse
import hashlib
import json
import multiprocessing
import os
import re
import sys
import tkinter as tk

from viewer.app import BUILD_TAG, BUILD_COMMIT, BUILD_TIME, StoryViewerApp
from viewer.model import RunData, EventProxy, EventLogProxy
from viewer.formatter import format_event_sentence, format_because_clause
from viewer.threads import extract_story_threads
from viewer.export import export_story_to_text, export_story_to_html


def compute_seed42_5yr_digest() -> str:
    from minemesis.systems.simulation import Simulation
    sim = Simulation(seed=42, enable_religion=True, enable_lore=True)
    sim.run_years(5)
    ev_dicts = [e.to_dict() for e in sim.event_log.all_events()]
    json_bytes = json.dumps(ev_dicts, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


def run_selftest() -> int:
    print(f"=== Minemesis Story Viewer Self-Test [{BUILD_TAG}] ===")
    try:
        from minemesis.systems.simulation import Simulation

        print("1. Running headless simulation (Seed 42, 5 Years)...")
        sim = Simulation(seed=42, enable_religion=True, enable_lore=True)
        sim.run_years(5)
        events = sim.event_log.all_events()
        print(f"   [OK] Generated {len(events)} events across {sim.current_year} years.")
        assert len(events) > 10, f"Expected >10 events, got {len(events)}"

        print("2. Converting to RunData model...")
        run_data = RunData.from_simulation(sim, years=5, build_info={"tag": BUILD_TAG, "commit": BUILD_COMMIT})
        assert len(run_data.events) == len(events), "Event count mismatch in RunData"
        print(f"   [OK] RunData captured {len(run_data.characters)} characters and {len(run_data.settlements)} settlements.")

        print("3. Validating formatting and asserting NO raw IDs appear in prose...")
        raw_pattern = re.compile(r"\b(char_\d+|set_[a-z0-9_]+)\b")
        for e in run_data.get_event_log_proxy().all_events():
            prose = format_event_sentence(e, run_data.characters, run_data.settlements)
            matches = raw_pattern.findall(prose)
            assert not matches, f"Raw ID leaked into prose: {matches} in '{prose}'"

            bc = format_because_clause(e, run_data.get_event_log_proxy(), run_data.characters, run_data.settlements)
            if bc:
                bc_matches = raw_pattern.findall(bc)
                assert not bc_matches, f"Raw ID leaked into because clause: {bc_matches} in '{bc}'"
        print("   [OK] All event sentences and because clauses formatted with zero raw ID leaks.")

        print("4. Testing Story Threads extraction...")
        threads = extract_story_threads(run_data.get_event_log_proxy(), run_data.characters, run_data.settlements, min_events=2)
        print(f"   [OK] Discovered {len(threads)} narrative threads.")

        print("5. Testing JSON serialization and round-trip integrity...")
        tmp_json = run_data.to_dict()
        restored = RunData.from_dict(tmp_json)
        assert restored.seed == 42, "Restored seed mismatch"
        assert len(restored.events) == len(run_data.events), "Restored event count mismatch"
        print("   [OK] JSON serialization round-trip verified.")

        print("6. Testing TXT and HTML export pipelines...")
        txt_out = export_story_to_text(run_data.get_event_log_proxy().all_events(), run_data.get_event_log_proxy(), run_data.characters, run_data.settlements)
        assert "MINEMESIS GENERATED WORLD CHRONICLE" in txt_out
        html_out = export_story_to_html(run_data.get_event_log_proxy().all_events(), run_data.get_event_log_proxy(), run_data.characters, run_data.settlements)
        assert "<!DOCTYPE html>" in html_out
        print("   [OK] Chronicle text and HTML generation successful.")

        print(f"\nALL SELF-TEST CHECKS PASSED. Viewer is sound and ready.")
        return 0
    except Exception as ex:
        print(f"\n[SELFTEST FAILED]: {ex}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(description=f"Minemesis Story Viewer ({BUILD_TAG})")
    parser.add_argument("--version", action="store_true", help="Print version, commit, build time, and digest, then exit")
    parser.add_argument("--selftest", action="store_true", help="Run headless self-tests and exit with 0 on success")
    parser.add_argument("--open", type=str, metavar="FILE", help="Open a minemesis_run.json file on launch")

    args = parser.parse_args()

    if args.version:
        digest = compute_seed42_5yr_digest()
        print(f"Minemesis Story Viewer")
        print(f"Release Tag   : {BUILD_TAG}")
        print(f"Commit Hash   : {BUILD_COMMIT}")
        print(f"Build Date    : {BUILD_TIME}")
        print(f"Seed 42 5Y SHA: {digest}")
        sys.exit(0)

    if args.selftest:
        code = run_selftest()
        sys.exit(code)

    # If on Windows and launching GUI (not CLI mode), hide console window
    if sys.platform == "win32":
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
        except Exception:
            pass

    # Launch GUI
    root = tk.Tk()
    app = StoryViewerApp(root, initial_file=args.open)
    root.mainloop()


if __name__ == "__main__":
    main()
