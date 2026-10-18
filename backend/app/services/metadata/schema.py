"""Normalised records exchanged between providers, the matcher, the merger and the API.

ProviderRecord  - what ONE provider says about ONE thing, already normalised (never raw JSON).
MergedRecord    - the aggregator's output: complementary data from several ProviderRecords merged, with
                  provenance. This is what search returns and what is stored (minus personal data).

`level` matters:
  "edition" - a concrete published edition / audio recording (has its own ISBN / ASIN, page count,
              publisher, date, narrators, runtime...). Edition-level fields may be merged across providers
              ONLY when the matcher decided they are the same edition.
  "work"    - the abstract work (e.g. an Open Library work or a Hardcover book). It may enrich an edition
              with work-level facts (description, subjects, series, first publication year) but must never
              overwrite edition-specific fields (its page count / publisher / language are aggregates over
              many editions).
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from .normalize import canonical_isbn13

Kind = Literal["book", "audiobook"]
Level = Literal["edition", "work"]


class Contributor(BaseModel):
    name: str
    role: str  # lower-case: "translator", "editor", "illustrator", ...


class SeriesInfo(BaseModel):
    name: str
    position: Optional[str] = None  # string on purpose: "1", "2.5", "0.5"


class ProviderRecord(BaseModel):
    provider: str
    kind: Kind
    level: Level = "edition"
    provider_id: Optional[str] = None
    rank: Optional[int] = None  # 0-based position in the provider's own result list
    url: Optional[str] = None

    # identifiers -------------------------------------------------------------------------
    # provider ids live in `identifiers` ("google_books", "open_library_edition", "open_library_work",
    # "hardcover_edition", "hardcover_book", "itunes"); ISBNs / ASIN have their own fields.
    identifiers: dict[str, str] = Field(default_factory=dict)
    isbn_10: Optional[str] = None
    isbn_13: Optional[str] = None
    other_isbns: list[str] = Field(default_factory=list)  # further ISBN-13s of the SAME edition
    asin: Optional[str] = None
    work_isbns: list[str] = Field(default_factory=list)  # work level: ISBN-13s of its many editions
    work_languages: list[str] = Field(default_factory=list)

    # metadata ----------------------------------------------------------------------------
    title: Optional[str] = None
    subtitle: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    narrators: list[str] = Field(default_factory=list)
    contributors: list[Contributor] = Field(default_factory=list)
    description: Optional[str] = None
    cover: Optional[str] = None
    publisher: Optional[str] = None
    published_date: Optional[str] = None  # 'YYYY' | 'YYYY-MM' | 'YYYY-MM-DD'
    language: Optional[str] = None  # ISO 639-1, lower case
    page_count: Optional[int] = None
    runtime_minutes: Optional[int] = None
    recording_type: Optional[str] = None  # unabridged | abridged | dramatized
    genres: list[str] = Field(default_factory=list)
    series: Optional[SeriesInfo] = None
    edition: Optional[str] = None  # "2nd edition", "Deluxe", ...
    first_published_year: Optional[int] = None

    extra: dict[str, Any] = Field(default_factory=dict)  # provider-specific hints, never persisted

    # -------------------------------------------------------------------------------------
    def edition_isbns(self) -> set[str]:
        """Canonical ISBN-13s that identify THIS edition (primary + converted ISBN-10 + alternates)."""
        out = {canonical_isbn13(x) for x in [self.isbn_13, self.isbn_10, *self.other_isbns]}
        return {x for x in out if x}

    def edition_ids(self) -> set[str]:
        """Provider ids that identify this specific edition (work-level ids are excluded)."""
        if self.level != "edition":
            return set()
        return {f"{k}:{v}" for k, v in self.identifiers.items() if v and not k.endswith(("_work", "_book"))}

    def has_strong_id(self) -> bool:
        return bool(self.edition_isbns() or self.asin)


class SourceRef(BaseModel):
    provider: str
    level: Level = "edition"
    provider_id: Optional[str] = None
    url: Optional[str] = None


class MergedRecord(BaseModel):
    kind: Kind
    level: Level = "edition"

    title: Optional[str] = None
    subtitle: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    narrators: list[str] = Field(default_factory=list)
    contributors: list[Contributor] = Field(default_factory=list)
    isbn_10: Optional[str] = None
    isbn_13: Optional[str] = None
    other_isbns: list[str] = Field(default_factory=list)
    asin: Optional[str] = None
    identifiers: dict[str, str] = Field(default_factory=dict)  # provider ids (+ nothing else)
    edition: Optional[str] = None
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    first_published_year: Optional[int] = None
    language: Optional[str] = None
    page_count: Optional[int] = None
    runtime_minutes: Optional[int] = None
    recording_type: Optional[str] = None
    description: Optional[str] = None
    cover: Optional[str] = None
    genres: list[str] = Field(default_factory=list)
    series: Optional[SeriesInfo] = None

    # provenance / bookkeeping
    providers: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    field_sources: dict[str, str] = Field(default_factory=dict)
    score: float = 0.0


# Fields that are copied from a MergedRecord into a stored document and refreshed later.
COMMON_FIELDS = (
    "title", "subtitle", "authors", "contributors", "isbn_10", "isbn_13", "other_isbns", "identifiers",
    "edition", "publisher", "published_date", "first_published_year", "language", "description", "cover",
    "genres", "series",
)
BOOK_FIELDS = COMMON_FIELDS + ("page_count",)
AUDIOBOOK_FIELDS = COMMON_FIELDS + ("narrators", "asin", "runtime_minutes", "recording_type")


def metadata_fields(kind: Kind) -> tuple[str, ...]:
    return BOOK_FIELDS if kind == "book" else AUDIOBOOK_FIELDS


# Fields that only make sense for a concrete edition / recording; never taken from a work-level record.
EDITION_ONLY_FIELDS = frozenset({
    "isbn_10", "isbn_13", "other_isbns", "asin", "edition", "publisher", "published_date", "language",
    "page_count", "runtime_minutes", "recording_type", "narrators", "contributors",
})
