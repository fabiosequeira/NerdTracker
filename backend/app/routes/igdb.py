# app/routes/igdb.py
import time
import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/igdb", tags=["igdb"])

IGDB_CLIENT_ID = "hsjerkcx7ssrpxnvrcqvb2id3vj91m"
IGDB_CLIENT_SECRET = "h33kqwt5lbhnlc4zv1syqlor5g3iyw"

_igdb_token: str | None = None
_igdb_token_expiry = 0.0


async def _get_igdb_token() -> str:
    global _igdb_token, _igdb_token_expiry

    if _igdb_token and time.time() < _igdb_token_expiry:
        return _igdb_token

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://id.twitch.tv/oauth2/token",
            params={
                "client_id": IGDB_CLIENT_ID,
                "client_secret": IGDB_CLIENT_SECRET,
                "grant_type": "client_credentials",
            },
            timeout=10,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch IGDB token")

        data = resp.json()
        _igdb_token = data.get("access_token")
        _igdb_token_expiry = time.time() + data.get("expires_in", 0) - 60
        return _igdb_token


@router.get("/search/game")
async def search_games(query: str):
    token = await _get_igdb_token()

    headers = {
        "Client-ID": IGDB_CLIENT_ID,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "text/plain",
    }

    # Request name, release date, genres, rating, and cover
    body = f'''
        search "{query}";
        fields id,name,first_release_date,genres.name,rating,cover.image_id;
        limit 10;
    '''

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.igdb.com/v4/games",
            content=body.encode("utf-8"),
            headers=headers
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data = resp.json()

    # Transform into something nicer for frontend
    results = []
    for g in data:
        results.append({
            "id": g.get("id"),
            "title": g.get("name"),
            "year": g.get("first_release_date"),
            "genres": [genre["name"] for genre in g.get("genres", [])] if g.get("genres") else [],
            "rating": round(g["rating"], 1) if g.get("rating") else None,
            "poster": f"https://images.igdb.com/igdb/image/upload/t_cover_big/{g['cover']['image_id']}.jpg"
                      if g.get("cover") else None
        })

    return results

