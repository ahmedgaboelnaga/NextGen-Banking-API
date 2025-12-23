from fastapi import APIRouter
from backend.app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/home", tags=["home"])


@router.get("/")
async def home():
    logger.info("Home endpoint accessed")
    logger.debug("Debugging home endpoint")
    logger.error("Error level log for testing")
    logger.warning("Home endpoint warning log")
    logger.critical("Home endpoint critical log")
    return {"message": "Welcome to the Next-Gen Backend API!"}
