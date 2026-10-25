"""
Settlement Libraries and Archives System for Milestone L0.

Operationalizes:
- Multi-tier settlement book repositories (Town Archives, Temple Libraries, Household Shelves).
- Archive damage, manuscript loss, and cultural amnesia during raids and disasters.
- Deterministic cataloging, retrieval, and serialization.
"""

from __future__ import annotations
from typing import Any, Mapping, Optional, Sequence
from minemesis.core.rng import KeyedRNG

from minemesis.lore.lore_models import Book, BookGenre, Library, LibraryType


class LibraryManager:
    """
    Manages all settlement repositories, libraries, and book archives in the world.
    Tracks book preservation, cataloging, and physical loss from conflicts/raids.
    """

    def __init__(self) -> None:
        # Maps settlement_id -> dict of LibraryType -> Library
        self._settlement_libraries: dict[str, dict[LibraryType, Library]] = {}
        # Global registry of all books by ID
        self._all_books: dict[str, Book] = {}

    def ensure_settlement_libraries(self, settlement_id: str) -> None:
        """Initializes all library types for a settlement if not already present."""
        if settlement_id not in self._settlement_libraries:
            self._settlement_libraries[settlement_id] = {
                LibraryType.TOWN_ARCHIVE: Library(settlement_id=settlement_id, library_type=LibraryType.TOWN_ARCHIVE),
                LibraryType.TEMPLE_LIBRARY: Library(settlement_id=settlement_id, library_type=LibraryType.TEMPLE_LIBRARY),
                LibraryType.HOUSEHOLD_SHELF: Library(settlement_id=settlement_id, library_type=LibraryType.HOUSEHOLD_SHELF),
                LibraryType.SCHOLARS_STUDY: Library(settlement_id=settlement_id, library_type=LibraryType.SCHOLARS_STUDY),
            }

    def add_book(
        self,
        book: Book,
        preferred_library: Optional[LibraryType] = None,
    ) -> None:
        """
        Stores a book in the specified settlement repository.
        If preferred_library is None, automatically directs based on book genre.
        """
        self.ensure_settlement_libraries(book.settlement_id)
        self._all_books[book.id] = book

        if preferred_library is None:
            preferred_library = self._default_library_for_genre(book.genre)

        lib = self._settlement_libraries[book.settlement_id][preferred_library]
        lib.add_book(book)

    def _default_library_for_genre(self, genre: BookGenre) -> LibraryType:
        """Determines the natural resting repository for a genre."""
        if genre in (BookGenre.RELIGIOUS_TEXT, BookGenre.MYTH_COLLECTION):
            return LibraryType.TEMPLE_LIBRARY
        elif genre in (BookGenre.HISTORICAL_CHRONICLE, BookGenre.LEGAL_RECORD):
            return LibraryType.TOWN_ARCHIVE
        elif genre in (BookGenre.BIOGRAPHY, BookGenre.TRAVEL_ACCOUNT):
            return LibraryType.SCHOLARS_STUDY
        else:  # FAMILY_HISTORY, PERSONAL_JOURNAL, LOCAL_FOLKLORE
            return LibraryType.HOUSEHOLD_SHELF

    def get_book(self, book_id: str) -> Optional[Book]:
        """Retrieves any book in the world by unique ID."""
        return self._all_books.get(book_id)

    def get_all_books(self) -> list[Book]:
        """Returns all books across all settlements, sorted by ID for determinism."""
        return sorted(self._all_books.values(), key=lambda b: b.id)

    def unload_all_pages(self) -> None:
        """Unloads rendered page strings across all libraries to keep heap footprint minimal."""
        for book in self._all_books.values():
            book.unload_pages()

    def get_settlement_books(
        self,
        settlement_id: str,
        library_type: Optional[LibraryType] = None,
    ) -> list[Book]:
        """Returns all books located within a settlement, optionally filtered by library type."""
        self.ensure_settlement_libraries(settlement_id)
        if library_type is not None:
            return list(self._settlement_libraries[settlement_id][library_type].books)

        all_books = []
        for lib in self._settlement_libraries[settlement_id].values():
            all_books.extend(lib.books)
        return all_books

    def get_books_by_genre(
        self,
        genre: BookGenre,
        settlement_id: Optional[str] = None,
    ) -> list[Book]:
        """Retrieves books matching a genre, globally or within a specific settlement."""
        if settlement_id is not None:
            return [b for b in self.get_settlement_books(settlement_id) if b.genre == genre]
        return [b for b in self.get_all_books() if b.genre == genre]

    def damage_archive(
        self,
        settlement_id: str,
        damage_ratio: float,
        rng: KeyedRNG,
    ) -> list[Book]:
        """
        Simulates physical devastation to archives during a raid or catastrophe.
        Each book in the settlement has a chance proportional to damage_ratio to be
        either physically destroyed or permanently damaged (pages torn/burned).
        Returns a list of books that were destroyed or damaged.
        """
        self.ensure_settlement_libraries(settlement_id)
        affected_books: list[Book] = []

        # Iterate deterministically over library types
        for lib_type in (
            LibraryType.TOWN_ARCHIVE,
            LibraryType.TEMPLE_LIBRARY,
            LibraryType.HOUSEHOLD_SHELF,
            LibraryType.SCHOLARS_STUDY,
        ):
            lib = self._settlement_libraries[settlement_id][lib_type]
            surviving_books: list[Book] = []

            for book in sorted(lib.books, key=lambda b: b.id):
                roll = rng.random()
                if roll < damage_ratio * 0.5:
                    # Book is entirely destroyed / lost to history
                    book.is_damaged = True
                    affected_books.append(book)
                    if book.id in self._all_books:
                        del self._all_books[book.id]
                elif roll < damage_ratio:
                    # Book is damaged: part of its text is lost
                    book.is_damaged = True
                    if book.pages:
                        # Corrupt or tear the last pages
                        torn_pages = [p for i, p in enumerate(book.pages) if i < max(1, len(book.pages) // 2)]
                        torn_pages.append("[... Parchment torn and blackened by fire. Remaining text illegible ...]")
                        book.pages = torn_pages
                        book.lazy_renderer = None  # Preserve damaged pages from being re-rendered undamaged
                        book.total_word_count = sum(len(p.split()) for p in book.pages)
                    affected_books.append(book)
                    surviving_books.append(book)
                else:
                    surviving_books.append(book)

            lib.books = surviving_books

        return affected_books

    def to_dict(self) -> dict[str, Any]:
        """Serializes the entire library manager state."""
        return {
            "all_books": [b.to_dict() for b in self.get_all_books()],
            "settlements": {
                s_id: {
                    lib_type.value: lib.to_dict()
                    for lib_type, lib in sorted(libs.items(), key=lambda item: item[0].value)
                }
                for s_id, libs in sorted(self._settlement_libraries.items(), key=lambda item: item[0])
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LibraryManager:
        """Restores a LibraryManager instance from serialized dictionary."""
        manager = cls()
        books_by_id: dict[str, Book] = {}
        for b_data in data.get("all_books", []):
            book = Book.from_dict(b_data)
            books_by_id[book.id] = book
            manager._all_books[book.id] = book

        for s_id, libs_data in data.get("settlements", {}).items():
            manager.ensure_settlement_libraries(s_id)
            for lib_name, lib_dict in libs_data.items():
                lib_type = LibraryType(lib_name)
                lib = Library(
                    settlement_id=s_id,
                    library_type=lib_type,
                    books=[books_by_id[b_dict["id"]] for b_dict in lib_dict.get("books", []) if b_dict["id"] in books_by_id],
                )
                manager._settlement_libraries[s_id][lib_type] = lib

        return manager
