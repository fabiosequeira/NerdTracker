# backend/app/utils/fill_shows.py
from app.models.show import Show
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

async def fill_shows():
    shows = await Show.find_all().to_list()

    for show in shows:
        needs_update = False

        # Case 1: no episodes at all
        if not show.episodes_list:
            needs_update = True

        # Case 2: episodes exist but no season 0
        else:
            has_specials = any(ep.season == 0 for ep in show.episodes_list)
            if not has_specials:
                needs_update = True

        if not needs_update:
            continue

        print(f"Fetching episodes for {show.title}...")

        try:
            if show.tmdb_id is not None:
                show.episodes_list = await fetch_episodes(show.tmdb_id)
            else:
                print(f"Skipping {show.title}: tmdb_id is None")
                continue

        except Exception as e:
            print(f"Failed to fetch episodes for {show.title}: {e}")
            continue

        await show.save()
        print(f"Saved {len(show.episodes_list or [])} episodes for {show.title}")
