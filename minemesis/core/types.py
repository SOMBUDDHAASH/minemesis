"""
Core Types and Enumerations for the simulation.
Adheres strictly to agent.md and Milestone 0.5 specifications.
"""

from __future__ import annotations
from enum import Enum


class EventType(str, Enum):
    """
    Milestone 0.5 Event Types.
    Routine per-caravan Trade has been demoted to continuous state.
    """
    BIRTH = "Birth"
    DEATH = "Death"
    MARRIAGE = "Marriage"
    FEUD = "Feud"
    RAID = "Raid"
    PEACE = "Peace"
    REVELATION = "Revelation"
    FAMINE = "Famine"
    TRADE_ROUTE_FOUNDED = "TradeRouteFounded"
    TRADE_ROUTE_BROKEN = "TradeRouteBroken"
    CHIEF_CHANGED = "ChiefChanged"
    SUCCESSION_CRISIS = "SuccessionCrisis"
    SETTLEMENT_COLLAPSE = "SettlementCollapse"
    MIGRATION = "Migration"

    # Milestone R0: Religion Engine event types
    CONVERSION = "Conversion"
    RELIGIOUS_REFORM = "ReligiousReform"
    RELIGIOUS_SCHISM = "ReligiousSchism"
    SAINT_CANONIZED = "SaintCanonized"
    PILGRIMAGE = "Pilgrimage"
    HOLY_SITE_DISCOVERED = "HolySiteDiscovered"

    # Alias for backwards compatibility
    FEUD_BEGINS = "Feud"


class Intent(str, Enum):
    """
    Objective intent recorded in the Event Log.
    Beliefs may disagree with this objective value.
    """
    INTENTIONAL = "Intentional"
    ACCIDENTAL = "Accidental"
    SELF_DEFENSE = "SelfDefense"
    MILITARY_ACTION = "MilitaryAction"


class Scale(str, Enum):
    """
    Event scale.
    """
    INDIVIDUAL = "Individual"
    AGGREGATE = "Aggregate"


class BeliefSource(str, Enum):
    """
    Belief source origin.
    """
    WITNESSED = "Witnessed"
    TOLD = "Told"
    INFERRED = "Inferred"


class Emotion(str, Enum):
    """
    Emotional reactions stored in memories.
    """
    GRIEF = "Grief"
    HATRED = "Hatred"
    ANGER = "Anger"
    RELIEF = "Relief"
    GRATITUDE = "Gratitude"
    FEAR = "Fear"
    RESPECT = "Respect"
    AFFECTION = "Affection"
    REGRET = "Regret"
