from fastapi import APIRouter, HTTPException
from beanie import PydanticObjectId
from app.models.comic import Comic
from app.core.cache import TTLCache
from app.core.http import get_client
from app.core.listing import list_documents
import re
from html import unescape
import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter(prefix="/comics", tags=["comics"])
COMICVINE_API_KEY = os.getenv("COMICVINE_API_KEY")
if not COMICVINE_API_KEY:
    raise ValueError("COMICVINE_API_KEY is not set in environment")


def extract_summary(html: str):
    if not html:
        return None

    # grab ONLY the first <p>...</p>
    match = re.search(r'<p>(.*?)</p>', html, re.DOTALL)
    if not match:
        return None

    # remove any remaining tags inside the paragraph
    text = re.sub(r'<[^>]+>', '', match.group(1))

    # decode HTML entities
    return unescape(text).strip()

def parse_year(value):
    if not value:
        return None
    
    match = re.search(r"\d{4}", value)
    return int(match.group()) if match else None


_search_cache = TTLCache(ttl=300, maxsize=256)


async def _search_comics_upstream(query: str):
    url = "https://comicvine.gamespot.com/api/search/"
    params = {
        "api_key": COMICVINE_API_KEY,
        "format": "json",
        "query": query,
        "resources": "volume",
        "limit": 10,
    }
    headers = {"User-Agent": "FabioMediaApp/1.0 (fabio10cfy@gmail.com)"}

    resp = await get_client().get(url, params=params, headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="ComicVine request failed")

    data = resp.json()

    if data.get("status_code") != 1:
        raise HTTPException(status_code=400, detail=data.get("error", "Unknown error"))

    results = []
    for item in data.get("results", []):
        image = item.get("image") or {}
        results.append({
            "id": item.get("id"),
            "title": item.get("name"),
            "year": parse_year(item.get("start_year") or ""),
            # search results are only shown as a tiny thumbnail: don't ship the full-size original
            "poster": image.get("small_url") or image.get("thumb_url") or image.get("original_url"),
            "count_of_issues": item.get("count_of_issues"),
            "publisher": (item.get("publisher") or {}).get("name"),
        })

    return results


@router.get("/search")
async def search_comics(query: str):
    return await _search_cache.get_or_load(query.strip().casefold(), lambda: _search_comics_upstream(query))


# Fields the grid doesn't need; omitted from the list by default (use ?full=true for everything).
LIST_EXCLUDE = ("summary", "site_detail_url", "api_detail_url")


@router.get("/", response_model=list[Comic])
async def list_comics(full: bool = False):
    return await list_documents(Comic, LIST_EXCLUDE, full)

@router.post("/", response_model=Comic)
async def add_comic(comicvine_id: int):
    
    #check for existing comic
    existing = await Comic.find_one(Comic.comicvine_id == comicvine_id)
    if existing:
        raise HTTPException(status_code=400, detail="Comic already exists")
    
    url = f"https://comicvine.gamespot.com/api/volume/4050-{comicvine_id}/"
    params = {
        "api_key": COMICVINE_API_KEY,
        "format": "json",
    }

    headers = {
        "User-Agent": "FabioMediaApp/1.0 (fabio10cfy@gmail.com)"
    }
    resp = await get_client().get(url, params=params, headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="ComicVine request failed")
    details = resp.json()


    if details.get("status_code") != 1:
        raise HTTPException(status_code=400, detail="ComicVine API error: " + details.get("error", "Unknown error"))

    result = details.get("results", {})
    payload = {
        "comicvine_id": comicvine_id,
        "title": result.get("name"),
        "year": parse_year(result.get("start_year") or ""),
        "publisher": result.get("publisher", {}).get("name"),
        "poster": result.get("image", {}).get("original_url"),
        "count_of_issues": result.get("count_of_issues"),
        "summary": result.get("deck") or extract_summary(result.get("description")) or "No description available",
        "site_detail_url": result.get("site_detail_url"),
        "api_detail_url": result.get("api_detail_url"),

    }
    
    comic = Comic(**payload)
    await comic.insert()
    return comic

@router.delete("/{comic_id}")
async def delete_comic(comic_id: PydanticObjectId):
    comic = await Comic.get(comic_id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")
    await comic.delete()
    return {"message": f"Comic {comic.title} deleted ✅"}

@router.get("/{comic_id}", response_model=Comic)
async def get_comic(comic_id: PydanticObjectId):
    comic = await Comic.get(comic_id)
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")
    return comic