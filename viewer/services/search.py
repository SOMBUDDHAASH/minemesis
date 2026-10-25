"""
Multi-Entity Search Service for Viewer V2.
"""

from __future__ import annotations
from typing import Any

from viewer.core.session import session


class SearchService:
    def search_all(self, query: str, limit_per_category: int = 10) -> dict[str, list[dict[str, Any]]]:
        if not session.db or not query.strip():
            return {"characters": [], "events": [], "books": [], "religions": []}

        q = query.strip()
        chars = session.db.get_characters(limit=limit_per_category, search=q)
        evts = session.db.get_events(limit=limit_per_category, search=q)
        books = session.db.get_books(search=q)[:limit_per_category]

        # Religions matching query
        rels = [
            r for r in session.db.get_religions()
            if q.lower() in r["name"].lower() or q.lower() in r["id"].lower()
        ][:limit_per_category]

        return {
            "characters": chars,
            "events": evts,
            "books": books,
            "religions": rels,
        }


search_service = SearchService()
