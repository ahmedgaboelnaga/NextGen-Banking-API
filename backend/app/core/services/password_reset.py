import uuid
from backend.app.core.config import settings
from backend.app.core.emails.base import EmailTemplate
from backend.app.auth.utils import create_password_reset_token


class PasswordResetEmail(EmailTemplate):
    template_name = "password_reset.html"
    template_name_plain = "password_reset.txt"
    subject = "Password Reset Request"


async def send_password_reset_email(email: str, user_id: uuid.UUID) -> None:
    reset_token = create_password_reset_token(user_id)
    reset_url = f"{settings.API_BASE_URL}{settings.API_V1_STR}/auth/reset-password?token={reset_token}"
    context = {
        "reset_url": reset_url,
        "expiry_time": settings.PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES,
        "site_name": settings.SITE_NAME,
        "support_email": settings.SUPPORT_EMAIL,
    }

    await PasswordResetEmail.send_email(email_to=email, context=context)
