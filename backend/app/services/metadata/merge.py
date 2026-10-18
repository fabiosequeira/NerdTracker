"""Merge the records of ONE cluster (one edition / recording) into a single MergedRecord.

Rules
  * Field-level provider priority (below) decides conflicts, per kind. Different fields trust
    different providers (e.g. Open Library for covers, Hardcover for series, Audnexus for narrators).
  * Empty / null / placeholder values are never candidates, so they can never displace real data.
  * Edition-only fields (ISBN, publisher, page count, runtime, narrators, language ...) are never taken
    from a work-level record: those are aggregates over many editions.
  * List fields (authors, narrators, contributors, genres) are unions with de-duplication.
  * `stored` lets a refresh offer the currently stored values as candidates, carrying their original
    provenance. A fresh value from a lower-priority provider therefore cannot replace a better stored
    one, while a fresh value from the same (or a better) provider can update it.
  * Every chosen field records which provider supplied it (`field_sources`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from .matching import Cluster
from .normalize import (
    canonical_isbn13,
    date_precision,
    dedupe_people,
    fold,
    isbn13_to_isbn10,
    normalize_genres,
    persons_match,
    year_of,
)
from .schema import (
    EDITION_ONLY_FIELDS,
    Contributor,
    Kind,
    MergedRecord,
    ProviderRecord,
    SeriesInfo,
    SourceRef,
)

_DEFAULT_ORDER = ["audnexus", "hardcover", "google_books", "open_library", "itunes"]

PRIORITIES: dict[str, dict[str, list[str]]] = {
    "book": {
        "title": ["hardcover", "google_books", "open_library"],
        "subtitle": ["google_books", "hardcover", "open_library"],
        "authors": ["hardcover", "google_books", "open_library"],
        "contributors": ["open_library", "hardcover", "google_books"],
        "description": ["hardcover", "google_books", "open_library"],
        "cover": ["open_library", "hardcover", "google_books"],
        "publisher": ["google_books", "hardcover", "open_library"],
        "published_date": ["google_books", "hardcover", "open_library"],
        "language": ["google_books", "open_library", "hardcover"],
        "page_count": ["hardcover", "google_books", "open_library"],
        "edition": ["open_library", "hardcover", "google_books"],
        "genres": ["hardcover", "google_books", "open_library"],
        "series": ["hardcover", "open_library", "google_books"],
        "first_published_year": ["open_library", "hardcover"],
        "isbn": ["google_books", "open_library", "hardcover"],
    },
    "audiobook": {
        "title": ["audnexus", "hardcover", "itunes"],
        "subtitle": ["audnexus", "hardcover", "itunes"],
        "authors": ["audnexus", "hardcover", "itunes"],
        "narrators": ["audnexus", "hardcover", "itunes"],
        "contributors": ["hardcover", "audnexus", "itunes"],
        "description": ["audnexus", "hardcover", "itunes"],
        "cover": ["audnexus", "hardcover", "itunes"],
        "publisher": ["audnexus", "hardcover", "itunes"],
        "published_date": ["audnexus", "hardcover", "itunes"],
        "language": ["audnexus", "hardcover", "itunes"],
        "runtime_minutes": ["audnexus", "hardcover"],
        "recording_type": ["audnexus", "hardcover", "itunes"],
        "edition": ["hardcover", "audnexus", "itunes"],
        "genres": ["audnexus", "hardcover", "itunes"],
        "series": ["audnexus", "hardcover"],
        "first_published_year": ["hardcover", "audnexus"],
        "isbn": ["hardcover", "audnexus", "itunes"],
    },
}

_PLACEHOLDER_DESC = re.compile(r"^\s*(no description( available)?|description not available|n/?a|-)\s*\.?\s*$", re.I)

# stored value + its original provenance, offered as a candidate during a refresh
Stored = dict[str, tuple[Any, str]]


@dataclass
class _Cand:
    value: Any
    provider: str
    level_rank: int  # 0 = edition-level (or stored), 1 = work-level
    order: int  # tie-break: smaller wins (fresh data before stored, earlier provider rank first)


def _empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, (str, list, dict, tuple, set)):
        return len(v) == 0
    return False


def _prio(kind: str, field: str, provider: str) -> int:
    order = PRIORITIES[kind].get(field) or _DEFAULT_ORDER
    if provider in order:
        return order.index(provider)
    return len(order) + (_DEFAULT_ORDER.index(provider) if provider in _DEFAULT_ORDER else 50)


def _candidates(kind: str, field: str, records: list[ProviderRecord], stored: Optional[Stored]) -> list[_Cand]:
    cands: list[_Cand] = []
    for i, r in enumerate(records):
        if r.level == "work" and field in EDITION_ONLY_FIELDS:
            continue
        v = getattr(r, field, None)
        if field == "description" and isinstance(v, str) and _PLACEHOLDER_DESC.match(v):
            continue
        if not _empty(v):
            cands.append(_Cand(v, r.provider, 0 if r.level == "edition" else 1, i))
    if stored and field in stored and not _empty(stored[field][0]):
        value, provider = stored[field]
        cands.append(_Cand(value, provider or "stored", 0, 10_000))
    cands.sort(key=lambda c: (c.level_rank, _prio(kind, field, c.provider), c.order))
    return cands


def _pick(kind: str, field: str, records, stored, fs: dict[str, str]) -> Any:
    cands = _candidates(kind, field, records, stored)
    if not cands:
        return None
    fs[field] = cands[0].provider
    return cands[0].value


# ---- special-case pickers ------------------------------------------------------------------
def _pick_description(kind, records, stored, fs):
    cands = _candidates(kind, "description", records, stored)
    if not cands:
        return None
    best = cands[0]
    longest = max(cands, key=lambda c: len(c.value))
    # priority winner is a stub (<120 chars) while someone else has a real blurb -> prefer the real one
    if len(best.value) < 120 and len(longest.value) >= 3 * len(best.value):
        best = longest
    fs["description"] = best.provider
    return best.value


def _pick_date(kind, records, stored, fs):
    cands = _candidates(kind, "published_date", records, stored)
    if not cands:
        return None
    best = cands[0]
    same_year = [c for c in cands if year_of(c.value) == year_of(best.value)]
    most_precise = max(same_year, key=lambda c: (date_precision(c.value), -same_year.index(c)))
    # only upgrade precision when it is consistent with (starts like) the winner's value
    if date_precision(most_precise.value) > date_precision(best.value) and most_precise.value.startswith(best.value):
        best = most_precise
    fs["published_date"] = best.provider
    return best.value


def _union_people(kind, field, records, stored, fs):
    out: list[str] = []
    first: Optional[str] = None
    for c in _candidates(kind, field, records, stored):
        for name in c.value:
            if not any(persons_match(name, o) for o in out):
                out.append(name)
                first = first or c.provider
    out = dedupe_people(out)
    if out:
        fs[field] = first or "stored"
    return out


def _union_contributors(kind, records, stored, fs):
    out: list[Contributor] = []
    first = None
    for c in _candidates(kind, "contributors", records, stored):
        for item in c.value:
            con = item if isinstance(item, Contributor) else Contributor(**item)
            if not any(o.role == con.role and persons_match(o.name, con.name) for o in out):
                out.append(con)
                first = first or c.provider
    if out:
        fs["contributors"] = first or "stored"
    return out


def _union_genres(kind, records, stored, fs):
    seen: set[str] = set()
    out: list[str] = []
    first = None
    for c in _candidates(kind, "genres", records, stored):
        for g in c.value:
            if fold(g) not in seen:
                seen.add(fold(g))
                out.append(g)
                first = first or c.provider
    out = normalize_genres(out, limit=8)
    if out:
        fs["genres"] = first or "stored"
    return out


def _pick_series(kind, records, stored, fs) -> Optional[SeriesInfo]:
    cands = _candidates(kind, "series", records, stored)
    if not cands:
        return None
    best = cands[0]
    value = best.value if isinstance(best.value, SeriesInfo) else SeriesInfo(**best.value)
    if not value.position:  # borrow the position from another source naming the same series
        for c in cands[1:]:
            other = c.value if isinstance(c.value, SeriesInfo) else SeriesInfo(**c.value)
            if other.position and fold(other.name) == fold(value.name):
                value = SeriesInfo(name=value.name, position=other.position)
                break
    fs["series"] = best.provider
    return value


def _pick_cover(kind, records, stored, fs):
    cands = _candidates(kind, "cover", records, stored)
    if not cands:
        return None
    best = cands[0]
    fs["cover"] = best.provider
    return best.value


def _merge_identity(kind, records: list[ProviderRecord], stored: Optional[Stored], fs, keep_hints: bool = False):
    """ISBNs, ASIN and provider ids. Never lost: every one seen is kept."""
    ed = sorted([r for r in records if r.level == "edition"],
                key=lambda r: (_prio(kind, "isbn", r.provider)))
    thirteens: list[str] = []
    ten: Optional[str] = None
    asin: Optional[str] = None

    def add13(x):
        c = canonical_isbn13(x)
        if c and c not in thirteens:
            thirteens.append(c)

    if stored:
        for f in ("isbn_13", "isbn_10", "other_isbns"):
            if f in stored:
                for x in ([stored[f][0]] if not isinstance(stored[f][0], list) else stored[f][0]):
                    add13(x)
        ten = stored.get("isbn_10", (None,))[0]
        asin = stored.get("asin", (None,))[0]
    first_isbn_provider = None
    for r in ed:
        if r.isbn_13 and canonical_isbn13(r.isbn_13) and canonical_isbn13(r.isbn_13) not in thirteens:
            first_isbn_provider = first_isbn_provider or r.provider
        # primary ISBN-13 of the best provider goes first
        for x in [r.isbn_13, r.isbn_10, *r.other_isbns]:
            add13(x)
        ten = ten or r.isbn_10
        asin = asin or r.asin
        if r.isbn_13 or r.isbn_10:
            fs.setdefault("isbn_13", r.provider)
        if r.asin:
            fs.setdefault("asin", r.provider)

    # stored primary stays primary; otherwise the best provider's primary
    primary = None
    if stored and stored.get("isbn_13", (None,))[0]:
        primary = canonical_isbn13(stored["isbn_13"][0])
    if not primary:
        for r in ed:
            if r.isbn_13 and canonical_isbn13(r.isbn_13):
                primary = canonical_isbn13(r.isbn_13)
                break
    primary = primary or (thirteens[0] if thirteens else None)
    others = [x for x in thirteens if x != primary]
    if primary and not ten:
        ten = isbn13_to_isbn10(primary)

    identifiers: dict[str, str] = {}
    for k, v in ((stored or {}).get("identifiers", ({}, ""))[0] or {}).items():
        identifiers[k] = v
    for r in sorted(records, key=lambda r: (r.level != "edition", _prio(kind, "isbn", r.provider))):
        for k, v in r.identifiers.items():
            # "*_hint" ids (e.g. Open Library's representative edition for a work) are only useful while the
            # result is still work-level; once a concrete edition exists they are dropped.
            if v and k not in identifiers and (keep_hints or not k.endswith("_hint")):
                identifiers[k] = v
    if not keep_hints:
        identifiers = {k: v for k, v in identifiers.items() if not k.endswith("_hint")}
    return primary, ten, others, asin, identifiers


# --------------------------------------------------------------------------------------------
def merge_cluster(cluster: Cluster, kind: Kind, stored: Optional[Stored] = None) -> MergedRecord:
    records = sorted(cluster.records, key=lambda r: (r.level != "edition", r.rank if r.rank is not None else 999))
    fs: dict[str, str] = {}

    primary, ten, others, asin, identifiers = _merge_identity(kind, records, stored, fs, keep_hints=not cluster.editions)

    merged = MergedRecord(
        kind=kind,
        level="edition" if cluster.editions else "work",
        title=_pick(kind, "title", records, stored, fs),
        subtitle=_pick(kind, "subtitle", records, stored, fs),
        authors=_union_people(kind, "authors", records, stored, fs),
        contributors=_union_contributors(kind, records, stored, fs),
        isbn_10=ten,
        isbn_13=primary,
        other_isbns=others,
        asin=asin if kind == "audiobook" else None,
        identifiers=identifiers,
        edition=_pick(kind, "edition", records, stored, fs),
        publisher=_pick(kind, "publisher", records, stored, fs),
        published_date=_pick_date(kind, records, stored, fs),
        first_published_year=_pick(kind, "first_published_year", records, stored, fs),
        language=_pick(kind, "language", records, stored, fs),
        description=_pick_description(kind, records, stored, fs),
        cover=_pick_cover(kind, records, stored, fs),
        genres=_union_genres(kind, records, stored, fs),
        series=_pick_series(kind, records, stored, fs),
    )
    if kind == "book":
        merged.page_count = _pick(kind, "page_count", records, stored, fs)
    else:
        merged.narrators = _union_people(kind, "narrators", records, stored, fs)
        merged.runtime_minutes = _pick(kind, "runtime_minutes", records, stored, fs)
        merged.recording_type = _pick(kind, "recording_type", records, stored, fs)

    for f in ("isbn_10", "isbn_13", "other_isbns"):
        if getattr(merged, f):
            fs.setdefault(f, fs.get("isbn_13") or "stored")
    if not (merged.isbn_13 or merged.isbn_10):
        fs.pop("isbn_13", None)
    fs["identifiers"] = "merged"

    seen: set[tuple] = set()
    for r in records:
        key = (r.provider, r.level, r.provider_id)
        if key not in seen:
            seen.add(key)
            merged.sources.append(SourceRef(provider=r.provider, level=r.level, provider_id=r.provider_id, url=r.url))
    merged.providers = list(dict.fromkeys(s.provider for s in merged.sources))
    merged.field_sources = {k: v for k, v in fs.items() if k != "identifiers" or v}
    return merged
