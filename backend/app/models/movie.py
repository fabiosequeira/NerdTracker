from beanie import Document
from typing import Optional, List, Dict

class Movie(Document):
    title: str
    year: Optional[int] = None
    genres: List[str] = []
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    overview: Optional[str] = None
    runtime: Optional[int] = None
    backdrop: Optional[str] = None
    videos: List[Dict] = []  # {name, key, site, type}
    images: List[str] = []   # URLs of images
    popularity: Optional[float] = None
    adult: Optional[bool] = None
    imdb_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    poster: Optional[str] = "https://upload.wikimedia.org/wikipedia/commons/6/65/No-Image-Placeholder.svg"

    class Settings:
        name = "movies"
