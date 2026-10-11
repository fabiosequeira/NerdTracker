# backend/app/utils/fill_anime.py

from app.models.anime import Anime, Episode
from app.routes.animes import TMDB_API_KEY
from app.core.http import get_client
from app.utils.tmdb_episodes import fetch_season_episodes


async def fetch_episodes(tmdb_id: int) -> list[Episode]:
    if not TMDB_API_KEY:
        raise RuntimeError(
            "TMDB_API_KEY environment variable is not configured"
        )

    client = get_client()
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}"
    params = {"api_key": TMDB_API_KEY, "language": "en-US"}

    resp = await client.get(url, params=params)

    if resp.status_code != 200:
        return []

    details = resp.json()

    episodes = await fetch_season_episodes(
        client,
        TMDB_API_KEY,
        tmdb_id,
        [
            season.get("season_number")
            for season in details.get("seasons", [])
        ],
        skip_specials=True,
    )

    return [
        Episode.model_validate(episode)
        for episode in episodes
    ]


async def fill_animes():
    # Only load entries that still need episodes.
    animes = await Anime.find(
        {
            "$or": [
                {"episodes_list": None},
                {"episodes_list": []},
            ]
        }
    ).to_list()

    for anime in animes:
        if not anime.episodes_list:
            print(f"Fetching episodes for {anime.title}...")

            try:
                if anime.tmdb_id is not None:
                    anime.episodes_list = await fetch_episodes(
                        anime.tmdb_id
                    )
                else:
                    print(
                        f"Skipping {anime.title}: tmdb_id is None"
                    )

            except Exception as e:
                print(
                    f"Failed to fetch episodes for "
                    f"{anime.title}: {e}"
                )

            await anime.save()

            print(
                f"Saved {len(anime.episodes_list or [])} "
                f"episodes for {anime.title}"
            )