"""
Unit and Integration Test Suite for Milestone R1: Religion Becomes History.

Validates all 10 Milestone R1 sub-systems:
R1.1 Religious Interpretation Layer
R1.2 Religious Tension System
R1.3 Religion Family Tree
R1.4 Great Religious Figures
R1.5 Religious Heresy Engine
R1.6 Sacred Geography
R1.7 Myth Creation
R1.8 Religious Virtue System
R1.9 Dynamic Spread (Refugees, Pilgrimages, Saint Cults, Conquests)
R1.10 Religious Analytics & History Generation
"""

import random
import pytest
from minemesis.core.event_log import Event, EventLog
from minemesis.core.types import EventType, Intent, Scale
from minemesis.models.belief import Belief
from minemesis.models.character import Character
from minemesis.models.settlement import Settlement
from minemesis.religion.religion_analytics import (
    calculate_settlement_diversity_index,
    format_religion_family_tree,
    format_religious_analytics_summary,
    generate_religious_analytics,
)
from minemesis.religion.religion_config import ENABLE_RELIGION_ENGINE
from minemesis.religion.religion_engine import ReligionEngine
from minemesis.religion.religion_figures import (
    evaluate_martyrdom,
    evaluate_prophet_or_mystic_emergence,
)
from minemesis.religion.religion_geography import (
    HolySiteType,
    generate_holy_site,
    process_pilgrimage_economic_benefit,
)
from minemesis.religion.religion_heresies import (
    check_and_declare_heresy,
    establish_heretical_schism,
    evaluate_counter_reformation,
    evaluate_sect_reunification,
)
from minemesis.religion.religion_interpretation import apply_religious_interpretation_filter
from minemesis.religion.religion_models import (
    CharacterFaith,
    HolySite,
    LoreStage,
    Religion,
    ReligionTrait,
    ReligiousFigureType,
    ReligiousRelationshipType,
    ReligiousRole,
    TraitCategory,
)
from minemesis.religion.religion_myths import (
    create_initial_story_from_event,
    retell_and_evolve_myths,
)
from minemesis.religion.religion_spread import (
    process_conquest_conversion,
    process_religious_refugee_migration,
    process_saint_cult_conversions,
)
from minemesis.religion.religion_tensions import (
    calculate_religious_relationship_modifier,
    calculate_settlement_religious_tension,
    get_religious_relationship,
)
from minemesis.religion.religion_traits import ALL_RELIGION_TRAITS, get_trait
from minemesis.religion.religion_virtues import evaluate_action_against_virtues
from minemesis.systems.simulation import Simulation


def create_dummy_character(char_id: str, name: str, settlement_id: str = "set_oakhaven") -> Character:
    return Character(
        id=char_id,
        first_name=name,
        last_name="Test",
        settlement_id=settlement_id,
        age_ticks=240,
        sex="M",
    )


# -----------------------------------------------------------------------------
# R1.1 Religious Interpretation Layer Tests
# -----------------------------------------------------------------------------
def test_religious_interpretation_divergence():
    """Validates that identical Death events are interpreted differently through distinct religious filters."""
    char = create_dummy_character("c1", "Aidan")
    base_belief = Belief(
        belief_id=1,
        believer_id="c1",
        event_ref=10,
        source="Witnessed",
        source_character_id=None,
        confidence=1.0,
        tick_acquired=50,
        believed_type=EventType.DEATH,
        believed_intent=Intent.INTENTIONAL,
        believed_actor="c2",
        believed_target="c3",
        believed_location="set_oakhaven",
    )

    # 1. Ancestor Worship Faith
    ancestor_rel = Religion(id="rel_anc", name="Ancestral Faith")
    t_anc = get_trait("ancestor_worship")
    assert t_anc is not None
    ancestor_rel.add_trait(t_anc)
    faith_anc = CharacterFaith(character_id="c1", religion_id="rel_anc", devotion=0.9)

    b_anc = apply_religious_interpretation_filter(
        belief=base_belief,
        observer=char,
        faith=faith_anc,
        religion=ancestor_rel,
        event_intent=Intent.INTENTIONAL,
    )
    assert b_anc.believed_payload["theological_framing"] == "ANCESTOR_WRATH"

    # 2. Reincarnation Faith
    reincarn_rel = Religion(id="rel_rein", name="Eternal Cycle")
    t_rein = get_trait("reincarnation")
    assert t_rein is not None
    reincarn_rel.add_trait(t_rein)
    faith_rein = CharacterFaith(character_id="c1", religion_id="rel_rein", devotion=0.9)

    b_rein = apply_religious_interpretation_filter(
        belief=base_belief,
        observer=char,
        faith=faith_rein,
        religion=reincarn_rel,
        event_intent=Intent.INTENTIONAL,
    )
    assert b_rein.believed_payload["theological_framing"] == "NATURAL_CYCLE"

    # 3. Divine Judgment Faith
    judgment_rel = Religion(id="rel_judge", name="Divine Law")
    t_judge = get_trait("apocalyptic_judgment")
    assert t_judge is not None
    judgment_rel.add_trait(t_judge)
    faith_judge = CharacterFaith(character_id="c1", religion_id="rel_judge", devotion=0.9)

    b_judge = apply_religious_interpretation_filter(
        belief=base_belief,
        observer=char,
        faith=faith_judge,
        religion=judgment_rel,
        event_intent=Intent.INTENTIONAL,
    )
    assert b_judge.believed_payload["theological_framing"] == "DIVINE_PUNISHMENT"

    # 4. Sacred Martyrdom Faith
    martyr_rel = Religion(id="rel_martyr", name="Holy Flame")
    t_martyr = get_trait("martyrdom_glory")
    assert t_martyr is not None
    martyr_rel.add_trait(t_martyr)
    faith_martyr = CharacterFaith(character_id="c1", religion_id="rel_martyr", devotion=0.9)

    b_martyr = apply_religious_interpretation_filter(
        belief=base_belief,
        observer=char,
        faith=faith_martyr,
        religion=martyr_rel,
        event_intent=Intent.INTENTIONAL,
    )
    assert b_martyr.believed_payload["theological_framing"] == "SACRED_SACRIFICE"


# -----------------------------------------------------------------------------
# R1.2 Religious Tension System Tests
# -----------------------------------------------------------------------------
def test_religious_tension_and_sectarian_rivalry():
    """Validates that divergent sects experience sectarian friction more intensely than distant faiths."""
    rel_root = Religion(id="rel_river", name="River Faith")
    rel_sect = Religion(
        id="rel_river_reformed",
        name="River Reformed Faith",
        parent_religion_id="rel_river",
        generation=1,
    )
    rel_root.child_religion_ids.append("rel_river_reformed")
    all_rels = {"rel_river": rel_root, "rel_river_reformed": rel_sect}

    # Verify classification as DivergentSect
    rel_type = get_religious_relationship(rel_root, rel_sect, all_rels)
    assert rel_type == ReligiousRelationshipType.DIVERGENT_SECT

    # Verify relationship modifiers produce trust penalty and hatred offset
    faith_a = CharacterFaith(character_id="c1", religion_id="rel_river", devotion=0.8)
    faith_b = CharacterFaith(character_id="c2", religion_id="rel_river_reformed", devotion=0.8)

    t_off, h_off, f_off, r_type = calculate_religious_relationship_modifier(
        faith_a, faith_b, rel_root, rel_sect, all_rels
    )
    assert r_type == ReligiousRelationshipType.DIVERGENT_SECT
    assert t_off < -10.0  # Trust penalty
    assert h_off > 10.0   # Sectarian hatred bonus


def test_settlement_religious_tension_calculation():
    """Validates that multiple conflicting sects within a village generate high sectarian tension."""
    c1 = create_dummy_character("c1", "Aidan", "set_oakhaven")
    c2 = create_dummy_character("c2", "Bera", "set_oakhaven")
    c3 = create_dummy_character("c3", "Cedric", "set_oakhaven")

    rel1 = Religion(id="rel_1", name="Orthodox River")
    rel2 = Religion(id="rel_2", name="Schismatic River", parent_religion_id="rel_1")
    rel1.child_religion_ids.append("rel_2")
    all_rels = {"rel_1": rel1, "rel_2": rel2}

    faiths = {
        "c1": CharacterFaith("c1", "rel_1", 0.9),
        "c2": CharacterFaith("c2", "rel_2", 0.9),
        "c3": CharacterFaith("c3", "rel_2", 0.8),
    }

    tension = calculate_settlement_religious_tension("set_oakhaven", [c1, c2, c3], faiths, all_rels)
    assert tension > 40.0


# -----------------------------------------------------------------------------
# R1.3 Religion Family Tree Tests
# -----------------------------------------------------------------------------
def test_religion_family_tree_genealogy():
    """Validates multi-generational religion lineage and ASCII tree printing."""
    r_root = Religion(id="rel_root", name="Ancient River Faith")
    r_gen1 = Religion(id="rel_gen1", name="Northern Reform Movement", parent_religion_id="rel_root", generation=1)
    r_gen2 = Religion(id="rel_gen2", name="Temple Restoration Sect", parent_religion_id="rel_gen1", generation=2)
    r_gen3 = Religion(id="rel_gen3", name="Pilgrim Revival Sect", parent_religion_id="rel_gen2", generation=3)

    r_root.child_religion_ids.append("rel_gen1")
    r_gen1.child_religion_ids.append("rel_gen2")
    r_gen2.child_religion_ids.append("rel_gen3")

    rels = {r.id: r for r in (r_root, r_gen1, r_gen2, r_gen3)}

    assert r_gen3.is_descendant_of("rel_root", rels) is True
    assert r_gen3.is_descendant_of("rel_gen1", rels) is True
    assert r_gen3.get_root_ancestor_id(rels) == "rel_root"
    assert r_gen3.get_lineage_path(rels) == ["rel_root", "rel_gen1", "rel_gen2", "rel_gen3"]

    tree_str = format_religion_family_tree("rel_root", rels)
    assert "Ancient River Faith" in tree_str
    assert "Northern Reform Movement" in tree_str
    assert "Temple Restoration Sect" in tree_str
    assert "Pilgrim Revival Sect" in tree_str


# -----------------------------------------------------------------------------
# R1.4 Great Religious Figures Tests
# -----------------------------------------------------------------------------
def test_martyrdom_and_prophet_emergence():
    """Validates emergence of Martyrs upon combat death and Prophets during religious crises."""
    char = create_dummy_character("c_hero", "Thorin", "set_oakhaven")
    rel = Religion(id="rel_1", name="Sacred Covenant")
    faith = CharacterFaith(character_id="c_hero", religion_id="rel_1", devotion=0.9, role=ReligiousRole.PRIEST)
    figure_counter = [1]

    # Combat death in raid creates a Martyr
    martyr = evaluate_martyrdom(
        deceased_char=char,
        deceased_faith=faith,
        religion=rel,
        cause_type=EventType.RAID,
        death_event_id=101,
        tick=45,
        figure_counter=figure_counter,
    )
    assert martyr is not None
    assert martyr.figure_type == ReligiousFigureType.MARTYR
    assert len(rel.figures) == 1
    assert len(rel.saints) == 1  # Posthumously canonized

    # Living devout follower becomes a Prophet
    c_survivor = create_dummy_character("c_survivor", "Elowen", "set_oakhaven")
    s_faith = CharacterFaith(character_id="c_survivor", religion_id="rel_1", devotion=0.85)
    rng = random.Random(42)
    fig = evaluate_prophet_or_mystic_emergence(
        candidates=[c_survivor],
        faiths={"c_survivor": s_faith},
        religion=rel,
        trigger_event_id=101,
        tick=46,
        rng=rng,
        figure_counter=figure_counter,
    )
    assert fig is not None
    assert fig.figure_type in (ReligiousFigureType.PROPHET, ReligiousFigureType.MYSTIC)


# -----------------------------------------------------------------------------
# R1.5 Religious Heresy Engine Tests
# -----------------------------------------------------------------------------
def test_heresy_schism_counter_reformation_and_reunification():
    """Validates the full cycle: Heresy -> Schism -> Counter-Reformation -> Reunification."""
    rng = random.Random(123)
    c1 = create_dummy_character("c1", "Luther", "set_oakhaven")
    c2 = create_dummy_character("c2", "Follower1", "set_oakhaven")
    c3 = create_dummy_character("c3", "Follower2", "set_oakhaven")

    parent_rel = Religion(id="rel_parent", name="Church of the River")
    t1 = get_trait("monotheism")
    t2 = get_trait("forgiveness_doctrine")
    assert t1 and t2
    parent_rel.add_trait(t1)
    parent_rel.add_trait(t2)

    faiths = {
        "c1": CharacterFaith("c1", "rel_parent", devotion=0.9, role=ReligiousRole.PRIEST),
        "c2": CharacterFaith("c2", "rel_parent", devotion=0.7),
        "c3": CharacterFaith("c3", "rel_parent", devotion=0.6),
    }

    # 1. Heresy Declaration
    heresy_res = check_and_declare_heresy(
        religion=parent_rel,
        settlement_characters=[c1, c2, c3],
        faiths=faiths,
        all_traits=ALL_RELIGION_TRAITS,
        tick=60,
        rng=rng,
        figure_counter=[1],
    )
    assert heresy_res is not None
    heretic_fig, followers, adopted_trait, h_payload = heresy_res
    assert heretic_fig.figure_type == ReligiousFigureType.HERETIC

    # 2. Breakaway Schism
    child_rel, schism_payload = establish_heretical_schism(
        parent_religion=parent_rel,
        heretic_fig=heretic_fig,
        follower_ids=followers,
        adopted_trait_id=adopted_trait,
        faiths=faiths,
        all_traits=ALL_RELIGION_TRAITS,
        rel_counter=[2],
        tick=61,
        rng=rng,
    )
    assert child_rel.parent_religion_id == parent_rel.id
    assert child_rel.id in parent_rel.child_religion_ids
    assert child_rel.generation == parent_rel.generation + 1
    assert faiths["c1"].religion_id == child_rel.id

    # 3. Counter-Reformation by Orthodox Mother Church
    cr_payload = evaluate_counter_reformation(
        parent_religion=parent_rel,
        child_religion=child_rel,
        all_traits=ALL_RELIGION_TRAITS,
        tick=62,
        rng=rng,
    )
    assert cr_payload is not None
    assert parent_rel.reformation_level >= 1
    assert len(parent_rel.reforms) >= 1

    # 4. Sectarian Reunification after long separation
    all_rels = {parent_rel.id: parent_rel, child_rel.id: child_rel}
    reun_res = evaluate_sect_reunification(
        rel_a=parent_rel,
        rel_b=child_rel,
        all_religions=all_rels,
        faiths=faiths,
        tick=300,
        rng=rng,
    )
    assert reun_res is not None
    assert (child_rel.is_extinct or parent_rel.is_extinct) is True


# -----------------------------------------------------------------------------
# R1.6 Sacred Geography Tests
# -----------------------------------------------------------------------------
def test_sacred_geography_and_pilgrimages():
    """Validates creation of holy sites and trade prosperity stimulated by pilgrimages."""
    rel = Religion(id="rel_geo", name="Mountain Faith")
    rng = random.Random(999)

    site, payload = generate_holy_site(
        religion=rel,
        settlement_id="set_ironpeak",
        site_type=HolySiteType.SACRED_MOUNTAIN,
        tick=20,
        site_counter=[1],
        rng=rng,
    )
    assert site.site_type == HolySiteType.SACRED_MOUNTAIN.value
    assert len(rel.holy_sites) == 1

    # Pilgrimage economic boost
    active_routes = {tuple(sorted(["set_oakhaven", "set_ironpeak"])): True}
    econ = process_pilgrimage_economic_benefit(
        pilgrim_home_id="set_oakhaven",
        holy_site_settlement_id="set_ironpeak",
        active_trade_routes=active_routes,
        rng=rng,
    )
    assert econ is not None
    assert econ["prosperity_bonus"] > 0.0


# -----------------------------------------------------------------------------
# R1.7 Myth Creation Tests
# -----------------------------------------------------------------------------
def test_myth_creation_and_evolution_pipeline():
    """Validates Event -> Story -> Legend -> Myth distortion pipeline."""
    rel = Religion(id="rel_myth", name="Sun Faith")
    hero = create_dummy_character("c_warrior", "Gareth")
    evt = Event(
        id=55,
        type=EventType.DEATH,
        tick=10,
        location="set_riverbend",
        causes=[],
        intent=Intent.INTENTIONAL,
        participants=[("victim", "Gareth")],
        scale=Scale.INDIVIDUAL,
        payload={"cause": "Raid defense"},
    )
    rng = random.Random(42)

    # Initial Story
    myth, m_payload = create_initial_story_from_event(
        religion=rel,
        event=evt,
        hero=hero,
        objective_summary="Gareth died defending the river crossing.",
        tick=10,
        myth_counter=[1],
    )
    assert myth.stage == LoreStage.STORY
    assert "defending the river crossing" in myth.objective_truth

    # Advance ~15 years (180 ticks): evolves to LEGEND
    retell_and_evolve_myths(rel, current_tick=190, rng=rng)
    assert myth.stage == LoreStage.LEGEND
    assert len(myth.embellishments) > 1

    # Advance ~45 years (550 ticks): evolves to MYTH with supernatural narrative
    retell_and_evolve_myths(rel, current_tick=560, rng=rng)
    assert myth.stage == LoreStage.MYTH
    assert "The Sacred Myth of Gareth" in myth.mythic_narrative


# -----------------------------------------------------------------------------
# R1.8 Religious Virtue System Tests
# -----------------------------------------------------------------------------
def test_religious_virtue_and_moral_standing():
    """Validates moral standing shifts based on action alignment with faith virtues."""
    char = create_dummy_character("c_devout", "Sister Sarah")
    rel = Religion(id="rel_virtue", name="Faith of Merciful Peace")
    t_forgive = get_trait("forgiveness_doctrine")
    assert t_forgive is not None
    rel.add_trait(t_forgive)

    faith = CharacterFaith(character_id="c_devout", religion_id="rel_virtue", devotion=0.8, religious_standing=50.0)

    # 1. Initiating peace increases standing in a forgiveness faith
    delta, reason = evaluate_action_against_virtues(
        character=char,
        faith=faith,
        religion=rel,
        action_type=EventType.PEACE,
        action_role="initiator",
        action_payload={},
    )
    assert delta > 0.0
    assert faith.religious_standing == 70.0

    # 2. Seeking revenge murder drops standing drastically
    delta_rev, reason_rev = evaluate_action_against_virtues(
        character=char,
        faith=faith,
        religion=rel,
        action_type=EventType.DEATH,
        action_role="actor",
        action_payload={"revenge_for_death_id": 99},
    )
    assert delta_rev < 0.0
    assert faith.religious_standing == 45.0


# -----------------------------------------------------------------------------
# R1.9 Dynamic Spread Tests (Refugees, Saint Cults, Conquests)
# -----------------------------------------------------------------------------
def test_refugee_migration_and_saint_cult_spread():
    """Validates minority flight from sectarian unrest and saint cult conversions."""
    c_refugee = create_dummy_character("c_ref", "Refugee Ruth", "set_oakhaven")
    faiths = {"c_ref": CharacterFaith("c_ref", "rel_minority", devotion=0.7)}
    settlements = {
        "set_oakhaven": Settlement("set_oakhaven", "Oakhaven", 0, 0),
        "set_sanctuary": Settlement("set_sanctuary", "Sanctuary", 10, 10),
    }
    dominant = {"set_oakhaven": "rel_majority", "set_sanctuary": "rel_minority"}
    rng = random.Random(42)

    # Refugee flight triggered by high tension (>50.0)
    ref_res = process_religious_refugee_migration(
        settlement_id="set_oakhaven",
        settlement_tension=75.0,
        settlement_characters=[c_refugee],
        settlements=settlements,
        faiths=faiths,
        dominant_by_settlement=dominant,
        rng=rng,
        tick=50,
    )
    assert ref_res is not None
    refugee, old_set, new_set, rel_id = ref_res
    assert old_set == "set_oakhaven"
    assert new_set == "set_sanctuary"
    assert rel_id == "rel_minority"


# -----------------------------------------------------------------------------
# R1.10 Religious Analytics & 100-Year Chronicle Tests
# -----------------------------------------------------------------------------
def test_religious_analytics_and_100_year_unscripted_history():
    """
    Validates that a 100-year simulation with ReligionEngine produces
    rich emergent, unscripted religious history milestones.
    """
    sim = Simulation(seed=101)
    sim.run_years(100)

    assert sim.religion_engine is not None
    assert sim.religion_engine.enabled is True

    # Generate analytics report
    report = sim.generate_religious_analytics()
    assert report is not None
    assert report.largest_religion is not None
    assert len(report.settlement_diversity_indices) == len(sim.settlements)

    # Format chronicle and summary
    summary_md = format_religious_analytics_summary(report)
    assert "Religious History & Analytics Report" in summary_md
    assert "Simpson's Index" in summary_md

    # Check religious event diversity in the event log
    all_types = {e.type.value for e in sim.event_log.all_events()}
    assert any(t in all_types for t in ["Conversion", "SaintCanonized", "HolySiteDiscovered", "Pilgrimage", "MythRecorded"])
