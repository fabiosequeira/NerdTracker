"""Apple iTunes Search API (https://performance-partners.apple.com/search-api). Audiobooks only. No key.

Gives audiobook title / author / cover art / release date / description / genre. It does NOT provide
narrators, runtime or ISBNs, so those come from Hardcover / Audnexus. Apple titles usually carry an
explicit "(Unabridged)" / "(Abridged)" marker, which is the source of `recording_type` here.
"""
from __future__ import annotations

import re
from typing import Optional

from ..normalize import (
    clean_html,
    clean_text,
    dedupe_people,
    normalize_genres,
    parse_partial_date,
    parse_recording_type,
    strip_title_noise,
)
from ..schema import Kind, ProviderRecord
from .base import Provider, http_json, safe_id

BASE = "https://itunes.apple.com"
_AUTHOR_SPLIT = re.compile(r"\s+&\s+|\s*;\s*")


def _artwork(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    return re.sub(r"/\d+x\d+bb\.", "/600x600bb.", url, count=1)  # Apple serves any size from the same path


def parse_item(item: dict, rank: Optional[int] = None) -> Optional[ProviderRecord]:
    cid = safe_id(item.get("collectionId"))
    raw_title = clean_text(item.get("collectionName"))
    if not cid or not raw_title:
        return None
    genre = clean_text(item.get("primaryGenreName"))
    return ProviderRecord(
        provider="itunes", kind="audiobook", level="edition", provider_id=cid, rank=rank,
        url=item.get("collectionViewUrl"),
        identifiers={"itunes": cid},
        title=strip_title_noise(raw_title) or raw_title,
        authors=dedupe_people(_AUTHOR_SPLIT.split(item.get("artistName") or "")),
        description=clean_html(item.get("description")),
        cover=_artwork(item.get("artworkUrl100") or item.get("artworkUrl60")),
        published_date=parse_partial_date(item.get("releaseDate")),
        recording_type=parse_recording_type(raw_title),
        genres=normalize_genres([genre]) if genre and genre.lower() != "audiobooks" else [],
    )


class ITunesProvider(Provider):
    name = "itunes"
    kinds = frozenset({"audiobook"})
    id_keys = frozenset({"itunes"})

    async def search(self, kind: Kind, query: str, limit: int) -> list[ProviderRecord]:
        data = await http_json(
            "GET", f"{BASE}/search",
            params={"term": query, "media": "audiobook", "entity": "audiobook",
                    "limit": min(max(limit, 1), 25), "country": self.settings.itunes_country},
            timeout=self.timeout,
        )
        out = []
        for i, item in enumerate((data or {}).get("results") or []):
            rec = parse_item(item, rank=i)
            if rec:
                out.append(rec)
        return out

    async def resolve(self, kind: Kind, identifiers: dict[str, str]) -> list[ProviderRecord]:
        cid = safe_id(identifiers.get("itunes"))
        if not cid:
            return []
        data = await http_json(
            "GET", f"{BASE}/lookup", params={"id": cid, "country": self.settings.itunes_country},
            timeout=self.timeout, ok_404=True,
        )
        for item in (data or {}).get("results") or []:
            if str(item.get("collectionId")) == cid:
                rec = parse_item(item, rank=0)
                return [rec] if rec else []
        return []
