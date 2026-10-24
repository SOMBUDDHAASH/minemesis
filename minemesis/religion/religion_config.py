"""
Configuration for the Standalone Religion Engine (Milestone R0).

The Religion Engine is an optional, independent subsystem.
When ENABLE_RELIGION_ENGINE is False, the simulation runs normally with zero religious overhead.
When ENABLE_RELIGION_ENGINE is True, procedural faiths, spread, schisms, and behavioral effects activate.
"""

from __future__ import annotations

# Primary architectural toggle
ENABLE_RELIGION_ENGINE: bool = True

# Generation parameters
INITIAL_RELIGIONS_PER_WORLD: int = 2
MIN_TRAITS_PER_RELIGION: int = 4
MAX_TRAITS_PER_RELIGION: int = 6

# Social spread probabilities (per monthly tick)
CHILD_INHERITANCE_CHANCE: float = 0.95
MARRIAGE_CONVERSION_CHANCE: float = 0.08
TRADE_ROUTE_SPREAD_CHANCE: float = 0.04
MIGRANT_FAITH_RETENTION_CHANCE: float = 0.90
MISSIONARY_PROSELYTIZE_CHANCE: float = 0.12
PILGRIMAGE_CHANCE: float = 0.02

# Evolution and schism thresholds
DEVOTION_DECAY_RATE: float = 0.005
DEVOTION_BOOST_RITUAL: float = 0.05
SAINT_CANONIZATION_MIN_DEVOTION: float = 0.85
SCHISM_CHANCE_PER_TICK: float = 0.008
REFORMATION_CHANCE_ON_CRISIS: float = 0.25
CLERGY_POPULATION_RATIO: float = 0.08
