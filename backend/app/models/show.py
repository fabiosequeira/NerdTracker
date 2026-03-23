from beanie import Document
from typing import Optional, List, Dict
from pydantic import BaseModel


class Episode(BaseModel):
    season: int
    episode: int
    title: Optional[str] = None
    overview: Optional[str] = None
    air_date: Optional[str] = None
    still: Optional[str] = None
class Show(Document):
    tmdb_id: Optional[int] = None
    title: str
    year: Optional[int] = None
    seasons: Optional[int] = None
    episodes: Optional[int] = None
    episodes_list: Optional[List[Episode]] = []
    genres: List[str] = []
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    overview: Optional[str] = None
    backdrop: Optional[str] = None
    videos: Optional[List[Dict]] = []
    images: Optional[List[str]] = []
    popularity: Optional[float] = None
    adult: Optional[bool] = None
    imdb_id: Optional[str] = None
    poster: Optional[str] = "https://upload.wikimedia.org/wikipedia/commons/6/65/No-Image-Placeholder.svg"
    in_production: Optional[bool] = True

    class Settings:
        name = "shows"
