"""Google Books API v1 (https://developers.google.com/books/docs/v1/using). Books only, edition level.

GOOGLE_BOOKS_API_KEY is optional; without it the (small, shared) anonymous quota applies.
"""
from __future__ import annotations

from typing import Any, Optional

from ..normalize import (
    canonical_isbn13,
    clean_html,
    clean_text,
    dedupe_people,
    normalize_genres,
    normalize_language,
    parse_partial_date,
    positive_int,
    split_isbns,
)
from ..schema import Kind, ProviderRecord
from .base import Provider, http_json, safe_id

BASE = "https://www.googleapis.com/books/v1/volumes"
_VOLUME_FIELDS = (
    "id,volumeInfo(title,subtitle,authors,publisher,publishedDate,description,industryIdentifiers,"
    "pageCount,categories,imageLinks,language,infoLink,canonicalVolumeLink,printType)"
)
_FIELDS = f"items({_VOLUME_FIELDS})"  # search responses wrap volumes in `items`
_COVER_ORDER = ("extraLarge", "large", "medium", "small", "thumbnail", "smallThumbnail")


def _cover(image_links: dict) -> Optional[str]:
    for key in _COVER_ORDER:
        url = (image_links or {}).get(key)
        if url:
            url = url.replace("http://", "https://", 1).replace("&edge=curl", "")
            return url
    return None


def parse_volume(item: dict, rank: Optional[int] = None) -> Optional[ProviderRecord]:
    info = (item or {}).get("volumeInfo") or {}
    title = clean_text(info.get("title"))
    vid = safe_id(item.get("id")) if item else None
    if not title or not vid:
        return None

    isbns = [i.get("identifier") for i in info.get("industryIdentifiers") or []
             if str(i.get("type", "")).startswith("ISBN")]
    isbn10, isbn13, others = split_isbns(isbns)

    return ProviderRecord(
        provider="google_books",
        kind="book",
        level="edition",
        provider_id=vid,
        rank=rank,
        url=info.get("canonicalVolumeLink") or info.get("infoLink"),
        identifiers={"google_books": vid},
        isbn_10=isbn10,
        isbn_13=isbn13,
        other_isbns=others,
        title=title,
        subtitle=clean_text(info.get("subtitle")),
        authors=dedupe_people(info.get("authors") or []),
        description=clean_html(info.get("description")),
        cover=_cover(info.get("imageLinks") or {}),
        publisher=clean_text(info.get("publisher")),
        published_date=parse_partial_date(info.get("publishedDate")),
        language=normalize_language(info.get("language")),
        page_count=positive_int(info.get("pageCount")),
        genres=normalize_genres(info.get("categories") or []),
    )


class GoogleBooksProvider(Provider):
    name = "google_books"
    kinds = frozenset({"book"})
    id_keys = frozenset({"google_books", "isbn_13", "isbn_10"})

    def _params(self, **extra) -> dict[str, Any]:
        params = {"printType": "books", "fields": _FIELDS, **extra}
        if self.settings.google_books_api_key:
            params["key"] = self.settings.google_books_api_key
        return params

    async def search(self, kind: Kind, query: str, limit: int) -> list[ProviderRecord]:
        data = await http_json(
            "GET", BASE, params=self._params(q=query, maxResults=min(max(limit, 1), 20)),
            timeout=self.timeout,
        )
        records = []
        for i, item in enumerate((data or {}).get("items") or []):
            rec = parse_volume(item, rank=i)
            if rec:
                records.append(rec)
        return records

    async def resolve(self, kind: Kind, identifiers: dict[str, str]) -> list[ProviderRecord]:
        vid = safe_id(identifiers.get("google_books"))
        if vid:
            item = await http_json(
                "GET", f"{BASE}/{vid}", params=self._params(fields=_VOLUME_FIELDS),
                timeout=self.timeout, ok_404=True,
            )
            rec = parse_volume(item, rank=0) if item else None
            return [rec] if rec else []

        isbn = canonical_isbn13(identifiers.get("isbn_13") or identifiers.get("isbn_10"))
        if isbn:
            data = await http_json(
                "GET", BASE, params=self._params(q=f"isbn:{isbn}", maxResults=10), timeout=self.timeout
            )
            out = []
            for i, item in enumerate((data or {}).get("items") or []):
                rec = parse_volume(item, rank=i)
                if rec and isbn in rec.edition_isbns():  # ignore unrelated fuzzy hits
                    out.append(rec)
            return out
        return []
