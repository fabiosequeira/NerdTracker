from beanie import Document
from typing import Optional

class Game(Document):
    igdb_id: int
    title: str
    year: Optional[int] = None
    genres: list[str] = []
    game_modes: list[str] = []
    rating: Optional[float] = None
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
    class Settings:
        name = "games"
