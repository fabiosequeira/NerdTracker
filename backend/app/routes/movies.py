from fastapi import APIRouter, HTTPException
from app.models.movie import Movie
import httpx

router = APIRouter(prefix="/movies", tags=["movies"])
TMDB_API_KEY = "279b31fd921c02d920708f2ecd2fae66"


@router.get("/", response_model=list[Movie])
async def list_movies():
    return await Movie.find_all().to_list()


@router.post("/", response_model=Movie)
async def add_movie(tmdb_id: int):
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    params = {"api_key": TMDB_API_KEY, "language": "en-US"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="TMDb request failed")
        details = resp.json()

    payload = {
        "title": details.get("title"),
        "year": details.get("release_date", "")[:4] if details.get("release_date") else None,
        "genres": [g["name"] for g in details.get("genres", [])],
        "rating": details.get("vote_average"),
        "poster": f"https://image.tmdb.org/t/p/original{details['poster_path']}" if details.get("poster_path") else None,
    }

    movie = Movie(**payload)
    await movie.insert()
    return movie


@router.delete("/{movie_id}")
async def delete_movie(movie_id: str):
    movie = await Movie.get(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    await movie.delete()
    return {"status": "ok", "message": f'Movie "{movie.title}" deleted'}
