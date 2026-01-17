from fastapi import APIRouter
from backend.app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/home", tags=["home"])


@router.get("/")
async def home():
    return {"message": "Welcome to the Next-Gen Backend API!"}
