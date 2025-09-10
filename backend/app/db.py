from beanie import init_beanie
import motor.motor_asyncio
from app.models.movie import Movie
from app.models.show import Show
from app.models.anime import Anime

async def init_db():
    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
    database = client["NerdTracker"]
    await init_beanie(database, document_models=[Movie, Show, Anime])
