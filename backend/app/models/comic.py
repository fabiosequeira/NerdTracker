from beanie import Document
from typing import Optional, List, Dict

class Comic(Document):
    comicvine_id: Optional[int] = None
    title: str
    year: Optional[int] = None
    publisher: Optional[str] = None
    poster: Optional[str] = "https://upload.wikimedia.org/wikipedia/commons/6/65/No-Image-Placeholder.svg"
    count_of_issues: Optional[int] = None
    summary: Optional[str] = None
    site_detail_url: Optional[str] = None
    api_detail_url: Optional[str] = None
    
    class Settings:
        name = "comics"