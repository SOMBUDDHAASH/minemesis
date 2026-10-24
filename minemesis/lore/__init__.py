"""
Milestone L0: Procedural Literature Engine for Minemesis.

Provides:
- Non-omniscient procedural literature generation from simulation data without LLMs.
- 9 distinct book genres (Annals, Journals, Scriptures, Folklore, Lineages, Biographies, etc.).
- Literacy tier evaluation (Illiterate to Historian/Scholar).
- Multi-tier settlement libraries and archive damage.
- Minecraft Written Book compatibility (paginated, title, author, lore tags).
"""

from minemesis.lore.lore_models import (
    Book,
    BookGenre,
    Library,
    LibraryType,
    LiteracyLevel,
)
from minemesis.lore.lore_templates import (
    VOCABULARY,
    get_term,
    paginate_text,
    render_event_sentence,
)
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
from minemesis.lore.lore_engine import LoreEngine

__all__ = [
    "Book",
    "BookGenre",
    "Library",
    "LibraryType",
    "LiteracyLevel",
    "VOCABULARY",
    "get_term",
    "paginate_text",
    "render_event_sentence",
    "generate_biography",
    "generate_family_history",
    "generate_historical_chronicle",
    "generate_legal_record",
    "generate_local_folklore",
    "generate_myth_collection",
    "generate_personal_journal",
    "generate_religious_text",
    "generate_travel_account",
    "LibraryManager",
    "LoreEngine",
]
