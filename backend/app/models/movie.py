from beanie import Document
from typing import Optional

class Movie(Document):
    title: str
    year: Optional[int]
    genres: list[str] = []
    rating: Optional[float] = None
    poster: Optional[str] = "https://upload.wikimedia.org/wikipedia/commons/6/65/No-Image-Placeholder.svg"
    
    class Settings:
        name = "movies"