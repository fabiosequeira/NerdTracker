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
            "poster": f"https://image.tmdb.org/t/p/original{m['poster_path']}" if m.get("poster_path") else None,
            "genres": m.get("genre_ids", []),
            "rating": m.get("vote_average", None),
            "popularity": m.get("popularity", 0),
        }
        for m in data.get("results", [])
    ]
    return results

@router.get("/search/tv")
async def search_show(query: str = Query(..., min_length=2)):
    url = "https://api.themoviedb.org/3/search/tv"
    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "language": "en-US",
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        
    results = []
    for m in data.get("results", []):
        if "JP" not in (m.get("origin_country") or []):
            # fetch details
            detail_url = f"https://api.themoviedb.org/3/tv/{m['id']}"
            async with httpx.AsyncClient() as client:
                detail_resp = await client.get(detail_url, params={"api_key": TMDB_API_KEY, "language": "en-US"})
                details = detail_resp.json()
            results.append({
                "id": m["id"],
                "title": m.get("name"),
                "year": m.get("first_air_date", "")[:4] if m.get("first_air_date") else None,
                "poster": f"https://image.tmdb.org/t/p/original{m['poster_path']}" if m.get("poster_path") else None,
                "genres": [g["name"] for g in details.get("genres", [])],
                "rating": details.get("vote_average"),
                "seasons": details.get("number_of_seasons"),
                "episodes": details.get("number_of_episodes"),
                "popularity": m.get("popularity", 0),
            })
    return results


@router.get("/search/anime")
async def search_anime(query: str = Query(..., min_length=2)):
    url = "https://api.themoviedb.org/3/search/tv"
    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "language": "en-US",
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
    
    results = [
        {
            "id": m["id"],
            "title": m.get("name"),
            "year": m.get("first_air_date", "")[:4] if m.get("first_air_date") else None,
            "poster": f"https://image.tmdb.org/t/p/original{m['poster_path']}" if m.get("poster_path") else None,
            "genres": m.get("genre_ids", []),
            "rating": m.get("vote_average", None),
            "popularity": m.get("popularity", 0),
        }
        for m in data.get("results", [])
        if "JP" in (m.get("origin_country") or [])
    ]
    return results

