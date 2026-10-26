"""
Narrative Director System (Milestone 5).

Provides pacing regulation through indirect environmental levers:
- Resource scarcity (frost, drought, bounty)
- Bandit pressure (wilderness outlaw raiding probability)
- Migration pressure (homesteading wanderlust)

Strict Invariant: The Director is forbidden from directly killing characters,
inventing prophecies, declaring wars, or creating stories.
All drama emerges strictly through standard downstream simulation pipelines.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from minemesis.core.rng import keyed_float
from minemesis.core.types import EventType, Intent, Scale


@dataclass
class DirectorLevers:
    resource_scarcity: float = 1.0   # Multiplier on food consumption/dormancy (0.7 to 1.3)
    bandit_pressure: float = 1.0     # Multiplier on wilderness raid rolls (0.5 to 2.0)
    migration_pressure: float = 1.0  # Multiplier on homesteading relocation (0.5 to 2.0)


class NarrativeDirector:
    """
    Evaluates global tension and stagnation metrics to tune environmental pressure levers.
    """

    def __init__(self, seed: int = 42, enabled: bool = True) -> None:
        self.seed = seed
        self.enabled = enabled
        self.levers = DirectorLevers()
        self.last_intervention_tick: int = -100
        self.interventions_history: list[dict[str, Any]] = []

        # Read-only tension state
        self.stagnation_ticks: int = 0
        self.chaos_score: float = 0.0

    def step_director(self, sim: Any) -> None:
        """
        Periodically reviews pacing (every 12 ticks / annually) and adjusts environmental levers.
        """
        if not self.enabled:
            return

        tick = sim.tick
        if tick < 24 or (tick - self.last_intervention_tick) < 24:
            return

        # 1. Measure Stagnation: count conflict events in last 24 ticks
        recent_conflict_events = [
            e for e in sim.event_log.all_events()[-40:]
            if (tick - e.tick) <= 24 and e.type in (EventType.FEUD, EventType.RAID, EventType.WAR_DECLARED, EventType.DEATH)
        ]

        # 2. Measure Chaos: count active famines and devastated settlements
        famine_settlements = [s for s in sim.settlements.values() if s.food < 15]
        low_pop_settlements = [s for s in sim.settlements.values() if 0 < len(sim.get_settlement_living_ids(s.id)) <= 5]

        # Scenario A: World Stagnation -> Increase bandit pressure or mild scarcity
        if len(recent_conflict_events) == 0:
            self.stagnation_ticks += 24
            if self.stagnation_ticks >= 48:
                # Mildly increase bandit activity from the untamed wilderness
                old_val = self.levers.bandit_pressure
                new_val = min(1.8, round(old_val + 0.25, 2))
                self.levers.bandit_pressure = new_val

                evt = sim.event_log.append(
                    tick=tick,
                    location="wilderness",
                    event_type=EventType.DIRECTOR_ACTION,
                    participants={"agent": "NarrativeDirector"},
                    causes=[],
                    intent=Intent.ACCIDENTAL,
                    scale=Scale.AGGREGATE,
                    payload={
                        "lever": "bandit_pressure",
                        "old_value": old_val,
                        "magnitude": new_val,
                        "reason": "prolonged historical stagnation",
                    },
                )
                self.last_intervention_tick = tick
                self.interventions_history.append({
                    "tick": tick,
                    "event_id": evt.id,
                    "lever": "bandit_pressure",
                    "magnitude": new_val,
                    "reason": "Stagnation Break",
                })
                self.stagnation_ticks = 0

        # Scenario B: World Crisis / Chaos -> Reduce scarcity and open migration relief
        elif len(famine_settlements) >= 2 or len(low_pop_settlements) >= 2:
            self.stagnation_ticks = 0
            if self.levers.resource_scarcity > 0.85:
                old_val = self.levers.resource_scarcity
                new_val = max(0.75, round(old_val - 0.20, 2))
                self.levers.resource_scarcity = new_val

                # Open homesteading migration incentives
                self.levers.migration_pressure = 1.5

                cause_evts = [
                    e.id for e in sim.event_log.all_events()[-20:]
                    if e.type in (EventType.FAMINE, EventType.SETTLEMENT_COLLAPSE)
                ]
                evt = sim.event_log.append(
                    tick=tick,
                    location="world",
                    event_type=EventType.DIRECTOR_ACTION,
                    participants={"agent": "NarrativeDirector"},
                    causes=cause_evts[:1],
                    intent=Intent.ACCIDENTAL,
                    scale=Scale.AGGREGATE,
                    payload={
                        "lever": "resource_scarcity",
                        "old_value": old_val,
                        "magnitude": new_val,
                        "reason": "widespread famine mitigation",
                    },
                )
                self.last_intervention_tick = tick
                self.interventions_history.append({
                    "tick": tick,
                    "event_id": evt.id,
                    "lever": "resource_scarcity",
                    "magnitude": new_val,
                    "reason": "Crisis Mitigation",
                })

        else:
            self.stagnation_ticks = max(0, self.stagnation_ticks - 12)
            # Gentle regression to baseline levers (1.0)
            if self.levers.bandit_pressure > 1.05:
                self.levers.bandit_pressure = max(1.0, round(self.levers.bandit_pressure - 0.05, 2))
            if self.levers.resource_scarcity < 0.95:
                self.levers.resource_scarcity = min(1.0, round(self.levers.resource_scarcity + 0.05, 2))
            if self.levers.migration_pressure > 1.05:
                self.levers.migration_pressure = max(1.0, round(self.levers.migration_pressure - 0.05, 2))

    def get_tension_metrics(self) -> dict[str, Any]:
        return {
            "stagnation_ticks": self.stagnation_ticks,
            "bandit_pressure": self.levers.bandit_pressure,
            "resource_scarcity": self.levers.resource_scarcity,
            "migration_pressure": self.levers.migration_pressure,
            "enabled": self.enabled,
        }
