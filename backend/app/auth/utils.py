import random
import string
import uuid
import jwt
from datetime import datetime, timedelta, timezone

from fastapi import Response
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from backend.app.core.config import settings

_ph = PasswordHasher()


def generate_otp(length=6) -> str:
    """Generate a random OTP of specified length."""
    return "".join(random.choices(string.digits, k=length))


def generate_password_hash(password: str) -> str:
    """Hash the password using Argon2."""
    return _ph.hash(password)


def verify_password_hash(password: str, hashed_password: str) -> bool:
    """Verify the password against the hashed password."""
    try:
        return _ph.verify(hashed_password, password)
    except VerifyMismatchError:
        return False


def generate_username() -> str:
    """Generate a random username."""
    bank_name = settings.SITE_NAME
    words = bank_name.split()
    prefix = "".join([word[0] for word in words]).upper()
    remaining_length = 12 - len(prefix) - 1
    random_string = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=remaining_length)
    )
    return f"{prefix}-{random_string}"


def create_activation_token(id: uuid.UUID) -> str:
    """Generate a JWT activation token."""
    payload = {
        "id": str(id),
        "type": "activation",
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.ACTIVATION_TOKEN_EXPIRATION_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return token


def create_jwt_token(id: uuid.UUID, type: str = settings.COOKIE_ACCESS_NAME) -> str:
    expire_minutes = (
        settings.JWT_ACCESS_TOKEN_EXPIRATION_MINUTES
        if type == settings.COOKIE_ACCESS_NAME
        else settings.JWT_REFRESH_TOKEN_EXPIRATION_DAYS * 24 * 60
    )
    payload = {
        "id": str(id),
        "type": type,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expire_minutes),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return token


def set_auth_cookies(
    response: Response, access_token: str, refresh_token: str | None = None
) -> None:
    cookie_settings = {
        "path": settings.COOKIE_PATH,
        "secure": settings.COOKIE_SECURE,
        "httponly": settings.COOKIE_HTTP_ONLY,
        "samesite": settings.COOKIE_SAME_SITE,
    }
    access_cookie_settings = cookie_settings.copy()
    access_cookie_settings["max_age"] = (
        settings.JWT_ACCESS_TOKEN_EXPIRATION_MINUTES * 60
    )
    response.set_cookie(
        key=settings.COOKIE_ACCESS_NAME,
        value=access_token,
        **access_cookie_settings,
    )
    if refresh_token:
        refresh_cookie_settings = cookie_settings.copy()
        refresh_cookie_settings["max_age"] = (
            settings.JWT_REFRESH_TOKEN_EXPIRATION_DAYS * 24 * 60 * 60
        )
        response.set_cookie(
            key=settings.COOKIE_REFRESH_NAME,
            value=refresh_token,
            **refresh_cookie_settings,
        )

    logged_in_cookie_settings = cookie_settings.copy()
    logged_in_cookie_settings["httponly"] = False
    logged_in_cookie_settings["max_age"] = (
        settings.JWT_ACCESS_TOKEN_EXPIRATION_MINUTES * 60
    )
    response.set_cookie(
        key=settings.COOKIE_LOGGED_IN_NAME,
        value="true",
        **logged_in_cookie_settings,
    )


def delete_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=settings.COOKIE_ACCESS_NAME, path=settings.COOKIE_PATH)
    response.delete_cookie(key=settings.COOKIE_REFRESH_NAME, path=settings.COOKIE_PATH)
    response.delete_cookie(
        key=settings.COOKIE_LOGGED_IN_NAME, path=settings.COOKIE_PATH
    )


def create_password_reset_token(id: uuid.UUID) -> str:
    """Generate a JWT password reset token."""
    payload = {
        "id": str(id),
        "type": "password_reset",
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return token
