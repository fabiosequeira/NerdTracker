"""Audnexus (https://api.audnex.us, OpenAPI docs at https://audnex.us). Audiobooks only. No key.

A community-run, documented API that serves Audible-derived audiobook metadata BY ASIN: narrators,
runtime, abridgement (`formatType`), series, genres, cover. It has no title search, so it is used to
ENRICH records whose ASIN is known (typed by the user, or discovered via Hardcover).
"""
from __future__ import annotations

from typing import Optional

from ..normalize import (
    clean_asin,
    clean_html,
    clean_text,
    dedupe_people,
    normalize_genres,
    normalize_language,
    parse_partial_date,
    parse_recording_type,
    positive_int,
    split_isbns,
)
from ..schema import Kind, ProviderRecord, SeriesInfo
from .base import Provider, http_json

BASE = "https://api.audnex.us"


def parse_book(data: dict) -> Optional[ProviderRecord]:
    asin = clean_asin(data.get("asin"))
    title = clean_text(data.get("title"))
    if not asin or not title:
        return None
    isbn10, isbn13, others = split_isbns([data.get("isbn")])
    s = data.get("seriesPrimary") or {}
    series_name = clean_text(s.get("name"))
    series = (
        SeriesInfo(
            name=series_name,
            position=clean_text(s.get("position"))
        )
        if series_name is not None
        else None
    )   
    return ProviderRecord(
        provider="audnexus", kind="audiobook", level="edition", provider_id=asin, rank=0,
        url=f"https://www.audible.com/pd/{asin}",
        asin=asin, isbn_10=isbn10, isbn_13=isbn13, other_isbns=others,
        title=title, subtitle=clean_text(data.get("subtitle")),
        authors=dedupe_people(
            name
            for a in data.get("authors") or []
            if isinstance(a, dict)
            if (name := clean_text(a.get("name"))) is not None
        ),

        narrators=dedupe_people(
            name
            for n in data.get("narrators") or []
            if isinstance(n, dict)
            if (name := clean_text(n.get("name"))) is not None
        ),
        description=clean_html(data.get("summary")) or clean_html(data.get("description")),
        cover=data.get("image") or None,
        publisher=clean_text(data.get("publisherName")),
        published_date=parse_partial_date(data.get("releaseDate")),
        language=normalize_language(data.get("language")),
        runtime_minutes=positive_int(data.get("runtimeLengthMin")),
        recording_type=parse_recording_type(data.get("formatType")),
        genres=normalize_genres(
            [
                name
                for g in data.get("genres") or []
                if isinstance(g, dict)
                if (name := clean_text(g.get("name"))) is not None
            ],
            limit=6
        ),        
        series=series,
    )


class AudnexusProvider(Provider):
    name = "audnexus"
    kinds = frozenset({"audiobook"})
    id_keys = frozenset({"asin"})

    async def resolve(self, kind: Kind, identifiers: dict[str, str]) -> list[ProviderRecord]:
        asin = clean_asin(identifiers.get("asin"))
        if not asin:
            return []
        data = await http_json(
            "GET", f"{BASE}/books/{asin}", params={"region": self.settings.audnexus_region},
            headers={"User-Agent": self.settings.user_agent, "Accept": "application/json"},
            timeout=self.timeout, ok_404=True,
        )
        rec = parse_book(data) if isinstance(data, dict) else None
        return [rec] if rec else []
