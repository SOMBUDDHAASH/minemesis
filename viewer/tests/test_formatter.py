"""
Tests for pure-function prose formatter in Minemesis Story Viewer.

Rules:
- Formats every EventType cleanly.
- Never outputs raw IDs (char_*, set_*).
- Includes negative control verifying raw ID detector catches leaks.
"""

from __future__ import annotations
import re
import pytest

from minemesis.core.types import EventType, Intent, Scale
from viewer.formatter import (
    format_character_name,
    format_settlement_name,
    format_event_sentence,
    format_because_clause,
    get_event_category_color,
)
from viewer.model import EventProxy, EventLogProxy


RAW_ID_REGEX = re.compile(r"\b(char_\d+|set_[a-z0-9_]+)\b")


def test_character_and_settlement_name_formatting():
    chars = {
        "char_1": type("Char", (), {"full_name": "Alden Thorne"})(),
        "char_2": {"full_name": "Brynn Vance"},
    }
    settlements = {
        "set_ironwood": type("Settle", (), {"name": "Ironwood Reach"})(),
        "set_oakhaven": {"name": "Oakhaven Haven"},
    }

    assert format_character_name("char_1", chars) == "Alden Thorne"
    assert format_character_name("char_2", chars) == "Brynn Vance"
    assert format_character_name("char_999", chars) == "Citizen 999"

    assert format_settlement_name("set_ironwood", settlements) == "Ironwood Reach"
    assert format_settlement_name("set_oakhaven", settlements) == "Oakhaven Haven"
    assert format_settlement_name("set_sunfall", settlements) == "Sunfall"


def test_format_all_event_types_without_raw_ids():
    chars = {
        "char_1": type("Char", (), {"full_name": "Eldred Wolf"})(),
        "char_2": type("Char", (), {"full_name": "Mira Frost"})(),
        "char_3": type("Char", (), {"full_name": "Kaelen Ash"})(),
    }
    settlements = {
        "set_ironwood": type("Settle", (), {"name": "Ironwood"})(),
        "set_highland": type("Settle", (), {"name": "Highland"})(),
    }

    # Test suite covering major event types
    test_events = [
        EventProxy(
            id=1, tick=12, location="set_ironwood", type_val=EventType.BIRTH.value,
            participants=(("child", "char_1"), ("father", "char_2"), ("mother", "char_3")),
            causes=(), intent_val=Intent.ACCIDENTAL.value, scale_val=Scale.INDIVIDUAL.value,
            payload={"child_name": "Eldred Wolf", "father_name": "Mira Frost", "mother_name": "Kaelen Ash"},
        ),
        EventProxy(
            id=2, tick=24, location="set_ironwood", type_val=EventType.MARRIAGE.value,
            participants=(("spouse_a", "char_1"), ("spouse_b", "char_2")),
            causes=(), intent_val=Intent.INTENTIONAL.value, scale_val=Scale.INDIVIDUAL.value,
            payload={},
        ),
        EventProxy(
            id=3, tick=36, location="set_ironwood", type_val=EventType.DEATH.value,
            participants=(("deceased", "char_1"),),
            causes=(), intent_val=Intent.ACCIDENTAL.value, scale_val=Scale.INDIVIDUAL.value,
            payload={"cause": "old_age", "age_years": 74},
        ),
        EventProxy(
            id=4, tick=48, location="set_ironwood", type_val=EventType.FEUD.value,
            participants=(("instigator", "char_1"), ("target", "char_2")),
            causes=(3,), intent_val=Intent.INTENTIONAL.value, scale_val=Scale.AGGREGATE.value,
            payload={"target_settlement": "set_highland"},
        ),
        EventProxy(
            id=5, tick=60, location="set_highland", type_val=EventType.RAID.value,
            participants=(("attacker", "char_1"),),
            causes=(4,), intent_val=Intent.INTENTIONAL.value, scale_val=Scale.AGGREGATE.value,
            payload={"source_settlement": "set_ironwood", "food_stolen": 25},
        ),
        EventProxy(
            id=6, tick=72, location="set_ironwood", type_val=EventType.PEACE.value,
            participants=(),
            causes=(5,), intent_val=Intent.INTENTIONAL.value, scale_val=Scale.AGGREGATE.value,
            payload={"settlement_a": "set_ironwood", "settlement_b": "set_highland"},
        ),
        EventProxy(
            id=7, tick=84, location="set_ironwood", type_val="BookWritten",
            participants=(("author", "char_1"),),
            causes=(), intent_val=Intent.INTENTIONAL.value, scale_val=Scale.INDIVIDUAL.value,
            payload={"title": "Chronicle of Ironwood", "genre": "History", "word_count": 420},
        ),
        EventProxy(
            id=8, tick=96, location="set_ironwood", type_val="Conversion",
            participants=(("convert", "char_1"),),
            causes=(), intent_val=Intent.INTENTIONAL.value, scale_val=Scale.INDIVIDUAL.value,
            payload={"religion_name": "River Faith", "is_notable": True},
        ),
    ]

    for ev in test_events:
        sentence = format_event_sentence(ev, chars, settlements)
        assert sentence, f"Empty sentence for event {ev.type_val}"
        leaks = RAW_ID_REGEX.findall(sentence)
        assert not leaks, f"Raw ID leaked in {ev.type_val}: {leaks} -> '{sentence}'"


def test_format_because_clause():
    chars = {
        "char_1": type("Char", (), {"full_name": "Eldred Wolf"})(),
        "char_2": type("Char", (), {"full_name": "Mira Frost"})(),
    }
    settlements = {
        "set_ironwood": type("Settle", (), {"name": "Ironwood"})(),
        "set_highland": type("Settle", (), {"name": "Highland"})(),
    }

    ev_root = EventProxy(
        id=10, tick=100, location="set_ironwood", type_val=EventType.DEATH.value,
        participants=(("deceased", "char_2"),), causes=(), intent_val=Intent.ACCIDENTAL.value,
        scale_val=Scale.INDIVIDUAL.value, payload={"cause": "natural_causes"},
    )
    ev_feud = EventProxy(
        id=11, tick=110, location="set_ironwood", type_val=EventType.FEUD.value,
        participants=(("instigator", "char_1"), ("target", "char_2")), causes=(10,),
        intent_val=Intent.INTENTIONAL.value, scale_val=Scale.AGGREGATE.value, payload={"target_settlement": "set_highland"},
    )

    log_proxy = EventLogProxy(_events=[ev_root, ev_feud])

    # Root event has no causes -> no because clause
    assert format_because_clause(ev_root, log_proxy, chars, settlements) is None

    # Feud event has cause 10 -> because clause references death of Mira Frost
    clause = format_because_clause(ev_feud, log_proxy, chars, settlements)
    assert "Mira Frost" in clause and "accident" in clause
    assert not RAW_ID_REGEX.findall(clause)


def test_negative_control_raw_id_detector():
    """Negative control: proves RAW_ID_REGEX actually catches raw IDs when present."""
    bad_sentence = "At set_ironwood, char_42 declared a blood feud against char_99."
    leaks = RAW_ID_REGEX.findall(bad_sentence)
    assert leaks == ["set_ironwood", "char_42", "char_99"], "Negative control failed: detector did not catch raw IDs"


def test_minecraft_book_export_and_give_command():
    """Validates Minecraft NBT JSON format and /give command synthesis."""
    import json
    from viewer.export import export_minecraft_book_json, generate_minecraft_give_command

    book = {
        "title": "The Great Annals of Ironwood",
        "author_name": "Alden Thorne",
        "genre": "HistoricalChronicle",
        "creation_year": 24,
        "settlement_id": "set_ironwood",
        "total_word_count": 280,
        "pages": [
            "# Annals of Ironwood\nRecorded in Year 24.",
            "Chapter 2: The Harvest\nGranaries were filled.",
        ],
    }

    mc_json = export_minecraft_book_json(book)
    parsed = json.loads(mc_json)
    assert parsed["title"] == "The Great Annals of Ironwood"
    assert parsed["author"] == "Alden Thorne"
    assert parsed["generation"] == 0
    assert len(parsed["pages"]) == 2
    assert "HistoricalChronicle" in parsed["lore"][0]

    cmd = generate_minecraft_give_command(book)
    assert cmd.startswith("/give @p written_book{")
    assert 'title:"The Great Annals of Ironwood"' in cmd
    assert 'author:"Alden Thorne"' in cmd
    assert "Annals of Ironwood" in cmd
