from fastapi import APIRouter, Response, HTTPException, status
from backend.app.auth.utils import delete_auth_cookies
from backend.app.core.i18n import _
from backend.app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    try:
        delete_auth_cookies(response)
        logger.info("User logged out successfully.")
        return {"message": _("Logged out successfully.")}
    except Exception as e:
        logger.error(f"Error during logout: {e}", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": _("An unexpected error occurred during logout."),
                "action": _("Please try again later."),
            },
        )
