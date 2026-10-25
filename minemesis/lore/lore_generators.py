"""
Procedural Document Generators for Milestone L0 (No LLMs).

Synthesizes 9 distinct procedural book genres from simulation state:
1. Family Histories (lineage, patriarchs, births, marriages, feuds)
2. Personal Journals (memories, beliefs, grudges, affections, goals)
3. Religious Texts (theology, virtues, taboos, rituals, divine decrees)
4. Myth Collections (sacred stories, legends, oral traditions, culture)
5. Historical Chronicles (settlement annals, trade, raids, peace)
6. Local Folklore (spirit guardians, sacred groves, annual festivals)
7. Legal & Dispute Records (inquests, treaties, armistices, charters)
8. Travel & Pilgrimage Accounts (holy journeys, caravan routes)
9. Biographies (life accounts of chiefs, saints, martyrs, prophets)
"""

from __future__ import annotations
from typing import Any, Mapping, Optional, Sequence

from minemesis.core.rng import KeyedRNG
from minemesis.core.types import EventType, Intent
from minemesis.lore.lore_models import Book, BookGenre, LiteracyLevel
from minemesis.lore.lore_templates import (
    clean_duplicate_words,
    format_settlement_name,
    get_term,
    paginate_text,
    render_event_sentence,
)
from minemesis.core.event_log import Event
from minemesis.models.character import Character


# =============================================================================
# 1. Family Histories
# =============================================================================
def generate_family_history(
    book_id: str,
    family_name: str,
    patriarch_or_author: Character,
    kin_characters: Sequence[Character],
    family_events: Sequence[Event],
    tick: int,
    rng: KeyedRNG,
    literacy: LiteracyLevel = LiteracyLevel.EDUCATED,
    author_beliefs: Optional[Mapping[int, Any]] = None,
) -> Book:
    """
    Compiles an authoritative family chronicle documenting lineage,
    hearth founding, births, marriages, departed forebears, and feuds.
    Synthesizes historical milestones from author beliefs when available.
    """
    author = patriarch_or_author
    year = (tick // 12) + 1
    title = f"Chronicle of House {family_name}"
    sources = [e.id for e in family_events]
    perspective_bias = f"House {family_name} Kin Perspective"
    seed_val = rng.randint(0, 10**9) if hasattr(rng, "randint") else (tick * 1000 + hash(book_id) % 1000)

    def _render() -> list[str]:
        render_rng = KeyedRNG(seed_val, "book_render")
        paras: list[str] = []
        auth_set = format_settlement_name(author.settlement_id)

        # Title & Prologue
        paras.append(
            f"# {title}\n"
            f"Penned by {author.full_name} in Year {year} at {auth_set}.\n\n"
            f"Let it be known to all descendants who read these lines: this book sets forth "
            f"the true record of our blood and hearth, that our lineage may endure unforgotten."
        )

        # Section 1: The Founders and Hearth
        paras.append(
            f"## The Roots of House {family_name}\n"
            f"Our blood was established in the settlement of {auth_set}. "
            f"Through toil in the soil, the forest, and the stone, our forebears carved "
            f"a homestead of honor. {len(kin_characters)} kin have shared our hearth in these annals."
        )

        # Section 2: Lineage Roster
        roster_lines = []
        for k in sorted(kin_characters, key=lambda c: (c.age_ticks, c.id), reverse=True):
            status = f"Living (Age {k.age_years})" if k.alive else "Departed this life"
            roster_lines.append(f"- **{k.full_name}**: {status}, settlement of {k.settlement_id}.")
        paras.append("## Family Lineage & Generations\n" + "\n".join(roster_lines))

        # Section 3: Historical Family Milestones
        paras.append("## Family Annals & Recorded Milestones")
        sorted_events = sorted(family_events, key=lambda e: e.tick)
        if sorted_events:
            for evt in sorted_events:
                b = author_beliefs.get(evt.id) if author_beliefs else None
                b_intent = getattr(b, "believed_intent", None)
                b_actor = getattr(b, "believed_actor", None)
                b_target = getattr(b, "believed_target", None)
                b_loc = getattr(b, "believed_location", None)

                actor_name = b_actor if (b and b_actor) else (evt.participants[0][1] if evt.participants else family_name)
                target_name = b_target if (b and b_target) else (evt.participants[1][1] if len(evt.participants) > 1 else "the house")
                loc_name = format_settlement_name(b_loc) if (b and b_loc) else format_settlement_name(evt.location)

                cause_desc = evt.payload.get("cause_of_death") or evt.payload.get("reason", "unforeseen fate")
                if b_intent == Intent.INTENTIONAL:
                    cause_desc = f"murder attributed to {b_actor or 'an enemy'}"

                ctx = {
                    "year": (evt.tick // 12) + 1,
                    "tick": evt.tick,
                    "actor_name": actor_name,
                    "target_name": target_name,
                    "location": loc_name,
                    "cause_desc": cause_desc,
                    "believed_intent": b_intent,
                    "believed_actor": b_actor,
                }
                sentence = render_event_sentence(
                    event_type_val=evt.type.value,
                    literacy=literacy,
                    context=ctx,
                    perspective_bias="Family Kin",
                    rng=render_rng,
                )
                paras.append(sentence)
        else:
            paras.append("Our years have been blessed with quiet labor upon the homestead.")

        # Epilogue
        paras.append(
            f"May our descendants honor these records, keep faith with our kin, "
            f"and never let the hearth fires of House {family_name} grow cold."
        )

        pages, _ = paginate_text(paras, words_per_page=120)
        return pages

    est_words = 120 + len(kin_characters) * 15 + len(family_events) * 25
    return Book(
        id=book_id,
        title=title,
        author_id=author.id,
        author_name=author.full_name,
        author_literacy=literacy,
        genre=BookGenre.FAMILY_HISTORY,
        settlement_id=author.settlement_id,
        creation_tick=tick,
        creation_year=year,
        sources=sources,
        perspective_bias=perspective_bias,
        total_word_count=est_words,
        lazy_renderer=_render,
    )


# =============================================================================
# 2. Personal Journals
# =============================================================================
def generate_personal_journal(
    book_id: str,
    character: Character,
    memories: Sequence[Any],
    beliefs: Sequence[Any],
    relationships: Mapping[str, Any],
    tick: int,
    rng: KeyedRNG,
    literacy: LiteracyLevel = LiteracyLevel.BASIC_LITERACY,
) -> Book:
    """
    Synthesizes a deeply subjective personal journal reflecting the author's
    memories, private suspicions, grief, love, and spiritual reflections.
    """
    year = (tick // 12) + 1
    title = f"The Personal Journal of {character.full_name}"
    sources = [getattr(b, "event_ref", 0) for b in beliefs]
    bias = "Subjective Personal Bias"
    if character.suspicion > 0.6:
        bias = "Deep Grudge & Paranoia Bias"
    elif character.forgiveness > 0.6:
        bias = "Forgiving & Reconciling Bias"

    def _render() -> list[str]:
        paras: list[str] = []
        loc_clean = format_settlement_name(character.settlement_id)
        paras.append(
            f"# {title}\n"
            f"Private diary kept by {character.full_name} at {loc_clean}, Year {year}.\n\n"
            f"I set down these private reflections so my heart may find peace."
        )

        # Grudges and Suspicions (Directive 3: at least 4 varied templates)
        suspicious_beliefs = [b for b in beliefs if getattr(b, "believed_intent", None) == Intent.INTENTIONAL]
        if suspicious_beliefs:
            paras.append("## Reflections of Sorrow & Suspicion")
            journal_suspicion_variants = [
                "I cannot shake the conviction that {actor} acted with malice. The folk call it chance, but in my soul, I know what occurred.",
                "They tell me {actor} had no ill intent, yet every rumor and glance tells a different story. I will not be blinded by pleasant lies.",
                "Dark whispers surround the deeds of {actor}. Though no magistrate lays charges, our blood demands vigilance and memory.",
                "My heart remains hardened against {actor}. The wound is too deep to call it mere misfortune; too many coincidences favor their gain.",
            ]
            for b in suspicious_beliefs[:5]:
                actor = getattr(b, "believed_actor", "A hidden enemy")
                template = rng.choice(journal_suspicion_variants)
                paras.append(template.format(actor=actor) + " I hold this truth close, though I must bide my time.")

        # Sentiments toward other characters
        if relationships:
            paras.append("## Of Friends and Adversaries")
            for target_id, rel in list(relationships.items())[:4]:
                affinity = getattr(rel, "affinity", 0.0)
                target_name = getattr(rel, "target_id", target_id)
                if affinity > 20.0:
                    paras.append(f"My bond with {target_name} remains strong. In troubled seasons, they are a true anchor.")
                elif affinity < -20.0:
                    paras.append(f"There is coldness and bitter distrust between myself and {target_name}. I watch my back when they are near.")

        # Recent Emotional Memories
        if memories:
            paras.append("## Memories of Recent Seasons")
            for m in sorted(memories, key=lambda m: getattr(m, "tick_formed", 0), reverse=True)[:5]:
                emo = getattr(m, "emotion", "Grief")
                emo_val = emo.value if hasattr(emo, "value") else str(emo)
                paras.append(f"The feeling of {emo_val} still lingers within me when I think upon past days.")

        # Closing
        paras.append(f"Recorded by my own hand at {loc_clean}, Year {year}.")

        pages, _ = paginate_text(paras, words_per_page=90)
        return pages

    est_words = 90 + len(memories) * 15 + len(beliefs) * 20
    return Book(
        id=book_id,
        title=title,
        author_id=character.id,
        author_name=character.full_name,
        author_literacy=literacy,
        genre=BookGenre.PERSONAL_JOURNAL,
        settlement_id=character.settlement_id,
        creation_tick=tick,
        creation_year=year,
        sources=sources,
        perspective_bias=bias,
        total_word_count=est_words,
        lazy_renderer=_render,
    )


# =============================================================================
# 3. Religious Texts & Holy Scriptures
# =============================================================================
def generate_religious_text(
    book_id: str,
    religion: Any,
    author: Character,
    tick: int,
    rng: KeyedRNG,
    literacy: LiteracyLevel = LiteracyLevel.PRIEST,
) -> Book:
    """
    Compiles canonical scriptures, theological doctrine, sacred commandments,
    virtues, taboos, and ritual duties for a religion.
    """
    year = (tick // 12) + 1
    scripture_title = getattr(religion, "scripture_name", f"The Sacred Precepts of {religion.name}")
    sites = list(getattr(religion, "holy_sites", []))
    traits = dict(getattr(religion, "traits", {}))

    def _render() -> list[str]:
        paras: list[str] = []

        paras.append(
            f"# {scripture_title}\n"
            f"Transcribed by {author.full_name}, devout servant of {religion.name}.\n"
            f"Consecrated in Year {year} at {author.settlement_id}.\n\n"
            f"Hear, O seekers of truth: these are the sacred tenets revealed to the faithful, "
            f"ordained before the dawn of memory."
        )

        # Core Traits & Cosmology
        paras.append("## Cosmological Foundations")
        for t_id, trait in traits.items():
            paras.append(f"### {trait.name}\n{trait.description}")

        # Moral Virtues & Ethical Obligations
        paras.append(
            "## Sacred Virtues & Holy Obligations\n"
            "Let every soul walk in righteousness according to these holy commandments:\n"
            "- **Reverence**: Guard the sanctity of holy grounds and observe seasonal feasts.\n"
            "- **Honor**: Fulfill every oath pledged before the divine witness.\n"
            "- **Fellowship**: Share grain and succor with the afflicted during days of trial."
        )

        # Sacred Taboos
        paras.append(
            "## Inviolable Taboos\n"
            "Whoever commits these abominations shall forfeit their standing among the faithful:\n"
            "- Defilement of ancestral graves and sacred groves.\n"
            "- Cowardice and oath-breaking before kin.\n"
            "- Spilling of innocent blood within sacred borders."
        )

        # Holy Sites and Pilgrimages
        if sites:
            paras.append("## Sanctuaries of Pilgrimage\n"
                         "Let the devout journey to these hallowed places to revitalize their spirit:")
            for s in sites:
                paras.append(f"- **{s.name}** at {s.settlement_id}: {s.significance} (Tier: {s.tier.value}).")

        # Closing benediction
        paras.append(f"Thus it is written in {religion.name}. May the celestial light preserve our people forever.")

        pages, _ = paginate_text(paras, words_per_page=130)
        return pages

    est_words = 130 + len(traits) * 35 + len(sites) * 20
    return Book(
        id=book_id,
        title=scripture_title,
        author_id=author.id,
        author_name=author.full_name,
        author_literacy=literacy,
        genre=BookGenre.RELIGIOUS_TEXT,
        settlement_id=author.settlement_id,
        creation_tick=tick,
        creation_year=year,
        sources=[s.founded_tick for s in sites],
        perspective_bias=f"Orthodox Theology of {religion.name}",
        total_word_count=est_words,
        lazy_renderer=_render,
    )


# =============================================================================
# 4. Myth Collections
# =============================================================================
def generate_myth_collection(
    book_id: str,
    religion: Any,
    author: Character,
    myths: Sequence[Any],
    tick: int,
    rng: KeyedRNG,
    literacy: LiteracyLevel = LiteracyLevel.PRIEST,
) -> Book:
    """
    Compiles foundational legends, ancestor transformations, and oral myths
    into a structured anthology of living tradition.
    """
    year = (tick // 12) + 1
    title = f"The Mythic Lore of {religion.name}"
    myth_list = list(myths)

    def _render() -> list[str]:
        paras: list[str] = []

        paras.append(
            f"# {title}\n"
            f"Collected and preserved by {author.full_name} at {author.settlement_id}, Year {year}.\n\n"
            f"This volume gathers the ancient stories, heroic legends, and sacred myths "
            f"chanted across the fires of our people."
        )

        if myth_list:
            for m in myth_list:
                paras.append(f"## {m.myth_id.upper()}: The Song of {m.hero_name}")
                paras.append(f"**Stage of Memory:** {m.stage.value} (Retold {m.retellings} times across generations)")
                paras.append(f"{m.mythic_narrative}")
                if m.embellishments:
                    emb_list = ", ".join(m.embellishments)
                    paras.append(f"*Oral Embellishments:* {emb_list}.")
                paras.append(f"*Known in Settlements:* {', '.join(sorted(m.known_by_settlements))}.")
        else:
            paras.append("The elders recount that the great heroes walk silently among us, awaiting their bards.")

        pages, _ = paginate_text(paras, words_per_page=120)
        return pages

    est_words = 80 + len(myth_list) * 60
    return Book(
        id=book_id,
        title=title,
        author_id=author.id,
        author_name=author.full_name,
        author_literacy=literacy,
        genre=BookGenre.MYTH_COLLECTION,
        settlement_id=author.settlement_id,
        creation_tick=tick,
        creation_year=year,
        sources=[getattr(m, "root_event_id", 0) for m in myth_list],
        perspective_bias=f"Mythological Canon of {religion.name}",
        total_word_count=est_words,
        lazy_renderer=_render,
    )


# =============================================================================
# 5. Historical Chronicles
# =============================================================================
def generate_historical_chronicle(
    book_id: str,
    settlement_id: str,
    events: Sequence[Event],
    author_name: str,
    author_id: str,
    tick: int,
    rng: KeyedRNG,
    literacy: LiteracyLevel = LiteracyLevel.HISTORIAN,
    author_beliefs: Optional[Mapping[int, Any]] = None,
) -> Book:
    """
    Compiles a settlement chronicle from the Event Log,
    recording foundational events, chiefs, trade, raids, and peace treaties.
    Synthesizes entries from author beliefs when available.
    """
    year = (tick // 12) + 1
    clean_set = settlement_id.replace("set_", "").capitalize()
    title = f"The Great Chronicle of {clean_set}"
    event_list = list(events)
    beliefs_snapshot = dict(author_beliefs) if author_beliefs else None
    seed_val = rng.randint(0, 10**9) if hasattr(rng, "randint") else (tick * 1000 + hash(book_id) % 1000)

    def _render() -> list[str]:
        render_rng = KeyedRNG(seed_val, "book_render")
        paras: list[str] = []

        paras.append(
            f"# {title}\n"
            f"Official annals recorded by {author_name}, Chief Scribe of {clean_set}.\n"
            f"Completed in Year {year} of the settlement era.\n\n"
            f"This official chronicle compiles the historical annals of {clean_set}, "
            f"preserving recorded events for future generations."
        )

        events_by_year: dict[int, list[Event]] = {}
        for e in event_list:
            y = (e.tick // 12) + 1
            events_by_year.setdefault(y, []).append(e)

        for y in sorted(events_by_year.keys()):
            paras.append(f"## Annals of Year {y:02d}")
            year_events = events_by_year[y]
            for evt in year_events:
                b = beliefs_snapshot.get(evt.id) if beliefs_snapshot else None
                b_intent = getattr(b, "believed_intent", None)
                b_actor = getattr(b, "believed_actor", None)
                b_target = getattr(b, "believed_target", None)
                b_loc = getattr(b, "believed_location", None)

                actor_name = b_actor if (b and b_actor) else (evt.participants[0][1] if evt.participants else clean_set)
                target_name = b_target if (b and b_target) else (evt.participants[1][1] if len(evt.participants) > 1 else "the realm")
                loc_name = format_settlement_name(b_loc) if (b and b_loc) else format_settlement_name(evt.location)

                cause_desc = evt.payload.get("cause_of_death") or evt.payload.get("reason", "unforeseen cause")
                if b_intent == Intent.INTENTIONAL:
                    cause_desc = f"murder attributed to {b_actor or 'an enemy'}"

                ctx = {
                    "year": y,
                    "tick": evt.tick,
                    "actor_name": actor_name,
                    "target_name": target_name,
                    "location": loc_name,
                    "cause_desc": cause_desc,
                    "believed_intent": b_intent,
                    "believed_actor": b_actor,
                }
                sentence = render_event_sentence(
                    event_type_val=evt.type.value,
                    literacy=literacy,
                    context=ctx,
                    perspective_bias="Objective Archive",
                    rng=render_rng,
                )
                paras.append(sentence)

        paras.append(
            f"Here conclude the annals of {clean_set} up to Year {year}. "
            f"Sealed under the authority of the town archive."
        )

        pages, _ = paginate_text(paras, words_per_page=140)
        return pages

    est_words = 60 + len(event_list) * 25
    return Book(
        id=book_id,
        title=title,
        author_id=author_id,
        author_name=author_name,
        author_literacy=literacy,
        genre=BookGenre.HISTORICAL_CHRONICLE,
        settlement_id=settlement_id,
        creation_tick=tick,
        creation_year=year,
        sources=[e.id for e in event_list],
        perspective_bias="Objective Settlement Archive",
        total_word_count=est_words,
        lazy_renderer=_render,
    )


# =============================================================================
# 6. Local Folklore
# =============================================================================
def generate_local_folklore(
    book_id: str,
    cultural_profile: Any,
    author: Character,
    tick: int,
    rng: KeyedRNG,
    literacy: LiteracyLevel = LiteracyLevel.EDUCATED,
) -> Book:
    """
    Records indigenous folk traditions, spirit guardians, sacred groves,
    and seasonal festival ceremonies.
    """
    year = (tick // 12) + 1
    clean_set = author.settlement_id.replace("set_", "").capitalize()
    title = f"Folklore and Traditions of {clean_set}"
    folk_traditions = list(getattr(cultural_profile, "folk_traditions", []))
    local_customs = list(getattr(cultural_profile, "local_customs", []))

    def _render() -> list[str]:
        paras: list[str] = []

        paras.append(
            f"# {title}\n"
            f"Penned by {author.full_name} at {clean_set}, Year {year}.\n\n"
            f"Before written law or temple walls, the spirits of the land spoke to our ancestors. "
            f"This book preserves their venerable names."
        )

        # Folk Spirits
        paras.append("## Guardian Spirits of Hearth and Wilderness")
        for ft in folk_traditions:
            absorbed_status = " (Absorbed into official canon)" if ft.is_absorbed_into_religion else " (Indigenous folk reverence)"
            paras.append(f"### {ft.name} [{ft.tradition_type.value}]{absorbed_status}\n{ft.significance}")

        # Annual Customs
        paras.append("## Annual Seasonal Ceremonies & Feasts")
        for lc in local_customs:
            paras.append(f"### {lc.name} (Month {lc.season_month})\n{lc.description}")

        pages, _ = paginate_text(paras, words_per_page=120)
        return pages

    est_words = 60 + len(folk_traditions) * 25 + len(local_customs) * 25
    return Book(
        id=book_id,
        title=title,
        author_id=author.id,
        author_name=author.full_name,
        author_literacy=literacy,
        genre=BookGenre.LOCAL_FOLKLORE,
        settlement_id=author.settlement_id,
        creation_tick=tick,
        creation_year=year,
        sources=[],
        perspective_bias=f"Local Folk Lore of {clean_set}",
        total_word_count=est_words,
        lazy_renderer=_render,
    )


# =============================================================================
# 7. Legal & Dispute Records
# =============================================================================
def generate_legal_record(
    book_id: str,
    event: Event,
    author_name: str,
    author_id: str,
    tick: int,
    rng: KeyedRNG,
    literacy: LiteracyLevel = LiteracyLevel.SCHOLAR,
    settlement_name: Optional[str] = None,
) -> Book:
    """
    Compiles an official legal inquest, treaty document, or inquest verdict.
    """
    year = (tick // 12) + 1
    e_type = event.type.value
    loc = settlement_name or (event.location.replace("set_", "").capitalize() if event.location else "the Settlement")

    if e_type == "Death":
        title = f"Official Inquest into the Death of {event.participants[0][1] if event.participants else 'Citizen'}"
    elif e_type == "Peace":
        title = f"The Treaty and Concord of {loc}"
    else:
        title = f"Council Record of {e_type} at {loc}"

    def _render() -> list[str]:
        if e_type == "Death":
            paras = [
                f"# {title}\n"
                f"Court Record ratified at {loc}, Year {year}.\n\n"
                f"Be it recorded by the elders of {loc} that upon tick {event.tick}, "
                f"an inquest was convened regarding the passing of {event.participants[0][1] if event.participants else 'the deceased'}.\n\n"
                f"**Official Finding:** Cause established as {event.payload.get('cause_of_death', 'misadventure')}. "
                f"The death has been ruled an accidental tragedy under natural law. "
                f"No homicide liability attaches to any clan or household.",
            ]
        elif e_type == "Peace":
            paras = [
                f"# {title}\n"
                f"Ratified by the Councils of {loc}, Year {year}.\n\n"
                f"Let it be known to all men and clans: the state of armed hostility "
                f"between the signatory houses is hereby dissolved forever.\n\n"
                f"**Articles of Armistice:**\n"
                f"1. Immediate cessation of all border raids and blood vengeance.\n"
                f"2. Restoration of commercial caravan rights across mutual roads.\n"
                f"3. Solemn oath sworn before the altars of the land to uphold this concord.",
            ]
        else:
            paras = [
                f"# {title}\n"
                f"Recorded in Year {year} at {loc}.\n\n"
                f"The council deliberated upon the occurrence of {e_type} involving {event.participants}."
            ]

        pages, _ = paginate_text(paras, words_per_page=120)
        return pages

    est_words = 120
    return Book(
        id=book_id,
        title=title,
        author_id=author_id,
        author_name=author_name,
        author_literacy=literacy,
        genre=BookGenre.LEGAL_RECORD,
        settlement_id=event.location,
        creation_tick=tick,
        creation_year=year,
        sources=[event.id],
        perspective_bias="Official Judicial Record",
        total_word_count=est_words,
        lazy_renderer=_render,
    )


# =============================================================================
# 8. Travel & Pilgrimage Accounts
# =============================================================================
def generate_travel_account(
    book_id: str,
    pilgrim: Character,
    holy_site_name: str,
    holy_site_settlement: str,
    tick: int,
    rng: KeyedRNG,
    literacy: LiteracyLevel = LiteracyLevel.EDUCATED,
) -> Book:
    """
    Compiles a first-person travelogue and pilgrimage account.
    """
    year = (tick // 12) + 1
    title = f"Pilgrim's Journey to {holy_site_name}"
    p_set = format_settlement_name(pilgrim.settlement_id)
    h_set = format_settlement_name(holy_site_settlement)

    def _render() -> list[str]:
        paras: list[str] = []

        paras.append(
            f"# {title}\n"
            f"A personal travelogue written by {pilgrim.full_name} of {p_set}.\n"
            f"Completed upon return in Year {year}.\n\n"
            f"I set down the perils and spiritual blessings of my holy expedition "
            f"from {p_set} across the wilderness to {h_set}."
        )

        paras.append(
            f"## The Departure and the Road\n"
            f"Leaving the familiar hearth of {p_set}, I joined a merchant caravan. "
            f"We crossed winding mountain paths and swift river fords. "
            f"Though fatigue weighed upon my limbs, the holy call of {holy_site_name} guided my steps."
        )

        paras.append(
            f"## Arrival at the Sanctuary\n"
            f"Upon reaching {h_set}, the sight of {holy_site_name} filled my soul "
            f"with awe. I performed the sacred ablutions, offered prayers for my kin, "
            f"and felt the heavy burdens of sorrow lift from my heart."
        )

        paras.append(
            f"## The Return Home\n"
            f"I return to {p_set} renewed in faith and spirit. "
            f"May every devout soul undertake this sacred journey before their days are done."
        )

        pages, _ = paginate_text(paras, words_per_page=110)
        return pages

    est_words = 150
    return Book(
        id=book_id,
        title=title,
        author_id=pilgrim.id,
        author_name=pilgrim.full_name,
        author_literacy=literacy,
        genre=BookGenre.TRAVEL_ACCOUNT,
        settlement_id=pilgrim.settlement_id,
        creation_tick=tick,
        creation_year=year,
        sources=[],
        perspective_bias="Devout Pilgrim Perspective",
        total_word_count=est_words,
        lazy_renderer=_render,
    )


# =============================================================================
# 9. Biographies
# =============================================================================
def generate_biography(
    book_id: str,
    subject: Character,
    author: Character,
    subject_events: Sequence[Event],
    tick: int,
    rng: KeyedRNG,
    literacy: LiteracyLevel = LiteracyLevel.HISTORIAN,
    author_beliefs: Optional[Mapping[int, Any]] = None,
) -> Book:
    """
    Compiles a comprehensive biographical account of a notable leader, saint,
    martyr, or founder. Synthesizes milestones through the author's subjective beliefs.
    """
    year = (tick // 12) + 1
    title = f"The Life and Deeds of {subject.full_name}"
    auth_set = format_settlement_name(author.settlement_id)
    subj_set = format_settlement_name(subject.settlement_id)
    event_list = list(subject_events)
    beliefs_snapshot = dict(author_beliefs) if author_beliefs else None
    seed_val = rng.randint(0, 10**9) if hasattr(rng, "randint") else (tick * 1000 + hash(book_id) % 1000)

    def _render() -> list[str]:
        render_rng = KeyedRNG(seed_val, "book_render")
        paras: list[str] = []

        paras.append(
            f"# {title}\n"
            f"Authored by {author.full_name} at {auth_set}, Year {year}.\n\n"
            f"This biography records the life, virtues, trials, and enduring legacy "
            f"of {subject.full_name}, whose actions shaped the history of {subj_set}."
        )

        paras.append(
            f"## Early Years and Origins\n"
            f"{subject.full_name} was born into House {subject.last_name} in {subj_set}. "
            f"From youth, they displayed notable character and earned the deep respect of their peers."
        )

        if event_list:
            paras.append("## Major Life Milestones")
            for evt in event_list[:8]:
                b = beliefs_snapshot.get(evt.id) if beliefs_snapshot else None
                b_intent = getattr(b, "believed_intent", None)
                b_actor = getattr(b, "believed_actor", None)
                b_target = getattr(b, "believed_target", None)
                b_loc = getattr(b, "believed_location", None)

                actor_name = subject.full_name
                target_name = b_target if (b and b_target) else (evt.participants[1][1] if len(evt.participants) > 1 else "the community")
                loc_name = format_settlement_name(b_loc) if (b and b_loc) else format_settlement_name(evt.location)

                cause_desc = evt.payload.get("cause_of_death", "fate")
                if b_intent == Intent.INTENTIONAL:
                    cause_desc = f"murder attributed to {b_actor or 'an enemy'}"

                ctx = {
                    "year": (evt.tick // 12) + 1,
                    "tick": evt.tick,
                    "actor_name": actor_name,
                    "target_name": target_name,
                    "location": loc_name,
                    "cause_desc": cause_desc,
                    "believed_intent": b_intent,
                    "believed_actor": b_actor,
                }
                sentence = render_event_sentence(
                    event_type_val=evt.type.value,
                    literacy=literacy,
                    context=ctx,
                    perspective_bias="Biographical Honor",
                    rng=render_rng,
                )
                paras.append(sentence)

        status_str = f"Living at age {subject.age_years}" if subject.alive else "Having completed their mortal tenure"
        paras.append(
            f"## Historical Legacy\n"
            f"{status_str}, {subject.full_name} stands as an enduring pillar of {subj_set}. "
            f"Their memory shall remain preserved in these archives across generations."
        )

        pages, _ = paginate_text(paras, words_per_page=130)
        return pages

    est_words = 100 + len(event_list) * 25
    return Book(
        id=book_id,
        title=title,
        author_id=author.id,
        author_name=author.full_name,
        author_literacy=literacy,
        genre=BookGenre.BIOGRAPHY,
        settlement_id=author.settlement_id,
        creation_tick=tick,
        creation_year=year,
        sources=[e.id for e in event_list],
        perspective_bias="Biographical Honor & Historical Memory",
        total_word_count=est_words,
        lazy_renderer=_render,
    )
