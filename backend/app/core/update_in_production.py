# app/core/update_in_production.py

import asyncio
import httpx
import os

from app.db import init_db
from app.models.show import Show
from app.models.anime import Anime

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "279b31fd921c02d920708f2ecd2fae66")
TMDB_BASE = "https://api.themoviedb.org/3"


async def update_in_production_show(show: Show):
    async with httpx.AsyncClient() as client:
        url = f"{TMDB_BASE}/tv/{show.tmdb_id}"
        resp = await client.get(url, params={"api_key": TMDB_API_KEY})
        resp.raise_for_status()
        details = resp.json()
        show.in_production = details.get("in_production", False)
        await show.save()
        print(f"✅ Updated show {show.title} ({show.tmdb_id})")


async def update_in_production_anime(anime: Anime):
    async with httpx.AsyncClient() as client:
        url = f"{TMDB_BASE}/tv/{anime.tmdb_id}"
        resp = await client.get(url, params={"api_key": TMDB_API_KEY})
        resp.raise_for_status()
        details = resp.json()
        anime.in_production = details.get("in_production", False)
        await anime.save()
        print(f"✅ Updated anime {anime.title} ({anime.tmdb_id})")


async def main():
    await init_db()

    # Update Shows
    shows = await Show.find_all().to_list()
    for show in shows:
        await update_in_production_show(show)

    # Update Animes
    animes = await Anime.find_all().to_list()
    for anime in animes:
        await update_in_production_anime(anime)

    print("🎉 All entries updated with in_production field.")


if __name__ == "__main__":
    asyncio.run(main())
