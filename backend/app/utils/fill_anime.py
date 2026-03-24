# backend/app/utils/fill_anime.py
from app.models.anime import Anime
from app.routes.animes import TMDB_API_KEY
import httpx

async def fetch_episodes(tmdb_id: int):
    episodes_list = []
    async with httpx.AsyncClient() as client:
        url = f"https://api.themoviedb.org/3/tv/{tmdb_id}"
        params = {"api_key": TMDB_API_KEY, "language": "en-US"}
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return []
        details = resp.json()
        for season in details.get("seasons", []):
            season_number = season.get("season_number")
            if season_number == 0:
                continue
            season_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season_number}"
            season_resp = await client.get(season_url, params={"api_key": TMDB_API_KEY, "language": "en-US"})
            if season_resp.status_code != 200:
                continue
            season_data = season_resp.json()
            for ep in season_data.get("episodes", []):
                episodes_list.append({
                    "season": season_number,
                    "episode": ep.get("episode_number"),
                    "title": ep.get("name"),
                    "overview": ep.get("overview"),
                    "air_date": ep.get("air_date"),
                    "still": f"https://image.tmdb.org/t/p/w500{ep['still_path']}" if ep.get("still_path") else None
                })
    return episodes_list

async def fill_animes():
    animes = await Anime.find_all().to_list()
    for anime in animes:
        if not anime.episodes_list:
            print(f"Fetching episodes for {anime.title}...")
            try:
                if anime.tmdb_id is not None:
                    anime.episodes_list = await fetch_episodes(anime.tmdb_id)
                else:
                    print(f"Skipping {anime.title}: tmdb_id is None")
            except Exception as e:
                print(f"Failed to fetch episodes for {anime.title}: {e}")
            
            await anime.save()
            print(f"Saved {len(anime.episodes_list or [])} episodes for {anime.title}")