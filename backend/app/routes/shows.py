from fastapi import APIRouter, HTTPException
from app.models.show import Show
import httpx

router = APIRouter(prefix="/shows", tags=["shows"])
TMDB_API_KEY = "279b31fd921c02d920708f2ecd2fae66"

@router.get("/", response_model=list[Show])
async def list_shows():
    return await Show.find_all().to_list()


@router.post("/", response_model=Show)
async def add_show(tmdb_id: int):
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}"
    params = {"api_key": TMDB_API_KEY, "language": "en-US"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="TMDb request failed")
        details = resp.json()

    payload = {
        "tmdb_id": details["id"],
        "title": details.get("name"),
        "year": details.get("first_air_date", "")[:4] if details.get("first_air_date") else None,
        "poster": f"https://image.tmdb.org/t/p/original{details['poster_path']}" if details.get("poster_path") else None,
        "genres": [g["name"] for g in details.get("genres", [])],
        "rating": round(details.get("vote_average", 0), 1) if details.get("vote_average") is not None else None,
        "seasons": details.get("number_of_seasons"),
        "episodes": details.get("number_of_episodes"),
    }

    show = Show(**payload)
    await show.insert()
    return show
