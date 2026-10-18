"""Race-free duplicate prevention.

Every stored item "claims" its identity keys (ISBN-13s, ASIN, provider edition ids ...) in a collection
with a UNIQUE index on the key. Adding an item is:

    1. claim every key (sorted order)       -> a key already owned by an existing item = duplicate
    2. insert the item document
    3. on any failure, release the claims

so two concurrent adds of the same edition can never both succeed, whatever the timing, and the check
holds across processes (the guarantee lives in the database, not in application memory).

Crash safety: a claim whose item does not exist yet is "in flight" for `grace_seconds`; after that it is an
orphan (the adder died between step 1 and 2) and is taken over instead of blocking the item forever.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Optional, Protocol, Sequence

from pymongo.errors import DuplicateKeyError


class DuplicateClaim(Exception):
    """Raised by a store when the key already exists."""


class AlreadyClaimed(Exception):
    def __init__(self, existing_id: str, in_progress: bool = False):
        super().__init__(f"already claimed by {existing_id}")
        self.existing_id = existing_id
        self.in_progress = in_progress


@dataclass
class ClaimRow:
    doc_id: str
    created_at: datetime


class ClaimStore(Protocol):
    async def insert(self, key: str, doc_id: str, created_at: datetime) -> None: ...
    async def get(self, key: str) -> Optional[ClaimRow]: ...
    async def delete(self, key: str, doc_id: str) -> bool: ...  # compare-and-delete
    async def delete_for_doc(self, doc_id: str) -> None: ...


class MongoClaimStore:
    async def insert(self, key: str, doc_id: str, created_at: datetime) -> None:
        from beanie import PydanticObjectId

        from app.models.catalog import CatalogKey

        try:
            await CatalogKey(key=key, doc_id=PydanticObjectId(doc_id), created_at=created_at).insert()
        except DuplicateKeyError as exc:
            raise DuplicateClaim(key) from exc

    async def get(self, key: str) -> Optional[ClaimRow]:
        from app.models.catalog import CatalogKey

        row = await CatalogKey.find_one(CatalogKey.key == key)
        return ClaimRow(str(row.doc_id), row.created_at) if row else None

    async def delete(self, key: str, doc_id: str) -> bool:
        from beanie import PydanticObjectId

        from app.models.catalog import CatalogKey

        res = await CatalogKey.find(CatalogKey.key == key, CatalogKey.doc_id == PydanticObjectId(doc_id)).delete()
        return bool(res and res.deleted_count)

    async def delete_for_doc(self, doc_id: str) -> None:
        from beanie import PydanticObjectId

        from app.models.catalog import CatalogKey

        await CatalogKey.find(CatalogKey.doc_id == PydanticObjectId(doc_id)).delete()


class InMemoryClaimStore:
    """Same semantics as the Mongo store; used by unit tests."""

    def __init__(self):
        self.rows: dict[str, ClaimRow] = {}

    async def insert(self, key, doc_id, created_at):
        if key in self.rows:
            raise DuplicateClaim(key)
        self.rows[key] = ClaimRow(doc_id, created_at)

    async def get(self, key):
        return self.rows.get(key)

    async def delete(self, key, doc_id):
        if key in self.rows and self.rows[key].doc_id == doc_id:
            del self.rows[key]
            return True
        return False

    async def delete_for_doc(self, doc_id):
        for k in [k for k, v in self.rows.items() if v.doc_id == doc_id]:
            del self.rows[k]


async def claim_keys(
    store: ClaimStore,
    keys: Sequence[str],
    doc_id: str,
    *,
    doc_exists: Callable[[str], Awaitable[bool]],
    now: Callable[[], datetime],
    grace_seconds: float = 30.0,
    tolerate_conflicts: bool = False,
) -> tuple[list[str], list[str]]:
    """Claim `keys` for `doc_id`. Returns (claimed, conflicting_keys).

    tolerate_conflicts=False (adding): the first conflict aborts, rolls back and raises AlreadyClaimed.
    tolerate_conflicts=True (refresh): conflicts are skipped and reported; the item keeps what it owns.
    """
    claimed: list[str] = []
    conflicts: list[str] = []
    try:
        for key in sorted(set(keys)):
            for _attempt in range(3):
                try:
                    await store.insert(key, doc_id, now())
                    claimed.append(key)
                    break
                except DuplicateClaim:
                    row = await store.get(key)
                    if row is None:  # released in the meantime: try again
                        continue
                    if row.doc_id == doc_id:
                        break  # already ours
                    if await doc_exists(row.doc_id):
                        if tolerate_conflicts:
                            conflicts.append(key)
                            break
                        raise AlreadyClaimed(row.doc_id)
                    if now() - row.created_at < timedelta(seconds=grace_seconds):
                        if tolerate_conflicts:
                            conflicts.append(key)
                            break
                        raise AlreadyClaimed(row.doc_id, in_progress=True)  # someone is adding it right now
                    await store.delete(key, row.doc_id)  # orphan from a crashed add: take it over
            else:
                raise RuntimeError("could not claim key")
    except BaseException:
        for key in claimed:  # only keys newly claimed by THIS call; anything already ours is left alone
            await store.delete(key, doc_id)
        raise
    return claimed, conflicts
