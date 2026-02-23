import asyncio
import jwt
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from backend.app.auth.models import User
from backend.app.auth.schema import AccountStatusSchema, UserCreateSchema
from backend.app.auth.utils import (
    generate_username,
    generate_password_hash,
    verify_password_hash,
    create_activation_token,
    generate_otp,
)
from backend.app.core.services.activation_email import send_activation_email
from backend.app.core.services.login_otp import send_login_otp_email
from backend.app.core.config import settings
from backend.app.core.i18n import _
from backend.app.core.logging import get_logger

logger = get_logger()


class UserAuthService:
    async def get_user_by_email(
        self, email: str, session: AsyncSession, include_inactive: bool = False
    ) -> User | None:
        statement = select(User).where(User.email == email)

        if not include_inactive:
            statement = statement.where(User.is_active)
        result = await session.exec(statement)
        user = result.first()
        return user

    async def get_user_by_id_no(
        self, id_no: int, session: AsyncSession, include_inactive: bool = False
    ) -> User | None:
        statement = select(User).where(User.id_no == id_no)

        if not include_inactive:
            statement = statement.where(User.is_active)
        result = await session.exec(statement)
        user = result.first()
        return user

    async def get_user_by_id(
        self, user_id: uuid.UUID, session: AsyncSession, include_inactive: bool = False
    ) -> User | None:
        statement = select(User).where(User.id == user_id)

        if not include_inactive:
            statement = statement.where(User.is_active)
        result = await session.exec(statement)
        user = result.first()
        return user

    async def check_user_email_exists(self, email: str, session: AsyncSession) -> bool:
        user = await self.get_user_by_email(email=email, session=session)
        return bool(user)

    async def check_user_id_no_exists(self, id_no: int, session: AsyncSession) -> bool:
        user = await self.get_user_by_id_no(id_no=id_no, session=session)
        return bool(user)

    async def verify_user_password(
        self, plain_password: str, hashed_password: str
    ) -> bool:
        return verify_password_hash(plain_password, hashed_password)

    async def reset_user_state(
        self,
        user: User,
        session: AsyncSession,
        *,
        clear_otp: bool = True,
        log_action: bool = True,
    ) -> None:
        previous_status = user.account_status
        user.failed_login_attempts = 0
        user.last_failed_login = None

        if clear_otp:
            user.otp = ""
            user.otp_expiary_time = None

        if previous_status == AccountStatusSchema.LOCKED:
            user.account_status = AccountStatusSchema.ACTIVE

        await session.commit()
        await session.refresh(user)

        if log_action and previous_status != user.account_status:
            logger.info(
                f"User {user.email} account status changed from {previous_status} to {user.account_status}"
            )

    async def validate_user_status(self, user: User) -> None:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": _("Account is not active"),
                    "action": _(
                        "Please activate your account using the link sent to your email."
                    ),
                },
            )
        if user.account_status == AccountStatusSchema.LOCKED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": "error",
                    "message": _("Account is locked"),
                    "action": _("Please contact support to unlock your account."),
                },
            )
        if user.account_status == AccountStatusSchema.INACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": _("Account is inactive"),
                    "action": _("Please contact support to activate your account."),
                },
            )

    async def generate_and_save_otp(
        self, user: User, session: AsyncSession
    ) -> tuple[bool, str]:
        try:
            otp = generate_otp()
            user.otp = otp
            user.otp_expiary_time = datetime.now(timezone.utc) + timedelta(
                minutes=settings.OTP_EXPIRATION_MINUTES
            )

            await session.commit()
            await session.refresh(user)

            for attempt in range(3):
                try:
                    await send_login_otp_email(email=user.email, otp=otp)
                    logger.info(f"OTP generated and sent to {user.email}")
                    return True, otp
                except Exception as e:
                    logger.error(f"Failed to send OTP email to {user.email}: {e}")
                    if attempt < 2:
                        logger.info(
                            f"Retrying to send OTP email to {user.email} (Attempt {attempt + 2}/3)"
                        )
                    else:
                        user.otp = ""
                        user.otp_expiary_time = None
                        await session.commit()
                        await session.refresh(user)
                        logger.error(
                            f"All attempts to send OTP email to {user.email} have failed."
                        )
                        return False, ""
                    await asyncio.sleep(2**attempt)
            return False, ""

        except Exception as e:
            logger.error(f"Failed to generate and save OTP: {e}")
            return (
                False,
                "An error occurred while generating OTP. Please try again later.",
            )

    async def create_user(
        self, user_data: UserCreateSchema, session: AsyncSession
    ) -> User:
        user_data_dict = user_data.model_dump(
            exclude={
                "confirm_password",
                "username",
                "is_active",
                "account_status",
            }
        )

        password = user_data_dict.pop("password")
        user_data_dict["hashed_password"] = generate_password_hash(password)
        user_data_dict["username"] = generate_username()

        new_user = User(
            **user_data_dict,
            is_active=False,
            account_status=AccountStatusSchema.PENDING,
        )

        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        activation_token = create_activation_token(new_user.id)
        try:
            await send_activation_email(email=new_user.email, token=activation_token)
            logger.info(f"Activation email sent to {new_user.email}")
        except Exception as e:
            logger.error(f"Failed to send activation email to {new_user.email}: {e}")
            raise

        return new_user

    async def activate_user_account(self, token: str, session: AsyncSession) -> User:
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            if payload.get("type") != "activation":
                raise ValueError("Invalid token type")

            user_id = uuid.UUID(payload.get("user_id"))

            user = await self.get_user_by_id(
                user_id=user_id, session=session, include_inactive=True
            )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "status": "error",
                        "message": _("User not found"),
                        "action": _(
                            "Please check the activation link or contact support."
                        ),
                    },
                )
            if user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "error",
                        "message": _("User already activated"),
                        "action": _("You can log in with your credentials."),
                    },
                )
            await self.reset_user_state(
                user=user, session=session, clear_otp=True, log_action=True
            )
            user.is_active = True
            user.account_status = AccountStatusSchema.ACTIVE
            await session.commit()
            await session.refresh(user)

            return user
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": _("Activation token expired"),
                    "action": _("Please request a new activation email."),
                },
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": _("Invalid activation token"),
                },
            )
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Failed to activate user account: {e}")
            raise

    async def verify_login_otp(
        self, email: str, otp: str, session: AsyncSession
    ) -> User:
        try:
            user = await self.get_user_by_email(email=email, session=session)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "status": "error",
                        "message": _("Invalid credentials"),
                    },
                )
            await self.validate_user_status(user)

            await self.check_user_lockout(user, session)

            if not user.otp or user.otp != otp:
                await self.increment_failed_login_attempts(user, session)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "error",
                        "message": _("Invalid OTP"),
                        "action": _("Please check your OTP and try again."),
                    },
                )

            if not user.otp_expiary_time or user.otp_expiary_time < datetime.now(
                timezone.utc
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "error",
                        "message": _("Expired OTP"),
                        "action": _("Please request a new OTP and try again."),
                    },
                )

            await self.reset_user_state(user, session, clear_otp=False)

            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to verify login OTP: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "status": "error",
                    "message": _("An unexpected error occurred while verifying OTP."),
                    "action": _("Please try again later."),
                },
            )

    async def check_user_lockout(self, user: User, session: AsyncSession) -> None:
        if user.account_status != AccountStatusSchema.LOCKED:
            return

        if user.last_failed_login is None:
            return

        lockout_time = user.last_failed_login + timedelta(
            minutes=settings.LOCKOUT_DURATION_MINUTES
        )

        current_time = datetime.now(timezone.utc)

        if current_time >= lockout_time:
            await self.reset_user_state(user, session, clear_otp=False)
            logger.info(f"Lockout period ended for user {user.email}")
            return

        remaining_minutes = int((lockout_time - current_time).total_seconds() / 60)
        logger.warning(f"Attempted login for a locked account: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "message": _("Your account is temporarily locked"),
                "action": _(
                    "Please try again after {remaining_minutes} minutes.",
                    remaining_minutes=remaining_minutes,
                ),
                "lockout_remaining_minutes": remaining_minutes,
            },
        )

    async def increment_failed_login_attempts(
        self, user: User, session: AsyncSession
    ) -> None:
        user.failed_login_attempts += 1
        user.last_failed_login = datetime.now(timezone.utc)

        if user.failed_login_attempts >= settings.LOGIN_ATTEMPTS:
            user.account_status = AccountStatusSchema.LOCKED
            logger.warning(
                f"User {user.email} account locked due to too many failed login attempts."
            )
        await session.commit()
        await session.refresh(user)


user_auth_service = UserAuthService()
