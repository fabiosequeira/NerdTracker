from fastapi import FastAPI
from app.routes import movies, shows, animes
from app.db import init_db

app = FastAPI(title="NerdTracker API")
app.include_router(movies.router, prefix="/movies", tags=["movies"])
app.include_router(shows.router, prefix="/shows", tags=["shows"])
app.include_router(animes.router, prefix="/animes", tags=["animes"])

@app.on_event("startup")
async def on_startup():
    await init_db()