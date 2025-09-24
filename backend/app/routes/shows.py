from fastapi import APIRouter, HTTPException
from beanie import PydanticObjectId
from app.models.show import Show
import httpx
import os

router = APIRouter(prefix="/shows", tags=["shows"])
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "279b31fd921c02d920708f2ecd2fae66")


@router.get("/", response_model=list[Show])
async def list_shows():
    return await Show.find_all().to_list()


@router.post("/", response_model=Show)
async def add_show(tmdb_id: int):
    
    #chek for existing show
    existing = await Show.find_one(Show.tmdb_id == tmdb_id)
    if existing:
        raise HTTPException(status_code=400, detail="Show already exists")
    
    
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
            for v in details.get("videos", {}).get("results", [])[:6]
        ],
        "images": [
            f"https://image.tmdb.org/t/p/original{i['file_path']}"
            for i in details.get("images", {}).get("backdrops", [])[:12]
        ],
        "popularity": details.get("popularity"),
        "adult": details.get("adult"),
        "imdb_id": details.get("external_ids", {}).get("imdb_id"),
    }

    show = Show(**payload)
    await show.insert()
    return show


@router.delete("/{show_id}")
async def delete_show(show_id: PydanticObjectId):
    show = await Show.get(show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    await show.delete()
    return {"message": f"Show {show.title} deleted ✅"}


@router.get("/{show_id}", response_model=Show)
async def get_show(show_id: PydanticObjectId):
    show = await Show.get(show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    return show
