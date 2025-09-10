from fastapi import FastAPI
from app.routes import movies, shows, animes, tmdb
from app.db import init_db
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost:5173",
    "http://127.0.0.1/"
]

app = FastAPI(title="NerdTracker API")
app.include_router(tmdb.router)
app.include_router(movies.router, prefix="/movies", tags=["movies"])
app.include_router(shows.router, prefix="/shows", tags=["shows"])
app.include_router(animes.router, prefix="/animes", tags=["animes"])
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