"""Stable identity keys for an item. Two items that share ANY key are the same edition/recording.

Used for (a) search result ids and (b) duplicate prevention in the database ("claims").

  isbn13:<canonical ISBN-13>          every ISBN of the edition (ISBN-10s converted)
  asin:<ASIN>                         audio recordings
  <provider>:<id>                     provider EDITION ids (google_books, open_library_edition, hardcover_edition, itunes)
  <provider_work_key>:<id>            only for work-level-only records (open_library_work, hardcover_book)
  fp:<sha1>                           last resort when nothing else identifies the item: a fingerprint of
                                      normalised title / authors / narrators / year / language / recording type

Distinct editions have distinct ISBNs / ids, so they never share a key and can coexist; the same edition
reached through different providers shares at least its ISBN or a provider id.
"""
from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping, Optional

from .normalize import canonical_isbn13, clean_asin, normalize_person, normalize_title, year_of

_WORK_SUFFIXES = ("_work", "_book")
_NON_ID_SUFFIXES = ("_hint",)


def fingerprint(*, title, subtitle=None, authors=(), narrators=(), published_date=None, language=None,
                recording_type=None, kind="book") -> str:
    parts = [
        kind,
        normalize_title(title or "", subtitle),
        "|".join(sorted(normalize_person(a) for a in authors or [])),
        "|".join(sorted(normalize_person(n) for n in narrators or [])),
        str(year_of(published_date) or ""),
        language or "",
        recording_type or "",
    ]
    return "fp:" + hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]


def identity_keys(
    kind: str,
    *,
    isbn_13: Optional[str] = None,
    isbn_10: Optional[str] = None,
    other_isbns: Iterable[str] = (),
    asin: Optional[str] = None,
    identifiers: Optional[Mapping[str, str]] = None,
    level: str = "edition",
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    authors: Iterable[str] = (),
    narrators: Iterable[str] = (),
    published_date: Optional[str] = None,
    language: Optional[str] = None,
    recording_type: Optional[str] = None,
    **_: Any,
) -> list[str]:
    identifiers = identifiers or {}
    keys: list[str] = []

    def add(k: Optional[str]):
        if k and k not in keys:
            keys.append(k)

    for raw in [isbn_13, isbn_10, *other_isbns]:
        c = canonical_isbn13(raw)
        if c:
            add(f"isbn13:{c}")
    a = clean_asin(asin) if kind == "audiobook" else None
    if a:
        add(f"asin:{a}")
    for k, v in identifiers.items():
        if not v or k.endswith(_NON_ID_SUFFIXES):
            continue
        is_work_id = k.endswith(_WORK_SUFFIXES)
        if (level == "edition") != is_work_id:  # editions claim edition ids; work-level-only claims work ids
            add(f"{k}:{v}")
    if not keys and title:
        add(fingerprint(title=title, subtitle=subtitle, authors=authors, narrators=narrators,
                        published_date=published_date, language=language, recording_type=recording_type, kind=kind))
    return keys
