"""Open Library (https://openlibrary.org/developers/api). Books only. No API key.

 * search.json            -> WORK-level records (aggregate over all editions of a work)
 * api/books + edition    -> EDITION-level record, by ISBN or OLID
 * works/{id}.json        -> WORK-level enrichment (description, subjects, first publication)

Open Library asks API clients to identify themselves: the User-Agent is built from
OPENLIBRARY_CONTACT (optional).
"""
from __future__ import annotations

import asyncio
import re
from typing import Any, Optional

from ..normalize import (
    canonical_isbn13,
    clean_html,
    clean_text,
    dedupe_people,
    normalize_genres,
    normalize_language,
    parse_partial_date,
    parse_series,
    positive_int,
    split_isbns,
    year_of,
)
from ..schema import Contributor, Kind, ProviderRecord, SeriesInfo
from .base import Provider, ProviderError, http_json, safe_id

SITE = "https://openlibrary.org"
COVERS = "https://covers.openlibrary.org/b/id"
_SEARCH_FIELDS = ("key,title,subtitle,author_name,first_publish_year,cover_i,cover_edition_key,isbn,"
                  "language,subject,edition_count")
_ROLE_RE = re.compile(r"^(?P<name>.+?)\s*\((?P<role>[^)]+)\)\s*$")


def _text(value: Any) -> Optional[str]:
    """Open Library text fields are either a string or {"type": "/type/text", "value": "..."}."""
    if isinstance(value, dict):
        value = value.get("value")
    return clean_html(value) if isinstance(value, str) else None


def _olid(key: Optional[str]) -> Optional[str]:
    return safe_id(key.rsplit("/", 1)[-1]) if key else None


def _cover(cover_id: Any) -> Optional[str]:
    n = positive_int(cover_id)
    return f"{COVERS}/{n}-L.jpg" if n else None


def parse_search_doc(doc: dict, rank: Optional[int] = None) -> Optional[ProviderRecord]:
    work = _olid(doc.get("key"))
    title = clean_text(doc.get("title"))
    if not work or not title:
        return None
    work_isbns: list[str] = []
    for raw in (doc.get("isbn") or [])[:600]:
        c = canonical_isbn13(raw)
        if c and c not in work_isbns:
            work_isbns.append(c)
    langs = [l for l in (normalize_language(x) for x in doc.get("language") or []) if l]
    hint = safe_id((doc.get("cover_edition_key") or "")) if doc.get("cover_edition_key") else None
    return ProviderRecord(
        provider="open_library", kind="book", level="work", provider_id=work, rank=rank,
        url=f"{SITE}/works/{work}",
        identifiers={"open_library_work": work, **({"open_library_edition_hint": hint} if hint else {})},
        title=title,
        subtitle=clean_text(doc.get("subtitle")),
        authors=dedupe_people(doc.get("author_name") or []),
        cover=_cover(doc.get("cover_i")),
        genres=normalize_genres(doc.get("subject") or [], limit=6),
        first_published_year=positive_int(doc.get("first_publish_year")),
        work_isbns=work_isbns,
        work_languages=list(dict.fromkeys(langs)),
    )


def parse_edition(data: Optional[dict], edition: Optional[dict], olid_hint: Optional[str] = None) -> Optional[ProviderRecord]:
    """Combine `api/books?jscmd=data` (names, publisher, cover) with the raw edition JSON (language,
    series, translators, description). Either may be missing."""
    data, edition = data or {}, edition or {}
    title = clean_text(edition.get("title") or data.get("title"))
    if not title:
        return None

    ident = data.get("identifiers") or {}
    isbn10, isbn13, others = split_isbns(
        [*(edition.get("isbn_13") or []), *(edition.get("isbn_10") or []),
         *(ident.get("isbn_13") or []), *(ident.get("isbn_10") or [])]
    )
    olid = _olid(edition.get("key")) or safe_id((ident.get("openlibrary") or [None])[0]) or olid_hint
    work = _olid(((edition.get("works") or [{}])[0]).get("key"))

    langs = [normalize_language(l.get("key")) for l in edition.get("languages") or [] if isinstance(l, dict)]
    langs = [l for l in langs if l]

    publishers = [p.get("name") for p in data.get("publishers") or [] if isinstance(p, dict)] or (edition.get("publishers") or [])
    cover = (data.get("cover") or {}).get("large") or (_cover((edition.get("covers") or [None])[0]))

    series = None
    for s in edition.get("series") or []:
        name, pos = parse_series(s)
        if name:
            series = SeriesInfo(name=name, position=pos)
            break

    contributors = []
    for raw in edition.get("contributions") or []:
        m = _ROLE_RE.match(str(raw))
        if m:
            contributors.append(Contributor(name=m.group("name").strip(), role=m.group("role").strip().lower()))

    identifiers = {}
    if olid:
        identifiers["open_library_edition"] = olid
    if work:
        identifiers["open_library_work"] = work

    return ProviderRecord(
        provider="open_library", kind="book", level="edition", provider_id=olid, rank=0,
        url=data.get("url") or (f"{SITE}/books/{olid}" if olid else None),
        identifiers=identifiers,
        isbn_10=isbn10, isbn_13=isbn13, other_isbns=others,
        title=title,
        subtitle=clean_text(edition.get("subtitle") or data.get("subtitle")),
        authors=dedupe_people(
            name
            for a in data.get("authors") or []
            if isinstance(a, dict)
            if (name := clean_text(a.get("name"))) is not None
        ),        
        contributors=contributors,
        description=_text(edition.get("description")),
        cover=cover,
        publisher=clean_text(publishers[0]) if publishers else None,
        published_date=parse_partial_date(edition.get("publish_date") or data.get("publish_date")),
        language=langs[0] if len(langs) == 1 else None,  # several languages = ambiguous, say nothing
        page_count=positive_int(edition.get("number_of_pages") or data.get("number_of_pages")),
        genres=normalize_genres(
            [
                name
                for s in data.get("subjects") or []
                if isinstance(s, dict)
                if (name := clean_text(s.get("name"))) is not None
            ],
            limit=6
        ),
        series=series,
        edition=clean_text(edition.get("edition_name")),
    )


def parse_work(work: Optional[dict], work_id: str) -> Optional[ProviderRecord]:
    if not work or not work.get("title"):
        return None
    first = year_of(parse_partial_date(work.get("first_publish_date")))
    covers = [c for c in work.get("covers") or [] if isinstance(c, int) and c > 0]
    return ProviderRecord(
        provider="open_library", kind="book", level="work", provider_id=work_id, rank=0,
        url=f"{SITE}/works/{work_id}",
        identifiers={"open_library_work": work_id},
        title=clean_text(work.get("title")),
        subtitle=clean_text(work.get("subtitle")),
        description=_text(work.get("description")),
        cover=_cover(covers[0]) if covers else None,
        genres=normalize_genres(work.get("subjects") or [], limit=6),
        first_published_year=first,
    )


class OpenLibraryProvider(Provider):
    name = "open_library"
    kinds = frozenset({"book"})
    id_keys = frozenset({"open_library_edition", "open_library_edition_hint", "open_library_work", "isbn_13", "isbn_10"})

    def _headers(self) -> dict:
        return {"User-Agent": self.settings.user_agent, "Accept": "application/json"}

    async def _get(self, path: str, params: Optional[dict] = None):
        return await http_json("GET", f"{SITE}{path}", params=params, headers=self._headers(),
                               timeout=self.timeout, follow_redirects=True, ok_404=True)

    async def search(self, kind: Kind, query: str, limit: int) -> list[ProviderRecord]:
        data = await self._get("/search.json", {"q": query, "limit": min(max(limit, 1), 20), "fields": _SEARCH_FIELDS})
        out = []
        for i, doc in enumerate((data or {}).get("docs") or []):
            rec = parse_search_doc(doc, rank=i)
            if rec:
                out.append(rec)
        return out

    async def _edition(self, bibkey: str, edition_path: str, olid_hint: Optional[str]) -> Optional[ProviderRecord]:
        data_task = self._get("/api/books", {"bibkeys": bibkey, "format": "json", "jscmd": "data"})
        ed_task = self._get(edition_path)
        data_res, ed_res = await asyncio.gather(data_task, ed_task, return_exceptions=True)
        if isinstance(data_res, Exception) and isinstance(ed_res, Exception):
            raise data_res  # both calls failed: surface it as a provider error
        data = data_res.get(bibkey) if isinstance(data_res, dict) else None
        edition = None if isinstance(ed_res, Exception) else ed_res
        return parse_edition(data, edition if isinstance(edition, dict) else None, olid_hint)

    async def resolve(self, kind: Kind, identifiers: dict[str, str]) -> list[ProviderRecord]:
        jobs = []
        isbn = canonical_isbn13(identifiers.get("isbn_13") or identifiers.get("isbn_10"))
        ol_edition = safe_id(identifiers.get("open_library_edition") or identifiers.get("open_library_edition_hint"))
        work = safe_id(identifiers.get("open_library_work"))

        if ol_edition:
            jobs.append(self._edition(f"OLID:{ol_edition}", f"/books/{ol_edition}.json", ol_edition))
        elif isbn:
            jobs.append(self._edition(f"ISBN:{isbn}", f"/isbn/{isbn}.json", None))
        if work:
            async def _work():
                return parse_work(await self._get(f"/works/{work}.json"), work)
            jobs.append(_work())

        results = await asyncio.gather(*jobs, return_exceptions=True)
        records = [r for r in results if isinstance(r, ProviderRecord)]
        errors = [r for r in results if isinstance(r, Exception)]
        if errors and not records:
            raise errors[0] if isinstance(errors[0], ProviderError) else ProviderError(type(errors[0]).__name__)
        return records
