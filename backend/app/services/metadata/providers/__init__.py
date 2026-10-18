from __future__ import annotations

from typing import Optional

from ..config import MetadataSettings, get_settings
from .audnexus import AudnexusProvider
from .base import Provider, ProviderError, ProviderTimeout
from .google_books import GoogleBooksProvider
from .hardcover import HardcoverProvider
from .itunes import ITunesProvider
from .open_library import OpenLibraryProvider

ALL_PROVIDERS = (GoogleBooksProvider, OpenLibraryProvider, HardcoverProvider, ITunesProvider, AudnexusProvider)


def build_providers(settings: Optional[MetadataSettings] = None) -> list[Provider]:
    settings = settings or get_settings()
    return [cls(settings) for cls in ALL_PROVIDERS]


__all__ = ["Provider", "ProviderError", "ProviderTimeout", "build_providers", "ALL_PROVIDERS"]
