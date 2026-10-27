"""
In-Game Physical Book Reader from Simulation Run Database.
"""

from __future__ import annotations
import json
import sqlite3
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional


class BookReader:
    """Manages physical book interaction and in-game page turning."""

    def __init__(self) -> None:
        self.is_reading: bool = False
        self.active_book: Optional[Dict[str, Any]] = None
        self.current_page: int = 0
        self.pages: List[str] = []

    def open_book(self, book_data: Dict[str, Any]) -> None:
        self.active_book = book_data
        self.is_reading = True
        self.current_page = 0

        # Unpack pages
        raw_pages = book_data.get("pages", [])
        if isinstance(raw_pages, list):
            self.pages = [str(p) for p in raw_pages]
        elif isinstance(raw_pages, (bytes, bytearray)):
            try:
                decomp = zlib.decompress(raw_pages).decode("utf-8")
                try:
                    parsed = json.loads(decomp)
                    if isinstance(parsed, list):
                        self.pages = [str(x) for x in parsed]
                    else:
                        self.pages = [str(parsed)]
                except Exception:
                    self.pages = decomp.split("\n\n--- PAGE ---\n\n")
            except Exception:
                self.pages = ["Error decompressing book pages."]
        else:
            self.pages = [str(raw_pages)]

        if not self.pages:
            self.pages = ["(This tome contains only blank parchment.)"]

    def close_book(self) -> None:
        self.is_reading = False
        self.active_book = None
        self.pages.clear()
        self.current_page = 0

    def next_page(self) -> None:
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1

    def prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1

    def get_current_page_text(self) -> List[str]:
        if not self.is_reading or not self.active_book:
            return []

        title = self.active_book.get("title", "Untitled Manuscript")
        author = self.active_book.get("author_name", "Unknown Scribe")
        year = self.active_book.get("year_written", 1)

        lines = [
            f"=== {title.upper()} ===",
            f"Penned by {author} in Year {year}",
            f"Page {self.current_page + 1} of {len(self.pages)}",
            "--------------------------------------------------",
        ]

        page_content = self.pages[self.current_page]
        for l in page_content.split("\n"):
            lines.append(l)

        lines.append("--------------------------------------------------")
        lines.append("[N] Next Page   [P] Previous Page   [Esc] Put Down Book")
        return lines

    @staticmethod
    def load_random_book_from_disk(samples_dir: str = "samples") -> Dict[str, Any]:
        """Attempts to load a random book from an available .minemesis run database."""
        p = Path(samples_dir)
        db_files = list(p.glob("*.minemesis")) if p.exists() else []

        if not db_files:
            # Fallback ancient chronicle
            return {
                "title": "The Founding of the First Hearth",
                "author_name": "Chronicler Eldrin",
                "year_written": 1,
                "pages": [
                    "In the dawn of our valley, our kin laid stone upon bedrock.\n"
                    "We shaped the timber from the Great Woods and raised the Great Hall.\n"
                    "Through bitter winters and marauding storms, our hearth endured.\n\n"
                    "May future generations honor this soil and tend our sacred fires.",
                    "Let every builder remember:\n"
                    "A settlement without walls invites ruin.\n"
                    "A granary left unguarded feeds our adversaries.\n"
                    "Stand true, foster kin, and heed the sacred customs.",
                ],
            }

        try:
            conn = sqlite3.connect(str(db_files[0]))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT title, author_name, year_written, pages_blob_compressed "
                "FROM books ORDER BY RANDOM() LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    "title": row[0],
                    "author_name": row[1],
                    "year_written": row[2],
                    "pages": row[3],
                }
        except Exception:
            pass

        return {
            "title": "Chronicle of the Valley",
            "author_name": "Valley Scribe",
            "year_written": 12,
            "pages": ["The ink has faded, yet the memory of our ancestors remains carved into the stones."],
        }
