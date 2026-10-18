from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncio
from app.routes import movies, shows, animes, games, comics, mangas, tmdb, igdb, jellyfin_webhook, books, audiobooks
from app.services.catalog import CatalogError
from app.db import init_db
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.core.http import close_client
from app.core.tasks import weekly_tmdb_sync
from app.utils.fill_anime import fill_animes
from app.utils.fill_shows import fill_shows

origins = ["*"]

app = FastAPI(title="NerdTracker API")
app.include_router(tmdb.router)
app.include_router(igdb.router)
app.include_router(movies.router)
app.include_router(shows.router)
app.include_router(animes.router)
app.include_router(games.router)
app.include_router(comics.router)
app.include_router(mangas.router)
app.include_router(books.router)
app.include_router(audiobooks.router)
app.include_router(jellyfin_webhook.router)
# JSON lists compress ~5-10x. Added before CORS so CORS stays the outermost middleware.
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,  # let browsers cache the CORS preflight instead of re-sending it constantly
)
@app.exception_handler(CatalogError)
async def catalog_error_handler(_: Request, exc: CatalogError):
    # keep the usual {"detail": "..."} shape; extras (existing_id, providers...) sit next to it
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, **exc.extra})


@app.on_event("startup")
async def on_startup():
    await init_db()
    # Start the weekly TMDB sync as a background task
    asyncio.create_task(weekly_tmdb_sync())
    
    asyncio.create_task(fill_animes()) 
    asyncio.create_task(fill_shows()) 


@app.on_event("shutdown")
async def on_shutdown():
    await close_client()
