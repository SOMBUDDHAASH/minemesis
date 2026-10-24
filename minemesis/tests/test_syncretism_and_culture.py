"""
Validation Suite for Milestone R1.5 + R2:
Syncretism, Cultural Evolution, and Living Faith Systems.

Tests:
1. R1.5.1 Religious Syncretism Engine (Faith A + Faith B -> Faith C fusion).
2. R1.5.2 Regional Doctrine Profiles (Regional Drift without schism).
3. R1.5.3 Folk Tradition Layer (Spirit guardians, sacred trees absorbed into official faith).
4. R1.5.4 Religious Trait Exchange (Doctrinal borrowing without conversion).
5. R1.5.5 Faith Convergence (Jaccard similarity computation).
6. R1.5.6 Religious Identity Strength spectrum.
7. R1.5.7 Myth Exchange across trade corridors.
8. R2.1 & R2.3 Cultural Profiles for settlements.
9. R2.4 Local Traditions & Seasonal Customs celebration.
10. R2.5 Evolutionary Lore Stages (Event -> Story -> Legend -> Myth -> Tradition -> Culture).
11. R2.6 Hero Archetypes veneration across traditions.
12. R2.7 Sacred Geography Evolution across site tiers.
13. R2.8 Cultural Behavioral Pressure modifiers.
14. R2.9 Cultural Mixing & Fluidity along trade corridors.
15. R2.10 Comprehensive Religion-Culture Analytics.
16. 100-Year Unscripted Simulation producing emergent living faiths.
"""

from __future__ import annotations
import random
from typing import Any
import pytest

from minemesis.core.types import EventType
from minemesis.models.character import Character
from minemesis.models.settlement import Settlement
from minemesis.religion.religion_analytics import (
    ReligiousAnalyticsReport,
    format_religious_analytics_summary,
    generate_religious_analytics,
)
from minemesis.religion.religion_culture import (
    absorb_folk_tradition_into_religion,
    celebrate_local_customs,
    get_cultural_behavioral_pressure,
    initialize_settlement_culture,
    process_cultural_mixing,
)
from minemesis.religion.religion_engine import ReligionEngine
from minemesis.religion.religion_figures import determine_hero_archetype
from minemesis.religion.religion_geography import check_and_elevate_holy_site
from minemesis.religion.religion_models import (
    CharacterFaith,
    CulturalProfile,
    CustomType,
    FolkTradition,
    FolkTraditionType,
    HeroArchetype,
    HolySite,
    HolySiteType,
    LocalCustom,
    LoreStage,
    RegionalDoctrineProfile,
    Religion,
    ReligionTrait,
    ReligiousFigure,
    ReligiousFigureType,
    ReligiousIdentityStrength,
    ReligiousMyth,
    ReligiousRole,
    Saint,
    SiteTier,
    TraitCategory,
)
from minemesis.religion.religion_myths import (
    exchange_myths_across_trade_routes,
    retell_and_evolve_myths,
)
from minemesis.religion.religion_syncretism import (
    calculate_jaccard_similarity,
    evaluate_doctrinal_borrowing,
    evaluate_syncretic_fusion,
)
from minemesis.religion.religion_traits import ALL_RELIGION_TRAITS
from minemesis.systems.simulation import Simulation


def _create_dummy_character(c_id: str, settlement_id: str = "set_oakhaven", age: int = 300) -> Character:
    return Character(
        id=c_id,
        first_name=f"First_{c_id}",
        last_name=f"Last_{c_id}",
        settlement_id=settlement_id,
        age_ticks=age,
        sex="M",
    )


# =============================================================================
# 1. R1.5.1: Religious Syncretism Engine (A + B -> C)
# =============================================================================
def test_syncretic_fusion_creates_new_faith():
    rng = random.Random(42)
    rel_a = Religion(
        id="rel_a",
        name="Way of the River",
        traits={
            "polytheism": ALL_RELIGION_TRAITS["polytheism"],
            "sacred_rivers": ALL_RELIGION_TRAITS["sacred_rivers"],
            "charity_obligation": ALL_RELIGION_TRAITS["charity_obligation"],
        },
    )
    rel_b = Religion(
        id="rel_b",
        name="Order of the High Peak",
        traits={
            "ancestral_veneration": ALL_RELIGION_TRAITS["ancestral_veneration"],
            "sacred_mountains": ALL_RELIGION_TRAITS["sacred_mountains"],
            "warrior_honor": ALL_RELIGION_TRAITS["warrior_honor"],
        },
    )

    chars = [_create_dummy_character(f"c_{i}", settlement_id="set_riverbend") for i in range(6)]
    faiths = {
        "c_0": CharacterFaith("c_0", "rel_a", devotion=0.8),
        "c_1": CharacterFaith("c_1", "rel_a", devotion=0.8),
        "c_2": CharacterFaith("c_2", "rel_a", devotion=0.8),
        "c_3": CharacterFaith("c_3", "rel_b", devotion=0.8),
        "c_4": CharacterFaith("c_4", "rel_b", devotion=0.8),
        "c_5": CharacterFaith("c_5", "rel_b", devotion=0.8),
    }

    rel_counter = [1]
    fusion_res = evaluate_syncretic_fusion(
        rel_a=rel_a,
        rel_b=rel_b,
        settlement_id="set_riverbend",
        settlement_characters=chars,
        faiths=faiths,
        all_traits=ALL_RELIGION_TRAITS,
        rel_counter=rel_counter,
        tick=120,
        rng=rng,
    )

    assert fusion_res is not None
    new_rel, payload = fusion_res
    assert new_rel.id == "rel_syncretic_1"
    assert "rel_a" in new_rel.syncretic_parents
    assert "rel_b" in new_rel.syncretic_parents
    assert "rel_syncretic_1" in rel_a.child_religion_ids
    assert "rel_syncretic_1" in rel_b.child_religion_ids
    assert len(new_rel.traits) >= 4
    # Adherents converted
    for c_id in ["c_0", "c_1", "c_2", "c_3", "c_4", "c_5"]:
        assert faiths[c_id].religion_id == "rel_syncretic_1"


# =============================================================================
# 2. R1.5.2 & R1.5.5: Jaccard Similarity and Regional Drift Profiles
# =============================================================================
def test_jaccard_similarity_and_regional_profiles():
    rel_1 = Religion(
        id="r1",
        name="Faith 1",
        traits={
            "polytheism": ALL_RELIGION_TRAITS["polytheism"],
            "sacred_rivers": ALL_RELIGION_TRAITS["sacred_rivers"],
        },
    )
    rel_2 = Religion(
        id="r2",
        name="Faith 2",
        traits={
            "polytheism": ALL_RELIGION_TRAITS["polytheism"],
            "sacred_rivers": ALL_RELIGION_TRAITS["sacred_rivers"],
            "ancestral_veneration": ALL_RELIGION_TRAITS["ancestral_veneration"],
        },
    )

    sim = calculate_jaccard_similarity(rel_1, rel_2)
    assert pytest.approx(sim, 0.01) == 2 / 3  # 0.667

    # Regional profile
    prof = RegionalDoctrineProfile(
        region_id="set_riverbend",
        trait_weights={"sacred_rivers": 1.5, "polytheism": 0.8},
    )
    rel_1.regional_profiles["set_riverbend"] = prof
    assert rel_1.regional_profiles["set_riverbend"].trait_weights["sacred_rivers"] == 1.5


# =============================================================================
# 3. R1.5.3: Folk Tradition Layer
# =============================================================================
def test_folk_tradition_absorption():
    rel = Religion(id="rel_1", name="Hearth Faith")
    folk_trad = FolkTradition(
        id="folk_1",
        name="The Whispering Oak",
        tradition_type=FolkTraditionType.SACRED_TREE,
        settlement_id="set_oakhaven",
        significance="Ancient oak sacred to forest spirits.",
    )

    assert not folk_trad.is_absorbed_into_religion
    res = absorb_folk_tradition_into_religion(rel, folk_trad, tick=100)

    assert folk_trad.is_absorbed_into_religion
    assert folk_trad.absorbed_by_religion_id == rel.id
    assert "folk_1" in rel.absorbed_folk_traditions
    assert res["folk_tradition_name"] == "The Whispering Oak"


# =============================================================================
# 4. R1.5.4: Religious Trait Exchange (Doctrinal Borrowing)
# =============================================================================
def test_doctrinal_borrowing_without_conversion():
    rng = random.Random(123)
    donor = Religion(
        id="r_donor",
        name="Steppe Nomads",
        traits={
            "ancestral_veneration": ALL_RELIGION_TRAITS["ancestral_veneration"],
            "warrior_honor": ALL_RELIGION_TRAITS["warrior_honor"],
        },
    )
    recipient = Religion(
        id="r_recip",
        name="Valley Cult",
        traits={
            "polytheism": ALL_RELIGION_TRAITS["polytheism"],
            "charity_obligation": ALL_RELIGION_TRAITS["charity_obligation"],
        },
    )

    assert "warrior_honor" not in recipient.traits
    borrow_payload = evaluate_doctrinal_borrowing(
        donor_rel=donor,
        recipient_rel=recipient,
        all_traits=ALL_RELIGION_TRAITS,
        tick=50,
        rng=rng,
    )

    assert borrow_payload is not None
    assert borrow_payload["recipient_religion_id"] == "r_recip"
    assert len(recipient.borrowed_traits) > 0
    assert any(t_id in recipient.traits for t_id in donor.traits)


# =============================================================================
# 5. R1.5.6: Religious Identity Strength Spectrum
# =============================================================================
def test_religious_identity_strength_spectrum():
    f1 = CharacterFaith("c_1", "r1", identity_strength=ReligiousIdentityStrength.ZEALOUS)
    f2 = CharacterFaith("c_2", "r1", identity_strength=ReligiousIdentityStrength.CULTURAL_MEMBER)
    f3 = CharacterFaith("c_3", "r1", identity_strength=ReligiousIdentityStrength.NON_PRACTICING)

    assert f1.identity_strength.value == "Zealous"
    assert f2.identity_strength.value == "CulturalMember"
    assert f3.identity_strength.value == "NonPracticing"

    f1_dict = f1.to_dict()
    assert f1_dict["identity_strength"] == "Zealous"
    restored = CharacterFaith.from_dict(f1_dict)
    assert restored.identity_strength == ReligiousIdentityStrength.ZEALOUS


# =============================================================================
# 6. R1.5.7: Myth Exchange Across Trade Routes
# =============================================================================
def test_myth_exchange_across_trade_routes():
    rng = random.Random(42)
    rel_a = Religion(id="r_a", name="Oakhaven Faith")
    rel_b = Religion(id="r_b", name="Riverbend Faith")

    m = ReligiousMyth(
        myth_id="myth_99",
        religion_id=rel_a.id,
        root_event_id=10,
        hero_id="c_1",
        hero_name="Brendan the Strong",
        stage=LoreStage.LEGEND,
        objective_truth="Silenced a great bear.",
        mythic_narrative="Felled the shadow beast of the woods.",
        known_by_settlements={"set_oakhaven"},
    )
    rel_a.myths.append(m)

    class DummyRoute:
        active = True

    active_routes = {("set_oakhaven", "set_riverbend"): DummyRoute()}
    dominant = {"set_oakhaven": "r_a", "set_riverbend": "r_b"}
    myth_counter = [100]

    exchanges = []
    for tick in range(10, 150, 10):
        exchanges = exchange_myths_across_trade_routes(
            active_trade_routes=active_routes,
            religions={"r_a": rel_a, "r_b": rel_b},
            dominant_by_settlement=dominant,
            current_tick=tick,
            rng=rng,
            myth_counter=myth_counter,
        )
        if exchanges:
            break

    assert len(exchanges) == 1
    assert exchanges[0]["hero_name"] == "Brendan the Strong"
    assert "set_riverbend" in m.known_by_settlements
    assert len(rel_b.myths) == 1
    assert "caravans" in rel_b.myths[0].mythic_narrative.lower()


# =============================================================================
# 7. R2.1 & R2.3: Cultural Profiles Initialization & Custom Celebrations
# =============================================================================
def test_cultural_profile_and_custom_celebrations():
    rng = random.Random(42)
    folk_c = [1]
    cust_c = [1]
    cp = initialize_settlement_culture("set_oakhaven", "Oakhaven", folk_c, cust_c, rng)

    assert cp.settlement_id == "set_oakhaven"
    assert "family_loyalty" in cp.social_values
    assert len(cp.folk_traditions) >= 1
    assert len(cp.local_customs) >= 1

    # Seasonal customs trigger during month match
    # Midsummer festival is month 6 (tick 5, 17, 29, etc. tick % 12 + 1 == 6)
    events_m6 = celebrate_local_customs("set_oakhaven", cp, current_tick=5)
    assert len(events_m6) >= 1
    assert any(e["custom_type"] == CustomType.HARVEST_FESTIVAL.value for e in events_m6)


# =============================================================================
# 8. R2.5: Evolution to Tradition and Culture Stages
# =============================================================================
def test_myth_progression_to_tradition_and_culture():
    rng = random.Random(99)
    rel = Religion(id="r_trad", name="Eternal Faith")
    m = ReligiousMyth(
        myth_id="m_1",
        religion_id=rel.id,
        root_event_id=1,
        hero_id="c_founder",
        hero_name="Eldrin the First",
        stage=LoreStage.MYTH,
        origin_tick=0,
        retellings=5,
    )
    rel.myths.append(m)

    # Retell myth when 60+ years have elapsed (tick 750 >= 720)
    retell_and_evolve_myths(rel, 750, rng)
    assert m.stage == LoreStage.TRADITION

    # Retell myth when 90+ years have elapsed (tick 1100 >= 1080)
    retell_and_evolve_myths(rel, 1100, rng)
    assert m.stage == LoreStage.CULTURE


# =============================================================================
# 9. R2.6: Hero Archetype Resolution
# =============================================================================
def test_hero_archetype_resolution():
    char = _create_dummy_character("c_1", age=200)

    # Ancestor faith
    rel_anc = Religion(id="r_anc", name="Ancestral Grove", traits={"ancestor_worship": ALL_RELIGION_TRAITS["ancestor_worship"]})
    assert determine_hero_archetype(rel_anc, char, ReligiousFigureType.MARTYR) == HeroArchetype.ANCESTOR

    # Warrior faith
    rel_war = Religion(id="r_war", name="Iron Clan", traits={"warrior_honor": ALL_RELIGION_TRAITS["warrior_honor"]})
    assert determine_hero_archetype(rel_war, char, ReligiousFigureType.MARTYR) == HeroArchetype.HERO

    # Elder / Patriarch
    old_char = _create_dummy_character("c_old", age=800)
    assert determine_hero_archetype(None, old_char, ReligiousFigureType.PROPHET) == HeroArchetype.CULTURAL_ICON


# =============================================================================
# 10. R2.7: Sacred Geography Evolution Across Tiers
# =============================================================================
def test_holy_site_tier_elevation():
    rel = Religion(id="r_geo", name="High Sanctuary")
    site = HolySite(
        id="site_1",
        name="The Whispering Springs",
        settlement_id="set_riverbend",
        site_type="Spring",
        significance="Cleansing waters",
        founded_tick=0,
        tier=SiteTier.NATURAL_SANCTUARY,
        pilgrims_visited=4,
    )

    # First elevation (5 pilgrims) -> LocalShrine
    site.pilgrims_visited += 1
    elev1 = check_and_elevate_holy_site(site, rel, tick=50)
    assert elev1 is not None
    assert site.tier == SiteTier.LOCAL_SHRINE
    assert elev1["new_tier"] == SiteTier.LOCAL_SHRINE.value

    # Jump to 15 pilgrims -> Temple
    site.pilgrims_visited = 15
    elev2 = check_and_elevate_holy_site(site, rel, tick=100)
    assert elev2 is not None
    assert site.tier == SiteTier.TEMPLE


# =============================================================================
# 11. R2.8: Cultural Behavioral Pressure System
# =============================================================================
def test_cultural_behavioral_pressure():
    cp = CulturalProfile(
        settlement_id="set_ironpeak",
        social_values={
            "family_loyalty": 0.90,
            "compassion": 0.40,
            "warrior_tradition": 0.85,
        },
    )
    profiles = {"set_ironpeak": cp}

    pressure = get_cultural_behavioral_pressure("set_ironpeak", profiles)
    assert pressure["grudge_retention_multiplier"] > 1.3
    assert pressure["raid_affinity_multiplier"] > 1.4
    assert pressure["forgiveness_propensity_multiplier"] == pytest.approx(1.20, 0.01)


# =============================================================================
# 12. R2.9: Cultural Mixing Along Trade Routes
# =============================================================================
def test_cultural_mixing_along_trade_routes():
    cp_a = CulturalProfile(
        settlement_id="set_a",
        social_values={"compassion": 0.90, "warrior_tradition": 0.20},
    )
    cp_b = CulturalProfile(
        settlement_id="set_b",
        social_values={"compassion": 0.30, "warrior_tradition": 0.80},
    )

    class DummyRoute:
        active = True

    routes = {("set_a", "set_b"): DummyRoute()}
    profiles = {"set_a": cp_a, "set_b": cp_b}

    process_cultural_mixing({}, routes, profiles, mixing_rate=0.10)
    # cp_a should increase warrior_tradition and decrease compassion
    assert cp_a.social_values["warrior_tradition"] > 0.20
    assert cp_a.social_values["compassion"] < 0.90
    # cp_b should increase compassion and decrease warrior_tradition
    assert cp_b.social_values["compassion"] > 0.30
    assert cp_b.social_values["warrior_tradition"] < 0.80


# =============================================================================
# 13. R2.10: Religion-Culture Analytics
# =============================================================================
def test_religion_culture_analytics_report():
    rel = Religion(
        id="rel_sync",
        name="Syncretic Way",
        syncretic_parents=["p1", "p2"],
        borrowed_traits={"trait_1": "src_1"},
        holy_sites=[
            HolySite("s1", "High Shrine", "set_1", "Shrine", "Holy", 0, pilgrims_visited=40),
        ],
    )
    m = ReligiousMyth(
        myth_id="m_cult",
        religion_id=rel.id,
        root_event_id=1,
        hero_id="c_1",
        hero_name="Ancient Sage",
        stage=LoreStage.CULTURE,
        retellings=15,
        known_by_settlements={"set_1", "set_2"},
    )
    rel.myths.append(m)

    cp = CulturalProfile(
        settlement_id="set_1",
        social_values={"compassion": 0.8, "honor": 0.7},
        folk_traditions=[FolkTradition("f1", "Tree", FolkTraditionType.SACRED_TREE, "set_1", "Desc")],
        local_customs=[LocalCustom("c1", "Fest", CustomType.HARVEST_FESTIVAL, "set_1", 6, "Desc")],
    )

    report = generate_religious_analytics(
        religions={"rel_sync": rel},
        faiths={},
        settlements={"set_1": {}},
        living_characters=[],
        current_tick=120,
        cultural_profiles={"set_1": cp},
        myths=[m],
    )

    assert report.most_syncretic_religion is not None
    assert report.most_syncretic_religion["id"] == "rel_sync"
    assert report.most_syncretic_religion["syncretic_parents"] == 2
    assert report.most_syncretic_religion["borrowed_traits"] == 1

    assert report.most_diverse_culture is not None
    assert report.most_diverse_culture["settlement_id"] == "set_1"

    assert report.largest_pilgrimage_network is not None
    assert report.largest_pilgrimage_network["total_pilgrims_visited"] == 40

    assert report.most_influential_myth is not None
    assert report.most_influential_myth["stage"] == "Culture"
    assert report.most_influential_myth["transmissions"] == 15

    summary = format_religious_analytics_summary(report)
    assert "Most Syncretic Faith" in summary
    assert "Most Diverse Culture" in summary
    assert "Largest Pilgrimage Network" in summary
    assert "Most Influential Myth" in summary


# =============================================================================
# 14. 100-Year Live Simulation Integration (Unscripted Syncretism & Culture)
# =============================================================================
def test_100_year_unscripted_syncretism_and_culture():
    sim = Simulation(seed=42)
    sim.run_years(100)

    assert sim.religion_engine is not None
    assert sim.religion_engine.enabled is True

    # Check cultural profiles initialized for all settlements
    for s_id in ["set_oakhaven", "set_riverbend", "set_ironpeak"]:
        culture = sim.religion_engine.get_settlement_culture(s_id)
        assert culture is not None
        assert len(culture.social_values) >= 5
        assert len(culture.folk_traditions) >= 1
        assert len(culture.local_customs) >= 3

    # Check event log recorded notable cultural customs (first celebrations or post-dormancy)
    custom_events = [e for e in sim.event_log.all_events() if e.type == EventType.LOCAL_CUSTOM_CELEBRATED]
    assert len(custom_events) >= 5
    assert all(e.payload.get("is_first_celebration") or e.payload.get("is_resumed") for e in custom_events)

    # Analytics report verifies living faith dynamics
    report = sim.generate_religious_analytics()
    assert report is not None
    assert report.most_syncretic_religion is not None
    assert report.most_diverse_culture is not None
    assert report.largest_pilgrimage_network is not None
    assert report.most_influential_myth is not None
