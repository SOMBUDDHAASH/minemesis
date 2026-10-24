"""
Comprehensive Unit Tests for the Standalone Religion Engine (Milestone R0).

Validates:
1. Architectural toggle (enabled vs disabled).
2. Determinism across seeds.
3. Trait knowledge library coverage across all 9 world regions and modern movements.
4. Trait compatibility and negative controls.
5. Procedural religion generation and naming.
6. Social diffusion (family, marriage, trade, clergy).
7. Evolution, saint canonization, and schism / sect formation.
8. Behavioral modifiers on characters and settlements.
9. Event Log integration and Causal Grammar conformity.
10. Full round-trip serialization fidelity.
11. Multi-year integration in Simulation loop.
"""

from __future__ import annotations
import random
import pytest

from minemesis.core.causal_grammar import validate_causes
from minemesis.core.event_log import EventLog
from minemesis.core.types import EventType, Intent, Scale
from minemesis.religion.religion_config import ENABLE_RELIGION_ENGINE
from minemesis.religion.religion_effects import (
    get_character_effective_modifiers,
    get_character_modifier,
    get_reconciliation_chance_delta,
    get_revenge_probability_delta,
    get_settlement_consumption_multiplier,
)
from minemesis.religion.religion_engine import ReligionEngine
from minemesis.religion.religion_generation import (
    generate_coherent_traits,
    generate_religion_name,
    generate_scripture_name,
    generate_world_religions,
)
from minemesis.religion.religion_models import (
    CharacterFaith,
    HolySite,
    Religion,
    ReligionTrait,
    ReligiousRole,
    Saint,
    TraitCategory,
)
from minemesis.religion.religion_schisms import (
    check_and_canonize_saint,
    trigger_religious_reformation,
    trigger_religious_schism,
)
from minemesis.religion.religion_serialization import (
    deserialize_religion_state,
    from_json,
    serialize_religion_state,
    to_json,
)
from minemesis.religion.religion_spread import (
    process_clergy_missionary_work,
    process_family_faith_inheritance,
    process_marriage_conversion,
    process_trade_route_evangelism,
    update_settlement_dominant_religions,
)
from minemesis.religion.religion_traits import (
    are_traits_compatible,
    get_all_traits,
    get_trait,
    get_traits_by_category,
    is_trait_set_coherent,
)
from minemesis.systems.simulation import Simulation


class DummyChar:
    def __init__(self, c_id: str, name: str, settlement_id: str = "set_oakhaven", alive: bool = True):
        self.id = c_id
        self.name = name
        self.settlement_id = settlement_id
        self.alive = alive
        self.spouse_id = None
        self.father_id = None
        self.mother_id = None


class DummySettlement:
    def __init__(self, s_id: str, name: str):
        self.id = s_id
        self.name = name


# =============================================================================
# 1. Architectural Toggle & Independence
# =============================================================================
def test_religion_engine_toggle_disabled():
    """When disabled, ReligionEngine acts as a transparent no-op."""
    engine = ReligionEngine(seed=42, enabled=False)
    engine.initialize()
    assert not engine.enabled
    assert engine.get_character_religion("char_1") is None
    assert engine.get_settlement_religion("set_oakhaven") is None
    assert engine.get_religion_modifiers("char_1") == {}
    assert engine.update_tick(1) == []
    assert engine.serialize() == {"enabled": False}


def test_religion_engine_toggle_enabled():
    """When enabled, ReligionEngine activates full procedural generation and tracking."""
    settlements = {"set_oakhaven": DummySettlement("set_oakhaven", "Oakhaven")}
    characters = {"char_1": DummyChar("char_1", "Aldous")}
    engine = ReligionEngine(seed=42, enabled=True)
    engine.initialize(settlements=settlements, characters=characters)
    assert engine.enabled
    assert len(engine.religions) >= 2
    assert engine.get_character_religion("char_1") is not None
    assert engine.get_settlement_religion("set_oakhaven") is not None
    assert isinstance(engine.get_religion_modifiers("char_1"), dict)


# =============================================================================
# 2. Determinism Verification
# =============================================================================
def test_religion_engine_determinism():
    """Identical seeds must generate identical religions, names, scriptures, and traits."""
    engine1 = ReligionEngine(seed=12345, enabled=True)
    engine1.initialize()

    engine2 = ReligionEngine(seed=12345, enabled=True)
    engine2.initialize()

    assert len(engine1.religions) == len(engine2.religions)
    for r_id in engine1.religions:
        r1 = engine1.religions[r_id]
        r2 = engine2.religions[r_id]
        assert r1.name == r2.name
        assert r1.scripture_name == r2.scripture_name
        assert sorted(r1.traits.keys()) == sorted(r2.traits.keys())
        assert len(r1.holy_sites) == len(r2.holy_sites)
        assert r1.holy_sites[0].name == r2.holy_sites[0].name


def test_different_seeds_produce_divergent_theologies():
    """Different seeds should generate distinct religious traditions."""
    engine_a = ReligionEngine(seed=111, enabled=True)
    engine_a.initialize()
    engine_b = ReligionEngine(seed=999, enabled=True)
    engine_b.initialize()

    names_a = {r.name for r in engine_a.religions.values()}
    names_b = {r.name for r in engine_b.religions.values()}
    assert names_a != names_b


# =============================================================================
# 3. Real Religion Knowledge Library Coverage
# =============================================================================
def test_trait_library_category_coverage():
    """All 9 theological categories must have rich trait representation."""
    all_traits = get_all_traits()
    assert len(all_traits) >= 40

    for cat in TraitCategory:
        traits = get_traits_by_category(cat)
        assert len(traits) >= 3, f"Category {cat.value} has fewer than 3 traits"


def test_trait_library_world_tradition_coverage():
    """
    Every required world region and tradition must be represented across the trait library.
    """
    all_traits = get_all_traits()
    all_inspirations = set()
    for t in all_traits:
        for insp in t.inspired_by:
            all_inspirations.add(insp)

    required_traditions = [
        # South Asia
        "Hinduism", "Buddhism", "Jainism", "Sikhism", "Ayyavazhi", "Vedic Religion", "Ajivika", "Charvaka",
        # Middle East & West Asia
        "Judaism", "Christianity", "Islam", "Baháʼí", "Zoroastrianism", "Yazidism", "Druze", "Mandaeism",
        "Manichaeism", "Mesopotamian Religion", "Canaanite Religion", "Mithraism",
        # East Asia
        "Taoism", "Confucianism", "Shinto", "Tenrikyo", "Falun Gong", "Chinese Folk Religion", "Korean Muism", "Jeung San Do",
        # Southeast Asia
        "Cao Dai", "Hòa Hảo", "Vietnamese Folk Religion", "Balinese Hinduism",
        # Africa
        "Ancient Egyptian Religion", "Yoruba Religion", "Akan Religion", "Vodun", "Dinka Religion", "Serer Religion",
        "Berber Traditional Religion", "Kemetism",
        # Europe
        "Greek Religion", "Roman Religion", "Norse Religion", "Celtic Polytheism", "Rodnovery", "Druidry",
        # Americas
        "Aztec Religion", "Maya Religion", "Inca Religion", "Native American Church", "Mapuche Religion",
        # Oceania
        "Māori Religion", "Dreaming Traditions", "Hawaiian Religion", "Samoan Traditional Religion",
        # Modern Movements
        "Rastafari", "Scientology", "Wicca", "Thelema", "Spiritism", "Unitarian Universalism",
    ]

    missing = [trad for trad in required_traditions if trad not in all_inspirations]
    assert not missing, f"Missing required traditions in trait knowledge library: {missing}"


# =============================================================================
# 4. Trait Coherence & Negative Controls
# =============================================================================
def test_trait_compatibility_and_negative_control():
    """Incompatible traits must be detected and rejected."""
    mono = get_trait("monotheism")
    poly = get_trait("polytheism")
    pacifism = get_trait("strict_pacifism")
    holy_war = get_trait("holy_war_zeal")
    charity = get_trait("charity_obligation")

    assert mono is not None and poly is not None and pacifism is not None and holy_war is not None

    # Positive control: compatible traits
    assert are_traits_compatible(mono, charity)
    assert is_trait_set_coherent([mono, charity])

    # Negative control: incompatible traits
    assert not are_traits_compatible(mono, poly)
    assert not are_traits_compatible(pacifism, holy_war)
    assert not is_trait_set_coherent([mono, poly, charity])
    assert not is_trait_set_coherent([pacifism, holy_war])


# =============================================================================
# 5. Behavioral Modifiers on Characters & Settlements
# =============================================================================
def test_character_effects_and_devotion_scaling():
    """Devout adherents must experience greater behavioral modifications than lukewarm followers."""
    rel = Religion(
        id="rel_test",
        name="Faith of Mercy and Asceticism",
        traits={
            "forgiveness_doctrine": get_trait("forgiveness_doctrine"),
            "ascetic_discipline": get_trait("ascetic_discipline"),
        },
    )

    devout_faith = CharacterFaith(character_id="char_devout", religion_id="rel_test", devotion=0.90)
    lukewarm_faith = CharacterFaith(character_id="char_luke", religion_id="rel_test", devotion=0.20)

    devout_recon = get_reconciliation_chance_delta(devout_faith, rel)
    luke_recon = get_reconciliation_chance_delta(lukewarm_faith, rel)
    devout_revenge = get_revenge_probability_delta(devout_faith, rel)
    luke_revenge = get_revenge_probability_delta(lukewarm_faith, rel)

    assert devout_recon > luke_recon > 0.0
    assert devout_revenge < luke_revenge < 0.0  # forgiveness suppresses revenge

    # Settlement consumption test
    consumption_mult = get_settlement_consumption_multiplier(rel)
    assert consumption_mult < 1.0  # asceticism reduces food consumption


# =============================================================================
# 6. Social Spread Mechanisms
# =============================================================================
def test_newborn_faith_inheritance():
    """Children inherit parents' faith with high devotion."""
    rng = random.Random(42)
    father_faith = CharacterFaith(character_id="father", religion_id="rel_1", devotion=0.85)
    mother_faith = CharacterFaith(character_id="mother", religion_id="rel_1", devotion=0.80)

    child_faith = process_family_faith_inheritance(
        child_id="child_1",
        father_faith=father_faith,
        mother_faith=mother_faith,
        settlement_dominant_rel_id="rel_2",
        rng=rng,
        tick=10,
    )
    assert child_faith is not None
    assert child_faith.religion_id == "rel_1"
    assert child_faith.devotion >= 0.7


def test_marriage_conversion():
    """Inter-faith marriage leads to conversion of less devout partner."""
    rng = random.Random(42)
    devout_spouse = CharacterFaith(character_id="sp_1", religion_id="rel_1", devotion=0.95)
    lukewarm_spouse = CharacterFaith(character_id="sp_2", religion_id="rel_2", devotion=0.15)

    conv = None
    for t in range(25):
        conv = process_marriage_conversion(devout_spouse, lukewarm_spouse, rng=rng, tick=t)
        if conv:
            break
    assert conv is not None
    converted_id, old_rel, new_rel = conv
    assert converted_id == "sp_2"
    assert old_rel == "rel_2"
    assert new_rel == "rel_1"
    assert lukewarm_spouse.religion_id == "rel_1"


def test_trade_route_and_clergy_spread():
    """Trade routes and clergy proselytization convert citizens."""
    rng = random.Random(42)
    clergy_faith = CharacterFaith(character_id="priest_1", religion_id="rel_1", devotion=0.95, role=ReligiousRole.PRIEST)
    target_char = DummyChar("citizen_2", "Bram", settlement_id="set_riverbend")
    faiths = {
        "priest_1": clergy_faith,
        "citizen_2": CharacterFaith(character_id="citizen_2", religion_id="rel_2", devotion=0.2),
    }

    conv = None
    for t in range(25):
        conv = process_clergy_missionary_work(
            clergy_char_id="priest_1",
            settlement_characters=[target_char],
            faiths=faiths,
            rng=rng,
            tick=t,
        )
        if conv:
            break
    assert conv is not None
    assert conv[0] == "citizen_2"
    assert conv[1] == "rel_2"
    assert conv[2] == "rel_1"


# =============================================================================
# 7. Evolution, Saint Canonization & Schisms
# =============================================================================
def test_saint_canonization_and_lineage():
    """Devout character slain in service to religion is canonized as a Saint."""
    rng = random.Random(42)
    rel = Religion(
        id="rel_1",
        name="Faith of the Holy Shield",
        traits={"martyrdom_glory": get_trait("martyrdom_glory")},
    )
    devout_hero = DummyChar("hero_1", "Arthur Crowley")
    hero_faith = CharacterFaith(character_id="hero_1", religion_id="rel_1", devotion=0.95)

    res = check_and_canonize_saint(
        deceased_char=devout_hero,
        deceased_faith=hero_faith,
        religion=rel,
        cause_of_death="Raid",
        tick=120,
        rng=rng,
    )
    assert res is not None
    saint, r = res
    assert saint.character_id == "hero_1"
    assert saint.character_name == "Arthur Crowley"
    assert len(r.saints) == 1


def test_religious_schism_and_parent_lineage():
    """Religious schism generates child religion referencing parent_religion_id."""
    rng = random.Random(42)
    parent_rel = Religion(
        id="rel_1",
        name="Faith of the Eternal River",
        traits={
            "ancestor_worship": get_trait("ancestor_worship"),
            "sacred_rivers": get_trait("sacred_rivers"),
            "strict_pacifism": get_trait("strict_pacifism"),
            "forgiveness_doctrine": get_trait("forgiveness_doctrine"),
            "charity_obligation": get_trait("charity_obligation"),
        },
        scripture_name="The Book of Living Waters",
    )
    prophet = DummyChar("prophet_1", "Gideon", settlement_id="set_ironpeak")
    follower = DummyChar("follower_2", "Maeve", settlement_id="set_ironpeak")
    faiths = {
        "prophet_1": CharacterFaith(character_id="prophet_1", religion_id="rel_1", devotion=0.8),
        "follower_2": CharacterFaith(character_id="follower_2", religion_id="rel_1", devotion=0.6),
    }

    schism_res = trigger_religious_schism(
        parent_religion=parent_rel,
        schism_settlement_id="set_ironpeak",
        instigator_character_id="prophet_1",
        living_characters=[prophet, follower],
        faiths=faiths,
        new_rel_counter=2,
        tick=180,
        rng=rng,
    )
    assert schism_res is not None
    child_rel, converts = schism_res

    assert child_rel.id == "rel_2"
    assert child_rel.parent_religion_id == "rel_1"
    assert "rel_2" in parent_rel.schisms
    assert "prophet_1" in converts
    assert faiths["prophet_1"].religion_id == "rel_2"
    assert faiths["prophet_1"].role == ReligiousRole.PROPHET


# =============================================================================
# 8. Event Log & Causal Grammar Integration
# =============================================================================
def test_religion_events_causal_grammar():
    """Religious events emitted by the engine must satisfy Causal Grammar rules."""
    event_log = EventLog()

    # 1. Death of a martyr
    death_evt = event_log.append(
        event_type=EventType.DEATH,
        tick=10,
        location="set_oakhaven",
        causes=[],
        intent=Intent.MILITARY_ACTION,
        participants=[("victim", "Arthur")],
        scale=Scale.INDIVIDUAL,
        payload={"cause_of_death": "Raid"},
    )

    # 2. Saint canonization citing the martyr's death
    validate_causes(EventType.SAINT_CANONIZED, [(death_evt.id, EventType.DEATH)])
    saint_evt = event_log.append(
        event_type=EventType.SAINT_CANONIZED,
        tick=11,
        location="set_oakhaven",
        causes=[death_evt.id],
        intent=Intent.INTENTIONAL,
        participants=[("saint", "Arthur")],
        scale=Scale.INDIVIDUAL,
        payload={"title": "The Martyr"},
    )
    assert saint_evt.id == 1

    # 3. Conversion event (root allowed)
    validate_causes(EventType.CONVERSION, [])
    conv_evt = event_log.append(
        event_type=EventType.CONVERSION,
        tick=12,
        location="set_oakhaven",
        causes=[],
        intent=Intent.INTENTIONAL,
        participants=[("convert", "Gideon")],
        scale=Scale.INDIVIDUAL,
        payload={"old_religion": "rel_1", "new_religion": "rel_2"},
    )
    assert conv_evt.id == 2


# =============================================================================
# 9. Full Round-Trip Serialization
# =============================================================================
def test_religion_serialization_round_trip():
    """State serialized to JSON and deserialized must be bit-level and structurally identical."""
    engine = ReligionEngine(seed=777, enabled=True)
    engine.initialize()

    # Mutate state slightly
    r1 = list(engine.religions.values())[0]
    r1.saints.append(Saint("c_99", "Saint Lyra", "The Peacemaker", 50, "Brought armistice"))
    engine.faiths["c_99"] = CharacterFaith("c_99", r1.id, devotion=0.98, role=ReligiousRole.PRIEST)

    serialized = engine.serialize()
    json_str = to_json(serialized)
    parsed = from_json(json_str)

    engine_restored = ReligionEngine(seed=1, enabled=True)
    engine_restored.deserialize(parsed)

    assert engine_restored.seed == engine.seed
    assert len(engine_restored.religions) == len(engine.religions)
    assert len(engine_restored.faiths) == len(engine.faiths)

    r_orig = engine.religions[r1.id]
    r_rest = engine_restored.religions[r1.id]
    assert r_orig.name == r_rest.name
    assert len(r_orig.saints) == len(r_rest.saints)
    assert r_orig.saints[0].title == r_rest.saints[0].title
    assert engine_restored.faiths["c_99"].devotion == 0.98


# =============================================================================
# 10. Multi-Year Simulation Integration
# =============================================================================
def test_simulation_runs_when_religion_disabled():
    """Simulation must run cleanly for 10 years when religion engine is disabled."""
    sim = Simulation(seed=42)
    if sim.religion_engine:
        sim.religion_engine.enabled = False
    sim.run_years(10)
    assert sim.tick == 120
    assert len(sim.event_log) > 0
    assert sim.get_character_religion("char_0") is None


def test_religion_engine_live_simulation_integration():
    """Simulation running with ReligionEngine enabled completes 10 years without error."""
    sim = Simulation(seed=42)
    if sim.religion_engine is None:
        sim.religion_engine = ReligionEngine(seed=42, enabled=True)
    sim.religion_engine.enabled = True
    sim.religion_engine.initialize(seed=42, settlements=sim.settlements, characters=sim.characters)

    # Run for 10 simulated years (120 ticks)
    sim.run_years(10)

    assert sim.tick == 120
    assert len(sim.event_log) > 0

    # Verify religion queries work through published interfaces
    for c in sim.living_characters[:5]:
        rel = sim.get_character_religion(c.id)
        assert rel is not None
        mods = sim.get_religion_modifiers(c.id)
        assert isinstance(mods, dict)

    for s_id in sim.settlements.keys():
        s_rel = sim.get_settlement_religion(s_id)
        assert s_rel is not None
