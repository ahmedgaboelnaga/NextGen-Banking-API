from fastapi import APIRouter, status, HTTPException, Response
from backend.app.core.db import SessionDep
from backend.app.core.i18n import _
from backend.app.auth.utils import create_jwt_token, set_auth_cookies
from backend.app.core.config import settings
from backend.app.auth.schema import LoginRequestSchema, OTPVerifyRequestSchema
from backend.app.api.services.user_auth import user_auth_service
from backend.app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login/request-otp", status_code=status.HTTP_200_OK)
async def request_login_otp(request_data: LoginRequestSchema, session: SessionDep):
    try:
        user = await user_auth_service.get_user_by_email(
            email=request_data.email, session=session
        )

        if user:
            await user_auth_service.check_user_lockout(user, session)

            if not await user_auth_service.verify_user_password(
                plain_password=request_data.password,
                hashed_password=user.hashed_password,
            ):
                await user_auth_service.increment_failed_login_attempts(user, session)
                remaining_attempts = (
                    settings.LOGIN_ATTEMPTS - user.failed_login_attempts
                )

                if remaining_attempts > 0:
                    error_message = _(
                        (
                            f"Invalid credentials. You have {remaining_attempts} login attempt"
                            f"{'s' if remaining_attempts != 1 else ''} remaining before your account is temporarily locked."
                        )
                    )
                else:
                    error_message = _(
                        (
                            "Your account has been temporarily locked due to multiple failed login attempts"
                            f"Please try again after {settings.LOCKOUT_DURATION_MINUTES} minutes."
                        )
                    )

                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "status": "error",
                        "message": error_message,
                        "action": _("Please check your credentials and try again."),
                        "remaining_attempts": remaining_attempts,
                    },
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "status": "error",
                        "message": _("Account is not activated."),
                        "action": _("Please activate your account before logging in."),
                    },
                )

            await user_auth_service.reset_user_state(user, session)
            await user_auth_service.generate_and_save_otp(user, session)

        return {
            "message": _(
                "If an account exists with this email, an OTP has been sent to it."
            )
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to process login otp request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": _("Failed to process login OTP request."),
                "action": _("Please try again later."),
            },
        )


@router.post("/login/verify-otp", status_code=status.HTTP_200_OK)
async def verify_login_otp(
    otp_data: OTPVerifyRequestSchema, session: SessionDep, response: Response
):
    try:
        user = await user_auth_service.verify_login_otp(
            otp_data.email, otp_data.otp, session
        )

        await user_auth_service.reset_user_state(user, session)

        access_token = create_jwt_token(id=user.id)
        refresh_token = create_jwt_token(id=user.id, type=settings.COOKIE_REFRESH_NAME)
        set_auth_cookies(response, access_token, refresh_token)

        return {
            "message": _("Login successful."),
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
        logger.error(f"Failed to verify login otp request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": _("Failed to verify login OTP request."),
                "action": _("Please try again later."),
            },
        )
