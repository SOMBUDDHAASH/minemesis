"""
Deterministic A* Road and Highway Network Generator for Milestone T0.

Derives roads between settlements from the travel-cost surface using A* pathfinding
with sorted deterministic tie-breaking.
Stores paths in WorldSpec and allows trade and raiding mechanics to travel along real routes.
"""

from __future__ import annotations
import heapq
import math
from typing import Sequence

from minemesis.systems.world_spec import SettlementSite
from minemesis.terrain.terrain_engine import TerrainGrid


def astar_road(
    grid: TerrainGrid,
    start: tuple[int, int],
    goal: tuple[int, int],
) -> list[tuple[int, int]]:
    """
    Deterministic A* pathfinding using travel-cost map.
    Sorted tie-breaking guarantees cross-platform reproducibility.
    """
    sx, sy = start
    gx, gy = goal

    if start == goal:
        return [start]

    # Priority queue entries: (f_score, h_score, (x, y))
    open_set: list[tuple[float, float, tuple[int, int]]] = []
    heapq.heappush(open_set, (0.0, 0.0, start))

    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {start: 0.0}

    def heuristic(x: int, y: int) -> float:
        # Euclidean distance * min base cost
        return math.sqrt((x - gx) ** 2 + (y - gy) ** 2) * 8.0

    while open_set:
        f, h, current = heapq.heappop(open_set)

        if current == goal:
            # Reconstruct path
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        cx, cy = current
        curr_g = g_score[current]

        # 8-directional neighbors with deterministic sorted order
        neighbors = [
            (cx + dx, cy + dy)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1))
        ]
        neighbors.sort(key=lambda pt: (pt[1], pt[0]))

        for nx, ny in neighbors:
            if not grid.in_bounds(nx, ny):
                continue

            idx = grid.index(nx, ny)
            cost_val = float(grid.travel_cost[idx])

            # Distance cost: 1.0 for orthogonal, ~1.414 for diagonal
            move_dist = 1.414 if (nx != cx and ny != cy) else 1.0
            tentative_g = curr_g + cost_val * move_dist

            nb_pt = (nx, ny)
            if nb_pt not in g_score or tentative_g < g_score[nb_pt]:
                came_from[nb_pt] = current
                g_score[nb_pt] = tentative_g
                h_val = heuristic(nx, ny)
                heapq.heappush(open_set, (tentative_g + h_val, h_val, nb_pt))

    # Fallback straight line if no water-free path
    return [start, goal]


def generate_road_network(
    grid: TerrainGrid,
    settlements: Sequence[SettlementSite],
) -> list[dict[str, Any]]:
    """
    Connects settlements via primary highways and secondary trade routes.
    """
    roads = []
    n = len(settlements)

    # Connect each settlement to its 2-3 closest geographic neighbors
    connected_pairs = set()

    for i in range(n):
        s1 = settlements[i]
        # Calculate distances to all other settlements
        dists = []
        for j in range(n):
            if i != j:
                s2 = settlements[j]
                d = math.sqrt((s1.x - s2.x) ** 2 + (s1.y - s2.y) ** 2)
                dists.append((d, j))
        dists.sort(key=lambda item: item[0])

        # Connect to closest 2 neighbors
        for d, j in dists[:2]:
            pair_key = (min(s1.id, settlements[j].id), max(s1.id, settlements[j].id))
            if pair_key not in connected_pairs:
                connected_pairs.add(pair_key)
                path = astar_road(grid, (s1.x, s1.y), (settlements[j].x, settlements[j].y))
                roads.append({
                    "from_id": s1.id,
                    "to_id": settlements[j].id,
                    "length": len(path),
                    "path": path,
                })

    return roads
