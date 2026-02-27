from fastapi import APIRouter, HTTPException, Request, Response, status

from backend.app.api.services.oauth_service import oauth, oauth_service
from backend.app.auth.schema import AccountStatusSchema
from backend.app.auth.utils import create_jwt_token, set_auth_cookies
from backend.app.core.config import settings
from backend.app.core.db import SessionDep
from backend.app.core.i18n import _
from backend.app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])

_CALLBACK_PATH = f"{settings.API_V1_STR}/auth/google/callback"


@router.get("/google", summary="Redirect to Google OAuth consent screen")
async def google_login(request: Request):
    """Redirect the browser to Google's OAuth 2.0 authorisation endpoint."""
    redirect_uri = str(request.base_url).rstrip("/") + _CALLBACK_PATH
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", summary="Handle Google OAuth callback")
async def google_callback(
    request: Request,
    session: SessionDep,
    response: Response,
):
    """
    Exchange the authorisation code for tokens, resolve (or create) the user,
    and set JWT cookies — exactly as the OTP-based login flow does.
    """
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        logger.error(f"Google OAuth token exchange failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "message": _("Google authorisation failed."),
                "action": _("Please try again."),
            },
        )

    google_info: dict = token.get("userinfo") or {}

    if not google_info.get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "message": _("Google did not return an email address."),
                "action": _(
                    "Please make sure your Google account has a verified email."
                ),
            },
        )

    try:
        user = await oauth_service.get_or_create_user_via_google(
            google_info=google_info,
            session=session,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth user resolution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": _("Failed to process Google login."),
                "action": _("Please try again later."),
            },
        )

    access_token = create_jwt_token(id=user.id)
    refresh_token = create_jwt_token(id=user.id, type=settings.COOKIE_REFRESH_NAME)
    set_auth_cookies(response, access_token, refresh_token)

    return {
        "message": _("Login successful."),
        # kyc_required tells the frontend to redirect the user to the KYC
        # screen to submit their national ID before they can use banking features.
        "kyc_required": user.account_status == AccountStatusSchema.PENDING_KYC,
        "user": {
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "id_no": user.id_no,
            "role": user.role,
            "account_status": user.account_status,
        },
    }
