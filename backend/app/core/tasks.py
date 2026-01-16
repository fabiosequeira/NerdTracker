import asyncio
import httpx
import os
from datetime import datetime

from app.models.show import Show
from app.models.anime import Anime

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY:
    raise ValueError("TMDB_API_KEY is not set in environment")
TMDB_BASE = "https://api.themoviedb.org/3"


async def sync_show_with_tmdb(show: Show):
    """Check if a show has changes and update it if needed."""
    async with httpx.AsyncClient() as client:
        # 1. Check for changes
        url = f"{TMDB_BASE}/tv/{show.tmdb_id}/changes"
        resp = await client.get(url, params={"api_key": TMDB_API_KEY})
        resp.raise_for_status()
        changes = resp.json().get("changes", [])

        if not changes:
            return False  # no update needed

        # 2. Fetch full details
        details_url = f"{TMDB_BASE}/tv/{show.tmdb_id}"
        details = (await client.get(details_url, params={"api_key": TMDB_API_KEY})).json()

        show.seasons = details.get("number_of_seasons", show.seasons)
        show.episodes = details.get("number_of_episodes", show.episodes)
        show.in_production = details.get("in_production", False)

        await show.save()
        print(f"✅ Updated show {show.title} ({show.tmdb_id})")
        return True


async def sync_anime_with_tmdb(anime: Anime):
    """Check if an anime has changes and update it if needed."""
    async with httpx.AsyncClient() as client:
        # 1. Check for changes
        url = f"{TMDB_BASE}/tv/{anime.tmdb_id}/changes"
        resp = await client.get(url, params={"api_key": TMDB_API_KEY})
        resp.raise_for_status()
        changes = resp.json().get("changes", [])

        if not changes:
            return False  # no update needed

        # 2. Fetch full details
        details_url = f"{TMDB_BASE}/tv/{anime.tmdb_id}"
        details = (await client.get(details_url, params={"api_key": TMDB_API_KEY})).json()

        anime.seasons = details.get("number_of_seasons", anime.seasons)
        anime.episodes = details.get("number_of_episodes", anime.episodes)
        anime.in_production = details.get("in_production", False)

        await anime.save()
        print(f"✅ Updated anime {anime.title} ({anime.tmdb_id})")
        return True


async def weekly_tmdb_sync():
    """Run a weekly sync of all shows and animes in the DB."""
    while True:
        print("🔄 Starting TMDB weekly sync...")

        # Sync Shows
        shows = await Show.find({"in_production": True}).to_list()
        updated_shows = 0
        for show in shows:
            changed = await sync_show_with_tmdb(show)
            if changed:
                updated_shows += 1
        print(f"📺 Shows sync complete: {updated_shows}/{len(shows)} active shows updated.")

        # Sync Animes
        animes = await Anime.find({"in_production": True}).to_list()
        updated_animes = 0
        for anime in animes:
            changed = await sync_anime_with_tmdb(anime)
            if changed:
                updated_animes += 1
        print(f"🌸 Animes sync complete: {updated_animes}/{len(animes)} active animes updated.")

        # Sleep 1 week (in seconds)
        await asyncio.sleep(7 * 24 * 60 * 60)
