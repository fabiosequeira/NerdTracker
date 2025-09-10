from fastapi import APIRouter, HTTPException
from app.models.movie import Movie

router = APIRouter()

@router.post("/", response_model=Movie)
async def add_movie(movie: Movie):
    await movie.insert()
    return movie

@router.get("/", response_model=list[Movie])
async def list_movies():
    return await Movie.find_all().to_list()

@router.get("/{movie_id}", response_model=Movie)
async def get_movie(movie_id: str):
    movie = await Movie.get(movie_id)
    if not movie:
        raise HTTPException(404, "Movie not found")
    return movie
