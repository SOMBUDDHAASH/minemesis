"""
Entropy Confinement & Purity Tests for Milestone 0.5.3.

Standing Rule:
- All non-determinism enters strictly through `minemesis.core.seed.new_game()`.
- No simulation, generation, or engine module may import `secrets`, `os.urandom`,
  `time`, `uuid`, or the Python standard library `random` module.
- Includes positive enforcement and negative controls proving forbidden imports fail.
"""

from __future__ import annotations
import ast
import os
import pytest


FORBIDDEN_MODULES = {"secrets", "random", "time", "uuid"}
ALLOWED_ENTROPY_FILES = {"seed.py"}  # strictly minemesis/core/seed.py


def check_source_for_entropy_imports(source: str, filename: str) -> list[str]:
    """Inspects AST of a Python file and returns list of forbidden entropy imports."""
    if os.path.basename(filename) in ALLOWED_ENTROPY_FILES:
        return []

    tree = ast.parse(source, filename=filename)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_root = alias.name.split(".")[0]
                if mod_root in FORBIDDEN_MODULES:
                    violations.append(f"line {node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod_root = node.module.split(".")[0]
                if mod_root in FORBIDDEN_MODULES:
                    violations.append(f"line {node.lineno}: from {node.module} import ...")
                if node.module == "os":
                    for alias in node.names:
                        if alias.name == "urandom":
                            violations.append(f"line {node.lineno}: from os import urandom")
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "os" and node.attr == "urandom":
                violations.append(f"line {node.lineno}: os.urandom access")
    return violations


def test_package_wide_entropy_confinement():
    """Verifies that no file under minemesis/ (excluding seed.py) imports forbidden entropy sources."""
    package_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    all_violations: dict[str, list[str]] = {}

    for root, _, files in os.walk(package_root):
        # Exclude tests directory from strict runtime check
        if os.path.basename(root) == "tests" or "tests" in root.split(os.sep):
            continue
        for f in files:
            if f.endswith(".py"):
                fpath = os.path.join(root, f)
                with open(fpath, "r", encoding="utf-8") as py_file:
                    content = py_file.read()
                viols = check_source_for_entropy_imports(content, fpath)
                if viols:
                    rel_p = os.path.relpath(fpath, package_root)
                    all_violations[rel_p] = viols

    assert not all_violations, f"Entropy confinement violated! Forbidden imports found in: {all_violations}"


def test_negative_control_entropy_detector():
    """Negative control: proves check_source_for_entropy_imports detects forbidden imports."""
    bad_code_1 = "import random\nx = random.randint(1, 10)"
    assert len(check_source_for_entropy_imports(bad_code_1, "dummy.py")) == 1

    bad_code_2 = "from secrets import token_bytes\nx = token_bytes(16)"
    assert len(check_source_for_entropy_imports(bad_code_2, "dummy.py")) == 1

    bad_code_3 = "import time\nt = time.time()"
    assert len(check_source_for_entropy_imports(bad_code_3, "dummy.py")) == 1

    bad_code_4 = "from os import urandom\nx = urandom(4)"
    assert len(check_source_for_entropy_imports(bad_code_4, "dummy.py")) == 1

    clean_code = "from minemesis.core.rng import keyed_hash_int\nx = keyed_hash_int(42, 'test', 0, 0)"
    assert len(check_source_for_entropy_imports(clean_code, "dummy.py")) == 0
