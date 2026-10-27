"""
Minemesis Standalone Game Engine Build and Packaging Script (Stage E0 Spike).
Compiles engine/__main__.py into Minemesis.exe using PyInstaller.
"""

from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))


def run_cmd(cmd: list[str], desc: str) -> None:
    print(f"\n[BUILD STEP] {desc}...")
    print(f"Command: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR))
    if res.returncode != 0:
        print(f"\n[ERROR] Step failed with return code {res.returncode}:")
        print(res.stdout)
        print(res.stderr)
        sys.exit(res.returncode)
    else:
        print(f"[SUCCESS] {desc} completed.")
        if res.stdout:
            lines = res.stdout.strip().split("\n")
            print("\n".join(lines[-6:]))


def build_engine_exe() -> Path:
    dist_dir = ROOT_DIR / "dist"
    releases_dir = ROOT_DIR / "releases"
    releases_dir.mkdir(parents=True, exist_ok=True)

    base_args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
        "--exclude-module", "pandas",
        "--exclude-module", "pytest",
        "--exclude-module", "unittest",
        "--exclude-module", "pydoc",
        "--exclude-module", "curses",
        "--exclude-module", "idlelib",
        "--collect-all", "moderngl",
        "--collect-all", "glcontext",
        "--collect-all", "glfw",
        "--add-data", f"engine{os.pathsep}engine",
        "--add-data", f"data{os.pathsep}data",
        "--onefile",
        "--name", "Minemesis",
        "engine/__main__.py",
    ]

    run_cmd(base_args, "Compiling Minemesis.exe (OpenGL 3.3 Core Standalone)")

    built_exe = dist_dir / "Minemesis.exe"
    target_exe = releases_dir / "Minemesis.exe"
    if built_exe.exists():
        shutil.copy2(built_exe, target_exe)
        print(f"[SUCCESS] Copied Minemesis.exe to: {target_exe}")
    else:
        print(f"[ERROR] Target {built_exe} not found!")
        sys.exit(1)

    return target_exe


def verify_engine_exe(exe_path: Path) -> None:
    print("\n[VERIFICATION] Testing Minemesis.exe execution...")

    # 1. Version check
    t0 = time.perf_counter()
    res_ver = subprocess.run([str(exe_path), "--version"], capture_output=True, text=True, timeout=15)
    t_ver = time.perf_counter() - t0
    print(f"[*] Startup Time (--version): {t_ver:.3f} s")
    print(f"[*] Output: {res_ver.stdout.strip()}")
    assert res_ver.returncode == 0, f"Version check failed: {res_ver.stderr}"

    # 2. Benchmark check (Stage E1 world meshing & rendering, 30 frames, headless)
    shot_path = ROOT_DIR / "reports" / "screens" / "stage_e1_exe_benchmark.png"
    t1 = time.perf_counter()
    cmd_bench = [str(exe_path), "--benchmark", "30", "--headless", "--screenshot", str(shot_path)]
    res_bench = subprocess.run(cmd_bench, capture_output=True, text=True, timeout=60)
    t_bench = time.perf_counter() - t1
    print(f"[*] Benchmark 30-frame run time: {t_bench:.3f} s")
    print(res_bench.stdout)
    assert res_bench.returncode == 0, f"Benchmark failed: {res_bench.stderr}"
    assert shot_path.exists(), f"Screenshot {shot_path} was not created!"
    print(f"[SUCCESS] Stage E1 Engine Executable Verified 100% Operational!")


def main() -> None:
    print("=====================================================")
    print(" Minemesis Standalone Engine Packaging Spike (E0)   ")
    print("=====================================================")
    exe = build_engine_exe()
    verify_engine_exe(exe)


if __name__ == "__main__":
    main()
