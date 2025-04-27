from tortoise import Tortoise, fields
from tortoise.models import Model
from tortoise.contrib.fastapi import register_tortoise
from .config import settings

TORTOISE_ORM = {
    "connections": {
        "default": settings.DATABASE_URL
    },
    "apps": {
        "models": {
            "models": [
                "app.models.user",
                "app.models.wallet",
                "aerich.models"
            ],
            "default_connection": "default",
        }
    }
}

async def init_db():
    await Tortoise.init(
        db_url=settings.DATABASE_URL,
        modules={"models": ["app.models.user", "app.models.wallet"]}
    )
    await Tortoise.generate_schemas()

async def close_db():
    await Tortoise.close_connections()

def register_db(app):
    register_tortoise(
        app,
        db_url=settings.DATABASE_URL,
        modules={"models": ["app.models.user", "app.models.wallet"]},
        generate_schemas=True,
        add_exception_handlers=True,
    ) 