from typing import Optional

from beanie import Document

from app.models.catalog import CatalogFields


class Audiobook(CatalogFields, Document):
    narrators: list[str] = []
    asin: Optional[str] = None
    runtime_minutes: Optional[int] = None
    recording_type: Optional[str] = None  # unabridged | abridged | dramatized (None when unknown)

    class Settings:
        name = "audiobooks"
        indexes = ["isbn_13", "isbn_10", "asin", "added_at"]
