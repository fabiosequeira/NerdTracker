from beanie import Document
from typing import Optional

class Anime(Document):
    title: str
    year: Optional[int]
    seasons: Optional[int] = None
    episodes: Optional[int] = None
    genres: list[str] = []
    rating: Optional[float]
    
    class Settings:
        name = "anime"