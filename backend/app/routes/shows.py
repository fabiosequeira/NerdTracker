from fastapi import APIRouter, HTTPException
from app.models.show import Show

router = APIRouter()

@router.post("/", response_model=Show)
async def add_show(show: Show):
    await show.insert()
    return show

@router.get("/", response_model=list[Show])
async def list_shows():
    return await Show.find_all().to_list()

@router.get("/{show_id}", response_model=Show)
async def get_show(show_id: str):
    show = await Show.get(show_id)
    if not show:
        raise HTTPException(404, "Show not found")
    return show
