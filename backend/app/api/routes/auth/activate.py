from fastapi import APIRouter, status, HTTPException
from backend.app.core.db import SessionDep
from backend.app.core.i18n import _
from backend.app.auth.schema import AccountStatusSchema, EmailRequestSchema
from backend.app.api.services.user_auth import user_auth_service
from backend.app.auth.utils import create_activation_token
from backend.app.core.services.activation_email import send_activation_email
from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/activate", status_code=status.HTTP_200_OK)
async def activate_account(token: str, session: SessionDep):
    try:
        user = await user_auth_service.activate_user_account(token, session)
        return {"message": _("Account activated successfully."), "email": user.email}
    except ValueError as ve:
        error_msg = str(ve)
        if error_msg == "Invalid token type":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": _("Invalid activation link."),
                    "action": _("Please confirm that the link is correct."),
                },
            )
        elif error_msg == "Activation token expired":
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={
                    "status": "error",
                    "message": _("Activation link has expired."),
                    "action": _("Please request a new activation email."),
                    "action_url": f"{settings.API_BASE_URL}{settings.API_V1_STR}/auth/resend-activation-link",
                    "email_required": True,
                },
            )
        elif error_msg == "Invalid activation token":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": _("Invalid activation link."),
                    "action": _("Please confirm that the link is correct."),
                },
            )
        elif error_msg == "User already activated":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": _("User already activated"),
                    "action": _("You can log in with your credentials."),
                },
            )

    except HTTPException as http_exc:
        logger.error(f"Activation error: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to activate user account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": _("Failed to activate user account."),
                "action": _("Please try again later."),
            },
        )


@router.post("/resend-activation-link", status_code=status.HTTP_200_OK)
async def resend_activation_link(email_data: EmailRequestSchema, session: SessionDep):
    try:
        user = await user_auth_service.get_user_by_email(
            email_data.email, session, include_inactive=True
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "message": _("User not found."),
                    "action": _("Please check the email address and try again."),
                },
            )
        if user.is_active or user.account_status == AccountStatusSchema.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": _("Account is already activated."),
                    "action": _("Please log in with your credentials."),
                },
            )
        activation_token = create_activation_token(user.id)
        await send_activation_email(user.email, activation_token)
        return {
            "message": _(
                "Activation email resent successfully, please check your inbox for activation link."
            ),
            "email": user.email,
        }
    except HTTPException as http_exc:
        logger.error(f"Resend activation link error: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to resend activation email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": _("Failed to resend activation email."),
                "action": _("Please try again later."),
            },
        )
