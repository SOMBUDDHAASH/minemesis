"""
Data Models for the Standalone Religion Engine (Milestone R0).

Core Philosophy:
- Religion is NOT a faction, kingdom, or village.
- Religion is an emergent collection of theological, moral, and social ideas.
- Settlements and characters adhere to religions independently of political borders.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class TraitCategory(str, Enum):
    COSMOLOGY = "Cosmology"
    VIRTUES = "Virtues"
    TABOOS = "Taboos"
    SOCIAL_STRUCTURES = "SocialStructures"
    WARFARE_VIEWS = "WarfareViews"
    FAMILY_BELIEFS = "FamilyBeliefs"
    SACRED_GEOGRAPHY = "SacredGeography"
    AFTERLIFE_CONCEPTS = "AfterlifeConcepts"
    RITUALS = "Rituals"


class ReligiousRole(str, Enum):
    LAITY = "Laity"
    PRIEST = "Priest"
    MONK = "Monk"
    SHAMAN = "Shaman"
    PROPHET = "Prophet"
    ELDER = "Elder"
    ORACLE = "Oracle"
    ZEALOT = "Zealot"


@dataclass(frozen=True)
class ReligionTrait:
    """
    A single theological, ethical, or structural component extracted from human religious history.
    """
    id: str
    name: str
    category: TraitCategory
    description: str
    inspired_by: tuple[str, ...]
    modifiers: dict[str, float] = field(default_factory=dict)
    incompatibilities: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "inspired_by": list(self.inspired_by),
            "modifiers": dict(self.modifiers),
            "incompatibilities": list(self.incompatibilities),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReligionTrait:
        return cls(
            id=data["id"],
            name=data["name"],
            category=TraitCategory(data["category"]),
            description=data["description"],
            inspired_by=tuple(data.get("inspired_by", ())),
            modifiers=data.get("modifiers", {}),
            incompatibilities=tuple(data.get("incompatibilities", ())),
        )


@dataclass
class HolySite:
    """A sacred physical location revered by adherents of a religion."""
    id: str
    name: str
    settlement_id: str
    site_type: str
    significance: str
    founded_tick: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "settlement_id": self.settlement_id,
            "site_type": self.site_type,
            "significance": self.significance,
            "founded_tick": self.founded_tick,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HolySite:
        return cls(**data)


@dataclass
class Saint:
    """A deceased adherent canonized into religious memory for heroic, pious, or martyred deeds."""
    character_id: str
    character_name: str
    title: str
    canonized_tick: int
    deed: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "character_name": self.character_name,
            "title": self.title,
            "canonized_tick": self.canonized_tick,
            "deed": self.deed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Saint:
        return cls(**data)


@dataclass
class Religion:
    """
    An emergent religion formed from a coherent combination of religious traits.
    Tracks lineage (parent_religion_id) to document historical schisms.
    """
    id: str
    name: str
    parent_religion_id: Optional[str] = None
    founded_tick: int = 0
    founded_year: int = 1
    traits: dict[str, ReligionTrait] = field(default_factory=dict)
    adherents: set[str] = field(default_factory=set)
    dominant_settlements: set[str] = field(default_factory=set)
    schisms: list[str] = field(default_factory=list)
    holy_sites: list[HolySite] = field(default_factory=list)
    saints: list[Saint] = field(default_factory=list)
    scripture_name: Optional[str] = None
    reformation_level: int = 0
    is_extinct: bool = False

    def add_trait(self, trait: ReligionTrait) -> None:
        self.traits[trait.id] = trait

    def remove_trait(self, trait_id: str) -> None:
        if trait_id in self.traits:
            del self.traits[trait_id]

    def has_trait(self, trait_id: str) -> bool:
        return trait_id in self.traits

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "parent_religion_id": self.parent_religion_id,
            "founded_tick": self.founded_tick,
            "founded_year": self.founded_year,
            "traits": {t_id: t.to_dict() for t_id, t in self.traits.items()},
            "adherents": sorted(list(self.adherents)),
            "dominant_settlements": sorted(list(self.dominant_settlements)),
            "schisms": list(self.schisms),
            "holy_sites": [s.to_dict() for s in self.holy_sites],
            "saints": [s.to_dict() for s in self.saints],
            "scripture_name": self.scripture_name,
            "reformation_level": self.reformation_level,
            "is_extinct": self.is_extinct,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Religion:
        traits = {t_id: ReligionTrait.from_dict(t) for t_id, t in data.get("traits", {}).items()}
        holy_sites = [HolySite.from_dict(s) for s in data.get("holy_sites", [])]
        saints = [Saint.from_dict(s) for s in data.get("saints", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            parent_religion_id=data.get("parent_religion_id"),
            founded_tick=data.get("founded_tick", 0),
            founded_year=data.get("founded_year", 1),
            traits=traits,
            adherents=set(data.get("adherents", [])),
            dominant_settlements=set(data.get("dominant_settlements", [])),
            schisms=list(data.get("schisms", [])),
            holy_sites=holy_sites,
            saints=saints,
            scripture_name=data.get("scripture_name"),
            reformation_level=data.get("reformation_level", 0),
            is_extinct=data.get("is_extinct", False),
        )


@dataclass
class CharacterFaith:
    """
    A character's personal religious adherence, devotion, and role.
    """
    character_id: str
    religion_id: str
    devotion: float = 0.5
    conversion_tick: int = 0
    role: ReligiousRole = ReligiousRole.LAITY
    is_zealot: bool = False
    pilgrimages_completed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "religion_id": self.religion_id,
            "devotion": round(self.devotion, 4),
            "conversion_tick": self.conversion_tick,
            "role": self.role.value,
            "is_zealot": self.is_zealot,
            "pilgrimages_completed": self.pilgrimages_completed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CharacterFaith:
        return cls(
            character_id=data["character_id"],
            religion_id=data["religion_id"],
            devotion=float(data.get("devotion", 0.5)),
            conversion_tick=int(data.get("conversion_tick", 0)),
            role=ReligiousRole(data.get("role", ReligiousRole.LAITY.value)),
            is_zealot=bool(data.get("is_zealot", False)),
            pilgrimages_completed=int(data.get("pilgrimages_completed", 0)),
        )
