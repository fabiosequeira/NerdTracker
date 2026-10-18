"""Decide which provider records describe the SAME edition / recording (and which merely share a title).

Verdicts, strongest first:
  strong    shared ISBN-13 (ISBN-10s are converted), shared ASIN, or shared provider edition id.
  conflict  both sides carry identifiers and they disagree -> DISTINCT editions. Never merged.
  soft      no identifier decides it, titles + authors agree and nothing contradicts (language,
            translators, narrators, recording type, runtime, page count, edition name, year).
  no        not the same thing.

Soft matches are only applied when they are UNAMBIGUOUS: if a record could belong to two different
clusters we leave it alone rather than risk gluing two distinct editions together.

Books and audiobooks are never compared with each other (callers pass one kind at a time and
`compare` returns "no" across kinds as a second line of defence).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from .normalize import (
    fold,
    people_overlap,
    similarity,
    titles_compatible,
    year_of,
)
from .schema import ProviderRecord

STRONG, SOFT, CONFLICT, NO = "strong", "soft", "conflict", "no"


@dataclass
class Verdict:
    kind: str
    evidence: int = 0


# --------------------------------------------------------------------------------------------
def _translators(r: ProviderRecord) -> list[str]:
    return [c.name for c in r.contributors if c.role == "translator"]


def _runtime_close(a: int, b: int) -> bool:
    return abs(a - b) <= max(10, int(0.08 * max(a, b)))


def _titles_ok(a: ProviderRecord, b: ProviderRecord) -> bool:
    return bool(a.title and b.title and titles_compatible(a.title, a.subtitle, b.title, b.subtitle))


def _authors_ok(a: ProviderRecord, b: ProviderRecord) -> bool:
    if a.authors and b.authors:
        return people_overlap(a.authors, b.authors) >= 0.5
    return True  # one side unknown: no evidence either way


def _soft_edition(a: ProviderRecord, b: ProviderRecord) -> Verdict:
    """Two edition-level records without a deciding identifier."""
    if not _titles_ok(a, b) or not _authors_ok(a, b):
        return Verdict(NO)

    # -- vetoes: any one of these means "different edition / recording / translation" -------------
    if a.language and b.language and a.language != b.language:
        return Verdict(CONFLICT)
    ta, tb = _translators(a), _translators(b)
    if ta and tb and people_overlap(ta, tb) == 0:
        return Verdict(CONFLICT)
    if a.edition and b.edition and fold(a.edition) != fold(b.edition):
        return Verdict(CONFLICT)

    evidence = 0
    ya, yb = year_of(a.published_date), year_of(b.published_date)

    if a.kind == "book":
        if a.page_count and b.page_count and abs(a.page_count - b.page_count) > max(30, int(0.2 * max(a.page_count, b.page_count))):
            return Verdict(CONFLICT)
        if ya and yb:
            if abs(ya - yb) >= 2:
                return Verdict(CONFLICT)
            evidence += 1 if ya == yb else 0
        if a.publisher and b.publisher and similarity(a.publisher, b.publisher) >= 0.6:
            evidence += 1
    else:  # audiobook: different narrators / abridgement / length = a different recording
        corroborated = False
        if a.narrators and b.narrators:
            if people_overlap(a.narrators, b.narrators) == 0:
                return Verdict(CONFLICT)
            evidence += 2
            corroborated = True
        if a.recording_type and b.recording_type:
            if a.recording_type != b.recording_type:
                return Verdict(CONFLICT)
            evidence += 1
        if a.runtime_minutes and b.runtime_minutes:
            if not _runtime_close(a.runtime_minutes, b.runtime_minutes):
                return Verdict(CONFLICT)
            evidence += 2
            corroborated = True
        if ya and yb:
            if ya == yb:
                evidence += 1
            elif abs(ya - yb) >= 2 and not corroborated:
                return Verdict(CONFLICT)  # re-releases differ in year; only forgive with corroboration
        if a.publisher and b.publisher and similarity(a.publisher, b.publisher) >= 0.6:
            evidence += 1
    return Verdict(SOFT, evidence)


def _work_vs_edition(work: ProviderRecord, ed: ProviderRecord) -> Verdict:
    """A work-level record (Open Library work, Hardcover book) against a concrete edition."""
    for key, value in work.identifiers.items():
        if value and ed.identifiers.get(key) == value:
            return Verdict(STRONG)  # e.g. both carry the same open_library_work / hardcover_book
    if work.work_isbns and ed.edition_isbns() & set(work.work_isbns):
        return Verdict(STRONG)
    if not _titles_ok(work, ed) or not _authors_ok(work, ed):
        return Verdict(NO)
    if ed.language and work.work_languages and ed.language not in work.work_languages:
        return Verdict(NO)  # a translation the work-level record doesn't list
    return Verdict(SOFT)


def _work_vs_work(a: ProviderRecord, b: ProviderRecord) -> Verdict:
    for key, value in a.identifiers.items():
        if value and b.identifiers.get(key) == value:
            return Verdict(STRONG)
    if a.work_isbns and b.work_isbns and set(a.work_isbns) & set(b.work_isbns):
        return Verdict(STRONG)
    if not _titles_ok(a, b) or not _authors_ok(a, b):
        return Verdict(NO)
    if a.work_languages and b.work_languages and not set(a.work_languages) & set(b.work_languages):
        return Verdict(NO)
    return Verdict(SOFT)


def compare(a: ProviderRecord, b: ProviderRecord) -> Verdict:
    if a.kind != b.kind:
        return Verdict(NO)  # a Book is never the same record as an Audiobook

    if a.level == "work" and b.level == "work":
        return _work_vs_work(a, b)
    if a.level == "work":
        return _work_vs_edition(a, b)
    if b.level == "work":
        return _work_vs_edition(b, a)

    # both editions ---------------------------------------------------------------------------
    if a.edition_ids() & b.edition_ids():
        return Verdict(STRONG)
    ia, ib = a.edition_isbns(), b.edition_isbns()
    if ia & ib:
        return Verdict(STRONG)
    if a.asin and b.asin:
        return Verdict(STRONG) if a.asin == b.asin else Verdict(CONFLICT)
    if ia and ib:
        return Verdict(CONFLICT)  # both have ISBNs and none are shared: different editions
    if a.provider == b.provider and a.provider_id and b.provider_id and a.provider_id != b.provider_id:
        return Verdict(CONFLICT)  # the provider itself lists them as separate entries
    return _soft_edition(a, b)


# --------------------------------------------------------------------------------------------
@dataclass
class Cluster:
    editions: list[ProviderRecord] = field(default_factory=list)
    works: list[ProviderRecord] = field(default_factory=list)

    @property
    def records(self) -> list[ProviderRecord]:
        return self.editions + self.works

    def has_strong_id(self) -> bool:
        return any(r.has_strong_id() for r in self.editions)


class _UnionFind:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def _group(records: list[ProviderRecord]) -> list[list[ProviderRecord]]:
    """Group by STRONG verdicts only (identifier-backed, always safe)."""
    uf = _UnionFind(len(records))
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            if compare(records[i], records[j]).kind == STRONG:
                uf.union(i, j)
    groups: dict[int, list[ProviderRecord]] = {}
    for i, r in enumerate(records):
        groups.setdefault(uf.find(i), []).append(r)
    return list(groups.values())


def _cluster_verdict(a: list[ProviderRecord], b: list[ProviderRecord]) -> Optional[int]:
    """Evidence score if every cross pair is compatible and at least one pair is soft/strong, else None."""
    best = -1
    for x in a:
        for y in b:
            v = compare(x, y)
            if v.kind in (CONFLICT, NO):
                return None
            best = max(best, v.evidence)
    return best if best >= 0 else None


def cluster_records(records: Iterable[ProviderRecord]) -> list[Cluster]:
    recs = list(records)
    editions = [r for r in recs if r.level == "edition"]
    works = [r for r in recs if r.level == "work"]

    # 1. editions that share an identifier ------------------------------------------------------
    groups = _group(editions)

    # 2. identifier-less groups: attach to ONE unambiguous best candidate -----------------------
    weak = [g for g in groups if not any(r.has_strong_id() for r in g)]
    weak_ids = {id(g) for g in weak}
    solid = [g for g in groups if id(g) not in weak_ids]
    pool = list(solid)
    for g in weak:
        candidates = [(c, _cluster_verdict(g, c)) for c in pool]
        candidates = [(c, s) for c, s in candidates if s is not None]
        if len(candidates) == 1 and candidates[0][1] >= 0:
            candidates[0][0].extend(g)
            continue
        if len(candidates) > 1:
            ranked = sorted(candidates, key=lambda cs: cs[1], reverse=True)
            if ranked[0][1] >= 2 and ranked[0][1] > ranked[1][1]:  # clear winner on real evidence
                ranked[0][0].extend(g)
                continue
        pool.append(g)  # stays its own result (may absorb later weak groups)

    clusters = [Cluster(editions=g) for g in pool]

    # 3. works: merge duplicates of the same work, then attach to the editions they describe ------
    work_groups = _group(works)
    merged_work_groups: list[list[ProviderRecord]] = []
    for g in work_groups:
        hit = None
        for m in merged_work_groups:
            if _cluster_verdict(g, m) is not None:
                hit = m
                break
        if hit is not None:
            hit.extend(g)
        else:
            merged_work_groups.append(list(g))

    attached = [False] * len(merged_work_groups)
    for cl in clusters:
        strong_hits, soft_hits = [], []
        for wi, wg in enumerate(merged_work_groups):
            verdicts = [compare(w, e).kind for w in wg for e in cl.editions]
            if STRONG in verdicts:
                strong_hits.append(wi)
            elif SOFT in verdicts:
                soft_hits.append(wi)
        chosen = strong_hits or (soft_hits if len(soft_hits) == 1 else [])
        for wi in chosen:
            cl.works.extend(merged_work_groups[wi])
            attached[wi] = True

    for wi, wg in enumerate(merged_work_groups):
        if not attached[wi]:
            clusters.append(Cluster(works=wg))
    return clusters
