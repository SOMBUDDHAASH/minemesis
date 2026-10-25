"""
Pure-function event sentence formatter for Minemesis Story Viewer.

Rules:
- Synthesizes readable prose strictly from event payload fields and resolved names.
- NEVER outputs raw IDs (char_0, set_ironwood).
- Formats because clauses for each antecedent cause.
- Assigns category colors for UI rendering.
"""

from __future__ import annotations
import re
from typing import Any, Mapping, Optional, Sequence
from minemesis.core.types import EventType, Intent


def format_settlement_name(settlement_id: str, settlements: Optional[Mapping[str, Any]] = None) -> str:
    """Resolves a settlement ID to its proper display name."""
    if not settlement_id:
        return "Unknown Settlement"
    if settlements and settlement_id in settlements:
        s = settlements[settlement_id]
        if hasattr(s, "name"):
            return str(s.name)
        elif isinstance(s, dict) and "name" in s:
            return str(s["name"])
    if settlement_id.startswith("set_"):
        return settlement_id[4:].replace("_", " ").title()
    return settlement_id.replace("_", " ").title()


def format_character_name(char_id: str, characters: Optional[Mapping[str, Any]] = None) -> str:
    """Resolves a character ID to their full human name."""
    if not char_id:
        return "Unknown Person"
    if characters and char_id in characters:
        c = characters[char_id]
        if hasattr(c, "full_name"):
            return str(c.full_name)
        elif isinstance(c, dict):
            return str(c.get("full_name") or f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or char_id)
    # Clean fallback if ID cannot be resolved
    if char_id.startswith("char_"):
        return f"Citizen {char_id[5:]}"
    return char_id.replace("_", " ").title()


def get_event_category_color(event_type: EventType) -> str:
    """Returns the highlight color category for the event type."""
    t_val = event_type.value if hasattr(event_type, "value") else str(event_type)

    if t_val in ("Feud", "Raid", "SuccessionCrisis", "SettlementCollapse"):
        return "#C0392B"  # Conflict red
    elif t_val in ("Peace", "Marriage", "Birth"):
        return "#27AE60"  # Flourishing / concord green
    elif t_val in (
        "Conversion", "Revelation", "HolySiteDiscovered", "HolySiteElevated",
        "ReligiousSchism", "ReligiousReform", "ReligiousSyncretism", "HeresyDeclared",
        "DoctrinalBorrowing", "FolkTraditionAbsorbed", "LocalCustomCelebrated",
        "GreatFigureEmergence", "MythRecorded", "SaintCanonized", "Pilgrimage"
    ):
        return "#2980B9"  # Religion blue
    elif t_val in ("BookWritten", "ArchiveDamaged"):
        return "#8E44AD"  # Literature & culture purple/brown
    elif t_val in ("Famine",):
        return "#D35400"  # Famine orange
    elif t_val in ("ChiefChanged", "Migration", "TradeRouteFounded", "TradeRouteBroken"):
        return "#2C3E50"  # Civic dark slate
    return "#34495E"


def format_event_sentence(
    event: Any,
    characters: Optional[Mapping[str, Any]] = None,
    settlements: Optional[Mapping[str, Any]] = None,
) -> str:
    """
    Synthesizes a clean, readable one-sentence summary of an event.
    Guaranteed: NO raw IDs appear in the generated prose.
    """
    payload = getattr(event, "payload", {}) or {}
    e_type = getattr(event, "type", None)
    t_val = e_type.value if hasattr(e_type, "value") else str(e_type)
    participants = dict(getattr(event, "participants", ())) or {}
    loc_name = format_settlement_name(getattr(event, "location", ""), settlements)
    tick = getattr(event, "tick", 0)
    year = (tick // 12) + 1

    # 1. Birth
    if t_val == "Birth":
        child = payload.get("child_name") or format_character_name(participants.get("child", ""), characters)
        father = payload.get("father_name") or format_character_name(participants.get("father", ""), characters)
        mother = payload.get("mother_name") or format_character_name(participants.get("mother", ""), characters)
        if father != "Unknown Person" and mother != "Unknown Person":
            return f"{child} was born to {father} and {mother} in {loc_name}."
        elif mother != "Unknown Person":
            return f"{child} was born to {mother} in {loc_name}."
        return f"{child} was born in {loc_name}."

    # 2. Death
    elif t_val == "Death":
        victim = payload.get("victim_name") or format_character_name(participants.get("target") or participants.get("deceased", ""), characters)
        cause = payload.get("cause_of_death") or payload.get("cause", "")
        actor = payload.get("actor_name") or format_character_name(participants.get("actor", ""), characters)

        evt_desc = str(payload.get("description") or getattr(event, "description", "")).lower()
        if payload.get("natural") or "old age" in evt_desc:
            return f"{victim} passed away peacefully of old age in {loc_name}."
        elif payload.get("revenge") or cause == "Revenge":
            return f"{victim} was slain in revenge by {actor} in {loc_name}."
        elif cause == "Starvation":
            return f"{victim} succumbed to starvation during the famine in {loc_name}."
        elif "raid" in evt_desc or getattr(event, "intent", None) == Intent.MILITARY_ACTION:
            return f"{victim} was slain defending {loc_name} during a border raid."
        elif payload.get("accidental") or getattr(event, "intent", None) == Intent.ACCIDENTAL:
            if actor and actor != "Unknown Person":
                return f"{victim} died in a forestry accident with {actor} at {loc_name}."
            return f"{victim} died in an unfortunate accident at {loc_name}."
        return f"{victim} departed this life in {loc_name}."

    # 3. Marriage
    elif t_val == "Marriage":
        sp1 = payload.get("spouse1_name") or format_character_name(participants.get("spouse1", ""), characters)
        sp2 = payload.get("spouse2_name") or format_character_name(participants.get("spouse2", ""), characters)
        is_alliance = payload.get("is_alliance", False)
        reloc = payload.get("relocation")
        suffix = ""
        if reloc:
            moved_char = format_character_name(reloc.get("moved_char_id", ""), characters)
            to_set = format_settlement_name(reloc.get("to_settlement_id", ""), settlements)
            suffix = f", with {moved_char} relocating to {to_set}"
        if is_alliance:
            return f"{sp1} and {sp2} were joined in an alliance marriage in {loc_name}{suffix}."
        return f"{sp1} and {sp2} were wed in {loc_name}{suffix}."

    # 4. Feud
    elif t_val == "Feud":
        instigator = payload.get("instigator_name") or format_character_name(participants.get("instigator", ""), characters)
        target = payload.get("target_name") or format_character_name(participants.get("target", ""), characters)
        return f"A bitter blood feud was declared by {instigator} against {target} in {loc_name}."

    # 5. Peace
    elif t_val == "Peace":
        p1 = format_character_name(participants.get("party1", ""), characters)
        p2 = format_character_name(participants.get("party2", ""), characters)
        reason = payload.get("reason", "exhaustion")
        if reason == "TruthRevelation":
            return f"A solemn peace treaty was signed between {p1} and {p2} in {loc_name} following the revelation of truth."
        return f"A peace treaty was ratified between {p1} and {p2} in {loc_name}, bringing an end to hostilities."

    # 6. Raid
    elif t_val == "Raid":
        attacker = format_settlement_name(participants.get("attacker", ""), settlements)
        defender = format_settlement_name(participants.get("defender", ""), settlements)
        loot = payload.get("food_looted", 0)
        cas = payload.get("defender_casualties", 0)
        return f"Warriors from {attacker} raided {defender}, seizing {loot} food and causing {cas} casualties."

    # 7. Famine
    elif t_val == "Famine":
        sev = payload.get("severity", "severe")
        return f"A {sev} famine struck {loc_name}, exhausting granaries and threatening the harvest."

    # 8. Chief Changed
    elif t_val == "ChiefChanged":
        new_c = payload.get("new_chief_name") or format_character_name(participants.get("new_chief", ""), characters)
        old_c = payload.get("old_chief_name") or format_character_name(participants.get("old_chief", ""), characters)
        rule = payload.get("rule", "succession")
        if old_c and old_c != "Unknown Person":
            return f"{new_c} succeeded {old_c} as Chief of {loc_name} through {rule} succession."
        return f"{new_c} assumed leadership as Chief of {loc_name}."

    # 9. Succession Crisis
    elif t_val == "SuccessionCrisis":
        r1 = format_character_name(participants.get("rival_1", ""), characters)
        r2 = format_character_name(participants.get("rival_2", ""), characters)
        return f"A contested succession crisis erupted in {loc_name} between {r1} and {r2}."

    # 10. Settlement Collapse & Migration
    elif t_val == "SettlementCollapse":
        surv = payload.get("surviving_population", 0)
        return f"{loc_name} collapsed after severe depopulation; {surv} survivors abandoned their hearths."
    elif t_val == "Migration":
        migrant = format_character_name(participants.get("migrant", ""), characters)
        from_set = format_settlement_name(payload.get("from_settlement_id", ""), settlements)
        to_set = format_settlement_name(payload.get("to_settlement_id", ""), settlements)
        return f"{migrant} migrated from {from_set} to seek sanctuary in {to_set}."

    # 11. Trade Routes
    elif t_val == "TradeRouteFounded":
        s1 = format_settlement_name(participants.get("settlement_a") or participants.get("settlement1", ""), settlements)
        s2 = format_settlement_name(participants.get("settlement_b") or participants.get("settlement2", ""), settlements)
        return f"A bilateral commercial and diplomatic trade route was opened between {s1} and {s2}."
    elif t_val == "TradeRouteBroken":
        s1 = format_settlement_name(participants.get("settlement_a") or participants.get("settlement1", ""), settlements)
        s2 = format_settlement_name(participants.get("settlement_b") or participants.get("settlement2", ""), settlements)
        reason = payload.get("reason", "conflict")
        return f"The trade corridor between {s1} and {s2} was severed due to {reason}."

    # 12. Revelation
    elif t_val == "Revelation":
        witness = format_character_name(participants.get("witness", ""), characters)
        inst = format_character_name(participants.get("instigator", ""), characters)
        return f"The objective truth was formally revealed to {inst} through the testimony of {witness} in {loc_name}."

    # 13. Conversion
    elif t_val == "Conversion":
        convert = format_character_name(payload.get("character_id") or participants.get("convert", ""), characters)
        old_rel = payload.get("old_religion", "old faith")
        new_rel = payload.get("new_religion", "new faith")
        reason = payload.get("reason", "faith")
        return f"{convert} converted from {old_rel} to {new_rel} in {loc_name} ({reason})."

    # 14. Book Written
    elif t_val == "BookWritten":
        title = payload.get("title", "Untitled Volume")
        # Format any raw settlement IDs embedded in book title
        if settlements and "set_" in title:
            title = re.sub(r"set_\w+", lambda m: format_settlement_name(m.group(0), settlements), title)
        author = format_character_name(participants.get("author", ""), characters)
        genre = payload.get("genre", "Literature")
        return f"{author} penned '{title}', a {genre} preserved in the archives of {loc_name}."

    # 15. Archive Damaged
    elif t_val == "ArchiveDamaged":
        cnt = payload.get("affected_count", 1)
        return f"The municipal archive in {loc_name} was desecrated during a raid, destroying or damaging {cnt} manuscripts."

    # 16. Holy Sites & Pilgrimages
    elif t_val == "HolySiteDiscovered":
        site = payload.get("site_name", "Sacred Ground")
        rel = payload.get("religion_name", "the faith")
        return f"The holy sanctuary of '{site}' was founded and consecrated to {rel} in {loc_name}."
    elif t_val == "HolySiteElevated":
        site = payload.get("site_name", "Sacred Ground")
        tier = payload.get("new_tier", "higher standing")
        return f"'{site}' in {loc_name} was elevated to the rank of {tier} due to influx of devout pilgrims."
    elif t_val == "Pilgrimage":
        pilgrim = format_character_name(participants.get("pilgrim", ""), characters)
        site = payload.get("site_name", "the holy shrine")
        return f"{pilgrim} completed a holy pilgrimage across the land to worship at '{site}'."

    # 17. Schisms, Heresies, Reforms, Syncretism
    elif t_val == "ReligiousSchism":
        parent = payload.get("parent_religion_name", "the orthodox faith")
        diss = payload.get("new_religion_name", "the reformed sect")
        return f"A theological schism split {parent}, establishing {diss} as an independent faith in {loc_name}."
    elif t_val == "HeresyDeclared":
        orth = payload.get("orthodox_religion_name", "the council")
        her = payload.get("heretical_religion_name", "the dissenters")
        return f"{orth} declared the doctrines of {her} to be anathema and heresy."
    elif t_val == "ReligiousSyncretism":
        r1 = payload.get("parent_a_name", "Faith A")
        r2 = payload.get("parent_b_name", "Faith B")
        syn = payload.get("syncretic_religion_name", "the Unified Way")
        return f"{r1} and {r2} coalesced through cultural syncretism into {syn} in {loc_name}."
    elif t_val == "DoctrinalBorrowing":
        r_b = payload.get("borrower_religion_name", "the church")
        r_l = payload.get("lender_religion_name", "neighboring tradition")
        trait = payload.get("trait_name", "sacred virtue")
        return f"{r_b} absorbed the holy trait of '{trait}' through contact with {r_l}."
    elif t_val == "FolkTraditionAbsorbed":
        trad = payload.get("tradition_name", "indigenous folk spirit")
        rel = payload.get("religion_name", "the official faith")
        return f"The ancient tradition of '{trad}' was officially canonized into {rel} in {loc_name}."
    elif t_val == "LocalCustomCelebrated":
        cust = payload.get("custom_name", "Annual Festival")
        return f"The people of {loc_name} celebrated the seasonal custom of '{cust}'."
    elif t_val == "GreatFigureEmergence":
        fig_name = payload.get("figure_name") or format_character_name(participants.get("martyr") or participants.get("prophet", ""), characters)
        arch = payload.get("figure_type", "Great Figure")
        rel = payload.get("religion_name", "the faith")
        return f"{fig_name} emerged as a venerated {arch} of {rel} in {loc_name}."
    elif t_val == "MythRecorded":
        hero = payload.get("hero_name") or format_character_name(participants.get("hero", ""), characters)
        rel = payload.get("religion_name", "the faith")
        return f"The heroic legend of {hero} was recorded into the living mythology of {rel}."
    elif t_val == "SaintCanonized":
        saint = payload.get("saint_name") or format_character_name(participants.get("saint", ""), characters)
        rel = payload.get("religion_name", "the church")
        return f"{saint} was canonized as a sacred protector in the liturgy of {rel}."

    # General Fallback
    desc = payload.get("description") or getattr(event, "description", None)
    if desc:
        # Clean any raw IDs from description
        cleaned = desc
        if characters and "char_" in cleaned:
            cleaned = re.sub(r"char_\w+", lambda m: format_character_name(m.group(0), characters), cleaned)
        if settlements and "set_" in cleaned:
            cleaned = re.sub(r"set_\w+", lambda m: format_settlement_name(m.group(0), settlements), cleaned)
        return cleaned

    return f"A notable {t_val} event occurred in {loc_name}."


def format_because_clause(
    event: Any,
    event_log: Any,
    characters: Optional[Mapping[str, Any]] = None,
    settlements: Optional[Mapping[str, Any]] = None,
) -> Optional[str]:
    """
    Builds the 'because: ...' clause for an event from its causes.
    Returns None if event has no causes (root event).
    """
    causes = getattr(event, "causes", ()) or ()
    if not causes:
        return None

    cause_phrases = []
    for c_id in causes:
        c_evt = getattr(event_log, "get", lambda x: None)(c_id)
        if c_evt is None and hasattr(event_log, "_by_id"):
            c_evt = event_log._by_id.get(c_id)
        if c_evt:
            # Ensure cause tick is strictly earlier or equal
            c_tick = getattr(c_evt, "tick", 0)
            c_year = (c_tick // 12) + 1
            c_sentence = format_event_sentence(c_evt, characters, settlements)
            # Shorten sentence for cause clause
            if c_sentence.endswith("."):
                c_sentence = c_sentence[:-1]
            cause_phrases.append(f"{c_sentence} (Year {c_year}, #{c_id})")
        else:
            cause_phrases.append(f"event #{c_id}")

    if not cause_phrases:
        return None

    return "because: " + "; and ".join(cause_phrases)
