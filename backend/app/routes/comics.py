from fastapi import APIRouter, HTTPException
from beanie import PydanticObjectId
from app.models.comic import Comic
import httpx
import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter(prefix="/comics", tags=["comics"])
COMICVINE_API_KEY = os.getenv("COMICVINE_API_KEY")
if not COMICVINE_API_KEY:
    raise ValueError("COMICVINE_API_KEY is not set in environment")

@router.get("/search")
async def search_comics(query: str):
    url = "https://comicvine.gamespot.com/api/search/"
    params = {
        "api_key": COMICVINE_API_KEY,
        "format": "json",
        "query": query,
        "resources": "volume",
        "limit": 10,
    }
    headers = {"User-Agent": "FabioMediaApp/1.0 (fabio10cfy@gmail.com)"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="ComicVine request failed")

        data = resp.json()

    if data.get("status_code") != 1:
        raise HTTPException(status_code=400, detail=data.get("error", "Unknown error"))

    results = []
    for item in data.get("results", []):
        results.append({
            "id": item.get("id"),
            "title": item.get("name"),
            "year": int(item["start_year"]) if item.get("start_year") else None,
            "poster": item.get("image", {}).get("original_url"),
            "count_of_issues": item.get("count_of_issues"),
            "publisher": item.get("publisher", {}).get("name"),
        })

    return results




@router.get("/", response_model=list[Comic])
async def list_comics():
    return await Comic.find_all().to_list()

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

    async with httpx.AsyncClient() as client:
        headers = {
            "User-Agent": "FabioMediaApp/1.0 (fabio10cfy@gmail.com)"
        }
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="ComicVine request failed")
        details = resp.json()


    if details.get("status_code") != 1:
        raise HTTPException(status_code=400, detail="ComicVine API error: " + details.get("error", "Unknown error"))

    result = details.get("results", {})
    payload = {
        "comicvine_id": comicvine_id,
        "title": result.get("name"),
        "year": int(result["start_year"]) if result.get("start_year") else None,
        "publisher": result.get("publisher", {}).get("name"),
        "poster": result.get("image", {}).get("original_url"),
        "count_of_issues": result.get("count_of_issues"),
        "deck": result.get("deck"),
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