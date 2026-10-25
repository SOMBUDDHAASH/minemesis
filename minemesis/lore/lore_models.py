"""
Data Models for the Procedural Literature Engine (Milestone L0).

Operationalizes:
- Literacy levels spanning Illiterate to Historian/Scholar.
- Diverse book genres (Family Histories, Personal Journals, Religious Texts,
  Myth Collections, Historical Chronicles, Local Folklore, Legal Records,
  Travel Accounts, Biographies).
- Perspective bias tracking (author point-of-view vs objective reality).
- Minecraft Written Book compatibility (paginated format, title, author, lore tags).
- Settlement library repositories (Town Archives, Temple Libraries, Household Shelves).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional, Sequence


class LiteracyLevel(str, Enum):
    """
    Simulated literacy and erudition tiers affecting writing quality,
    vocabulary selection, and sentence complexity.
    """
    ILLITERATE = "Illiterate"
    BASIC_LITERACY = "BasicLiteracy"
    EDUCATED = "Educated"
    SCHOLAR = "Scholar"
    PRIEST = "Priest"
    HISTORIAN = "Historian"


class BookGenre(str, Enum):
    """
    Genre classification of procedural books and manuscripts.
    """
    FAMILY_HISTORY = "FamilyHistory"
    PERSONAL_JOURNAL = "PersonalJournal"
    RELIGIOUS_TEXT = "ReligiousText"
    MYTH_COLLECTION = "MythCollection"
    HISTORICAL_CHRONICLE = "HistoricalChronicle"
    LOCAL_FOLKLORE = "LocalFolklore"
    LEGAL_RECORD = "LegalRecord"
    TRAVEL_ACCOUNT = "TravelAccount"
    BIOGRAPHY = "Biography"


class LibraryType(str, Enum):
    """
    Settlement repository types where manuscripts are preserved and curated.
    """
    TOWN_ARCHIVE = "TownArchive"
    TEMPLE_LIBRARY = "TempleLibrary"
    HOUSEHOLD_SHELF = "HouseholdShelf"
    SCHOLARS_STUDY = "ScholarsStudy"


class Book:
    """
    A written manuscript, chronicle, scripture, or journal authored within the simulation.
    Strictly generated from simulation state without LLMs.
    Supports lazy page rendering to eliminate heap overhead when books are unread.
    """
    def __init__(
        self,
        id: str,
        title: str,
        author_id: str,
        author_name: str,
        author_literacy: LiteracyLevel,
        genre: BookGenre,
        settlement_id: str,
        creation_tick: int,
        creation_year: int,
        sources: Optional[list[int]] = None,
        perspective_bias: str = "Objective",
        pages: Optional[list[str]] = None,
        total_word_count: int = 0,
        original_book_id: Optional[str] = None,
        is_damaged: bool = False,
        lazy_renderer: Optional[Callable[[], list[str]]] = None,
    ) -> None:
        self.id = id
        self.title = title
        self.author_id = author_id
        self.author_name = author_name
        self.author_literacy = author_literacy
        self.genre = genre
        self.settlement_id = settlement_id
        self.creation_tick = creation_tick
        self.creation_year = creation_year
        self.sources = list(sources) if sources is not None else []
        self.perspective_bias = perspective_bias
        self._pages = list(pages) if pages is not None else None
        self.total_word_count = total_word_count
        self.original_book_id = original_book_id
        self.is_damaged = is_damaged
        self.lazy_renderer = lazy_renderer

    @property
    def pages(self) -> list[str]:
        """Lazily synthesizes formatted page strings on demand."""
        if self._pages is None:
            if self.lazy_renderer is not None:
                self._pages = self.lazy_renderer()
                if self.total_word_count == 0 and self._pages:
                    self.total_word_count = sum(len(p.split()) for p in self._pages)
            else:
                self._pages = []
        return self._pages

    @pages.setter
    def pages(self, val: list[str]) -> None:
        self._pages = val

    def unload_pages(self) -> None:
        """Frees rendered page strings from RAM if a lazy renderer is available."""
        if self.lazy_renderer is not None and not self.is_damaged:
            self._pages = None

    def full_text(self) -> str:
        """Returns the complete combined text across all pages."""
        return "\n\n".join(self.pages)

    def to_minecraft_json(self) -> dict[str, Any]:
        """
        Exports the book to a standard Minecraft written book JSON structure.
        Compatible with NBT book data tags.
        """
        raw_title = self.title
        if len(raw_title) > 32:
            trunc = raw_title[:32]
            last_space = trunc.rfind(" ")
            short_title = trunc[:last_space] if last_space > 0 else trunc
        else:
            short_title = raw_title

        return {
            "title": short_title,  # Minecraft title limit (word-boundary truncated)
            "author": self.author_name[:16],
            "generation": 0 if self.original_book_id is None else 1,
            "pages": list(self.pages),
            "lore": [
                f"Genre: {self.genre.value}",
                f"Written: Year {self.creation_year} at {self.settlement_id}",
                f"Perspective: {self.perspective_bias}",
            ],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "author_literacy": self.author_literacy.value,
            "genre": self.genre.value,
            "settlement_id": self.settlement_id,
            "creation_tick": self.creation_tick,
            "creation_year": self.creation_year,
            "sources": list(self.sources),
            "perspective_bias": self.perspective_bias,
            "pages": list(self.pages),
            "total_word_count": self.total_word_count,
            "original_book_id": self.original_book_id,
            "is_damaged": self.is_damaged,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Book:
        return cls(
            id=data["id"],
            title=data["title"],
            author_id=data["author_id"],
            author_name=data["author_name"],
            author_literacy=LiteracyLevel(data.get("author_literacy", LiteracyLevel.EDUCATED.value)),
            genre=BookGenre(data.get("genre", BookGenre.HISTORICAL_CHRONICLE.value)),
            settlement_id=data["settlement_id"],
            creation_tick=int(data["creation_tick"]),
            creation_year=int(data.get("creation_year", (int(data["creation_tick"]) // 12) + 1)),
            sources=list(data.get("sources", [])),
            perspective_bias=data.get("perspective_bias", "Objective"),
            pages=list(data.get("pages", [])),
            total_word_count=int(data.get("total_word_count", 0)),
            original_book_id=data.get("original_book_id"),
            is_damaged=bool(data.get("is_damaged", False)),
        )


@dataclass
class Library:
    """
    A collection of books maintained in a settlement archive or temple repository.
    """
    settlement_id: str
    library_type: LibraryType
    books: list[Book] = field(default_factory=list)

    def add_book(self, book: Book) -> None:
        """Adds a book to the library collection."""
        self.books.append(book)

    def get_books_by_genre(self, genre: BookGenre) -> list[Book]:
        """Returns all books matching the specified genre."""
        return [b for b in self.books if b.genre == genre]

    def to_dict(self) -> dict[str, Any]:
        return {
            "settlement_id": self.settlement_id,
            "library_type": self.library_type.value,
            "books": [b.to_dict() for b in self.books],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Library:
        return cls(
            settlement_id=data["settlement_id"],
            library_type=LibraryType(data.get("library_type", LibraryType.TOWN_ARCHIVE.value)),
            books=[Book.from_dict(b_data) for b_data in data.get("books", [])],
        )
