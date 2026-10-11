import asyncio
import os
from fastapi import APIRouter, Query
from dotenv import load_dotenv
from app.core.cache import TTLCache
from app.core.http import get_client
load_dotenv()

router = APIRouter(prefix="/tmdb", tags=["tmdb"])

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY:
    raise ValueError("TMDB_API_KEY is not set in environment")

TMDB_BASE = "https://api.themoviedb.org/3"
# Search results are only rendered as ~40px thumbnails, so don't ship `original`-size posters.
SEARCH_POSTER_BASE = "https://image.tmdb.org/t/p/w185"

_search_cache = TTLCache(ttl=300, maxsize=256)


def _key(kind: str, query: str):
    return (kind, query.strip().casefold())


async def _search_movie(query: str):
    resp = await get_client().get(
        f"{TMDB_BASE}/search/movie",
        params={"api_key": TMDB_API_KEY, "query": query, "language": "en-US"},
    )
    data = resp.json()

    return [
        {
            "id": m["id"],
            "title": m.get("title"),
            "year": m.get("release_date", "")[:4] if m.get("release_date") else None,
            "poster": f"{SEARCH_POSTER_BASE}{m['poster_path']}" if m.get("poster_path") else None,
            "genres": m.get("genre_ids", []),
            "rating": m.get("vote_average", None),
            "popularity": m.get("popularity", 0),
        }
        for m in data.get("results", [])
    ]


async def _search_show(query: str):
    client = get_client()
    resp = await client.get(
        f"{TMDB_BASE}/search/tv",
        params={"api_key": TMDB_API_KEY, "query": query, "language": "en-US"},
    )
    data = resp.json()

    candidates = [m for m in data.get("results", []) if "JP" not in (m.get("origin_country") or [])]

    # The search endpoint doesn't return genre names / season counts, so each hit needs a detail
    # call. These used to run one after another (up to ~20 sequential round-trips); run them together.
    sem = asyncio.Semaphore(10)

    async def fetch_details(m: dict) -> dict:
        async with sem:
            try:
                r = await client.get(
                    f"{TMDB_BASE}/tv/{m['id']}",
                    params={"api_key": TMDB_API_KEY, "language": "en-US"},
                )
                return r.json()
            except Exception:
                return {}

    details_list = await asyncio.gather(*(fetch_details(m) for m in candidates))

    return [
        {
            "id": m["id"],
            "title": m.get("name"),
            "year": m.get("first_air_date", "")[:4] if m.get("first_air_date") else None,
            "poster": f"{SEARCH_POSTER_BASE}{m['poster_path']}" if m.get("poster_path") else None,
            "genres": [g["name"] for g in details.get("genres", [])],
            "rating": details.get("vote_average"),
            "seasons": details.get("number_of_seasons"),
            "episodes": details.get("number_of_episodes"),
            "popularity": m.get("popularity", 0),
        }
        for m, details in zip(candidates, details_list)
    ]


async def _search_anime(query: str):
    resp = await get_client().get(
        f"{TMDB_BASE}/search/tv",
        params={"api_key": TMDB_API_KEY, "query": query, "language": "en-US"},
    )
    data = resp.json()

    return [
        {
            "id": m["id"],
            "title": m.get("name"),
            "year": m.get("first_air_date", "")[:4] if m.get("first_air_date") else None,
            "poster": f"{SEARCH_POSTER_BASE}{m['poster_path']}" if m.get("poster_path") else None,
            "genres": m.get("genre_ids", []),
            "rating": m.get("vote_average", None),
            "popularity": m.get("popularity", 0),
        }
        for m in data.get("results", [])
        if "JP" in (m.get("origin_country") or [])
    ]


@router.get("/search/movie")
async def search_movie(query: str = Query(..., min_length=2)):
    return await _search_cache.get_or_load(_key("movie", query), lambda: _search_movie(query))


@router.get("/search/tv")
async def search_show(query: str = Query(..., min_length=2)):
    return await _search_cache.get_or_load(_key("tv", query), lambda: _search_show(query))


@router.get("/search/anime")
async def search_anime(query: str = Query(..., min_length=2)):
    return await _search_cache.get_or_load(_key("anime", query), lambda: _search_anime(query))
