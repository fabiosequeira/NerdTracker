"""FastAPI dependency that builds the aggregator (override it in tests with fake providers)."""
from __future__ import annotations

from .aggregator import MetadataAggregator
from .providers import build_providers


def get_aggregator() -> MetadataAggregator:
    return MetadataAggregator(build_providers())
