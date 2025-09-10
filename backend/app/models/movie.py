from beanie import Document
from typing import Optional

class Movie(Document):
    title: str
    year: Optional[int]
    genres: list[str] = []
    rating: Optional[float]
    
    class Settings:
        name = "movies"