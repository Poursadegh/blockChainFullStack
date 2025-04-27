from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .core.config import settings
from .api.v1.endpoints import bitcoin, wallet, auth, user, market, trading, kyc, support, liveness
from .core.database import register_db
from .core.cache import init_cache
import os

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Tortoise ORM
register_db(app)

# Mount static files directory for media
media_dir = os.path.join(settings.BASE_DIR, "media")
os.makedirs(media_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=media_dir), name="media")

# Include routers
app.include_router(bitcoin.router, prefix=f"{settings.API_V1_STR}/bitcoin", tags=["bitcoin"])
app.include_router(wallet.router, prefix=f"{settings.API_V1_STR}/wallet", tags=["wallet"])
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(user.router, prefix=settings.API_V1_STR)
app.include_router(market.router, prefix=settings.API_V1_STR)
app.include_router(trading.router, prefix=settings.API_V1_STR)
app.include_router(kyc.router, prefix=settings.API_V1_STR)
app.include_router(support.router, prefix=settings.API_V1_STR)
app.include_router(liveness.router, prefix=f"{settings.API_V1_STR}/liveness")

@app.on_event("startup")
async def startup_event():
    await init_cache()

@app.get("/")
async def root():
    return {
        "message": "Welcome to Crypto Explorer Enterprise API",
        "version": settings.VERSION,
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    } 