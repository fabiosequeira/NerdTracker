from fastapi import Depends, HTTPException

from app.models.audiobook import Audiobook
from app.routes.catalog_router import build_router
from app.services.metadata.aggregator import MetadataAggregator, to_search_item
from app.services.metadata.normalize import clean_asin
from app.services.metadata.registry import get_aggregator

router, service = build_router(prefix="/audiobooks", tag="audiobooks", kind="audiobook", model=Audiobook, label="Audiobook")


@router.get("/asin/{asin}")
async def lookup_asin(asin: str, agg: MetadataAggregator = Depends(get_aggregator)):
    """Look up a recording by its Audible ASIN (enriched via Audnexus / Hardcover)."""
    a = clean_asin(asin)
    if not a:
        raise HTTPException(status_code=422, detail="Not a valid ASIN")
    res = await agg.resolve("audiobook", {"asin": a})
    if not res.results:
        raise HTTPException(status_code=404, detail="No audiobook found for this ASIN")
    return {"result": to_search_item(res.results[0]), "providers": res.providers}
