from fastapi import FastAPI
from app.routes import movies, shows, animes, games, tmdb, igdb, jellyfin_webhook
from app.db import init_db
from fastapi.middleware.cors import CORSMiddleware

origins = ["*"]

app = FastAPI(title="NerdTracker API")
app.include_router(tmdb.router)
app.include_router(igdb.router)
app.include_router(movies.router)
app.include_router(shows.router)
app.include_router(animes.router)
app.include_router(games.router)
app.include_router(jellyfin_webhook.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.on_event("startup")
async def on_startup():
    await init_db()