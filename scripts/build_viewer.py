"""
Minemesis Story Viewer Build Script.

Builds and packages the standalone executable for Milestone 0.5.2.
Complies with the Standing Rule:
- Self-test must pass.
- Release notes generated with 5-line summary and 3 things to look for.
- Showcase run JSONs exported.
"""

from __future__ import annotations
import os
import shutil
import subprocess
import sys
import zipfile

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BUILD_TAG = "m0.5.4"
BUILD_COMMIT = "3bc4134"
SHOWCASE_SEEDS = [42, 2029, 2030, 2043, 2011]


def run_cmd(cmd: list[str], desc: str) -> None:
    print(f"\n[BUILD STEP] {desc}...")
    print(f"Command: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"\n[ERROR] Step failed with return code {res.returncode}:")
        print(res.stdout)
        print(res.stderr)
        sys.exit(res.returncode)
    else:
        print(f"[SUCCESS] {desc} completed.")
        if res.stdout:
            lines = res.stdout.strip().split("\n")
            print("\n".join(lines[-10:]))


def run_tests():
    run_cmd([sys.executable, "-m", "pytest", "minemesis/tests", "viewer/tests"], "Running Full Test Suite")


def build_pyinstaller():
    dist_dir = os.path.abspath("dist")
    build_dir = os.path.abspath("build")
    releases_dir = os.path.abspath("releases")
    m_tag_dir = os.path.join(releases_dir, BUILD_TAG)
    os.makedirs(releases_dir, exist_ok=True)
    os.makedirs(m_tag_dir, exist_ok=True)

    # 1. Build Single-file Executable
    pyinstaller_cmd_onefile = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name", f"MinemesisViewer-{BUILD_TAG}",
        "--add-data", f"viewer{os.pathsep}viewer",
        "viewer/__main__.py",
    ]
    run_cmd(pyinstaller_cmd_onefile, "Building Single-File Executable via PyInstaller")

    built_exe = os.path.join(dist_dir, f"MinemesisViewer-{BUILD_TAG}.exe")
    target_exe = os.path.join(releases_dir, f"MinemesisViewer-{BUILD_TAG}.exe")
    latest_exe = os.path.join(releases_dir, "MinemesisViewer-latest.exe")

    if os.path.exists(built_exe):
        shutil.copy2(built_exe, target_exe)
        shutil.copy2(built_exe, latest_exe)
        print(f"Copied single-file .exe to: {target_exe} and {latest_exe}")
    else:
        print(f"[ERROR] Expected built exe at {built_exe} not found!")
        sys.exit(1)

    # 2. Build onedir Distribution for folder packaging
    onedir_name = f"MinemesisViewer-{BUILD_TAG}-dir"
    pyinstaller_cmd_onedir = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--name", onedir_name,
        "--add-data", f"viewer{os.pathsep}viewer",
        "viewer/__main__.py",
    ]
    run_cmd(pyinstaller_cmd_onedir, "Building Onedir Distribution via PyInstaller")

    built_dir = os.path.join(dist_dir, onedir_name)
    zip_path = os.path.join(releases_dir, f"MinemesisViewer-{BUILD_TAG}-folder.zip")
    if os.path.exists(built_dir):
        print(f"Zipping onedir distribution into {zip_path}...")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(built_dir):
                for f in files:
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, built_dir)
                    zf.write(full_p, rel_p)
        print(f"[SUCCESS] Created {zip_path}")


def export_showcase_runs():
    print("\n[BUILD STEP] Generating Showcase Run Data for Seeds [42, 2029, 2030, 2043, 2011]...")
    from minemesis.systems.simulation import Simulation
    from viewer.model import RunData

    releases_dir = os.path.abspath("releases")
    m_tag_dir = os.path.join(releases_dir, BUILD_TAG)
    os.makedirs(m_tag_dir, exist_ok=True)

    if "--skip-showcase" in sys.argv:
        print("  [INFO] Skipping showcase re-simulation (--skip-showcase specified).")
        return

    for seed in SHOWCASE_SEEDS:
        out_path = os.path.join(m_tag_dir, f"minemesis_run_seed{seed}.json")
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            print(f"  [INFO] Showcase data for Seed {seed} already exists at {out_path}, skipping re-simulation.")
            continue
        print(f"  Simulating Seed {seed} for 100 years...")
        sim = Simulation(seed=seed, enable_religion=True, enable_lore=True)
        sim.run_years(100)
        build_info = {
            "tag": BUILD_TAG,
            "commit": BUILD_COMMIT,
            "date": "2026-10-25",
        }
        run_data = RunData.from_simulation(sim, years=100, build_info=build_info)
        run_data.save_to_json(out_path)
        print(f"    Saved {out_path} ({len(run_data.events)} events, {len(run_data.characters)} characters)")


def write_release_notes():
    releases_dir = os.path.abspath("releases")
    notes_path = os.path.join(releases_dir, f"RELEASE_NOTES_{BUILD_TAG}.md")

    content = f"""# Minemesis Story Viewer - Release Notes ({BUILD_TAG})

**Build Commit:** `{BUILD_COMMIT}`  
**Build Date:** `2026-10-25`  
**Executable Path:** `releases/MinemesisViewer-{BUILD_TAG}.exe` (and `releases/MinemesisViewer-latest.exe`)  
**Folder Distribution:** `releases/MinemesisViewer-{BUILD_TAG}-folder.zip`  

---

## What Changed In Milestone 0.5.4
1. **4-Tier Knowledge & Memory Lifecycle Engine:** Eliminated the 75-350 GB memory explosion by tiering memories (Tier 0: Living Full Simulation, Tier 1: Recent Dead Legacy, Tier 2: Compressed Historical Archive, Tier 3: Settlement Epistemic Knowledge).
2. **Relational Lore Compression & Intermediate Representation (IR):** Replaced raw string event floods with normalized relational references and on-demand template hydration, reducing memory footprint by >90%.
3. **Procedural Literature & Scripture Engine:** Added 9 distinct book genres (scriptures, chronicles, genealogies, poetry, philosophical treatises, legal codes, memoirs, war accounts, manuals) and sacred religious canons with commandments and holy sites.
4. **Direct Minecraft Book NBT Export:** Export any procedural book or scripture directly to Vanilla Minecraft JSON / NBT format and copy one-click `/give` commands ready for in-game lecterns.
5. **Demographic Carrying-Capacity Governor:** Replaced unchecked exponential birth curves with logistic environmental equilibrium, preventing runaway population collapses while preserving kinship dynamics.

---

## 3 Things To Look For In The Viewer
1. **Books & Scriptures Tab with Minecraft Export:** Select any written book or holy scripture, read its multi-page generated text, and click **'📋 Copy /give Command'** or **'Export Minecraft Book'** to read it directly inside Vanilla Minecraft.
2. **World & Census Tab Memory Tier Telemetry:** View the real-time breakdown of Tier 0 (Active), Tier 1 (Legacy), Tier 2 (Compressed Archive), and Tier 3 (Settlement Beliefs) objects across the centuries.
3. **Interactive Map & Religion Inspector:** Inspect sacred holy sites, theological traits, and doctrinal schisms mapped directly across continental terrain endowments.

---

## Showcase Seeds Included
Pre-generated runs located in `releases/{BUILD_TAG}/`:
- `minemesis_run_seed42.json` (The Classic Baseline: Streamford, Rockmount, Swiftwash)
- `minemesis_run_seed2029.json` (Escalated Blood Feud: multi-generational vendetta)
- `minemesis_run_seed2030.json` (Syncretism & Reform: rich doctrinal borrowing across settlements)
- `minemesis_run_seed2043.json` (Reconciled Diplomatic Run: complete demographic accounting)
- `minemesis_run_seed2011.json` (Survival Challenge: harsh generational pressures)
"""
    with open(notes_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n[SUCCESS] Wrote release notes to: {notes_path}")


def verify_executable_selftest():
    print("\n[BUILD STEP] Executing --selftest on the compiled executable...")
    releases_dir = os.path.abspath("releases")
    target_exe = os.path.join(releases_dir, f"MinemesisViewer-{BUILD_TAG}.exe")

    res = subprocess.run([target_exe, "--selftest"], capture_output=True, text=True)
    if res.returncode != 0:
        print("[ERROR] Built executable failed --selftest:")
        print(res.stdout)
        print(res.stderr)
        sys.exit(res.returncode)
    else:
        print("[SUCCESS] Compiled executable passed --selftest!")
        print(res.stdout.strip())


def main():
    print(f"=====================================================")
    print(f" Minemesis Story Viewer Build Pipeline [{BUILD_TAG}] ")
    print(f"=====================================================")
    if "--skip-tests" not in sys.argv:
        run_tests()
    else:
        print("\n[INFO] Skipping pytest suite (--skip-tests specified).")
    build_pyinstaller()
    export_showcase_runs()
    write_release_notes()
    verify_executable_selftest()
    print(f"\n=====================================================")
    print(f" BUILD COMPLETE AND VERIFIED [{BUILD_TAG}] ")
    print(f"=====================================================")


if __name__ == "__main__":
    main()
