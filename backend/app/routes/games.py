from fastapi import APIRouter, HTTPException, Query, Body
from beanie import PydanticObjectId
from app.models.game import Game, Trophy
from typing import List, Optional
import httpx
import os
import time

router = APIRouter(prefix="/games", tags=["games"])

# Load your IGDB credentials
IGDB_CLIENT_ID = os.getenv("IGDB_CLIENT_ID", "hsjerkcx7ssrpxnvrcqvb2id3vj91m")
IGDB_CLIENT_SECRET = os.getenv("IGDB_CLIENT_SECRET", "h33kqwt5lbhnlc4zv1syqlor5g3iyw")

# Simple in-memory token cache
igdb_token = None
igdb_token_expiry = 0


async def get_igdb_token() -> str:
    global igdb_token, igdb_token_expiry

    if igdb_token and time.time() < igdb_token_expiry:
        return igdb_token

    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": IGDB_CLIENT_ID,
        "client_secret": IGDB_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch IGDB token")
        data = resp.json()
        igdb_token = data["access_token"]
        igdb_token_expiry = time.time() + data["expires_in"] - 60  # renew a bit earlier
        return igdb_token


@router.get("/", response_model=list[Game])
async def list_games():
    return await Game.find_all().to_list()


@router.post("/", response_model=Game)
async def add_game(    
    igdb_id: int = Query(..., description="IGDB game ID"),
    trophies: Optional[List[Trophy]] = Body(None, description="Optional list of trophies")
):
    #chek for existing game
    existing = await Game.find_one(Game.igdb_id == igdb_id)
    if existing:
        raise HTTPException(status_code=400, detail="Game already exists")
    
    token = await get_igdb_token()
    url = "https://api.igdb.com/v4/games"
    headers = {
        "Client-ID": IGDB_CLIENT_ID,
        "Authorization": f"Bearer {token}",
    }

    body = f"""
fields id, name, first_release_date, hypes, genres.name, rating, cover.image_id, 
       platforms.name, game_modes.name, rating_count, aggregated_rating, aggregated_rating_count, 
       screenshots.image_id, artworks.image_id, websites.url, dlcs.name, expansions.name, 
       remakes.name, remasters.name, bundles.name, involved_companies.company.name,
       summary, storyline;
where id = {igdb_id};
"""

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, content=body, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="IGDB request failed")
        data = resp.json()
        if not data:
            raise HTTPException(status_code=404, detail="Game not found in IGDB")
        details = data[0]


    # Build payload
    payload = {
        "igdb_id": details.get("id"),
        "title": details.get("name"),
        "year": time.gmtime(details["first_release_date"]).tm_year if details.get("first_release_date") else None,
        "genres": [g.get("name") for g in details.get("genres", []) if g.get("name")],
        "category": details.get("category", {}).get("name") if details.get("category") else None,
        "game_modes": [m.get("name") for m in details.get("game_modes", []) if m.get("name")],
        "rating": round(details.get("rating"), 1) if details.get("rating") is not None else None,
        "rating_count": details.get("rating_count"),
        "aggregated_rating": round(details.get("aggregated_rating"), 1) if details.get("aggregated_rating") is not None else None,
        "aggregated_rating_count": details.get("aggregated_rating_count"),
        "popularity": details.get("hypes"),
        "cover": f"https://images.igdb.com/igdb/image/upload/t_720p/{details['cover']['image_id']}.jpg" if details.get("cover") else None,
        "screenshots": [
            f"https://images.igdb.com/igdb/image/upload/t_1080p/{s['image_id']}.jpg"
            for s in details.get("screenshots", [])[:12]   
            if s.get("image_id")
        ],
        "artworks": [
            f"https://images.igdb.com/igdb/image/upload/t_1080p/{a['image_id']}.jpg"
            for a in details.get("artworks", [])[:12]      
            if a.get("image_id")
        ],
        "videos": [
            v.get("video_id")
            for v in details.get("videos", [])[:6]         
            if v.get("video_id")
        ],
        "websites": [w.get("url") for w in details.get("websites", []) if w.get("url")],
        "platforms": [p.get("name") for p in details.get("platforms", []) if p.get("name")],
        "dlcs": [d.get("name") for d in details.get("dlcs", []) if d.get("name")],
        "expansions": [e.get("name") for e in details.get("expansions", []) if e.get("name")],
        "remakes": [r.get("name") for r in details.get("remakes", []) if r.get("name")],
        "remasters": [r.get("name") for r in details.get("remasters", []) if r.get("name")],
        "bundles": [b.get("name") for b in details.get("bundles", []) if b.get("name")],
        "involved_companies": [c.get("company", {}).get("name") for c in details.get("involved_companies", []) if c.get("company")],
        "collection": details.get("collection", {}).get("name") if details.get("collection") else None,
        "franchise": details.get("franchise", {}).get("name") if details.get("franchise") else None,
        "version_title": details.get("version_title"),
        "parent_game": details.get("parent_game", {}).get("name") if details.get("parent_game") else None,
        "language_supports": [l.get("language", {}).get("name") for l in details.get("language_supports", []) if l.get("language")],
        "summary": details.get("summary"),
        "storyline": details.get("storyline"),
    }

    game = Game(**payload)
    await game.insert()
    return game



@router.delete("/{game_id}")
async def delete_game(game_id: PydanticObjectId):
    game = await Game.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    await game.delete()
    return {"message": f"Game {game.title} deleted ✅"}



@router.get("/{game_id}", response_model=Game)
async def get_game(game_id: PydanticObjectId):
    game = await Game.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


