"""
Data Models for the Standalone Religion Engine (Milestones R0, R1, R1.5 & R2).

Core Philosophy:
- Religion is NOT a church, kingdom, faction, or denomination.
- Religion is an emergent, living collection of ideas, myths, rituals, sacred places,
  cultural practices, and historical memory.
- R1.5: Syncretism, regional doctrinal drift, folk traditions, trait borrowing, convergence.
- R2: Religion shapes culture and civilization (cultural profiles, dimensions, traditions,
  hero worship, sacred geography evolution, cultural mixing).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple


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


class ReligiousRelationshipType(str, Enum):
    """
    R1.2: Inter-faith and sectarian relationship classification.
    """
    SHARED_FAITH = "SharedFaith"
    SIMILAR_FAITH = "SimilarFaith"
    DIVERGENT_SECT = "DivergentSect"
    HOSTILE_DOCTRINE = "HostileDoctrine"


class ReligiousFigureType(str, Enum):
    """
    R1.4: Archetypes of prominent religious figures.
    """
    PROPHET = "Prophet"
    SAINT = "Saint"
    MYSTIC = "Mystic"
    MARTYR = "Martyr"
    REFORMER = "Reformer"
    HERETIC = "Heretic"


class HolySiteType(str, Enum):
    """
    R1.6: Categorization of sacred geography.
    """
    SACRED_MOUNTAIN = "SacredMountain"
    SACRED_FOREST = "SacredForest"
    SACRED_RIVER = "SacredRiver"
    SACRED_TREE = "SacredTree"
    TEMPLE = "Temple"
    SHRINE = "Shrine"


class SiteTier(str, Enum):
    """
    R2.7: Evolutionary tiers of sacred places.
    NaturalSanctuary -> LocalShrine -> Temple -> RegionalPilgrimageSite -> HolyCapital
    """
    NATURAL_SANCTUARY = "NaturalSanctuary"
    LOCAL_SHRINE = "LocalShrine"
    TEMPLE = "Temple"
    REGIONAL_PILGRIMAGE_SITE = "RegionalPilgrimageSite"
    HOLY_CAPITAL = "HolyCapital"


class LoreStage(str, Enum):
    """
    R1.7 & R2.5: Evolutionary stages of religious myth & cultural memory formation.
    Event -> Story -> Legend -> Myth -> Tradition -> Culture
    """
    STORY = "Story"
    LEGEND = "Legend"
    MYTH = "Myth"
    TRADITION = "Tradition"
    CULTURE = "Culture"


class ReligiousIdentityStrength(str, Enum):
    """
    R1.5.6: Individual variation in personal religious attachment.
    """
    ZEALOUS = "Zealous"
    DEVOUT = "Devout"
    AVERAGE = "Average"
    NOMINAL = "Nominal"
    CULTURAL_MEMBER = "CulturalMember"
    NON_PRACTICING = "NonPracticing"


class HeroArchetype(str, Enum):
    """
    R2.6: Diverse models of venerating historical figures.
    """
    HERO = "Hero"
    FOUNDER = "Founder"
    ANCESTOR = "Ancestor"
    PROTECTIVE_SPIRIT = "ProtectiveSpirit"
    SAINT = "Saint"
    CULTURAL_ICON = "CulturalIcon"


class FolkTraditionType(str, Enum):
    """
    R1.5.3: Sub-stratum folk traditions.
    """
    VILLAGE_SPIRIT = "VillageSpirit"
    SACRED_TREE = "SacredTree"
    RIVER_GUARDIAN = "RiverGuardian"
    MOUNTAIN_LEGEND = "MountainLegend"
    ANCESTOR_HERO = "AncestorHero"


class CustomType(str, Enum):
    """
    R2.4: Recurring village ceremonies and annual cultural customs.
    """
    HARVEST_FESTIVAL = "HarvestFestival"
    ANCESTOR_CEREMONY = "AncestorCeremony"
    WINTER_PILGRIMAGE = "WinterPilgrimage"
    RIVER_IMMERSION = "RiverImmersion"
    HERO_REMEMBRANCE = "HeroRemembrance"


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
    tier: SiteTier = SiteTier.NATURAL_SANCTUARY
    pilgrims_visited: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "settlement_id": self.settlement_id,
            "site_type": self.site_type,
            "significance": self.significance,
            "founded_tick": self.founded_tick,
            "tier": self.tier.value,
            "pilgrims_visited": self.pilgrims_visited,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HolySite:
        tier_val = data.get("tier", SiteTier.NATURAL_SANCTUARY.value)
        return cls(
            id=data["id"],
            name=data["name"],
            settlement_id=data["settlement_id"],
            site_type=data["site_type"],
            significance=data["significance"],
            founded_tick=int(data["founded_tick"]),
            tier=SiteTier(tier_val),
            pilgrims_visited=int(data.get("pilgrims_visited", 0)),
        )


@dataclass
class Saint:
    """A deceased adherent canonized into religious memory for heroic, pious, or martyred deeds."""
    character_id: str
    character_name: str
    title: str
    canonized_tick: int
    deed: str
    archetype: HeroArchetype = HeroArchetype.SAINT

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "character_name": self.character_name,
            "title": self.title,
            "canonized_tick": self.canonized_tick,
            "deed": self.deed,
            "archetype": self.archetype.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Saint:
        archetype_val = data.get("archetype", HeroArchetype.SAINT.value)
        return cls(
            character_id=data["character_id"],
            character_name=data["character_name"],
            title=data["title"],
            canonized_tick=int(data["canonized_tick"]),
            deed=data["deed"],
            archetype=HeroArchetype(archetype_val),
        )


@dataclass
class ReligiousFigure:
    """
    R1.4 & R2.6: Great religious leaders, visionaries, martyrs, reformers, and cultural icons.
    """
    id: str
    character_id: str
    character_name: str
    figure_type: ReligiousFigureType
    religion_id: str
    title: str
    deeds: list[str] = field(default_factory=list)
    tick_recognized: int = 0
    is_alive: bool = True
    associated_event_id: Optional[int] = None
    archetype: HeroArchetype = HeroArchetype.HERO

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "character_id": self.character_id,
            "character_name": self.character_name,
            "figure_type": self.figure_type.value,
            "religion_id": self.religion_id,
            "title": self.title,
            "deeds": list(self.deeds),
            "tick_recognized": self.tick_recognized,
            "is_alive": self.is_alive,
            "associated_event_id": self.associated_event_id,
            "archetype": self.archetype.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReligiousFigure:
        arch_val = data.get("archetype", HeroArchetype.HERO.value)
        return cls(
            id=data["id"],
            character_id=data["character_id"],
            character_name=data["character_name"],
            figure_type=ReligiousFigureType(data["figure_type"]),
            religion_id=data["religion_id"],
            title=data["title"],
            deeds=list(data.get("deeds", [])),
            tick_recognized=int(data.get("tick_recognized", 0)),
            is_alive=bool(data.get("is_alive", True)),
            associated_event_id=data.get("associated_event_id"),
            archetype=HeroArchetype(arch_val),
        )


@dataclass
class ReligiousMyth:
    """
    R1.7 & R2.5: Myth Creation & Cultural Memory System.
    Event -> Story -> Legend -> Myth -> Tradition -> Culture
    """
    myth_id: str
    religion_id: str
    root_event_id: int
    hero_id: str
    hero_name: str
    stage: LoreStage = LoreStage.STORY
    objective_truth: str = ""
    mythic_narrative: str = ""
    embellishments: list[str] = field(default_factory=list)
    retellings: int = 0
    origin_tick: int = 0
    last_retold_tick: int = 0
    origin_settlement_id: Optional[str] = None
    known_by_settlements: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        return {
            "myth_id": self.myth_id,
            "religion_id": self.religion_id,
            "root_event_id": self.root_event_id,
            "hero_id": self.hero_id,
            "hero_name": self.hero_name,
            "stage": self.stage.value,
            "objective_truth": self.objective_truth,
            "mythic_narrative": self.mythic_narrative,
            "embellishments": list(self.embellishments),
            "retellings": self.retellings,
            "origin_tick": self.origin_tick,
            "last_retold_tick": self.last_retold_tick,
            "origin_settlement_id": self.origin_settlement_id,
            "known_by_settlements": sorted(list(self.known_by_settlements)),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReligiousMyth:
        return cls(
            myth_id=data["myth_id"],
            religion_id=data["religion_id"],
            root_event_id=int(data["root_event_id"]),
            hero_id=data["hero_id"],
            hero_name=data["hero_name"],
            stage=LoreStage(data.get("stage", LoreStage.STORY.value)),
            objective_truth=data.get("objective_truth", ""),
            mythic_narrative=data.get("mythic_narrative", ""),
            embellishments=list(data.get("embellishments", [])),
            retellings=int(data.get("retellings", 0)),
            origin_tick=int(data.get("origin_tick", 0)),
            last_retold_tick=int(data.get("last_retold_tick", 0)),
            origin_settlement_id=data.get("origin_settlement_id"),
            known_by_settlements=set(data.get("known_by_settlements", [])),
        )


@dataclass
class FolkTradition:
    """
    R1.5.3: Local folk spirits, sacred trees, and ancestral legends.
    """
    id: str
    name: str
    tradition_type: FolkTraditionType
    settlement_id: str
    significance: str
    is_absorbed_into_religion: bool = False
    absorbed_by_religion_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tradition_type": self.tradition_type.value,
            "settlement_id": self.settlement_id,
            "significance": self.significance,
            "is_absorbed_into_religion": self.is_absorbed_into_religion,
            "absorbed_by_religion_id": self.absorbed_by_religion_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FolkTradition:
        return cls(
            id=data["id"],
            name=data["name"],
            tradition_type=FolkTraditionType(data["tradition_type"]),
            settlement_id=data["settlement_id"],
            significance=data["significance"],
            is_absorbed_into_religion=bool(data.get("is_absorbed_into_religion", False)),
            absorbed_by_religion_id=data.get("absorbed_by_religion_id"),
        )


@dataclass
class LocalCustom:
    """
    R2.4: Annual village customs, seasonal immersions, and ceremonies.
    """
    id: str
    name: str
    custom_type: CustomType
    settlement_id: str
    season_month: int
    description: str
    celebration_count: int = 0
    last_celebrated_tick: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "custom_type": self.custom_type.value,
            "settlement_id": self.settlement_id,
            "season_month": self.season_month,
            "description": self.description,
            "celebration_count": self.celebration_count,
            "last_celebrated_tick": self.last_celebrated_tick,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LocalCustom:
        return cls(
            id=data["id"],
            name=data["name"],
            custom_type=CustomType(data["custom_type"]),
            settlement_id=data["settlement_id"],
            season_month=int(data["season_month"]),
            description=data["description"],
            celebration_count=data.get("celebration_count", 0),
            last_celebrated_tick=data.get("last_celebrated_tick"),
        )


@dataclass
class RegionalDoctrineProfile:
    """
    R1.5.2: Regional doctrinal drift and trait emphasis without schism.
    """
    region_id: str
    trait_weights: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "trait_weights": dict(self.trait_weights),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegionalDoctrineProfile:
        return cls(
            region_id=data["region_id"],
            trait_weights=dict(data.get("trait_weights", {})),
        )


@dataclass
class CulturalProfile:
    """
    R2.1 & R2.3: Multi-dimensional cultural composition of a settlement.
    """
    settlement_id: str
    religious_composition: dict[str, float] = field(default_factory=dict)  # {rel_id: proportion}
    social_values: dict[str, float] = field(default_factory=dict)          # family_loyalty, honor, discipline, compassion, etc.
    historical_biases: dict[str, float] = field(default_factory=dict)
    folk_traditions: list[FolkTradition] = field(default_factory=list)
    local_customs: list[LocalCustom] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "settlement_id": self.settlement_id,
            "religious_composition": {k: round(v, 3) for k, v in self.religious_composition.items()},
            "social_values": {k: round(v, 3) for k, v in self.social_values.items()},
            "historical_biases": {k: round(v, 3) for k, v in self.historical_biases.items()},
            "folk_traditions": [ft.to_dict() for ft in self.folk_traditions],
            "local_customs": [lc.to_dict() for lc in self.local_customs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CulturalProfile:
        return cls(
            settlement_id=data["settlement_id"],
            religious_composition=dict(data.get("religious_composition", {})),
            social_values=dict(data.get("social_values", {})),
            historical_biases=dict(data.get("historical_biases", {})),
            folk_traditions=[FolkTradition.from_dict(ft) for ft in data.get("folk_traditions", [])],
            local_customs=[LocalCustom.from_dict(lc) for lc in data.get("local_customs", [])],
        )


@dataclass
class Religion:
    """
    An emergent religion formed from a coherent combination of religious traits.
    Tracks lineage (parent_religion_id, child_religion_ids), syncretism, and regional drift.
    """
    id: str
    name: str
    parent_religion_id: Optional[str] = None
    child_religion_ids: list[str] = field(default_factory=list)
    syncretic_parents: list[str] = field(default_factory=list)  # R1.5.1
    borrowed_traits: dict[str, str] = field(default_factory=dict)  # R1.5.4 {trait_id: donor_rel_id}
    absorbed_folk_traditions: list[str] = field(default_factory=list)  # R1.5.3
    regional_profiles: dict[str, RegionalDoctrineProfile] = field(default_factory=dict)  # R1.5.2
    cultural_traditions: list[str] = field(default_factory=list)  # R2.5
    founded_tick: int = 0
    founded_year: int = 1
    traits: dict[str, ReligionTrait] = field(default_factory=dict)
    adherents: set[str] = field(default_factory=set)
    dominant_settlements: set[str] = field(default_factory=set)
    schisms: list[str] = field(default_factory=list)
    reforms: list[str] = field(default_factory=list)
    generation: int = 0
    holy_sites: list[HolySite] = field(default_factory=list)
    saints: list[Saint] = field(default_factory=list)
    figures: list[ReligiousFigure] = field(default_factory=list)
    myths: list[ReligiousMyth] = field(default_factory=list)
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

    def is_descendant_of(self, ancestor_id: str, religions: Mapping[str, Religion]) -> bool:
        """Returns True if this religion descends directly or indirectly from ancestor_id."""
        curr_parent = self.parent_religion_id
        visited = set()
        while curr_parent and curr_parent not in visited:
            if curr_parent == ancestor_id:
                return True
            visited.add(curr_parent)
            parent_rel = religions.get(curr_parent)
            curr_parent = parent_rel.parent_religion_id if parent_rel else None

        # Check syncretic parents as well
        if ancestor_id in self.syncretic_parents:
            return True
        return False

    def get_root_ancestor_id(self, religions: Mapping[str, Religion]) -> str:
        """Finds the root patriarch religion ID of this lineage."""
        curr = self
        visited = {curr.id}
        while curr.parent_religion_id and curr.parent_religion_id in religions:
            p_id = curr.parent_religion_id
            if p_id in visited:
                break
            visited.add(p_id)
            curr = religions[p_id]
        return curr.id

    def get_lineage_path(self, religions: Mapping[str, Religion]) -> list[str]:
        """Returns ordered chain of religion IDs from root ancestor to self."""
        chain = [self.id]
        curr_parent = self.parent_religion_id
        visited = {self.id}
        while curr_parent and curr_parent in religions and curr_parent not in visited:
            chain.append(curr_parent)
            visited.add(curr_parent)
            parent_rel = religions[curr_parent]
            curr_parent = parent_rel.parent_religion_id
        chain.reverse()
        return chain

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "parent_religion_id": self.parent_religion_id,
            "child_religion_ids": list(self.child_religion_ids),
            "syncretic_parents": list(self.syncretic_parents),
            "borrowed_traits": dict(self.borrowed_traits),
            "absorbed_folk_traditions": list(self.absorbed_folk_traditions),
            "regional_profiles": {k: v.to_dict() for k, v in self.regional_profiles.items()},
            "cultural_traditions": list(self.cultural_traditions),
            "founded_tick": self.founded_tick,
            "founded_year": self.founded_year,
            "traits": {t_id: t.to_dict() for t_id, t in self.traits.items()},
            "adherents": sorted(list(self.adherents)),
            "dominant_settlements": sorted(list(self.dominant_settlements)),
            "schisms": list(self.schisms),
            "reforms": list(self.reforms),
            "generation": self.generation,
            "holy_sites": [s.to_dict() for s in self.holy_sites],
            "saints": [s.to_dict() for s in self.saints],
            "figures": [f.to_dict() for f in self.figures],
            "myths": [m.to_dict() for m in self.myths],
            "scripture_name": self.scripture_name,
            "reformation_level": self.reformation_level,
            "is_extinct": self.is_extinct,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Religion:
        traits = {t_id: ReligionTrait.from_dict(t) for t_id, t in data.get("traits", {}).items()}
        holy_sites = [HolySite.from_dict(s) for s in data.get("holy_sites", [])]
        saints = [Saint.from_dict(s) for s in data.get("saints", [])]
        figures = [ReligiousFigure.from_dict(f) for f in data.get("figures", [])]
        myths = [ReligiousMyth.from_dict(m) for m in data.get("myths", [])]
        regional = {k: RegionalDoctrineProfile.from_dict(v) for k, v in data.get("regional_profiles", {}).items()}

        return cls(
            id=data["id"],
            name=data["name"],
            parent_religion_id=data.get("parent_religion_id"),
            child_religion_ids=list(data.get("child_religion_ids", [])),
            syncretic_parents=list(data.get("syncretic_parents", [])),
            borrowed_traits=dict(data.get("borrowed_traits", {})),
            absorbed_folk_traditions=list(data.get("absorbed_folk_traditions", [])),
            regional_profiles=regional,
            cultural_traditions=list(data.get("cultural_traditions", [])),
            founded_tick=data.get("founded_tick", 0),
            founded_year=data.get("founded_year", 1),
            traits=traits,
            adherents=set(data.get("adherents", [])),
            dominant_settlements=set(data.get("dominant_settlements", [])),
            schisms=list(data.get("schisms", [])),
            reforms=list(data.get("reforms", [])),
            generation=int(data.get("generation", 0)),
            holy_sites=holy_sites,
            saints=saints,
            figures=figures,
            myths=myths,
            scripture_name=data.get("scripture_name"),
            reformation_level=data.get("reformation_level", 0),
            is_extinct=data.get("is_extinct", False),
        )


@dataclass
class CharacterFaith:
    """
    A character's personal religious adherence, devotion, moral standing, and role.
    """
    character_id: str
    religion_id: str
    devotion: float = 0.5
    religious_standing: float = 50.0  # R1.8: Virtue and standing [0.0, 100.0]
    conversion_tick: int = 0
    role: ReligiousRole = ReligiousRole.LAITY
    is_zealot: bool = False
    pilgrimages_completed: int = 0
    former_religion_ids: list[str] = field(default_factory=list)
    identity_strength: ReligiousIdentityStrength = ReligiousIdentityStrength.DEVOUT  # R1.5.6

    @property
    def adherence_weight(self) -> float:
        """
        R1.5.6: Computes behavioral weight scaled by religious identity strength.
        """
        multipliers = {
            ReligiousIdentityStrength.ZEALOUS: 1.3,
            ReligiousIdentityStrength.DEVOUT: 1.0,
            ReligiousIdentityStrength.AVERAGE: 0.7,
            ReligiousIdentityStrength.NOMINAL: 0.4,
            ReligiousIdentityStrength.CULTURAL_MEMBER: 0.25,
            ReligiousIdentityStrength.NON_PRACTICING: 0.1,
        }
        return self.devotion * multipliers.get(self.identity_strength, 1.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "religion_id": self.religion_id,
            "devotion": round(self.devotion, 4),
            "religious_standing": round(self.religious_standing, 2),
            "conversion_tick": self.conversion_tick,
            "role": self.role.value,
            "is_zealot": self.is_zealot,
            "pilgrimages_completed": self.pilgrimages_completed,
            "former_religion_ids": list(self.former_religion_ids),
            "identity_strength": self.identity_strength.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CharacterFaith:
        id_str_val = data.get("identity_strength", ReligiousIdentityStrength.DEVOUT.value)
        return cls(
            character_id=data["character_id"],
            religion_id=data["religion_id"],
            devotion=float(data.get("devotion", 0.5)),
            religious_standing=float(data.get("religious_standing", 50.0)),
            conversion_tick=int(data.get("conversion_tick", 0)),
            role=ReligiousRole(data.get("role", ReligiousRole.LAITY.value)),
            is_zealot=bool(data.get("is_zealot", False)),
            pilgrimages_completed=int(data.get("pilgrimages_completed", 0)),
            former_religion_ids=list(data.get("former_religion_ids", [])),
            identity_strength=ReligiousIdentityStrength(id_str_val),
        )
