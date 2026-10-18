
from fastapi import APIRouter, HTTPException
from beanie import PydanticObjectId
from app.models.show import Show
from app.core.http import get_client
from app.core.listing import list_documents
from app.utils.tmdb_episodes import fetch_season_episodes
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/shows", tags=["shows"])

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY:
    raise ValueError("TMDB_API_KEY is not set in environment")


# Fields that the catalog grid doesn't need.
# Exclude heavy metadata by default for faster loading.
# Use ?full=true to retrieve complete documents.
LIST_EXCLUDE = (
    "episodes_list",
    "overview",
    "backdrop",
    "videos",
    "images",
)


@router.get("/", response_model=list[Show])
async def list_shows(full: bool = False):
    return await list_documents(Show, LIST_EXCLUDE, full)


@router.post("/", response_model=Show)
async def add_show(tmdb_id: int):
    if not TMDB_API_KEY:
        raise RuntimeError("TMDB_API_KEY environment variable is not configured")
    # Prevent duplicate shows.
    existing = await Show.find_one(Show.tmdb_id == tmdb_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Show already exists",
        )

    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "append_to_response": "videos,images,external_ids",
        "include_image_language": "en,null",
    }

    # Reuse the application's shared HTTP client.
    client = get_client()
    resp = await client.get(url, params=params)

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail="TMDb request failed",
        )

    details = resp.json()

    # Fetch episode metadata using the shared optimized helper.
    # Includes specials (season 0), as in the original implementation.
    season_numbers = [
        season.get("season_number")
        for season in details.get("seasons", [])
        if season.get("season_number") is not None
    ]

    episodes_list = await fetch_season_episodes(
        client,
        TMDB_API_KEY,
        tmdb_id,
        season_numbers,
    )

    payload = {
        "tmdb_id": details.get("id"),
        "title": details.get("name"),
        "year": (
            int(details["first_air_date"][:4])
            if details.get("first_air_date")
            else None
        ),
        "poster": (
            f"https://image.tmdb.org/t/p/w780{details['poster_path']}"
            if details.get("poster_path")
            else None
        ),
        "backdrop": (
            f"https://image.tmdb.org/t/p/original{details['backdrop_path']}"
            if details.get("backdrop_path")
            else None
        ),
        "genres": [
            genre["name"]
            for genre in details.get("genres", [])
        ],
        "rating": (
            round(details.get("vote_average", 0), 1)
            if details.get("vote_average") is not None
            else None
        ),
        "rating_count": details.get("vote_count"),
        "overview": details.get("overview"),
        "seasons": details.get("number_of_seasons"),
        "episodes": details.get("number_of_episodes"),
        "episodes_list": episodes_list,
        "videos": [
            {
                "name": video["name"],
                "key": video["key"],
                "site": video["site"],
                "type": video["type"],
            }
            for video in details.get("videos", {}).get("results", [])[:6]
        ],
        "images": [
            f"https://image.tmdb.org/t/p/original{image['file_path']}"
            for image in details.get("images", {}).get("backdrops", [])[:12]
        ],
        "popularity": details.get("popularity"),
        "adult": details.get("adult"),
        "imdb_id": details.get("external_ids", {}).get("imdb_id"),
        "in_production": details.get("in_production", False),
    }

    show = Show(**payload)
    await show.insert()

    return show


@router.delete("/{show_id}")
async def delete_show(show_id: PydanticObjectId):
    show = await Show.get(show_id)

    if not show:
        raise HTTPException(
            status_code=404,
            detail="Show not found",
        )

    await show.delete()

    return {"message": f"Show {show.title} deleted ✅"}


@router.get("/{show_id}", response_model=Show)
async def get_show(show_id: PydanticObjectId):
    show = await Show.get(show_id)

    if not show:
        raise HTTPException(
            status_code=404,
            detail="Show not found",
        )

    return show
