"""
Procedural Template and Grammar Engine for Milestone L0 (No LLMs).

Provides deterministic text synthesis via combinatoric slot grammars,
vocabulary banks by literacy level, emotional perspective transformers,
and dynamic page formatting.
"""

from __future__ import annotations
import re
from typing import Any, Mapping, Optional, Sequence
from minemesis.core.rng import KeyedRNG
from minemesis.core.types import Intent
from minemesis.lore.lore_models import LiteracyLevel


def format_settlement_name(settlement_id: str) -> str:
    """Formats a settlement ID into a clean display name (e.g. 'set_ironwood' -> 'Ironwood')."""
    if not settlement_id:
        return "the settlement"
    if settlement_id.startswith("set_"):
        return settlement_id[4:].replace("_", " ").title()
    return settlement_id.replace("_", " ").title()


def clean_duplicate_words(text: str) -> str:
    """Removes accidental consecutive duplicate words (e.g. 'Covenant Covenant' -> 'Covenant')."""
    return re.sub(r'\b([A-Za-z]+)(?:\s+\1\b)+', r'\1', text, flags=re.IGNORECASE)


# =============================================================================
# Vocabulary Dictionaries by Literacy Tier
# =============================================================================
VOCABULARY = {
    LiteracyLevel.BASIC_LITERACY: {
        "died": ["died", "passed away", "is gone", "lost their breath"],
        "killed": ["was killed", "was struck down", "died in a fight"],
        "married": ["married", "took as wife", "took as husband", "joined together"],
        "born": ["was born", "came into the world", "arrived"],
        "feud": ["feud", "blood fight", "bad blood", "grudge"],
        "peace": ["peace", "made peace", "stopped fighting", "shook hands"],
        "trade": ["traded goods", "swapped grain and ore", "sent caravans"],
        "sad": ["very sad", "cried bitter tears", "miss them deeply"],
        "angry": ["angry", "bitter in heart", "will not forget"],
        "holy": ["good", "blessed", "holy"],
    },
    LiteracyLevel.EDUCATED: {
        "died": ["departed this mortal world", "breathed their last", "passed into eternal rest", "succumbed to fate"],
        "killed": ["fell in combat", "was tragically slain", "perished by violence", "met a violent end"],
        "married": ["was united in sacred matrimony", "pledged eternal vows", "formed an enduring marriage bond"],
        "born": ["was welcomed into life", "brought joy to the family", "entered the generational line"],
        "feud": ["bitter clan feud", "prolonged hostility", "unyielding vendetta", "grievous rivalry"],
        "peace": ["solemn armistice", "concord and reconciliation", "treaty of lasting peace", "restoration of harmony"],
        "trade": ["established prosperous commerce", "opened trade avenues", "conducted fruitful trade caravans"],
        "sad": ["overwhelmed with sorrow", "mourned with heavy hearts", "bore the weight of deep grief"],
        "angry": ["held deep indignation", "swore righteous vengeance", "nursed a solemn grievance"],
        "holy": ["sacred and revered", "sanctified", "divinely blessed", "hallowed"],
    },
    LiteracyLevel.SCHOLAR: {
        "died": ["succumbed to mortality", "concluded their earthly tenure", "perished under documented circumstances"],
        "killed": ["was mortally stricken during hostilities", "suffered fatal trauma in conflict"],
        "married": ["ratified a formal conjugal union", "contracted familial alliances via marriage"],
        "born": ["was recorded in the vital registers", "commenced biological lineage"],
        "feud": ["protracted inter-communal conflict", "formal state of belligerence", "retributive vendetta"],
        "peace": ["ratified a comprehensive peace treaty", "established diplomatic concord", "reconciliation accord"],
        "trade": ["instituted bilateral mercantile exchange", "facilitated inter-settlement commerce"],
        "sad": ["lamented with profound gravity", "incurred significant psychological sorrow"],
        "angry": ["maintained severe hostile dispositions", "demanded restitution under law"],
        "holy": ["theologically preeminent", "venerated canon", "hallowed tradition"],
    },
    LiteracyLevel.PRIEST: {
        "died": ["was called home by the divine powers", "surrendered their soul to the heavens", "crossed the veil of mortality"],
        "killed": ["was offered as a sacred sacrifice", "perished defending the righteous fold", "fell under dark trial"],
        "married": ["was sanctified under the holy rites", "joined hands before the altars of faith"],
        "born": ["received the spark of life from the creator", "was bestowed as a sacred blessing"],
        "feud": ["unholy strife of pride", "righteous trial of faith", "tribulation between souls"],
        "peace": ["blessed armistice bestowed by providence", "reconciliation under divine grace"],
        "trade": ["fellowship of honest stewardship", "sharing the fruits of righteous labor"],
        "sad": ["offered prayers through tears of grief", "found solace in divine mercy"],
        "angry": ["called down divine judgment", "prayed for righteous retribution"],
        "holy": ["most sacred and inviolable", "ordained by celestial decree", "anointed and holy"],
    },
    LiteracyLevel.HISTORIAN: {
        "died": ["is recorded as having died", "concluded their historical role", "passed away according to the annals"],
        "killed": ["was recorded as a casualty of warfare", "succumbed to violence during the historical campaign"],
        "married": ["formed a recorded marital alliance", "entered a documented union"],
        "born": ["was born, marking the start of their historical record", "entered the settlement census"],
        "feud": ["the documented historical feud", "the protracted hostilities of that era"],
        "peace": ["the historical armistice of that year", "the treaty formally concluding hostilities"],
        "trade": ["the establishment of documented trade corridors", "commercial integration between settlements"],
        "sad": ["an event producing widespread communal lamentation", "an era marked by widespread mourning"],
        "angry": ["instigating lasting historical grievances", "fueling generational animosity"],
        "holy": ["traditionally held as sacred in historical memory", "enshrined in religious annals"],
    },
}

# Fallback for Basic Literacy
VOCABULARY[LiteracyLevel.ILLITERATE] = VOCABULARY[LiteracyLevel.BASIC_LITERACY]


def get_term(literacy: LiteracyLevel, category: str, rng: KeyedRNG) -> str:
    """Returns a context-appropriate word or phrase for the given literacy tier."""
    vocab_tier = VOCABULARY.get(literacy, VOCABULARY[LiteracyLevel.EDUCATED])
    terms = vocab_tier.get(category, [category])
    return rng.choice(terms)


def resolve_participant_name(
    entity_id: str,
    characters: Optional[Mapping[str, Any]] = None,
    archive: Optional[Mapping[str, Any]] = None,
    default_role: str = "an unidentified assailant",
) -> str:
    """
    Resolves an entity or character ID into an authentic display name.
    If actor is missing or unrecorded, returns default_role (e.g. 'an unidentified assailant').
    Never invents fake placeholder characters like 'Master Thorne'.
    """
    if not entity_id or str(entity_id).strip() in ("", "None", "Unknown", "unknown", "someone", "Someone"):
        return default_role
    if characters and entity_id in characters:
        c = characters[entity_id]
        return getattr(c, "display_name", None) or getattr(c, "name", None) or getattr(c, "full_name", str(entity_id))
    if archive and entity_id in archive:
        arch = archive[entity_id]
        if isinstance(arch, dict):
            return arch.get("display_name") or arch.get("name") or str(entity_id)
        return getattr(arch, "display_name", None) or getattr(arch, "name", str(entity_id))
    if str(entity_id).startswith("set_"):
        return format_settlement_name(str(entity_id))
    if str(entity_id).startswith("rel_"):
        return format_religion_name(str(entity_id))
    return str(entity_id)


# =============================================================================
# Event Sentence Template Synthesis
# =============================================================================
def render_event_sentence(
    event_type_val: str,
    literacy: LiteracyLevel,
    context: Mapping[str, Any],
    perspective_bias: str,
    rng: KeyedRNG,
) -> str:
    """
    Synthesizes a descriptive sentence from an event record, author literacy,
    and subjective emotional perspective.
    """
    year = context.get("year", 1)
    tick = context.get("tick", 0)
    raw_actor = context.get("actor_name")
    if not raw_actor or str(raw_actor).strip() in ("", "None", "Unknown", "unknown", "Someone", "someone"):
        actor = "an unidentified assailant" if event_type_val in ("Death", "Raid", "Feud") else "an unidentified party"
    else:
        actor = str(raw_actor)

    raw_target = context.get("target_name")
    if not raw_target or str(raw_target).strip() in ("", "None", "Unknown", "unknown", "someone", "the house", "the realm", "the community"):
        target = "an unidentified party"
    else:
        target = str(raw_target)

    loc = format_settlement_name(str(context.get("location", "the settlement")))
    cause_desc = context.get("cause_desc", "unforeseen circumstances")

    # Perspective modifiers
    is_grudge = "Grudge" in perspective_bias or "Suspicious" in perspective_bias or "Hostile" in perspective_bias
    is_pious = "Pious" in perspective_bias or "Religious" in perspective_bias or "Devout" in perspective_bias
    is_family = "Family" in perspective_bias or "Kin" in perspective_bias

    if event_type_val == "Death":
        die_term = get_term(literacy, "died", rng)
        believed_intent = context.get("believed_intent")
        believed_actor = context.get("believed_actor")

        # Directive 5.2: Books read author beliefs rather than raw event reality
        if believed_intent == Intent.INTENTIONAL or (believed_intent is not None and str(believed_intent).lower() == "intentional"):
            killer = believed_actor or context.get("target_name") or "an unidentified assailant"
            if not killer or str(killer).strip() in ("", "None", "Unknown", "unknown", "an enemy"):
                killer = "an unidentified assailant"
            murder_templates = [
                f"In Year {year}, {actor} was murdered at {loc}. {killer} was believed responsible for the deliberate slaying.",
                f"Year {year}: {actor} fell to murder at {loc}, slain by {killer} in cold blood.",
                f"Tragedy struck in Year {year} when {actor} was murdered at {loc}; many held {killer} guilty of the crime.",
                f"The annals record that in Year {year}, {actor} was murdered at {loc}, a victim of {killer}'s malice.",
            ]
            return rng.choice(murder_templates)

        if is_grudge:
            templates = [
                f"In Year {year}, {actor} {die_term} at {loc}, though many whispered that dark hands and malice were responsible.",
                f"Word came in Year {year} that {actor} {die_term}. Our house refuses the convenient tale that it was merely an accident.",
                f"Year {year} saw {actor} {die_term} under contested circumstances at {loc}, deepening bitter suspicions and accusations of foul play.",
                f"The sudden end of {actor} in Year {year} at {loc} left our kin convinced that dark hands and deliberate malice took their life.",
                f"Though official voices called it an accident in Year {year}, we whispered that {actor} fell to covert enmity at {loc}.",
            ]
        elif is_pious:
            templates = [
                f"In the grace of Year {year}, {actor} {die_term} at {loc}, entering the realm of the ancestors and sacred spirits.",
                f"The heavens called {actor} home during Year {year} at {loc}. We lit sacred torches in solemn prayer.",
                f"Year {year}: {actor} {die_term} at {loc}. The sacred cycle moves onward according to divine decree.",
            ]
        elif is_family:
            sad_term = get_term(literacy, "sad", rng)
            templates = [
                f"In Year {year}, our beloved kin {actor} {die_term} at {loc}. Our hearth {sad_term}.",
                f"A day of dark sorrow in Year {year}: {actor} {die_term} at {loc}, leaving an enduring void among our kin.",
                f"Year {year} brought bitter grief when {actor} {die_term} at {loc}. We will hold their memory forever.",
            ]
        else:  # Objective / Chronicle
            templates = [
                f"In Year {year}, {actor} {die_term} at {loc} due to {cause_desc}.",
                f"Year {year} (Tick {tick}): The death of {actor} occurred at {loc}.",
                f"The annals record that in Year {year}, {actor} {die_term} at {loc}.",
            ]
        return rng.choice(templates)

    elif event_type_val == "Birth":
        born_term = get_term(literacy, "born", rng)
        if is_family or is_pious:
            templates = [
                f"In Year {year}, a blessed child, {actor}, {born_term} at {loc}, bringing great rejoicing to the family.",
                f"The family rejoiced in Year {year} as {actor} {born_term} under auspicious skies at {loc}.",
                f"Year {year} saw the arrival of {actor}, who {born_term} at {loc} to carry forward our ancestral bloodline.",
            ]
        else:
            templates = [
                f"In Year {year}, {actor} {born_term} at {loc}.",
                f"Year {year}: Birth of {actor} was registered at {loc}.",
                f"The records note that in Year {year}, {actor} was born at {loc}.",
            ]
        return rng.choice(templates)

    elif event_type_val == "Marriage":
        marr_term = get_term(literacy, "married", rng)
        templates = [
            f"In Year {year}, {actor} and {target} {marr_term} at {loc}, binding their houses together.",
            f"A joyous celebration in Year {year}: {actor} {marr_term} {target} at {loc}.",
            f"Year {year} witnessed the union of {actor} and {target} at {loc}.",
        ]
        return rng.choice(templates)

    elif event_type_val == "Feud":
        feud_term = get_term(literacy, "feud", rng)
        if is_grudge:
            templates = [
                f"In Year {year}, a bitter {feud_term} erupted between {actor} and {target} at {loc}. We swore never to yield.",
                f"Year {year}: The treachery of {target} sparked an unyielding {feud_term} with {actor} at {loc}.",
            ]
        else:
            templates = [
                f"In Year {year}, a {feud_term} commenced between {actor} and {target} at {loc}.",
                f"Year {year} marked the onset of hostilities between {actor} and {target} at {loc}.",
            ]
        return rng.choice(templates)

    elif event_type_val == "Raid":
        kill_term = get_term(literacy, "killed", rng)
        templates = [
            f"In Year {year}, raiders from {actor} fell upon {target} at {loc}, devastating storehouses and fields.",
            f"Year {year}: A violent raid by {actor} struck {loc}, leaving bitter scars upon {target}.",
            f"The annals document a destructive raid launched by {actor} against {target} at {loc} during Year {year}.",
        ]
        return rng.choice(templates)

    elif event_type_val == "Peace":
        peace_term = get_term(literacy, "peace", rng)
        templates = [
            f"In Year {year}, {actor} and {target} established {peace_term} at {loc}, formally bringing an end to bloodshed.",
            f"A restoration of calm in Year {year}: {peace_term} was agreed upon between {actor} and {target} at {loc}.",
            f"Year {year}: The factions of {actor} and {target} signed an accord of {peace_term} at {loc}.",
        ]
        return rng.choice(templates)

    elif event_type_val == "Pilgrimage":
        holy_term = get_term(literacy, "holy", rng)
        templates = [
            f"In Year {year}, {actor} undertook a devout pilgrimage to the {holy_term} site of {target} at {loc}.",
            f"Year {year}: Devout pilgrim {actor} completed their holy journey to {target} at {loc}.",
        ]
        return rng.choice(templates)

    elif event_type_val == "ReligiousSchism":
        templates = [
            f"In Year {year}, theological dissent fractured the faith at {loc}, establishing the breakaway sect {actor}.",
            f"Year {year}: A historic religious schism occurred at {loc}, as {actor} broke communion with mother doctrines.",
        ]
        return rng.choice(templates)

    elif event_type_val == "ReligiousSyncretism":
        templates = [
            f"In Year {year}, cohabiting traditions harmonized at {loc}, giving birth to the syncretic faith {actor}.",
            f"Year {year} witnessed the sacred fusion of faiths at {loc}, establishing the united path of {actor}.",
        ]
        return rng.choice(templates)

    elif event_type_val == "LocalCustomCelebrated":
        custom_name = context.get("custom_name", "the seasonal festival")
        templates = [
            f"In Year {year}, the folk of {loc} gathered to celebrate {custom_name} with communal rejoicing.",
            f"Year {year}: The solemn tradition of {custom_name} was observed at {loc}.",
        ]
        return rng.choice(templates)

    # General fallback
    return f"In Year {year}, the event of {event_type_val} was recorded regarding {actor} at {loc}."


# =============================================================================
# Dynamic Text Pagination (Minecraft Written Book Compatibility)
# =============================================================================
def paginate_text(
    paragraphs: Sequence[str],
    words_per_page: int = 120,
    max_words: int = 10000,
) -> tuple[list[str], int]:
    """
    Breaks a continuous manuscript into clean Minecraft-compatible pages.
    Enforces a hard limit of max_words (10,000 words max per book specification).
    Returns (pages, total_word_count).
    """
    pages: list[str] = []
    current_page_paras: list[str] = []
    current_page_words = 0
    total_words = 0

    for para in paragraphs:
        p_text = para.strip()
        if not p_text:
            continue

        p_words = len(p_text.split())

        # Check hard cap
        if total_words + p_words > max_words:
            # Truncate and close
            allowed = max_words - total_words
            truncated_p = " ".join(p_text.split()[:allowed]) + " ... [The manuscript ends here due to damaged parchment.]"
            current_page_paras.append(truncated_p)
            pages.append("\n\n".join(current_page_paras))
            total_words = max_words
            return pages, total_words

        if current_page_words + p_words > words_per_page and current_page_paras:
            # Finish current page
            pages.append("\n\n".join(current_page_paras))
            current_page_paras = [p_text]
            current_page_words = p_words
        else:
            current_page_paras.append(p_text)
            current_page_words += p_words

        total_words += p_words

    if current_page_paras:
        pages.append("\n\n".join(current_page_paras))

    if not pages:
        pages = ["(This book contains blank pages.)"]
        total_words = 5

    return pages, total_words
