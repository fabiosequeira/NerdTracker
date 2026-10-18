"""Provider configuration, read lazily from the environment.

Unlike the TMDB / IGDB modules (which raise at import time when their keys are missing), every key
here is OPTIONAL: a missing key simply disables that provider and the rest keep working.

    GOOGLE_BOOKS_API_KEY   optional. Works without it, but anonymous quota is small and shared.
    HARDCOVER_API_TOKEN    optional. Enables Hardcover (series, narrators, runtime, ASIN).
    OPENLIBRARY_CONTACT    optional. E-mail/URL appended to the User-Agent (Open Library asks for one).
    AUDNEXUS_REGION        optional, default "us". Audible region used for ASIN lookups.
    ITUNES_COUNTRY         optional, default "US". Apple storefront used for audiobook search.
    METADATA_PROVIDERS_DISABLED   optional, comma separated provider names to switch off,
                                  e.g. "google_books,itunes".
    METADATA_PROVIDER_TIMEOUT     optional, seconds per provider call (default 7).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class MetadataSettings:
    google_books_api_key: str | None = None
    hardcover_token: str | None = None
    openlibrary_contact: str | None = None
    audnexus_region: str = "us"
    itunes_country: str = "US"
    disabled: frozenset[str] = field(default_factory=frozenset)
    timeout: float = 7.0

    @property
    def user_agent(self) -> str:
        ua = "NerdTracker/1.0 (personal media vault)"
        return f"{ua} {self.openlibrary_contact}" if self.openlibrary_contact else ua


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def get_settings() -> MetadataSettings:
    """Re-read on every call so tests (and `docker compose up -d` env changes) take effect."""
    token = _clean(os.getenv("HARDCOVER_API_TOKEN"))
    if token and token.lower().startswith("bearer "):
        token = token[7:].strip()

    try:
        timeout = float(os.getenv("METADATA_PROVIDER_TIMEOUT", "7"))
    except ValueError:
        timeout = 7.0

    return MetadataSettings(
        google_books_api_key=_clean(os.getenv("GOOGLE_BOOKS_API_KEY")),
        hardcover_token=token,
        openlibrary_contact=_clean(os.getenv("OPENLIBRARY_CONTACT")),
        audnexus_region=(_clean(os.getenv("AUDNEXUS_REGION")) or "us").lower(),
        itunes_country=(_clean(os.getenv("ITUNES_COUNTRY")) or "US").upper(),
        disabled=frozenset(
            p.strip().lower() for p in os.getenv("METADATA_PROVIDERS_DISABLED", "").split(",") if p.strip()
        ),
        timeout=max(1.0, min(timeout, 30.0)),
    )
