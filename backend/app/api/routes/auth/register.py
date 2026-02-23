from fastapi import APIRouter, status, HTTPException
from sqlalchemy.exc import IntegrityError
from backend.app.core.db import SessionDep
from backend.app.core.i18n import _
from backend.app.auth.schema import UserCreateSchema, UserReadSchema
from backend.app.api.services.user_auth import user_auth_service
from backend.app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register", response_model=UserReadSchema, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_data: UserCreateSchema, session: SessionDep
) -> UserReadSchema:
    """
    Register a new user.

    - **user_data**: The user registration data.
    - **session**: The database session.

    Returns the created user details.
    """
    try:
        # Check if the email is already registered
        if await user_auth_service.check_user_email_exists(user_data.email, session):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": _("User is already registered."),
                    "action": _("Please register with different credentials."),
                },
            )
        if await user_auth_service.check_user_id_no_exists(user_data.id_no, session):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": _("ID number is already registered."),
                    "action": _("Please register with different credentials."),
                },
            )

        new_user = await user_auth_service.create_user(user_data, session)
        logger.info(
            f"New user {new_user.email} registered successfully awaiting acivation"
        )
        return new_user

    except HTTPException as http_exc:
        await session.rollback()
        raise http_exc
    except IntegrityError as e:
        await session.rollback()
        logger.warning(f"Registration integrity error: {e}")
        if "id_no" in str(e.orig):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": _("ID number is already registered."),
                    "action": _("Please register with different credentials."),
                },
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "message": _("User is already registered."),
                "action": _(
                    "Please check your inbox for the activation email or use the resend activation link."
                ),
            },
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Error during user registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "error", "message": _("Internal server error.")},
        )
