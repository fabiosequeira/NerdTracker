import httpx
from fastapi import APIRouter, Query

router = APIRouter(prefix="/tmdb", tags=["tmdb"])

TMDB_API_KEY = "279b31fd921c02d920708f2ecd2fae66"

@router.get("/search/movie")
async def search_movie(query: str = Query(..., min_length=2)):
    url = "https://api.themoviedb.org/3/search/movie"
    params = {"api_key": TMDB_API_KEY, "query": query, "language": "en-US"}
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        
    results = [
        {
            "id": m["id"],
            "title": m.get("title"),
            "year": m.get("release_date", "")[:4] if m.get("release_date") else None,
            "poster": f"https://image.tmdb.org/t/p/w200{m['poster_path']}" if m.get("poster_path") else None,
            "popularity": m.get("popularity", 0),
        }
        for m in data.get("results", [])
    ]
    return results

@router.get("/search/tv")
async def search_show(query: str = Query(..., min_length=2)):
    url = "https://api.themoviedb.org/3/search/tv"
    params = {"api_key": TMDB_API_KEY, "query": query, "language": "en-US"}
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        
    results = [
        {
            "id": m["id"],
            "title": m.get("name"),  # TV usa "name" em vez de "title"
            "year": m.get("first_air_date", "")[:4] if m.get("first_air_date") else None,
            "poster": f"https://image.tmdb.org/t/p/w200{m['poster_path']}" if m.get("poster_path") else None,
            "popularity": m.get("popularity", 0),
        }
        for m in data.get("results", [])
    ]
    return results
