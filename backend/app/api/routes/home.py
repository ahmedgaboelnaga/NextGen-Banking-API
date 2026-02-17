from fastapi import APIRouter
from backend.app.core.logging import get_logger
from backend.app.core.i18n import _

logger = get_logger()

router = APIRouter(prefix="/home", tags=["home"])


@router.get("/")
async def home():
    return {"message": _("Welcome to the Next-Gen Backend API!")}
