from typing import Optional

from beanie import Document

from app.models.catalog import CatalogFields


class Book(CatalogFields, Document):
    page_count: Optional[int] = None

    class Settings:
        name = "books"
        indexes = ["isbn_13", "isbn_10", "added_at"]
