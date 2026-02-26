from email.policy import HTTP
import stat
import uuid
import jwt
from fastapi import APIRouter, Response, status, Cookie, HTTPException
from sentry_sdk import HttpTransport
from backend.app.core.db import SessionDep
from backend.app.auth.utils import create_jwt_token, set_auth_cookies
from backend.app.api.services.user_auth import user_auth_service
from backend.app.core.i18n import _
from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_access_token(
    response: Response,
    session: SessionDep,
    refresh_token: str | None = Cookie(None, alias=settings.COOKIE_REFRESH_NAME),
) -> dict:
    try:
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "message": _("No refresh token provided."),
                    "action": _("Please log in again."),
                },
            )
        try:
            payload = jwt.decode(
                refresh_token, settings.SIGNING_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "message": _("Refresh token has expired."),
                    "action": _("Please log in again."),
                },
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "message": _("Invalid refresh token."),
                    "action": _("Please log in again."),
                },
            )
        if payload.get("type") != settings.COOKIE_REFRESH_NAME:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "message": _("Invalid token type."),
                    "action": _("Please log in again."),
                },
            )
        user_id = uuid.UUID(payload.get("id"))
        user = await user_auth_service.get_user_by_id(user_id, session)
        if not user:
            logger.warning(f"User not found for ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "error",
                    "message": _("User not found."),
                    "action": _("Please log in again."),
                },
            )
        await user_auth_service.validate_user_status(user)

        new_access_token = create_jwt_token(id=user.id)
        set_auth_cookies(response, new_access_token)

        logger.info(f"Successfully refreshed access token for user ID: {user.email}")
        return {
            "message": _("Access token refreshed successfully."),
            "user": {
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": user.full_name,
                "id_no": user.id_no,
                "role": user.role,
            },
        }
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to refresh access token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": _("Failed to refresh access token."),
                "action": _("Please try again later."),
            },
        )
