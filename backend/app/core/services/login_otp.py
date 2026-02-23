from backend.app.core.config import settings
from backend.app.core.emails.base import EmailTemplate


class LoginOTPEmail(EmailTemplate):
    template_name = "login_otp.html"
    template_name_plain = "login_otp.txt"
    subject = "Your Login OTP Code"


async def send_login_otp_email(email: str, otp: str) -> None:
    context = {
        "otp": otp,
        "expiry_time": settings.OTP_EXPIRATION_MINUTES,
        "site_name": settings.SITE_NAME,
        "support_email": settings.SUPPORT_EMAIL,
    }
    await LoginOTPEmail.send_email(email_to=email, context=context)
