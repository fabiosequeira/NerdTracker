from beanie import Document
from typing import Optional, List, Dict

from pydantic.v1 import Field

class Manga(Document):
    anilist_id: Optional[int] = None
    title: str
    title_native: Optional[str] = None
    title_romaji: Optional[str] = None
    year: Optional[int] = None
    poster: Optional[str] = "https://upload.wikimedia.org/wikipedia/commons/6/65/No-Image-Placeholder.svg"
    genres: List[str] = []
    summary: Optional[str] = None
    banner_image: Optional[str] = None
    trailer_site: Optional[str] = None
    trailer_id: Optional[str] = None
    trailer_thumbnail: Optional[str] = None
    average_score: Optional[int] = None
    popularity: Optional[int] = None
    country_of_origin: Optional[str] = None
    
    class Settings:
        name = "manga"
        indexes = ["anilist_id"]