"""One shared outbound HTTP client for the whole app.

Every route used to open a brand-new ``httpx.AsyncClient`` per request, which means a fresh
TCP + TLS handshake to TMDB / IGDB / ComicVine / AniList each time (easily 100-300 ms of pure
overhead per call). A single long-lived client keeps connections alive and reuses them.
"""
from __future__ import annotations

import httpx

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(
                max_connections=50,
                max_keepalive_connections=20,
                keepalive_expiry=60.0,
            ),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
