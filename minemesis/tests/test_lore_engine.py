"""
Test Suite for Procedural Literature Engine (Milestone L0).

Validates:
1. Genre Coverage: All 9 book genres generated procedurally from simulation state.
2. Subjective Perspective & Bias: Same event yields divergent accounts across son, priest, historian, and court.
3. Literacy Levels: Vocabulary and syntactic complexity scale across literacy tiers.
4. Minecraft Compatibility: Page splitting, lore tags, character limits, and 10,000-word hard cap.
5. Settlement Libraries & Archive Devastation: Multi-repository cataloging and raid damage memory loss.
6. Determinism: Byte-identical book generation across runs with identical seed.
7. End-to-End Simulation Integration: Multi-year run with active lore generation and memory formation.
"""

import random
import pytest

from minemesis.core.causal_grammar import validate_causes
from minemesis.core.event_log import Event, EventLog
from minemesis.core.rng import KeyedRNG
from minemesis.core.types import BeliefSource, EventType, Intent, Scale
from minemesis.models.belief import Belief
from minemesis.lore.lore_engine import LoreEngine
from minemesis.lore.lore_generators import (
    generate_biography,
    generate_family_history,
    generate_historical_chronicle,
    generate_legal_record,
    generate_local_folklore,
    generate_myth_collection,
    generate_personal_journal,
    generate_religious_text,
    generate_travel_account,
)
from minemesis.lore.lore_libraries import LibraryManager
from minemesis.lore.lore_models import BookGenre, LibraryType, LiteracyLevel
from minemesis.lore.lore_templates import paginate_text, render_event_sentence
from minemesis.models.character import Character
from minemesis.religion.religion_models import CustomType, FolkTradition, FolkTraditionType, HolySite, LocalCustom, ReligiousMyth, SiteTier
from minemesis.systems.simulation import Simulation


def _create_dummy_character(
    char_id: str,
    first_name: str,
    last_name: str,
    settlement_id: str = "set_ironwood",
    age_years: int = 35,
    sex: str = "M",
    suspicion: float = 0.2,
    forgiveness: float = 0.5,
) -> Character:
    return Character(
        id=char_id,
        first_name=first_name,
        last_name=last_name,
        settlement_id=settlement_id,
        age_ticks=age_years * 12,
        sex=sex,
        alive=True,
        suspicion=suspicion,
        forgiveness=forgiveness,
    )


class DummyTrait:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description


class DummyReligion:
    def __init__(self, rel_id: str = "rel_river", name: str = "River Faith"):
        self.id = rel_id
        self.name = name
        self.scripture_name = f"The River Canon of {name}"
        self.traits = {
            "sacred_waters": DummyTrait("Sacred Waters", "All rivers carry divine cleansing power.")
        }
        self.holy_sites = [
            HolySite(
                id="site_1",
                name="Spring of Whispers",
                settlement_id="set_ironwood",
                site_type="SacredRiver",
                significance="Primary sacred spring",
                founded_tick=12,
                tier=SiteTier.REGIONAL_PILGRIMAGE_SITE,
            )
        ]
        self.myths = [
            ReligiousMyth(
                myth_id="myth_001",
                religion_id=rel_id,
                root_event_id=1,
                hero_id="c1",
                hero_name="Elder Rowan",
                mythic_narrative="Rowan parted the swollen waters during the ancient deluge.",
                embellishments=["parted the floodwaters", "heard the voice of the deep river"],
                known_by_settlements={"set_ironwood"},
            )
        ]


class DummyCulturalProfile:
    def __init__(self, settlement_id: str = "set_ironwood"):
        self.settlement_id = settlement_id
        self.folk_traditions = [
            FolkTradition(
                id="ft_1",
                name="Guardian of the Timber",
                tradition_type=FolkTraditionType.VILLAGE_SPIRIT,
                settlement_id=settlement_id,
                significance="Forest spirit protecting lumberjacks",
            )
        ]
        self.local_customs = [
            LocalCustom(
                id="lc_1",
                name="River Lantern Feast",
                custom_type=CustomType.HARVEST_FESTIVAL,
                settlement_id=settlement_id,
                season_month=6,
                description="Releasing floating lanterns downriver at summer solstice",
            )
        ]


# =============================================================================
# 1. All 9 Genres Procedural Generation
# =============================================================================
def test_all_nine_book_genres_generation():
    rng = random.Random(12345)
    char1 = _create_dummy_character("c1", "Rowan", "Ironwood", age_years=60)
    char2 = _create_dummy_character("c2", "Kaelen", "Ironwood", age_years=30)
    religion = DummyReligion()
    culture = DummyCulturalProfile()

    # 1. Family History
    b_fam = generate_family_history(
        book_id="b_fam",
        family_name="Ironwood",
        patriarch_or_author=char1,
        kin_characters=[char1, char2],
        family_events=[],
        tick=120,
        rng=rng,
        literacy=LiteracyLevel.EDUCATED,
    )
    assert b_fam.genre == BookGenre.FAMILY_HISTORY
    assert "House Ironwood" in b_fam.title
    assert len(b_fam.pages) >= 1

    # 2. Personal Journal
    b_jour = generate_personal_journal(
        book_id="b_jour",
        character=char2,
        memories=[],
        beliefs=[],
        relationships={},
        tick=120,
        rng=rng,
        literacy=LiteracyLevel.BASIC_LITERACY,
    )
    assert b_jour.genre == BookGenre.PERSONAL_JOURNAL
    assert "Personal Journal of Kaelen Ironwood" in b_jour.title

    # 3. Religious Text
    b_rel = generate_religious_text(
        book_id="b_rel",
        religion=religion,
        author=char1,
        tick=120,
        rng=rng,
        literacy=LiteracyLevel.PRIEST,
    )
    assert b_rel.genre == BookGenre.RELIGIOUS_TEXT
    assert "Sacred Waters" in b_rel.full_text()

    # 4. Myth Collection
    b_myth = generate_myth_collection(
        book_id="b_myth",
        religion=religion,
        author=char1,
        myths=religion.myths,
        tick=120,
        rng=rng,
        literacy=LiteracyLevel.PRIEST,
    )
    assert b_myth.genre == BookGenre.MYTH_COLLECTION
    assert "Song of Elder Rowan" in b_myth.full_text()

    # 5. Historical Chronicle
    log = EventLog()
    evt1 = log.append(
        tick=24,
        location="set_ironwood",
        event_type=EventType.TRADE_ROUTE_FOUNDED,
        participants=[("initiator", "set_ironwood"), ("partner", "set_glen")],
        causes=[],
        intent=Intent.INTENTIONAL,
        scale=Scale.AGGREGATE,
        payload={"volume": 10},
    )
    b_chron = generate_historical_chronicle(
        book_id="b_chron",
        settlement_id="set_ironwood",
        events=[evt1],
        author_name=char1.full_name,
        author_id=char1.id,
        tick=120,
        rng=rng,
        literacy=LiteracyLevel.HISTORIAN,
    )
    assert b_chron.genre == BookGenre.HISTORICAL_CHRONICLE
    assert "Great Chronicle" in b_chron.title

    # 6. Local Folklore
    b_folk = generate_local_folklore(
        book_id="b_folk",
        cultural_profile=culture,
        author=char1,
        tick=120,
        rng=rng,
        literacy=LiteracyLevel.EDUCATED,
    )
    assert b_folk.genre == BookGenre.LOCAL_FOLKLORE
    assert "Guardian of the Timber" in b_folk.full_text()

    # 7. Legal Record
    evt_death = log.append(
        tick=60,
        location="set_ironwood",
        event_type=EventType.DEATH,
        participants=[("deceased", "c_victim")],
        causes=[],
        intent=Intent.ACCIDENTAL,
        scale=Scale.INDIVIDUAL,
        payload={"cause_of_death": "forestry accident"},
    )
    b_leg = generate_legal_record(
        book_id="b_leg",
        event=evt_death,
        author_name=char1.full_name,
        author_id=char1.id,
        tick=120,
        rng=rng,
        literacy=LiteracyLevel.SCHOLAR,
    )
    assert b_leg.genre == BookGenre.LEGAL_RECORD
    assert "Official Inquest" in b_leg.title

    # 8. Travel Account
    b_trav = generate_travel_account(
        book_id="b_trav",
        pilgrim=char2,
        holy_site_name="Spring of Whispers",
        holy_site_settlement="set_ironwood",
        tick=120,
        rng=rng,
        literacy=LiteracyLevel.EDUCATED,
    )
    assert b_trav.genre == BookGenre.TRAVEL_ACCOUNT
    assert "Pilgrim's Journey" in b_trav.title

    # 9. Biography
    b_bio = generate_biography(
        book_id="b_bio",
        subject=char1,
        author=char2,
        subject_events=[evt1],
        tick=120,
        rng=rng,
        literacy=LiteracyLevel.HISTORIAN,
    )
    assert b_bio.genre == BookGenre.BIOGRAPHY
    assert "Life and Deeds of Rowan Ironwood" in b_bio.title


# =============================================================================
# 2. Subjective Perspectives: Same Event Rendered Divergently
# =============================================================================
def test_subjective_perspectives_on_identical_event():
    """
    Validates that the identical underlying reality (accidental death in the forest)
    is recorded with starkly differing perspectives and vocabulary depending on authorship.
    """
    rng = random.Random(999)
    ctx = {
        "year": 4,
        "tick": 48,
        "actor_name": "Kaelen Ironwood",
        "target_name": "the forestry workgroup",
        "location": "set_ironwood",
        "cause_desc": "forestry accident",
    }

    # Son with grudge/suspicion
    son_text = render_event_sentence(
        event_type_val="Death",
        literacy=LiteracyLevel.BASIC_LITERACY,
        context=ctx,
        perspective_bias="Son Grudge Suspicious",
        rng=rng,
    )
    assert any(term in son_text.lower() for term in ["malice", "dark hands", "accident", "suspicions", "whispered"])

    # Devout Priest
    priest_text = render_event_sentence(
        event_type_val="Death",
        literacy=LiteracyLevel.PRIEST,
        context=ctx,
        perspective_bias="Devout Priestly Sanctity",
        rng=rng,
    )
    assert any(term in priest_text.lower() for term in ["ancestors", "sacred", "heavens", "prayer", "divine", "soul", "mortal"])

    # Objective Historian
    historian_text = render_event_sentence(
        event_type_val="Death",
        literacy=LiteracyLevel.HISTORIAN,
        context=ctx,
        perspective_bias="Objective",
        rng=rng,
    )
    assert any(term in historian_text.lower() for term in ["record", "annals", "died", "passed", "death of"])


# =============================================================================
# 3. Literacy Levels Influence Vocabulary
# =============================================================================
def test_literacy_level_vocabulary_scaling():
    rng = random.Random(42)
    ctx = {
        "year": 10,
        "actor_name": "Settlement Alpha",
        "target_name": "Settlement Beta",
        "location": "set_alpha",
    }

    basic_sentence = render_event_sentence(
        event_type_val="Peace",
        literacy=LiteracyLevel.BASIC_LITERACY,
        context=ctx,
        perspective_bias="Objective",
        rng=rng,
    )
    scholar_sentence = render_event_sentence(
        event_type_val="Peace",
        literacy=LiteracyLevel.SCHOLAR,
        context=ctx,
        perspective_bias="Objective",
        rng=rng,
    )

    # Basic literacy uses simpler words like "peace" or "shook hands"
    # Scholar uses formal words like "accord", "treaty", "diplomatic concord", "armistice"
    assert len(scholar_sentence.split()) >= len(basic_sentence.split()) or "accord" in scholar_sentence or "treaty" in scholar_sentence


# =============================================================================
# 4. Minecraft Compatibility & Hard Word Cap
# =============================================================================
def test_minecraft_compatibility_and_word_cap():
    # Long text exceeding words_per_page
    paras = [f"This is paragraph number {i} detailing historical events with several interesting words." for i in range(50)]
    pages, word_count = paginate_text(paras, words_per_page=50, max_words=10000)

    assert len(pages) > 1
    assert word_count > 100

    # Test hard cap enforcement
    huge_paras = ["word " * 500 for _ in range(30)]  # 15,000 words
    capped_pages, capped_count = paginate_text(huge_paras, words_per_page=100, max_words=10000)
    assert capped_count <= 10000
    assert "manuscript ends here" in capped_pages[-1].lower()

    # Test Minecraft JSON schema
    char = _create_dummy_character("c1", "Elspeth", "Vance")
    b = generate_personal_journal(
        book_id="b_test",
        character=char,
        memories=[],
        beliefs=[],
        relationships={},
        tick=12,
        rng=random.Random(1),
    )
    mc_json = b.to_minecraft_json()
    assert "title" in mc_json and len(mc_json["title"]) <= 32
    assert "author" in mc_json and len(mc_json["author"]) <= 16
    assert "pages" in mc_json and isinstance(mc_json["pages"], list)
    assert "generation" in mc_json
    assert "lore" in mc_json


# =============================================================================
# 5. Settlement Libraries and Archive Devastation
# =============================================================================
def test_library_archive_storage_and_raid_damage():
    manager = LibraryManager()
    rng = random.Random(777)
    char = _create_dummy_character("c1", "Goran", "Stone")

    b1 = generate_personal_journal("b1", char, [], [], {}, 12, rng)
    b2 = generate_personal_journal("b2", char, [], [], {}, 24, rng)
    b3 = generate_personal_journal("b3", char, [], [], {}, 36, rng)

    manager.add_book(b1, LibraryType.TOWN_ARCHIVE)
    manager.add_book(b2, LibraryType.TOWN_ARCHIVE)
    manager.add_book(b3, LibraryType.TOWN_ARCHIVE)

    assert len(manager.get_settlement_books("set_ironwood", LibraryType.TOWN_ARCHIVE)) == 3

    # Damage archive with high damage ratio (1.0 -> guarantees damage or destruction)
    damaged = manager.damage_archive("set_ironwood", damage_ratio=1.0, rng=rng)
    assert len(damaged) > 0
    # Remaining or damaged books must reflect damage flag
    for b in damaged:
        assert b.is_damaged is True


# =============================================================================
# 6. Byte-Identical Determinism
# =============================================================================
def test_byte_identical_determinism_across_identical_seeds():
    sim1 = Simulation(seed=4242)
    sim1.run_years(5)

    sim2 = Simulation(seed=4242)
    sim2.run_years(5)

    # Validate Event Log exact parity
    events1 = sim1.event_log.all_events()
    events2 = sim2.event_log.all_events()
    assert len(events1) == len(events2)
    for e1, e2 in zip(events1, events2):
        assert e1.id == e2.id
        assert e1.type == e2.type
        assert e1.payload == e2.payload

    # Validate Books exact parity
    books1 = sim1.lore_engine.library_manager.get_all_books()
    books2 = sim2.lore_engine.library_manager.get_all_books()
    assert len(books1) == len(books2)
    for b1, b2 in zip(books1, books2):
        assert b1.id == b2.id
        assert b1.title == b2.title
        assert b1.author_id == b2.author_id
        assert b1.full_text() == b2.full_text()


# =============================================================================
# 7. End-to-End Simulation Integration & Causal Grammar Validation
# =============================================================================
def test_full_simulation_with_lore_engine_enabled():
    sim = Simulation(seed=9876)
    sim.run_years(10)

    # Check that books were penned across multiple genres
    all_books = sim.lore_engine.library_manager.get_all_books()
    assert len(all_books) >= 3

    genres = {b.genre for b in all_books}
    assert len(genres) >= 2

    # Check BOOK_WRITTEN events in event log
    book_events = [e for e in sim.event_log.all_events() if e.type == EventType.BOOK_WRITTEN]
    assert len(book_events) >= len(all_books)
    # The difference represents books physically destroyed in raids (cultural amnesia)
    destroyed_count = len(book_events) - len(all_books)
    assert destroyed_count >= 0

    # Check Minecraft export helper on Simulation
    first_book = all_books[0]
    mc_book = sim.export_minecraft_book(first_book.id)
    assert mc_book is not None
    assert "pages" in mc_book


# =============================================================================
# 8. Books Read Author Beliefs Rather Than Raw Event Reality (Directive 5.2)
# =============================================================================
def test_books_read_author_beliefs_not_raw_reality():
    """
    Directive 5.2: Books cite and synthesize from author beliefs rather than raw event reality.
    If the author believes an accidental death was intentional murder, the book text reflects murder.
    Includes negative control.
    """
    rng = KeyedRNG(42, "test_author_beliefs")
    deceased = _create_dummy_character("c_deceased", "Aethelgard", "Ironwood", age_years=60)
    author_objective = _create_dummy_character("c_auth_obj", "Rowan", "Oak", age_years=40)
    author_suspicious = _create_dummy_character("c_auth_susp", "Varek", "Crow", age_years=40)

    # Raw event reality: Accidental death in a forestry accident
    raw_death_event = Event(
        id=101,
        tick=24,
        location="set_ironwood",
        type=EventType.DEATH,
        participants=[("deceased", "c_deceased")],
        causes=[],
        intent=Intent.ACCIDENTAL,
        scale=Scale.INDIVIDUAL,
        payload={"cause_of_death": "forestry mishap with falling timber"},
    )

    # Author Objective has belief reflecting reality (Accidental)
    belief_accidental = Belief(
        belief_id=1,
        believer_id=author_objective.id,
        event_ref=101,
        source=BeliefSource.WITNESSED,
        source_character_id=None,
        confidence=0.9,
        tick_acquired=24,
        believed_type=EventType.DEATH,
        believed_intent=Intent.ACCIDENTAL,
        believed_actor=None,
        believed_target="c_deceased",
        believed_location="set_ironwood",
        believed_payload={"cause_of_death": "forestry mishap with falling timber"},
    )

    # Author Suspicious believes it was intentional murder by Cormac
    belief_murder = Belief(
        belief_id=2,
        believer_id=author_suspicious.id,
        event_ref=101,
        source=BeliefSource.INFERRED,
        source_character_id=None,
        confidence=0.95,
        tick_acquired=25,
        believed_type=EventType.DEATH,
        believed_intent=Intent.INTENTIONAL,
        believed_actor="Cormac Blackwood",
        believed_target="c_deceased",
        believed_location="set_ironwood",
        believed_payload={"cause_of_death": "murder"},
    )

    # 1. Author with objective belief writes biography
    book_objective = generate_biography(
        book_id="b_obj",
        subject=deceased,
        author=author_objective,
        subject_events=[raw_death_event],
        tick=36,
        rng=rng,
        literacy=LiteracyLevel.HISTORIAN,
        author_beliefs={101: belief_accidental},
    )
    obj_text = book_objective.full_text().lower()

    # 2. Author with suspicious belief writes biography
    book_suspicious = generate_biography(
        book_id="b_susp",
        subject=deceased,
        author=author_suspicious,
        subject_events=[raw_death_event],
        tick=36,
        rng=rng,
        literacy=LiteracyLevel.HISTORIAN,
        author_beliefs={101: belief_murder},
    )
    susp_text = book_suspicious.full_text().lower()

    # Positive assertions:
    assert ("murder" in susp_text or "slain" in susp_text)
    assert "cormac blackwood" in susp_text
    assert ("murder" not in obj_text and "slain" not in obj_text)

    # Negative control:
    # If the system ignored beliefs and read only raw event reality, both texts would be identical
    # and neither would mention murder or Cormac Blackwood.
    raw_book = generate_biography(
        book_id="b_raw",
        subject=deceased,
        author=author_suspicious,
        subject_events=[raw_death_event],
        tick=36,
        rng=rng,
        literacy=LiteracyLevel.HISTORIAN,
        author_beliefs=None,  # No beliefs provided -> falls back to raw reality
    )
    raw_text = raw_book.full_text().lower()
    assert "cormac blackwood" not in raw_text
    assert "murder" not in raw_text and "slain" not in raw_text
