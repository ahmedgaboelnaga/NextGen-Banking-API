from backend.app.core.emails.config import TEMPLATES_DIR
from jinja2 import Environment, FileSystemLoader
from jinja2.ext import i18n as jinja2_i18n
from backend.app.core.logging import get_logger
from backend.app.core.emails.tasks import send_email_task
from backend.app.core.i18n import get_translations, get_current_language

logger = get_logger()

# Create Jinja2 environment with i18n support
email_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=True,
    extensions=[jinja2_i18n],
)


def update_jinja_translations():
    """Update Jinja2 environment with current language translations."""
    lang = get_current_language()
    translations = get_translations(lang)
    if translations:
        email_env.install_gettext_translations(translations, newstyle=True)
    else:
        email_env.install_null_translations(newstyle=True)


# Initialize with default translations
update_jinja_translations()


class EmailTemplate:
    template_name: str
    template_name_plain: str
    subject: str

    @classmethod
    async def send_email(
        cls,
        email_to: str | list[str],
        context: dict,
        subject_override: str | None = None,
    ) -> None:
        try:
            recipients_list = [email_to] if isinstance(email_to, str) else email_to
            if not cls.template_name or not cls.template_name_plain:
                raise ValueError("Template names must be defined in the subclass.")

            # Update Jinja2 with current language translations
            update_jinja_translations()

            html_template = email_env.get_template(cls.template_name)
            plain_template = email_env.get_template(cls.template_name_plain)
            html_content = html_template.render(**context)
            plain_content = plain_template.render(**context)
            send_email_task.delay(
                recipients=recipients_list,
                subject=subject_override or cls.subject,
                html_content=html_content,
                plain_content=plain_content,
            )
            logger.info(
                f"Email task queued for {recipients_list} with subject '{subject_override or cls.subject}'"
            )
        except Exception as e:
            logger.error(
                f"Failed to queue email task for {recipients_list}: Error: {e}"
            )
