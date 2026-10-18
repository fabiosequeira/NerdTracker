"""Orchestrates providers: concurrent calls, isolated failures, per-provider caching, clustering, merging.

 search(kind, query)            -> merged, de-duplicated results + per-provider status
 lookup_isbn(kind, isbn)        -> the merged edition for an ISBN
 resolve(kind, identifiers)     -> ONE merged record for specific identifiers (used by add / refresh)

A provider that is unconfigured, slow or broken is reported in `providers` and otherwise ignored: it can
never fail the request. Successful provider responses are cached; failures never are.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from app.core.cache import TTLCache

from .identity import identity_keys
from .matching import Cluster, cluster_records
from .merge import Stored, merge_cluster
from .normalize import canonical_isbn13, clean_asin, fold, looks_like_isbn, similarity
from .providers import Provider, ProviderError, ProviderTimeout
from .schema import Kind, MergedRecord, ProviderRecord

_DEFAULT_CACHE = TTLCache(ttl=300, maxsize=512)
_ID_RANK = {"ok": 0, "empty": 0, "timeout": 1, "error": 2}


@dataclass
class AggregateResult:
    results: list[MergedRecord] = field(default_factory=list)
    providers: dict[str, dict] = field(default_factory=dict)


def _base_key(k: str) -> str:
    return k[:-5] if k.endswith("_hint") else k


def _record_ids(r: ProviderRecord) -> set[str]:
    ids = {f"{_base_key(k)}:{v}" for k, v in r.identifiers.items() if v}
    ids |= {f"isbn13:{i}" for i in r.edition_isbns()}
    if r.asin:
        ids.add(f"asin:{r.asin}")
    return ids


def _requested_ids(identifiers: dict[str, str]) -> set[str]:
    out = set()
    for k, v in identifiers.items():
        if not v:
            continue
        if k in ("isbn_13", "isbn_10"):
            c = canonical_isbn13(v)
            if c:
                out.add(f"isbn13:{c}")
        elif k == "asin":
            a = clean_asin(v)
            if a:
                out.add(f"asin:{a}")
        else:
            out.add(f"{_base_key(k)}:{v}")
    return out


def _completeness(m: MergedRecord) -> float:
    return sum(bool(x) for x in (m.cover, m.authors, m.description, m.publisher, m.published_date, m.isbn_13 or m.asin))


class MetadataAggregator:
    def __init__(self, providers: list[Provider], *, cache: Optional[TTLCache] = None):
        self.providers = providers
        self.cache = cache if cache is not None else _DEFAULT_CACHE

    # ---------------------------------------------------------------------------------------
    async def _call(self, provider: Provider, cache_key: tuple, factory) -> tuple[Optional[list[ProviderRecord]], dict]:
        t0 = time.monotonic()
        try:
            records = await asyncio.wait_for(self.cache.get_or_load(cache_key, factory), provider.timeout + 1.0)
            return records, {"status": "ok" if records else "empty", "count": len(records),
                             "ms": int((time.monotonic() - t0) * 1000)}
        except (asyncio.TimeoutError, ProviderTimeout):
            return None, {"status": "timeout", "detail": f"no answer within {provider.timeout:.0f}s", "count": 0,
                          "ms": int((time.monotonic() - t0) * 1000)}
        except ProviderError as exc:
            return None, {"status": "error", "detail": str(exc)[:160], "count": 0, "ms": int((time.monotonic() - t0) * 1000)}
        except Exception as exc:  # a bug in one provider must not break the request
            return None, {"status": "error", "detail": type(exc).__name__, "count": 0, "ms": int((time.monotonic() - t0) * 1000)}

    def _active(self, kind: Kind, statuses: dict[str, dict]) -> list[Provider]:
        active = []
        for p in self.providers:
            if not p.supports(kind):
                continue
            reason = p.disabled_reason()
            if reason:
                statuses[p.name] = {"status": "skipped", "detail": reason, "count": 0}
            else:
                active.append(p)
        return active

    @staticmethod
    def _merge_status(statuses: dict[str, dict], name: str, new: dict) -> None:
        old = statuses.get(name)
        if not old:
            statuses[name] = new
            return
        worse = new if _ID_RANK.get(new["status"], 0) > _ID_RANK.get(old["status"], 0) else old
        statuses[name] = {**worse, "count": old.get("count", 0) + new.get("count", 0)}

    # ---------------------------------------------------------------------------------------
    async def search(self, kind: Kind, query: str, limit: int = 10) -> AggregateResult:
        query = (query or "").strip()
        limit = max(1, min(limit, 25))
        isbn = looks_like_isbn(query)
        if isbn:
            return await self._lookup_many(kind, {"isbn_13": isbn}, query)
        asin = clean_asin(query) if kind == "audiobook" else None
        if asin:
            return await self._lookup_many(kind, {"asin": asin}, query)

        statuses: dict[str, dict] = {}
        active = self._active(kind, statuses)
        q = fold(query)

        async def run(p: Provider):
            return p, *(await self._call(p, (p.name, "search", kind, q, limit), lambda: p.search(kind, query, limit)))

        records: list[ProviderRecord] = []
        for p, recs, st in await asyncio.gather(*(run(p) for p in active)):
            statuses[p.name] = st
            records.extend(recs or [])

        merged = [self._score(merge_cluster(c, kind), c, query) for c in cluster_records(records)]
        merged.sort(key=lambda m: m.score, reverse=True)
        return AggregateResult(merged[:limit], statuses)

    @staticmethod
    def _score(m: MergedRecord, cluster: Cluster, query: str) -> MergedRecord:
        rrf = sum(1.0 / (60 + r.rank) for r in cluster.records if r.rank is not None)
        by_title = similarity(query, m.title or "")
        by_both = similarity(query, f"{m.title or ''} {' '.join(m.authors)}")
        m.score = round(10 * rrf + max(by_title, by_both) + 0.05 * _completeness(m) + (0.1 if m.level == "edition" else 0), 5)
        return m

    # ---------------------------------------------------------------------------------------
    async def _gather_resolve(self, kind: Kind, identifiers: dict[str, str], statuses: dict[str, dict]) -> list[ProviderRecord]:
        active = self._active(kind, statuses)
        used: dict[str, set] = {p.name: set() for p in active}
        records: list[ProviderRecord] = []
        known = dict(identifiers)

        for _round in range(2):
            jobs = []
            for p in active:
                rel = p.relevant(kind, known)
                fresh = {k: v for k, v in rel.items() if (k, v) not in used[p.name]}
                if not fresh:
                    continue
                used[p.name].update(fresh.items())
                key = (p.name, "resolve", kind, tuple(sorted(fresh.items())))
                jobs.append((p, self._call(p, key, lambda p=p, fresh=fresh: p.resolve(kind, fresh))))
            if not jobs:
                break
            for (p, _), (recs, st) in zip(jobs, await asyncio.gather(*(j for _, j in jobs))):
                self._merge_status(statuses, p.name, st)
                records.extend(recs or [])
            # identifiers discovered this round unlock providers in the next one ...
            for r in records:
                pairs = list(r.identifiers.items()) + [(k, v) for k, v in (("isbn_13", r.isbn_13), ("isbn_10", r.isbn_10), ("asin", r.asin)) if v]
                for k, v in pairs:
                    known.setdefault(k, v)
                    # ... but never ask a provider again about ids that came from its own records
                    used.setdefault(r.provider, set()).add((k, v))
        return records

    @staticmethod
    def _pick_primary(clusters: list[Cluster], identifiers: dict[str, str]) -> Optional[Cluster]:
        if not clusters:
            return None
        wanted = _requested_ids(identifiers)

        def overlap(c: Cluster) -> tuple:
            ids = set().union(*(_record_ids(r) for r in c.records)) if c.records else set()
            return (len(ids & wanted), len(c.editions), len(c.records))

        return max(clusters, key=overlap)

    async def resolve(self, kind: Kind, identifiers: dict[str, str], stored: Optional[Stored] = None) -> AggregateResult:
        statuses: dict[str, dict] = {}
        records = await self._gather_resolve(kind, identifiers, statuses)
        primary = self._pick_primary(cluster_records(records), identifiers)
        if primary is None:
            return AggregateResult([], statuses)
        return AggregateResult([merge_cluster(primary, kind, stored)], statuses)

    async def _lookup_many(self, kind: Kind, identifiers: dict[str, str], query: str) -> AggregateResult:
        res = await self.resolve(kind, identifiers)
        for m in res.results:
            m.score = 1.0
        return res

    async def lookup_isbn(self, kind: Kind, isbn: str) -> AggregateResult:
        c = canonical_isbn13(isbn)
        if not c:
            return AggregateResult([], {})
        return await self._lookup_many(kind, {"isbn_13": c}, c)


def result_key(m: MergedRecord) -> str:
    keys = identity_keys(m.kind, isbn_13=m.isbn_13, isbn_10=m.isbn_10, other_isbns=m.other_isbns, asin=m.asin,
                         identifiers=m.identifiers, level=m.level, title=m.title, subtitle=m.subtitle,
                         authors=m.authors, narrators=m.narrators, published_date=m.published_date,
                         language=m.language, recording_type=m.recording_type)
    return keys[0] if keys else ""


def to_search_item(m: MergedRecord) -> dict:
    """Shape consumed by the frontend search dropdown (poster/year mirror the other media types)."""
    ids: dict[str, str] = dict(m.identifiers)
    for k, v in (("isbn_13", m.isbn_13), ("isbn_10", m.isbn_10), ("asin", m.asin)):
        if v:
            ids[k] = v
    data = m.model_dump(exclude={"field_sources", "score", "sources"})
    data.update({
        "id": result_key(m),
        "poster": m.cover,
        "year": int(m.published_date[:4]) if m.published_date else m.first_published_year,
        "identifiers": ids,
        "description": (m.description or "")[:400] or None,  # dropdown only needs a teaser
    })
    return data
