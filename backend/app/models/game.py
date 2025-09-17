from beanie import Document
from pydantic import BaseModel
from typing import Optional, List

class Trophy(BaseModel):
    name: str
    description: Optional[str] = None
    type: str  # "platinum", "gold", "silver", "bronze"
    order: int
    unlocked: bool = False
    date_unlocked: Optional[str] = None  # ISO format

class Game(Document):
    igdb_id: int
    title: str
    year: Optional[int] = None
    genres: list[str] = []
    game_modes: list[str] = []
    rating: Optional[float] = None
    popularity: Optional[float] = None
    rating_count: Optional[int] = None
    aggregated_rating: Optional[float] = None
    aggregated_rating_count: Optional[int] = None
    cover: Optional[str] = "https://upload.wikimedia.org/wikipedia/commons/6/65/No-Image-Placeholder.svg"
    screenshots: list[str] = []
    artworks: list[str] = []
    websites: list[str] = []
    platforms: list[str] = []
    dlcs: list[str] = []
    expansions: list[str] = []
    remakes: list[str] = []
    remasters: list[str] = []
    bundles: list[str] = []
    involved_companies: list[str] = []
    summary: Optional[str] = None
    storyline: Optional[str] = None 
    trophies: List[Trophy] = []
    class Settings:
        name = "games"
