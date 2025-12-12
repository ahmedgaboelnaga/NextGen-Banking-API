from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.main import api_router
from .core.config import settings
from .core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    await init_db()
    yield
    # Shutdown code


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.API_V1_STR)
