from fastapi import APIRouter, HTTPException
from beanie import PydanticObjectId
from app.models.anime import Anime
from app.core.http import get_client
from app.core.listing import list_documents
from app.utils.tmdb_episodes import fetch_season_episodes
import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter(prefix="/animes", tags=["animes"])
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY:
    raise ValueError("TMDB_API_KEY is not set in environment")


# Fields the grid doesn't need (episodes_list alone can be hundreds of rows per show);
# omitted from the list by default. Use ?full=true to get complete documents.
LIST_EXCLUDE = ("episodes_list", "overview", "backdrop", "videos", "images")


@router.get("/", response_model=list[Anime])
async def list_animes(full: bool = False):
    return await list_documents(Anime, LIST_EXCLUDE, full)


@router.post("/", response_model=Anime)
async def add_anime(tmdb_id: int):
    
    if not TMDB_API_KEY:
        raise RuntimeError("TMDB_API_KEY environment variable is not configured")
    
    #check for existing anime
    existing = await Anime.find_one(Anime.tmdb_id == tmdb_id)
    if existing:
        raise HTTPException(status_code=400, detail="Anime already exists")
    
    
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "append_to_response": "videos,images,external_ids",
        "include_image_language": "en,null"
    }

    client = get_client()
    resp = await client.get(url, params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="TMDb request failed")
    details = resp.json()
    episodes_list = await fetch_season_episodes(
        client,
        TMDB_API_KEY,
        tmdb_id,
        [season.get("season_number") for season in details.get("seasons", [])],
    )

    payload = {
        "tmdb_id": details.get("id"),
        "title": details.get("name"),
        "year": int(details["first_air_date"][:4]) if details.get("first_air_date") else None,
        "poster": f"https://image.tmdb.org/t/p/w780{details['poster_path']}" if details.get("poster_path") else None,
        "backdrop": f"https://image.tmdb.org/t/p/original{details['backdrop_path']}" if details.get("backdrop_path") else None,
        "genres": [g["name"] for g in details.get("genres", [])],
        "rating": round(details.get("vote_average", 0), 1) if details.get("vote_average") is not None else None,
        "rating_count": details.get("vote_count"),
        "overview": details.get("overview"),
        "seasons": details.get("number_of_seasons"),
        "episodes": details.get("number_of_episodes"),
        "episodes_list": episodes_list,
        "videos": [
            {"name": v["name"], "key": v["key"], "site": v["site"], "type": v["type"]}
            for v in details.get("videos", {}).get("results", [])[:6]
        ],
        "images": [
            f"https://image.tmdb.org/t/p/original{i['file_path']}"
            for i in details.get("images", {}).get("backdrops", [])[:12]
        ],
        "popularity": details.get("popularity"),
        "adult": details.get("adult"),
        "imdb_id": details.get("external_ids", {}).get("imdb_id"),
        "in_production": details.get("in_production", False),
    }

    anime = Anime(**payload)
    await anime.insert()
    return anime


@router.delete("/{anime_id}")
async def delete_anime(anime_id: PydanticObjectId):
    anime = await Anime.get(anime_id)
    if not anime:
        raise HTTPException(status_code=404, detail="Anime not found")
    await anime.delete()
    return {"message": f"Anime {anime.title} deleted ✅"}


@router.get("/{anime_id}", response_model=Anime)
async def get_anime(anime_id: PydanticObjectId):
    anime = await Anime.get(anime_id)
    if not anime:
        raise HTTPException(status_code=404, detail="Anime not found")
    return anime
