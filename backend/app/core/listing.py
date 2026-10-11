"""Lean list queries.

The home page grid only needs a handful of fields per item, but ``find_all().to_list()`` used to
ship (and re-validate with Pydantic) *everything*: every episode of every show, every screenshot
URL, long summaries... Mongo can skip those fields server-side with a projection.

The response shape is unchanged (same model, same keys); the heavy fields just come back as
their empty defaults. Pass ``full=True`` (``?full=true`` on the endpoints) for complete documents.
"""
from typing import Iterable, List, Type, TypeVar

from beanie import Document

D = TypeVar("D", bound=Document)


def _raw_collection(model: Type[Document]):
    # Beanie 2.x exposes get_pymongo_collection(); 1.x called it get_motor_collection().
    getter = getattr(model, "get_pymongo_collection", None) or getattr(model, "get_motor_collection")
    return getter()


async def list_documents(model: Type[D], heavy_fields: Iterable[str], full: bool = False) -> List[D]:
    if full:
        return await model.find_all().to_list()

    projection = {field: 0 for field in heavy_fields}
    raw_docs = await _raw_collection(model).find({}, projection).to_list(length=None)
    return [model.model_validate(doc) for doc in raw_docs]
