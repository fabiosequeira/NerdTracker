from fastapi import APIRouter, HTTPException
from beanie import PydanticObjectId
from app.models.manga import Manga
import re
from html import unescape
import httpx
import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter(prefix="/manga", tags=["manga"])
client = httpx.AsyncClient()

def clean_description(html: str):
    if not html:
        return None

    text = re.sub(r'<br\s*/?>', '\n', html)
    text = re.sub(r'<[^>]+>', '', text)
    return unescape(text).strip()


@router.get("/search")
async def search_manga(query: str):
    url = "https://graphql.anilist.co/"
    graphql_query = {
        "query": """
    query ($search: String) {
      Page(perPage: 10) {
        media(search: $search, type: MANGA) {
          id
          title {
            romaji
            english
          }
          startDate {
            year
          }
          coverImage {
            extraLarge
          }
        }
      }
    }
    """
        
    }
    variables = {"search": query}

    resp = await client.post(url, json={
            "query": graphql_query,
            "variables": variables
        })

    if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="AniList request failed")

    data = resp.json()

    results = []
    for item in data["data"]["Page"]["media"]:
        results.append({
            "id": item["id"],
            "title": item["title"]["english"] or item["title"]["romaji"],
            "year": item.get("startDate", {}).get("year"),
            "poster": item.get("coverImage", {}).get("extraLarge"),
        })

    return results



@router.get("/", response_model=list[Manga])
async def list_manga():
    return await Manga.find_all().to_list()

@router.post("/", response_model=Manga)
async def add_manga(anilist_id: int):

    # check for existing
    existing = await Manga.find_one(Manga.anilist_id == anilist_id)
    if existing:
        raise HTTPException(status_code=400, detail="Manga already exists")

    url = "https://graphql.anilist.co"

    graphql_query = """
    query ($id: Int) {
      Media(id: $id, type: MANGA) {
        id
        title {
          romaji
          english
          native
        }
        bannerImage
        averageScore
        countryOfOrigin
        coverImage {
          extraLarge
        }
        description
        genres
        isAdult
        startDate {
          year
        }
        status
        trailer {
          site
          id
          thumbnail
        }
        popularity
      }
    }
    """

    variables = {"id": anilist_id}

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={
            "query": graphql_query,
            "variables": variables
        })

        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="AniList request failed")

        data = resp.json()

    media = data.get("data", {}).get("Media")
    if not media:
        raise HTTPException(status_code=404, detail="Manga not found")

    payload = {
        "anilist_id": media["id"],
        "title": media["title"]["english"] or media["title"]["romaji"],
        "title_native": media["title"].get("native"),
        "title_romaji": media["title"].get("romaji"),
        "year": media.get("startDate", {}).get("year"),
        "poster": media.get("coverImage", {}).get("extraLarge"),
        "banner_image": media.get("bannerImage"),
        "genres": media.get("genres", []),
        "summary": clean_description(media.get("description")) or "No description available",
        "trailer_site": media.get("trailer", {}).get("site"),
        "trailer_id": media.get("trailer", {}).get("id"),
        "trailer_thumbnail": media.get("trailer", {}).get("thumbnail"),
        "average_score": media.get("averageScore"),
        "popularity": media.get("popularity"),
        "country_of_origin": media.get("countryOfOrigin"),
    }

    manga = Manga(**payload)
    await manga.insert()
    return manga


@router.delete("/{manga_id}")
async def delete_manga(manga_id: PydanticObjectId):
    manga = await Manga.get(manga_id)
    if not manga:
        raise HTTPException(status_code=404, detail="Manga not found")
    await manga.delete()
    return {"message": f"Manga {manga.title} deleted ✅"}

@router.get("/{manga_id}", response_model=Manga)
async def get_manga(manga_id: PydanticObjectId):
    manga = await Manga.get(manga_id)
    if not manga:
        raise HTTPException(status_code=404, detail="Manga not found")
    return manga