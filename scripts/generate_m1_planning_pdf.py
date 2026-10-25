"""
Milestone 1 Technical Specification & Planning PDF Generator for Project Minemesis.
Reads reports/minemesis_m1_planning.html and invokes headless Microsoft Edge to render
a publication-grade 8-page PDF report.
"""

from __future__ import annotations
import os
import shutil
import subprocess
import sys

def main():
    in_html = os.path.abspath("reports/minemesis_m1_planning.html")
    out_pdf_root = os.path.abspath("Minemesis_Milestone1_Planning_Report.pdf")
    out_pdf_reports = os.path.abspath("reports/Minemesis_Milestone1_Planning_Report.pdf")
    artifact_dir = r"C:\Users\Sombuddha Ash\.gemini\antigravity\brain\f6297504-bc94-4940-ba31-52272d1ae3a9"
    out_pdf_artifact = os.path.join(artifact_dir, "Minemesis_Milestone1_Planning_Report.pdf")

    if not os.path.exists(in_html):
        print(f"Error: {in_html} does not exist!")
        sys.exit(1)

    edge_path = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"

    edge_cmd = [
        edge_path,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={out_pdf_root}",
        in_html,
    ]
    print(f"Rendering PDF via Microsoft Edge from {in_html}...")
    subprocess.run(edge_cmd, check=True)
    print(f"PDF generated successfully at {out_pdf_root}")

    shutil.copyfile(out_pdf_root, out_pdf_reports)
    print(f"PDF copied to {out_pdf_reports}")

    os.makedirs(artifact_dir, exist_ok=True)
    shutil.copyfile(out_pdf_root, out_pdf_artifact)
    print(f"PDF copied to artifact directory at {out_pdf_artifact}")

if __name__ == "__main__":
    main()
