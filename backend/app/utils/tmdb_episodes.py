"""Fetch a show's episode list from TMDB, one request per season, *in parallel*.

Previously each season was requested one after another, so adding a 15-season show meant
~15 sequential round-trips. Results keep the original season order.
"""
import asyncio
from typing import Iterable, Optional

import httpx

TMDB_BASE = "https://api.themoviedb.org/3"


async def fetch_season_episodes(
    client: httpx.AsyncClient,
    api_key: str,
    tmdb_id: int,
    season_numbers: Iterable[Optional[int]],
    *,
    skip_specials: bool = False,
    concurrency: int = 6,
) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)

    async def one(season_number: Optional[int]) -> list[dict]:
        async with sem:
            resp = await client.get(
                f"{TMDB_BASE}/tv/{tmdb_id}/season/{season_number}",
                params={"api_key": api_key, "language": "en-US"},
            )
        if resp.status_code != 200:
            return []

        episodes = []
        for ep in resp.json().get("episodes", []):
            if ep.get("episode_number") is None:
                continue
            episodes.append({
                "season": season_number,
                "episode": ep.get("episode_number"),
                "title": ep.get("name"),
                "overview": ep.get("overview"),
                "air_date": ep.get("air_date"),
                "still": f"https://image.tmdb.org/t/p/w500{ep['still_path']}" if ep.get("still_path") else None,
            })
        return episodes

    numbers = [n for n in season_numbers if not (skip_specials and n == 0)]
    chunks = await asyncio.gather(*(one(n) for n in numbers))
    return [ep for chunk in chunks for ep in chunk]
