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


def validate_tab_data_non_empty(snapshot: RunData) -> dict[str, Any]:
    """
    Validates that every tab in the viewer data contract has non-empty, renderable content:
    - Story: > 0 lines
    - Why: returns a chain for the first event with causes
    - Threads: >= 1 when feuds exist (or a message saying none)
    - People & Truth: shows >= 1 character and a Truth vs Belief entry for a wrongful feud
    - World & Census: rows for every settlement-year
    - Books: lists >= 1 book and renders page 1
    - Religion: lists >= 1 religion
    """
    proxy = snapshot.get_event_log_proxy()
    events = proxy.all_events()

    # 1. Story
    assert len(events) > 0, "Story data source has 0 events"
    story_sentences = [
        format_event_sentence(e, snapshot.characters, snapshot.settlements, snapshot.religions)
        for e in events[:20]
    ]
    assert len(story_sentences) > 0, "Story generated 0 sentences"

    # 2. Why (Causality)
    first_with_causes = next((e for e in events if getattr(e, "causes", None)), None)
    assert first_with_causes is not None, "Why tab validation: No events with causes found"
    because_clause = format_because_clause(first_with_causes, proxy, snapshot.characters, snapshot.settlements, snapshot.religions)
    assert because_clause is not None and len(because_clause) > 5, "Why tab validation: Empty causal chain"

    # 3. Threads
    feud_events = [e for e in events if e.type.value in ("Feud", "FeudBegins", "Raid")]
    threads = extract_story_threads(proxy, snapshot.characters, snapshot.settlements, min_events=2)
    if feud_events:
        assert len(threads) >= 1, "Threads tab validation: Feuds exist but 0 story threads extracted"

    # 4. People & Truth
    assert len(snapshot.characters) >= 1, "People tab validation: 0 characters found"
    wrongful_entries = [e for e in getattr(snapshot, "epistemic_ledger", []) if e.get("is_wrongful")]
    assert len(wrongful_entries) >= 1, "People tab validation: Expected >= 1 Truth vs Belief entry for wrongful feud"

    # 5. World & Census
    assert len(snapshot.census) == snapshot.years, f"World & Census: Expected {snapshot.years} years, got {len(snapshot.census)}"
    settlement_count = len(snapshot.settlements)
    for c_entry in snapshot.census:
        assert len(c_entry.get("populations", {})) == settlement_count, "Census missing settlement population rows"

    # 6. Books
    assert len(snapshot.books) >= 1, "Books tab validation: 0 books in snapshot"
    first_book_id = snapshot.books[0]["id"]
    book_pages = snapshot.get_book_pages(first_book_id)
    assert len(book_pages) >= 1, "Books tab validation: First book rendered 0 pages"
    assert len(book_pages[0].strip()) > 10, "Books tab validation: Page 1 is empty"

    # 7. Religion
    assert len(snapshot.religions) >= 1, "Religion tab validation: 0 religions in snapshot"

    return {
        "story_events": len(events),
        "why_first_cause": first_with_causes.id,
        "threads": len(threads),
        "characters": len(snapshot.characters),
        "wrongful_feuds": len(wrongful_entries),
        "census_years": len(snapshot.census),
        "books": len(snapshot.books),
        "religions": len(snapshot.religions),
    }


def run_negative_control_validation(snapshot: RunData) -> None:
    """Negative control: proves validate_tab_data_non_empty strictly fails when a data source is empty."""
    import copy
    bad_snap = copy.copy(snapshot)
    bad_snap.books = []
    failed = False
    try:
        validate_tab_data_non_empty(bad_snap)
    except AssertionError:
        failed = True
    assert failed, "Negative control failed: validator did not catch empty books data source!"


def run_selftest() -> int:
    print(f"=== Minemesis Story Viewer Self-Test [{BUILD_TAG}] ===")
    try:
        from minemesis.systems.simulation import Simulation
        from minemesis.core.seed import SeedPair
        from viewer.model import build_run_snapshot

        print("1. Running headless simulation (Seed 42, 5 Years)...")
        sim5 = Simulation(seed=42, enable_religion=True, enable_lore=True)
        sim5.run_years(5)
        events = sim5.event_log.all_events()
        print(f"   [OK] Generated {len(events)} events across {sim5.current_year} years.")
        assert len(events) > 10, f"Expected >10 events, got {len(events)}"

        print("2. Converting to RunData model...")
        run_data = RunData.from_simulation(sim5, years=5, build_info={"tag": BUILD_TAG, "commit": BUILD_COMMIT})
        assert len(run_data.events) == len(events), "Event count mismatch in RunData"
        print(f"   [OK] RunData captured {len(run_data.characters)} characters and {len(run_data.settlements)} settlements.")

        print("3. Validating formatting and asserting NO raw IDs appear in prose...")
        raw_pattern = re.compile(r"\b(char_\d+|set_[a-z0-9_]+|rel_\w+)\b")
        for e in run_data.get_event_log_proxy().all_events():
            prose = format_event_sentence(e, run_data.characters, run_data.settlements, run_data.religions)
            matches = raw_pattern.findall(prose)
            assert not matches, f"Raw ID leaked into prose: {matches} in '{prose}'"

            bc = format_because_clause(e, run_data.get_event_log_proxy(), run_data.characters, run_data.settlements, run_data.religions)
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

        print("7. Testing SeedPair and WorldSpec in RunData...")
        assert run_data.seed_pair is not None, "Expected seed_pair in RunData"
        assert run_data.pair_code is not None, "Expected pair_code in RunData"
        assert run_data.world_spec is not None, "Expected world_spec in RunData"
        print(f"   [OK] Verified SeedPair {run_data.pair_code} and WorldSpec ({len(run_data.world_spec.get('settlements', []))} settlements).")

        print("8. Running 20-Year Multi-Tab Contract Validation (SeedPair 42)...")
        seed_pair_20 = SeedPair.from_legacy(42)
        sim20 = Simulation(seed=seed_pair_20, enable_religion=True, enable_lore=True)
        sim20.run_years(20)
        snap20 = build_run_snapshot(sim20, years=20, build_info={"tag": BUILD_TAG, "commit": BUILD_COMMIT})
        tab_metrics = validate_tab_data_non_empty(snap20)
        print(f"   [OK] All 7 tabs verified non-empty: {tab_metrics}")

        print("9. Running Negative Control (ensuring empty data source triggers assertion failure)...")
        run_negative_control_validation(snap20)
        print("   [OK] Negative control verified: deliberate empty tab data strictly caught.")

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
