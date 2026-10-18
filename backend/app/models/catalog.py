"""Shared pieces of the Book / Audiobook documents + the identity-claims collection."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pymongo
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, field_serializer
from pymongo import IndexModel

from app.services.metadata.schema import Contributor, SeriesInfo, SourceRef


def utcnow() -> datetime:
    # Mongo stores naive UTC at MILLISECOND precision. Produce exactly that, so the value returned by the API
    # right after a write is identical to what a later read returns.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return now.replace(microsecond=now.microsecond // 1000 * 1000)


class CatalogFields(BaseModel):
    """Fields common to Book and Audiobook.

    Three groups, kept strictly apart so a metadata refresh can never touch personal data:
      * bibliographic metadata  - replaced/merged by refresh
      * personal data           - personal_rating / notes / finished_on: only ever changed by the user
      * bookkeeping             - added_at (never changes), updated_at, metadata_refreshed_at
    """

    level: str = "edition"  # "edition" normally; "work" if no provider could resolve a concrete edition
    title: str
    subtitle: Optional[str] = None
    authors: list[str] = []
    contributors: list[Contributor] = []
    isbn_10: Optional[str] = None
    isbn_13: Optional[str] = None
    other_isbns: list[str] = []
    identifiers: dict[str, str] = {}  # provider ids: google_books, open_library_edition, hardcover_edition, ...
    edition: Optional[str] = None
    publisher: Optional[str] = None
    published_date: Optional[str] = None  # 'YYYY' | 'YYYY-MM' | 'YYYY-MM-DD' (never padded to false precision)
    first_published_year: Optional[int] = None
    language: Optional[str] = None  # ISO 639-1
    description: Optional[str] = None
    cover: Optional[str] = None  # None -> the UI shows a placeholder
    genres: list[str] = []
    series: Optional[SeriesInfo] = None

    # provenance
    sources: list[SourceRef] = []
    field_sources: dict[str, str] = {}

    # personal (user-owned) ----------------------------------------------------------------------
    personal_rating: Optional[float] = None  # 0.5 .. 5 in half-star steps
    notes: Optional[str] = None
    finished_on: Optional[str] = None  # ISO date the user finished it (optional, informational)

    # bookkeeping --------------------------------------------------------------------------------
    added_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    metadata_refreshed_at: Optional[datetime] = None

    @field_serializer("added_at", "updated_at", "metadata_refreshed_at")
    def _utc(self, v: Optional[datetime]):
        # naive values are UTC; say so, otherwise browsers read them as local time
        return v.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z") if v else None


PERSONAL_FIELDS = ("personal_rating", "notes", "finished_on")


class CatalogKey(Document):
    """One row per identity key of a stored item ("book:isbn13:978...").

    The unique index on `key` is what makes adds race-free: whoever inserts the claim first owns that
    identity, everyone else gets a duplicate-key error. See app/services/claims.py.
    """

    key: str
    doc_id: PydanticObjectId
    created_at: datetime = Field(default_factory=utcnow)

    class Settings:
        name = "catalog_keys"
        indexes = [IndexModel([("key", pymongo.ASCENDING)], unique=True), "doc_id"]
