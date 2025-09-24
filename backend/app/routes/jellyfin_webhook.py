# app/routes/jellyfin_webhook.py
from fastapi import APIRouter, Request
import httpx
import os

router = APIRouter(prefix="/jellyfin", tags=["jellyfin"])

TRACKER_URL = os.getenv("TRACKER_URL", "http://127.0.0.1:8000")

@router.post("/webhook")
async def jellyfin_webhook(request: Request):
    """
    Receives Jellyfin webhook events.
    Expects JSON payload from Jellyfin.
    Only processes "ItemPlaybackEnded" events.
    """
    payload = await request.json()
    event = payload.get("Event")
    if event != "ItemPlaybackEnded":
        return {"message": "Ignored non-playback event."}

    item = payload.get("Item")
    if not item:
        return {"message": "No item in payload."}

    tmdb_id = item.get("ProviderIds", {}).get("Tmdb")
    if not tmdb_id:
        return {"message": f"No TMDb ID for {item.get('Name')}"}

    item_type = item.get("Type")  # Movie or Series
    origin = item.get("ProductionLocations", [])
    is_anime = "JP" in [loc.upper() for loc in origin]

    endpoint = None
    if item_type == "Movie":
        endpoint = f"{TRACKER_URL}/movies"
    elif item_type == "Series" and is_anime:
        endpoint = f"{TRACKER_URL}/animes"
    elif item_type == "Series":
        endpoint = f"{TRACKER_URL}/shows"
    else:
        return {"message": f"Unknown type for {item.get('Name')}"}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(endpoint, json={"tmdb_id": tmdb_id})
        if resp.status_code in (200, 201):
            return {"message": f"Added {item.get('Name')} to tracker at {endpoint}"}
        else:
            return {"message": f"Failed to add {item.get('Name')} - status {resp.status_code}"}
