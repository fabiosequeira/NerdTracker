"""Router factory shared by /books and /audiobooks (identical API, different kind / model)."""
from __future__ import annotations

from typing import Type

from beanie import Document, PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.listing import list_documents
from app.services.catalog import AddRequest, CatalogService, PersonalUpdate
from app.services.metadata.aggregator import MetadataAggregator, to_search_item
from app.services.metadata.normalize import canonical_isbn13
from app.services.metadata.registry import get_aggregator
from app.services.metadata.schema import Kind

# Not needed by the grid: omitted from the list unless ?full=true (same convention as the other media).
LIST_EXCLUDE = ("description", "contributors", "sources", "field_sources", "notes", "identifiers", "other_isbns")


def build_router(*, prefix: str, tag: str, kind: Kind, model: Type[Document], label: str) -> tuple[APIRouter, CatalogService]:
    router = APIRouter(prefix=prefix, tags=[tag])
    service = CatalogService(kind, model)

    async def get_or_404(item_id: PydanticObjectId) -> Document:
        doc = await model.get(item_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"{label} not found")
        return doc

    @router.get("/search")
    async def search(
        query: str = Query(..., min_length=2, max_length=200),
        limit: int = Query(10, ge=1, le=25),
        agg: MetadataAggregator = Depends(get_aggregator),
    ):
        """Merged, de-duplicated results from every configured provider.
        `providers` reports each provider's outcome; a failing provider never fails the search."""
        res = await agg.search(kind, query, limit)
        return {"results": [to_search_item(m) for m in res.results], "providers": res.providers}

    @router.get("/isbn/{isbn}")
    async def lookup_isbn(isbn: str, agg: MetadataAggregator = Depends(get_aggregator)):
        if not canonical_isbn13(isbn):
            raise HTTPException(status_code=422, detail="Not a valid ISBN-10 or ISBN-13")
        res = await agg.lookup_isbn(kind, isbn)
        if not res.results:
            raise HTTPException(status_code=404, detail=f"No {label.lower()} found for this ISBN")
        return {"result": to_search_item(res.results[0]), "providers": res.providers}

    @router.get("/", response_model=list[model])
    async def list_items(full: bool = False):
        return await list_documents(model, LIST_EXCLUDE, full)

    @router.post("/", response_model=model, status_code=201)
    async def add(body: AddRequest, agg: MetadataAggregator = Depends(get_aggregator)):
        """Add an item you have finished. Send the `identifiers` object of a search result; the server
        re-fetches and merges the metadata itself (it never trusts client-supplied metadata)."""
        doc, _providers = await service.add(agg, body.identifiers)
        return doc

    @router.get("/{item_id}", response_model=model)
    async def get_item(item_id: PydanticObjectId):
        return await get_or_404(item_id)

    @router.patch("/{item_id}", response_model=model)
    async def update_personal(item_id: PydanticObjectId, body: PersonalUpdate):
        """Edit personal data only (rating / notes / finished date). Omitted fields are untouched; an
        explicit null clears a field."""
        return await service.update_personal(await get_or_404(item_id), body)

    @router.post("/{item_id}/refresh")
    async def refresh(item_id: PydanticObjectId, agg: MetadataAggregator = Depends(get_aggregator)):
        """Re-fetch metadata from the providers. Personal data and the added date are never touched."""
        return await service.refresh(agg, await get_or_404(item_id))

    @router.delete("/{item_id}")
    async def delete_item(item_id: PydanticObjectId):
        doc = await get_or_404(item_id)
        await service.delete(doc)
        return {"message": f"{label} {doc.title} deleted ✅"}

    return router, service
