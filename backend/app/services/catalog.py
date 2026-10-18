"""Add / refresh / edit / delete for Books and Audiobooks (one implementation, parameterised by kind)."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any, Optional, Type

from beanie import Document, PydanticObjectId
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, field_validator

from app.models.catalog import PERSONAL_FIELDS, utcnow
from app.services.claims import AlreadyClaimed, ClaimStore, MongoClaimStore, claim_keys
from app.services.metadata.aggregator import AggregateResult, MetadataAggregator
from app.services.metadata.identity import identity_keys
from app.services.metadata.merge import Stored
from app.services.metadata.normalize import canonical_isbn13, clean_asin
from app.services.metadata.providers.base import safe_id
from app.services.metadata.schema import Kind, MergedRecord, SourceRef, metadata_fields

ALLOWED_IDENTIFIERS = (
    "isbn_10", "isbn_13", "asin", "google_books", "open_library_edition", "open_library_edition_hint",
    "open_library_work", "hardcover_edition", "hardcover_book", "itunes",
)


# ------------------------------------------------------------------------------------------------
# Errors (routes translate them to HTTP)
# ------------------------------------------------------------------------------------------------
class CatalogError(Exception):
    status_code = 400

    def __init__(self, detail: str, **extra: Any):
        super().__init__(detail)
        self.detail = detail
        self.extra = extra


class InvalidRequest(CatalogError):
    status_code = 422


class InvalidIdentifiers(InvalidRequest):
    pass


class NotResolvable(CatalogError):
    status_code = 404


class ProvidersUnavailable(CatalogError):
    status_code = 502


class AlreadyInLibrary(CatalogError):
    status_code = 409


# ------------------------------------------------------------------------------------------------
# Request models
# ------------------------------------------------------------------------------------------------
def validate_identifiers(kind: Kind, raw: dict[str, str]) -> dict[str, str]:
    """Identifiers end up in provider URLs and in the database: validate everything, accept nothing odd."""
    if not isinstance(raw, dict) or not raw:
        raise InvalidIdentifiers("identifiers is required")
    out: dict[str, str] = {}
    for key, value in raw.items():
        if key not in ALLOWED_IDENTIFIERS:
            raise InvalidIdentifiers(f"unknown identifier '{key}'")
        if value in (None, ""):
            continue
        if key in ("isbn_10", "isbn_13"):
            c = canonical_isbn13(value)
            if not c:
                raise InvalidIdentifiers(f"'{value}' is not a valid ISBN")
            out["isbn_13"] = c
        elif key == "asin":
            a = clean_asin(value)
            if not a:
                raise InvalidIdentifiers(f"'{value}' is not a valid ASIN")
            if kind == "audiobook":
                out["asin"] = a
        else:
            v = safe_id(value)
            if not v:
                raise InvalidIdentifiers(f"invalid value for '{key}'")
            out[key] = v
    if not out:
        raise InvalidIdentifiers("no usable identifiers supplied")
    return out


class AddRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    identifiers: dict[str, str]


class PersonalUpdate(BaseModel):
    """Only user-owned fields; anything else is rejected, so metadata can't be edited through this."""

    model_config = ConfigDict(extra="forbid")
    personal_rating: Optional[float] = None
    notes: Optional[str] = None
    finished_on: Optional[str] = None

    @field_validator("personal_rating")
    @classmethod
    def _rating(cls, v):
        if v is None:
            return v
        if not (0.5 <= v <= 5) or round(v * 2) != v * 2:
            raise ValueError("personal_rating must be between 0.5 and 5 in steps of 0.5")
        return float(v)

    @field_validator("notes")
    @classmethod
    def _notes(cls, v):
        if v is None:
            return v
        v = v.strip()
        if len(v) > 10_000:
            raise ValueError("notes are limited to 10,000 characters")
        return v or None

    @field_validator("finished_on")
    @classmethod
    def _finished(cls, v):
        if v in (None, ""):
            return None
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            raise ValueError("finished_on must be YYYY-MM-DD")
        try:
            d = date.fromisoformat(v)
        except ValueError as exc:
            raise ValueError("finished_on is not a valid date") from exc
        if d > date.today() + timedelta(days=1):
            raise ValueError("finished_on cannot be in the future")
        return v


# ------------------------------------------------------------------------------------------------
class CatalogService:
    kind: Kind

    def __init__(
        self,
        kind: Kind,
        model: Type[Document],
        claim_store: Optional[ClaimStore] = None
    ):
        self.kind = kind
        self.model = model
        self.claims = claim_store or MongoClaimStore()

    # -- helpers ---------------------------------------------------------------------------------
    @property
    def _prefix(self) -> str:
        return f"{self.kind}:"

    
    def _keys_for(self, rec: MergedRecord | Document) -> list[str]:
        def g(f: str, default: Any = None) -> Any:
            value = getattr(rec, f, None)
            return default if value is None else value

        return [
            self._prefix + k
            for k in identity_keys(
                self.kind,
                isbn_13=g("isbn_13"),
                isbn_10=g("isbn_10"),
                other_isbns=g("other_isbns", []),
                asin=g("asin"),
                identifiers=g("identifiers", {}),
                level=g("level", "edition"),
                title=g("title"),
                subtitle=g("subtitle"),
                authors=g("authors", []),
                narrators=g("narrators", []),
                published_date=g("published_date"),
                language=g("language"),
                recording_type=g("recording_type"),
            )
        ]


    async def _exists(self, doc_id: str) -> bool:
        return await self.model.get(PydanticObjectId(doc_id)) is not None

    def _identifier_keys_from_request(self, ids: dict[str, str]) -> list[str]:
        keys = []
        if ids.get("isbn_13"):
            keys.append(f"{self._prefix}isbn13:{ids['isbn_13']}")
        if ids.get("asin"):
            keys.append(f"{self._prefix}asin:{ids['asin']}")
        for k in ("google_books", "open_library_edition", "hardcover_edition", "itunes"):
            if ids.get(k):
                keys.append(f"{self._prefix}{k}:{ids[k]}")
        return keys

    async def _already(self, keys: list[str]) -> Optional[str]:
        for key in keys:
            row = await self.claims.get(key)
            if row and await self._exists(row.doc_id):
                return row.doc_id
        return None

    @staticmethod
    def _stored_view(doc: Document, kind: Kind) -> Stored:
        out: Stored = {}
        for f in metadata_fields(kind):
            v = getattr(doc, f, None)
            if v in (None, "", [], {}):
                continue
            if f == "series":
                v = v.model_dump() if hasattr(v, "model_dump") else v
            elif f == "contributors":
                v = [c.model_dump() if hasattr(c, "model_dump") else c for c in v]
            out[f] = (v, doc.field_sources.get(f, "stored"))
        return out

    @staticmethod
    def _identifiers_of(doc: Document) -> dict[str, str]:
        ids = {k: v for k, v in (doc.identifiers or {}).items() if v}
        for k in ("isbn_13", "isbn_10", "asin"):
            if getattr(doc, k, None):
                ids[k] = getattr(doc, k)
        return ids

    # -- add -------------------------------------------------------------------------------------
    async def add(self, agg: MetadataAggregator, raw_identifiers: dict[str, str]) -> tuple[Document, dict]:
        ids = validate_identifiers(self.kind, raw_identifiers)

        existing = await self._already(self._identifier_keys_from_request(ids))
        if existing:  # cheap early exit, before any provider traffic
            raise AlreadyInLibrary("This item is already in your library", existing_id=existing)

        res: AggregateResult = await agg.resolve(self.kind, ids)
        if not res.results or not res.results[0].title:
            failed = [n for n, s in res.providers.items() if s.get("status") in ("error", "timeout")]
            if failed and not any(s.get("status") == "ok" for s in res.providers.values()):
                raise ProvidersUnavailable("Metadata providers are unavailable right now, please try again", providers=res.providers)
            raise NotResolvable("No metadata provider could find this item", providers=res.providers)
        merged = res.results[0]

        doc_id = ObjectId()
        fields = merged.model_dump(include=set(metadata_fields(self.kind)) | {"level"})
        doc = self.model(
            id=doc_id, **fields,
            sources=merged.sources, field_sources=merged.field_sources,
            metadata_refreshed_at=utcnow(),
        )

        try:
            await claim_keys(self.claims, self._keys_for(merged), str(doc_id), doc_exists=self._exists, now=utcnow)
        except AlreadyClaimed as exc:
            raise AlreadyInLibrary(
                "This item is already in your library" if not exc.in_progress else "This item is being added right now",
                existing_id=exc.existing_id, in_progress=exc.in_progress,
            ) from exc

        try:
            await doc.insert()
        except BaseException:
            await self.claims.delete_for_doc(str(doc_id))
            raise
        return doc, res.providers

    # -- refresh ---------------------------------------------------------------------------------
    async def refresh(self, agg: MetadataAggregator, doc: Document) -> dict:
        """Re-fetch metadata and fold it into the stored item.

        Safe by construction:
          * stored values go back into the merge as candidates (with their original provenance), so a
            lower-priority or empty answer can't replace them;
          * only metadata fields are written (`$set`), personal fields are never read or written, so a
            concurrent edit of notes/rating can't be lost;
          * if every provider fails the item is left exactly as it was.
        """
        res = await agg.resolve(self.kind, self._identifiers_of(doc), stored=self._stored_view(doc, self.kind))
        if not res.results:
            statuses = res.providers
            if any(s.get("status") in ("error", "timeout") for s in statuses.values()) and not any(
                    s.get("status") == "ok" for s in statuses.values()):
                raise ProvidersUnavailable("Metadata providers are unavailable right now, nothing was changed", providers=statuses)
            return {"item": doc, "changed_fields": [], "providers": statuses, "warnings": ["no provider returned data"]}

        merged = res.results[0]
        updates: dict[str, Any] = {}
        for f in metadata_fields(self.kind):
            new = getattr(merged, f, None)
            old = getattr(doc, f, None)
            if new in (None, "", [], {}) and old not in (None, "", [], {}):
                continue  # never replace useful data with nothing
            new_cmp = new.model_dump() if isinstance(new, BaseModel) else new
            old_cmp = old.model_dump() if isinstance(old, BaseModel) else old
            if f == "contributors":
                new_cmp = [
                    c.model_dump() if hasattr(c, "model_dump") else c
                    for c in (new if isinstance(new, (list, tuple)) else [])
                ]
                old_cmp = [
                    c.model_dump() if hasattr(c, "model_dump") else c
                    for c in (old if isinstance(old, (list, tuple)) else [])
                ]

            if new_cmp != old_cmp:
                updates[f] = new_cmp if f in ("series", "contributors") else new

        # provenance: keep what we knew, overlay what this merge decided
        sources = {(s.provider, s.level, s.provider_id): s for s in doc.sources}
        for s in merged.sources:
            sources[(s.provider, s.level, s.provider_id)] = s
        field_sources = {**doc.field_sources, **merged.field_sources}

        warnings: list[str] = []
        _, conflicts = await claim_keys(
            self.claims, self._keys_for(merged), str(doc.id), doc_exists=self._exists, now=utcnow, tolerate_conflicts=True)
        if conflicts:
            warnings.append("some identifiers of this item are already used by another item in your library")

        now = utcnow()
        await doc.set({
            **updates,
            "sources": [s.model_dump() for s in sources.values()],
            "field_sources": field_sources,
            "metadata_refreshed_at": now,
            **({"updated_at": now} if updates else {}),
        })
        return {"item": doc, "changed_fields": sorted(updates), "providers": res.providers, "warnings": warnings}

    # -- personal data / delete --------------------------------------------------------------------
    async def update_personal(self, doc: Document, patch: PersonalUpdate) -> Document:
        provided = patch.model_fields_set & set(PERSONAL_FIELDS)
        if not provided:
            raise InvalidRequest("nothing to update")
        await doc.set({**{f: getattr(patch, f) for f in provided}, "updated_at": utcnow()})
        return doc

    async def delete(self, doc: Document) -> None:
        await doc.delete()  # document first: a leftover claim is an orphan that self-heals, the reverse is not
        await self.claims.delete_for_doc(str(doc.id))
