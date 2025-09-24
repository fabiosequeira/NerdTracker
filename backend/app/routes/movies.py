from fastapi import APIRouter, HTTPException
from beanie import PydanticObjectId
from app.models.movie import Movie
import httpx
import os

router = APIRouter(prefix="/movies", tags=["movies"])
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "279b31fd921c02d920708f2ecd2fae66")


@router.get("/", response_model=list[Movie])
async def list_movies():
    return await Movie.find_all().to_list()


@router.post("/", response_model=Movie)
async def add_movie(tmdb_id: int):
    
    #chek for existing movie
    existing = await Movie.find_one(Movie.tmdb_id == tmdb_id)
    if existing:
        raise HTTPException(status_code=400, detail="Movie already exists")
    
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "append_to_response": "videos,images",
        "include_image_language": "en,null"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="TMDb request failed")
        details = resp.json()

    payload = {
        "title": details.get("title"),
        "year": int(details["release_date"][:4]) if details.get("release_date") else None,
        "genres": [g["name"] for g in details.get("genres", [])],
        "rating": round(details.get("vote_average", 0), 1) if details.get("vote_average") is not None else None,
        "rating_count": details.get("vote_count"),
        "overview": details.get("overview"),
        "runtime": details.get("runtime"),
        "backdrop": f"https://image.tmdb.org/t/p/original{details['backdrop_path']}" if details.get("backdrop_path") else None,
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
        "imdb_id": details.get("imdb_id"),
        "tmdb_id": details.get("id"),
        "poster": f"https://image.tmdb.org/t/p/w780{details['poster_path']}" if details.get("poster_path") else None
    }

    movie = Movie(**payload)
    await movie.insert()
    return movie


@router.delete("/{movie_id}")
async def delete_movie(movie_id: PydanticObjectId):
    movie = await Movie.get(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    await movie.delete()
    return {"message": f"Movie {movie.title} deleted ✅"}


@router.get("/{movie_id}", response_model=Movie)
async def get_movie(movie_id: PydanticObjectId):
    movie = await Movie.get(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie
