"""
Census & Demographic Analytics Service for Viewer V2.
"""

from __future__ import annotations
from collections import defaultdict
from typing import Any

from viewer.core.session import session


class CensusService:
    def get_population_history(self) -> dict[str, list[tuple[int, int]]]:
        """
        Returns {settlement_id: [(year, pop), ...], '__total__': [(year, total_pop), ...]}
        """
        if not session.db:
            return {}

        rows = session.db.get_census()
        by_settlement: dict[str, list[tuple[int, int]]] = defaultdict(list)
        total_by_year: dict[int, int] = defaultdict(int)

        for r in rows:
            y = int(r["year"])
            s_id = str(r["settlement_id"])
            pop = int(r["population"])
            by_settlement[s_id].append((y, pop))
            total_by_year[y] += pop

        by_settlement["__total__"] = sorted(total_by_year.items())
        return by_settlement

    def get_vital_rates(self) -> dict[str, list[tuple[int, int]]]:
        """Calculates births and deaths per year from events."""
        if not session.db:
            return {"births": [], "deaths": []}

        births_by_year: dict[int, int] = defaultdict(int)
        deaths_by_year: dict[int, int] = defaultdict(int)

        cur = session.db._conn.cursor()
        rows = cur.execute("SELECT year, type, COUNT(*) FROM events WHERE type IN ('Birth', 'Death') GROUP BY year, type").fetchall()
        for y, t, c in rows:
            if t == "Birth":
                births_by_year[int(y)] = int(c)
            elif t == "Death":
                deaths_by_year[int(y)] = int(c)

        all_years = sorted(set(list(births_by_year.keys()) + list(deaths_by_year.keys())))
        return {
            "births": [(y, births_by_year.get(y, 0)) for y in all_years],
            "deaths": [(y, deaths_by_year.get(y, 0)) for y in all_years],
        }


census_service = CensusService()
