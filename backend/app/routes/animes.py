from fastapi import APIRouter, HTTPException
from app.models.anime import Anime

router = APIRouter()

@router.post("/", response_model=Anime)
async def add_anime(anime: Anime):
    await anime.insert()
    return anime

@router.get("/", response_model=list[Anime])
async def list_animes():
    return await Anime.find_all().to_list()

@router.get("/{anime_id}", response_model=Anime)
async def get_anime(anime_id: str):
    anime = await Anime.get(anime_id)
    if not anime:
        raise HTTPException(404, "Anime not found")
    return anime
