from fastapi_mail import FastMail, ConnectionConfig
from pydantic import SecretStr
from pathlib import Path
from backend.app.core.config import settings

TEMPLATES_DIR = Path(__file__).parent / "templates"

email_config = ConnectionConfig(
    MAILFROM=settings.MAIL_FROM,
    MAILFROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_HOST,
    MAIL_USERNAME="",
    MAIL_PASSWORD=SecretStr(""),
    MAIL_SSL_TLS=False,
    MAIL_STARTTLS=False,
    USER_CREDENTIALS=False,
    VALIDATE_CERTS=False,
    TEMPLATE_FOLDER=TEMPLATES_DIR,
)

fastmail = FastMail(email_config)
