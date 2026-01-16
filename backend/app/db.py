import os
from beanie import init_beanie
import motor.motor_asyncio

from app.models.movie import Movie
from app.models.show import Show
from app.models.anime import Anime
from app.models.game import Game


async def init_db():
    mongo_uri = os.getenv("MONGO_URI")

    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    database = client["NerdTracker"]

    await init_beanie(
        database=database,
        document_models=[Movie, Show, Anime, Game],
    )
    print("Connected to MongoDB and initialized Beanie ODM.")