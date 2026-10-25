"""
Centralized logging and visual error banners for Viewer V2.
Logs tracebacks to viewer_errors.log and renders visible banners.
"""

from __future__ import annotations
import logging
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk
import traceback
from typing import Optional

from viewer.core.settings import get_appdata_dir

LOG_FILE = get_appdata_dir() / "viewer_errors.log"

logger = logging.getLogger("viewer")
logger.setLevel(logging.INFO)

if not logger.handlers:
    # File handler
    try:
        fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
        fh.setLevel(logging.INFO)
        fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(ch)


def log_error(msg: str, exc: Optional[BaseException] = None) -> None:
    if exc:
        logger.error(f"{msg}: {exc}\n{traceback.format_exc()}")
    else:
        logger.error(msg)


def create_error_banner(
    parent: tk.Widget,
    error_msg: str,
    details: Optional[str] = None,
) -> tk.Frame:
    """Creates a visible modern red banner inside a tab or container."""
    banner = tk.Frame(parent, bg="#7f1d1d", padx=10, pady=8, highlightbackground="#b91c1c", highlightthickness=1)
    
    header_frame = tk.Frame(banner, bg="#7f1d1d")
    header_frame.pack(fill=tk.X, expand=True)

    icon_lbl = tk.Label(header_frame, text="⚠", font=("Segoe UI", 12, "bold"), fg="#fca5a5", bg="#7f1d1d")
    icon_lbl.pack(side=tk.LEFT, padx=(0, 6))

    msg_lbl = tk.Label(header_frame, text=error_msg, font=("Segoe UI", 10, "bold"), fg="#fee2e2", bg="#7f1d1d", anchor="w")
    msg_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

    if details:
        def toggle_details():
            if details_txt.winfo_viewable():
                details_txt.pack_forget()
                btn.config(text="View Details ▼")
            else:
                details_txt.pack(fill=tk.X, pady=(6, 0))
                btn.config(text="Hide Details ▲")

        btn = tk.Button(
            header_frame,
            text="View Details ▼",
            command=toggle_details,
            font=("Segoe UI", 8),
            bg="#991b1b",
            fg="#fef2f2",
            relief=tk.FLAT,
            padx=6,
            pady=2,
        )
        btn.pack(side=tk.RIGHT)

        details_txt = tk.Text(
            banner,
            height=4,
            bg="#450a0a",
            fg="#fca5a5",
            font=("Consolas", 8),
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=4,
            pady=4,
        )
        details_txt.insert(tk.END, details)
        details_txt.config(state=tk.DISABLED)

    return banner
