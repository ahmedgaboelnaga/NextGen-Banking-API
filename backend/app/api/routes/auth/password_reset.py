from fastapi import APIRouter, HTTPException, status
from backend.app.core.db import SessionDep
from backend.app.core.i18n import _
from backend.app.auth.schema import (
    ConfirmPasswordResetSchema,
    PasswordResetRequestSchema,
)
from backend.app.api.services.user_auth import user_auth_service
from backend.app.core.services.password_reset import send_password_reset_email
from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/request-password-reset", status_code=status.HTTP_200_OK)
async def request_password_reset(
    reset_data: PasswordResetRequestSchema,
    session: SessionDep,
) -> dict:
    try:
        user = await user_auth_service.get_user_by_email(
            reset_data.email, session, include_inactive=True
        )

        if user:
            await send_password_reset_email(email=user.email, user_id=user.id)

        return {
            "message": _(
                "If an account with that email exists, a password reset link has been sent."
            )
        }
    except Exception as e:
        logger.error(f"Failed to process password reset request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": _(
                    "An unexpected error occurred while processing your request."
                ),
                "action": _("Please try again later."),
            },
        )


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    token: str, reset_data: ConfirmPasswordResetSchema, session: SessionDep
):
    try:
        await user_auth_service.reset_password(token, reset_data.new_password, session)
        return {"message": _("Password has been reset successfully.")}
    except ValueError as ve:
        error_msg = str(ve)
        if error_msg == "Password reset token expired":
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={
                    "status": "error",
                    "message": _("Password reset link has expired."),
                    "action": _("Please request a new password reset email."),
                    "action_url": f"{settings.API_BASE_URL}{settings.API_V1_STR}/auth/request-password-reset",
                    "email_required": True,
                },
            )
        elif error_msg == "Invalid password reset token":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": _("Invalid password reset link."),
                    "action": _("Please confirm that the link is correct."),
                },
            )
        elif error_msg == "Invalid token type":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": _("Invalid password reset link."),
                    "action": _("Please confirm that the link is correct."),
                },
            )
    except HTTPException as http_exc:
        logger.error(f"Password reset error: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to reset password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": _("An unexpected error occurred while resetting password."),
                "action": _("Please try again later."),
            },
        )
