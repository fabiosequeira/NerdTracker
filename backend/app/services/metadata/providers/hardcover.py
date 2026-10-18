"""Hardcover GraphQL API (https://docs.hardcover.app/api/getting-started/). Books AND audiobooks.

Requires HARDCOVER_API_TOKEN (free; from your Hardcover account settings). Without it the provider is
reported as "skipped" and everything else keeps working.

Hardcover is the main source of audiobook-specific data here: narrators, runtime (audio_seconds), ASIN,
audio edition ISBNs, plus series and genres. Queries stay at depth <= 3 (Hardcover's documented limit):
`books` and `editions` are separate root fields and are joined in code.

NOTE: field names follow Hardcover's public schema docs; if Hardcover changes its schema the provider
fails soft (status "error: ..." in the API's `providers` block) and the others carry on.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from ..normalize import (
    canonical_isbn13,
    clean_html,
    clean_text,
    dedupe_people,
    normalize_genres,
    normalize_language,
    parse_partial_date,
    parse_recording_type,
    positive_int,
    seconds_to_minutes,
    split_isbns,
)
from ..schema import Contributor, Kind, ProviderRecord, SeriesInfo
from .base import Provider, ProviderError, http_json, safe_id

ENDPOINT = "https://api.hardcover.app/v1/graphql"

_BOOK_FIELDS = "id slug title subtitle description release_year cached_tags cached_image book_series { position series { name } }"
_EDITION_FIELDS = ("id book_id title subtitle isbn_10 isbn_13 asin pages audio_seconds release_date edition_format "
                   "edition_information cached_image cached_contributors language { code2 } publisher { name }")

SEARCH_Q = 'query Search($q: String!, $n: Int!) { search(query: $q, query_type: "Book", per_page: $n, page: 1) { results } }'
DETAILS_Q = ("query Details($ids: [Int!]!, $audio: Boolean!) {"
             f" books(where: {{id: {{_in: $ids}}}}) {{ {_BOOK_FIELDS} }}"
             f" editions(where: {{book_id: {{_in: $ids}}, audio_seconds: {{_is_null: false}}}}, limit: 40) @include(if: $audio) {{ {_EDITION_FIELDS} }} }}")
EDITIONS_BY_ISBN_Q = (f"query ByIsbn($i13: String, $i10: String) {{ editions(where: {{_or: [{{isbn_13: {{_eq: $i13}}}}, {{isbn_10: {{_eq: $i10}}}}]}}, limit: 10) {{ {_EDITION_FIELDS} }} }}")
EDITIONS_BY_ASIN_Q = f"query ByAsin($asin: String!) {{ editions(where: {{asin: {{_eq: $asin}}}}, limit: 10) {{ {_EDITION_FIELDS} }} }}"
EDITION_BY_ID_Q = f"query ById($id: Int!) {{ editions(where: {{id: {{_eq: $id}}}}, limit: 1) {{ {_EDITION_FIELDS} }} }}"


def _num_str(v: Any) -> Optional[str]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return clean_text(v)
    return str(int(f)) if f == int(f) else str(f)


def _img(cached: Any) -> Optional[str]:
    if isinstance(cached, str):
        try:
            cached = json.loads(cached)
        except ValueError:
            return None
    return cached.get("url") if isinstance(cached, dict) else None


def _json(v: Any) -> Any:
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return None
    return v


def _series(book: dict) -> Optional[SeriesInfo]:
    for bs in book.get("book_series") or []:
        name = clean_text(((bs or {}).get("series") or {}).get("name"))
        if name:
            return SeriesInfo(name=name, position=_num_str((bs or {}).get("position")))
    return None


def _genres(book: dict) -> list[str]:
    tags = _json(book.get("cached_tags")) or {}
    items = tags.get("Genre") if isinstance(tags, dict) else None

    return normalize_genres(
        [
            tag
            for t in items or []
            if isinstance(t, dict)
            if (tag := clean_text(t.get("tag"))) is not None
        ],
        limit=6
    )


def parse_search_hit(hit: dict, rank: int) -> Optional[ProviderRecord]:
    doc = (hit or {}).get("document") or {}
    bid, title = safe_id(doc.get("id")), clean_text(doc.get("title"))
    if not bid or not title:
        return None
    work_isbns = [c for c in dict.fromkeys(canonical_isbn13(x) for x in doc.get("isbns") or []) if c]
    series = clean_text((doc.get("series_names") or [None])[0])
    slug = doc.get("slug")
    return ProviderRecord(
        provider="hardcover", kind="book", level="work", provider_id=bid, rank=rank,
        url=f"https://hardcover.app/books/{slug}" if slug else None,
        identifiers={"hardcover_book": bid},
        title=title, subtitle=clean_text(doc.get("subtitle")),
        authors=dedupe_people(doc.get("author_names") or []),
        description=clean_html(doc.get("description")),
        cover=_img(doc.get("image")),
        genres=normalize_genres(doc.get("genres") or [], limit=6),
        series=SeriesInfo(name=series) if series is not None else None,
        first_published_year=positive_int(doc.get("release_year")),
        work_isbns=work_isbns,
    )


def parse_book(book: dict, kind: Kind, rank: Optional[int] = None) -> Optional[ProviderRecord]:
    bid, title = safe_id(book.get("id")), clean_text(book.get("title"))
    if not bid or not title:
        return None
    slug = book.get("slug")
    return ProviderRecord(
        provider="hardcover", kind=kind, level="work", provider_id=bid, rank=rank,
        url=f"https://hardcover.app/books/{slug}" if slug else None,
        identifiers={"hardcover_book": bid},
        title=title, subtitle=clean_text(book.get("subtitle")),
        description=clean_html(book.get("description")),
        cover=_img(book.get("cached_image")),
        genres=_genres(book), series=_series(book),
        first_published_year=positive_int(book.get("release_year")),
    )


def parse_edition(ed: dict, kind: Kind, book: Optional[dict] = None, rank: Optional[int] = None) -> Optional[ProviderRecord]:
    audio = ed.get("audio_seconds") is not None
    if (kind == "audiobook") != audio:  # keep Books and Audiobooks strictly apart
        return None
    eid = safe_id(ed.get("id"))
    book = book or {}
    title = clean_text(ed.get("title") or book.get("title"))
    if not eid or not title:
        return None

    authors, narrators, contributors = [], [], []
    for c in _json(ed.get("cached_contributors")) or []:
        name = clean_text(((c or {}).get("author") or {}).get("name"))
        role = (clean_text((c or {}).get("contribution")) or "").lower()
        if not name:
            continue
        if role in ("", "author", "authors", "writer"):
            authors.append(name)
        elif "narrat" in role or role in ("reader", "read by"):
            narrators.append(name)
        else:
            contributors.append(Contributor(name=name, role=role))

    isbn10, isbn13, others = split_isbns([ed.get("isbn_13"), ed.get("isbn_10")])
    bid = safe_id(ed.get("book_id"))
    slug = book.get("slug")
    ident = {"hardcover_edition": eid}
    if bid:
        ident["hardcover_book"] = bid

    rec = ProviderRecord(
        provider="hardcover", kind=kind, level="edition", provider_id=eid, rank=rank,
        url=f"https://hardcover.app/books/{slug}" if slug else None,
        identifiers=ident,
        isbn_10=isbn10, isbn_13=isbn13, other_isbns=others,
        title=title, subtitle=clean_text(ed.get("subtitle") or book.get("subtitle")),
        authors=dedupe_people(authors), contributors=contributors,
        cover=_img(ed.get("cached_image")) or _img(book.get("cached_image")),
        publisher=clean_text(((ed.get("publisher") or {}).get("name"))),
        published_date=parse_partial_date(ed.get("release_date")),
        language=normalize_language((ed.get("language") or {}).get("code2")),
        edition=clean_text(ed.get("edition_information")) if not audio else None,
    )
    if audio:
        rec.narrators = dedupe_people(narrators)
        rec.asin = (clean_text(ed.get("asin")) or "").upper() or None
        rec.runtime_minutes = seconds_to_minutes(ed.get("audio_seconds"))
        rec.recording_type = parse_recording_type(ed.get("edition_format"), ed.get("edition_information"), title)
    else:
        rec.page_count = positive_int(ed.get("pages"))
    return rec


class HardcoverProvider(Provider):
    name = "hardcover"
    kinds = frozenset({"book", "audiobook"})
    id_keys = frozenset({"hardcover_edition", "hardcover_book", "isbn_13", "isbn_10", "asin"})

    def disabled_reason(self) -> Optional[str]:
        return super().disabled_reason() or (None if self.settings.hardcover_token else "HARDCOVER_API_TOKEN not set")

    def relevant(self, kind: Kind, identifiers: dict[str, str]) -> dict[str, str]:
        out = super().relevant(kind, identifiers)
        if kind == "book":
            out.pop("asin", None)  # ASINs identify audio recordings
        return out

    async def _gql(self, query: str, variables: dict) -> dict:
        data = await http_json(
            "POST", ENDPOINT, json_body={"query": query, "variables": variables},
            headers={"authorization": f"Bearer {self.settings.hardcover_token}", "content-type": "application/json"},
            timeout=self.timeout,
        )
        if not isinstance(data, dict):
            raise ProviderError("unexpected response")
        if data.get("errors"):
            msg = clean_text((data["errors"][0] or {}).get("message")) or "GraphQL error"
            raise ProviderError(f"graphql: {msg[:120]}")
        return data.get("data") or {}

    async def _details(self, kind: Kind, book_ids: list[int]) -> tuple[dict[str, dict], list[dict]]:
        if not book_ids:
            return {}, []
        data = await self._gql(DETAILS_Q, {"ids": book_ids, "audio": kind == "audiobook"})
        books = {str(b["id"]): b for b in data.get("books") or [] if b.get("id") is not None}
        return books, data.get("editions") or []

    def _records(self, kind: Kind, books: dict[str, dict], editions: list[dict], order: list[str]) -> list[ProviderRecord]:
        out: list[ProviderRecord] = []
        for rank, bid in enumerate(order):
            book = books.get(bid)
            if not book:
                continue
            work = parse_book(book, kind, rank)
            if work:
                out.append(work)
        for i, ed in enumerate(editions):
            rec = parse_edition(ed, kind, books.get(str(ed.get("book_id"))), rank=order.index(str(ed.get("book_id"))) if str(ed.get("book_id")) in order else i)
            if rec:
                out.append(rec)
        return out

    async def search(self, kind: Kind, query: str, limit: int) -> list[ProviderRecord]:
        data = await self._gql(SEARCH_Q, {"q": query, "n": min(max(limit, 1), 20)})
        results = _json(((data.get("search") or {}).get("results"))) or {}
        hits = results.get("hits") or []
        if kind == "book":
            return [r for r in (parse_search_hit(h, i) for i, h in enumerate(hits)) if r]
        ids = [int(h["document"]["id"]) for h in hits if (h.get("document") or {}).get("id") is not None][:10]
        books, editions = await self._details("audiobook", ids)
        return self._records("audiobook", books, editions, [str(i) for i in ids])

    async def resolve(self, kind: Kind, identifiers: dict[str, str]) -> list[ProviderRecord]:
        editions: list[dict] = []
        eid = positive_int(identifiers.get("hardcover_edition"))
        asin = clean_text(identifiers.get("asin"))
        isbn = canonical_isbn13(identifiers.get("isbn_13") or identifiers.get("isbn_10"))

        if eid:
            editions = (await self._gql(EDITION_BY_ID_Q, {"id": eid})).get("editions") or []
        elif asin and kind == "audiobook":
            editions = (await self._gql(EDITIONS_BY_ASIN_Q, {"asin": asin.upper()})).get("editions") or []
        elif isbn:
            from ..normalize import isbn13_to_isbn10
            editions = (await self._gql(EDITIONS_BY_ISBN_Q, {"i13": isbn, "i10": isbn13_to_isbn10(isbn)})).get("editions") or []

        book_ids = {int(e["book_id"]) for e in editions if e.get("book_id") is not None}
        hardcover_book_id = positive_int(identifiers.get("hardcover_book"))
        if hardcover_book_id is not None:
            book_ids.add(hardcover_book_id)
        if not book_ids and not editions:
            return []
        books, audio_editions = await self._details(kind, sorted(book_ids))
        # keep only editions we explicitly resolved (an ISBN / ASIN / edition id), not every edition of the book
        wanted = editions if editions else (audio_editions if kind == "audiobook" else [])
        return self._records(kind, books, wanted, [str(b) for b in sorted(book_ids)])
