from datetime import datetime, timedelta
from backend.app.core.config import settings
from backend.app.core.emails.base import EmailTemplate


class AccountLockoutEmail(EmailTemplate):
    template_name = "account_lockout.html"
    template_name_plain = "account_lockout.txt"
    subject = "Account Security Alert - Temporary Lockout"


async def send_account_lockout_email(email: str, lockout_time: datetime) -> None:
    unlock_time = lockout_time + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
    context = {
        "lockout_duration": settings.LOCKOUT_DURATION_MINUTES,
        "lockout_time": lockout_time.strftime("%Y-%m-%d %H:%M:%S %Z UTC"),
        "unlock_time": unlock_time.strftime("%Y-%m-%d %H:%M:%S %Z UTC"),
        "site_name": settings.SITE_NAME,
        "support_email": settings.SUPPORT_EMAIL,
    }

    await AccountLockoutEmail.send_email(email_to=email, context=context)
