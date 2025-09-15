from fastapi import APIRouter, HTTPException
from beanie import PydanticObjectId
from app.models.anime import Anime
import httpx
import os

router = APIRouter(prefix="/animes", tags=["animes"])
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "279b31fd921c02d920708f2ecd2fae66")


@router.get("/", response_model=list[Anime])
async def list_animes():
    return await Anime.find_all().to_list()


@router.post("/", response_model=Anime)
async def add_anime(tmdb_id: int):
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "append_to_response": "videos,images,external_ids",
        "include_image_language": "en,null"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="TMDb request failed")
        details = resp.json()

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
        "videos": [
            {"name": v["name"], "key": v["key"], "site": v["site"], "type": v["type"]}
            for v in details.get("videos", {}).get("results", [])
        ],
        "images": [
            f"https://image.tmdb.org/t/p/original{i['file_path']}"
            for i in details.get("images", {}).get("backdrops", [])
        ],
        "popularity": details.get("popularity"),
        "adult": details.get("adult"),
        "imdb_id": details.get("external_ids", {}).get("imdb_id"),
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
