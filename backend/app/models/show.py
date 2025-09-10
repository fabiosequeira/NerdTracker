from beanie import Document
from typing import Optional

class Show(Document):
    title: str
    year: Optional[int]
    seasons: Optional[int]
    episodes: Optional[int]
    genres: list[str] = []
    rating: Optional[float]
    
    class Settings:
        name = "shows"