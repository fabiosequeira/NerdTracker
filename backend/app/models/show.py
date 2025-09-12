from beanie import Document
from typing import Optional

class Show(Document):
    tmdb_id: Optional[int] = None
    title: str
    year: Optional[int]
    seasons: Optional[int] = None
    episodes: Optional[int] = None
    genres: list[str] = []
    rating: Optional[float] = None
    poster: Optional[str] = "https://upload.wikimedia.org/wikipedia/commons/6/65/No-Image-Placeholder.svg"
    
    class Settings:
        name = "shows"