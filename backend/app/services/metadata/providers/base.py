"""Provider interface + safe HTTP helper shared by all metadata providers."""
from __future__ import annotations

import re
from typing import Any, Optional

import httpx

from app.core.http import get_client

from ..config import MetadataSettings, get_settings
from ..schema import Kind, ProviderRecord

_SAFE_ID = re.compile(r"^[A-Za-z0-9_\-]{1,40}$")


class ProviderError(Exception):
    """A provider failed in a way that should be reported but must never break the whole request."""


class ProviderTimeout(ProviderError):
    pass


def safe_id(value: Any) -> Optional[str]:
    """Identifiers end up inside URLs: accept only boring characters."""
    s = str(value).strip() if value is not None else ""
    return s if _SAFE_ID.fullmatch(s) else None


async def http_json(
    method: str,
    url: str,
    *,
    params: Optional[dict] = None,
    json_body: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: float = 7.0,
    follow_redirects: bool = False,
    ok_404: bool = False,
) -> Any:
    """JSON request through the app's shared pooled client.

    Error text deliberately never includes the URL/params (they can contain API keys).
    """
    try:
        resp = await get_client().request(
            method, url, params=params, json=json_body, headers=headers,
            timeout=timeout, follow_redirects=follow_redirects,
        )
    except httpx.TimeoutException as exc:
        raise ProviderTimeout("request timed out") from exc
    except httpx.HTTPError as exc:
        raise ProviderError(f"network error ({type(exc).__name__})") from exc

    if resp.status_code == 404 and ok_404:
        return None
    if resp.status_code == 429:
        raise ProviderError("rate limited (HTTP 429)")
    if resp.status_code in (401, 403):
        raise ProviderError(f"not authorised (HTTP {resp.status_code}); check the API key")
    if resp.status_code >= 400:
        raise ProviderError(f"HTTP {resp.status_code}")
    try:
        return resp.json()
    except ValueError as exc:
        raise ProviderError("invalid JSON in response") from exc


class Provider:
    name: str = "provider"
    kinds: frozenset[str] = frozenset()
    # identifier keys this provider can use to fetch a specific record (isbn_13 / isbn_10 / asin included)
    id_keys: frozenset[str] = frozenset()

    def __init__(self, settings: Optional[MetadataSettings] = None):
        self.settings = settings or get_settings()

    # -- availability ---------------------------------------------------------------------------
    def disabled_reason(self) -> Optional[str]:
        """None when usable; otherwise a human-readable reason (shown in the API's provider status)."""
        if self.name in self.settings.disabled:
            return "disabled via METADATA_PROVIDERS_DISABLED"
        return None

    def supports(self, kind: Kind) -> bool:
        return kind in self.kinds

    def relevant(self, kind: Kind, identifiers: dict[str, str]) -> dict[str, str]:
        if not self.supports(kind):
            return {}
        return {k: v for k, v in identifiers.items() if k in self.id_keys and v}

    # -- operations (override) --------------------------------------------------------------------
    async def search(self, kind: Kind, query: str, limit: int) -> list[ProviderRecord]:
        return []

    async def resolve(self, kind: Kind, identifiers: dict[str, str]) -> list[ProviderRecord]:
        """Fetch specific record(s) by identifiers (only keys listed in `id_keys` are passed in)."""
        return []

    @property
    def timeout(self) -> float:
        return self.settings.timeout
