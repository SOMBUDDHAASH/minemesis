"""
Tests for architectural boundary rules and determinism in Minemesis Story Viewer.

Boundary Rule:
- The viewer is a read-only presentation layer.
- `minemesis` MUST NEVER import `viewer`.
- Negative control included: proves AST checker detects forbidden imports.
"""

from __future__ import annotations
import ast
import hashlib
import json
import os
import pytest

from minemesis.systems.simulation import Simulation
from viewer.model import RunData


def find_viewer_imports_in_source(source_code: str) -> list[str]:
    """Inspects Python source AST and returns any imports referencing 'viewer'."""
    tree = ast.parse(source_code)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "viewer" or alias.name.startswith("viewer."):
                    violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "viewer" or (node.module and node.module.startswith("viewer.")):
                violations.append(node.module)
    return violations


def test_minemesis_package_never_imports_viewer():
    """Scans all Python source files in minemesis/ to verify strict unidirectional dependency."""
    minemesis_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "minemesis"))
    assert os.path.exists(minemesis_root), f"Minemesis root not found at {minemesis_root}"

    all_violations = {}
    for root, _, files in os.walk(minemesis_root):
        for f in files:
            if f.endswith(".py"):
                fpath = os.path.join(root, f)
                with open(fpath, "r", encoding="utf-8") as py_file:
                    content = py_file.read()
                violations = find_viewer_imports_in_source(content)
                if violations:
                    rel_path = os.path.relpath(fpath, minemesis_root)
                    all_violations[rel_path] = violations

    assert not all_violations, f"Strict boundary rule violated: minemesis imports viewer in: {all_violations}"


def test_negative_control_viewer_import_detector():
    """Negative control: proves find_viewer_imports_in_source catches forbidden imports."""
    bad_code_1 = "import viewer.app\nprint('hello')"
    assert find_viewer_imports_in_source(bad_code_1) == ["viewer.app"]

    bad_code_2 = "from viewer.model import RunData\n"
    assert find_viewer_imports_in_source(bad_code_2) == ["viewer.model"]

    clean_code = "import os\nfrom minemesis.core.types import EventType\n"
    assert find_viewer_imports_in_source(clean_code) == []


def test_simulation_digest_identical_with_and_without_viewer():
    """Verifies that instantiating simulation via viewer tools does not alter simulation determinism."""
    # Run 1: Direct simulation
    sim1 = Simulation(seed=42, enable_religion=True, enable_lore=True)
    sim1.run_years(5)
    evs1 = [e.to_dict() for e in sim1.event_log.all_events()]
    digest1 = hashlib.sha256(json.dumps(evs1, sort_keys=True).encode("utf-8")).hexdigest()

    # Run 2: Simulation wrapped into RunData
    sim2 = Simulation(seed=42, enable_religion=True, enable_lore=True)
    sim2.run_years(5)
    run_data = RunData.from_simulation(sim2, years=5)
    evs2 = run_data.events
    digest2 = hashlib.sha256(json.dumps(evs2, sort_keys=True).encode("utf-8")).hexdigest()

    assert digest1 == digest2, "Viewer integration corrupted simulation determinism"
