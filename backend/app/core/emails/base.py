from backend.app.core.emails.config import TEMPLATES_DIR
from jinja2 import Environment, FileSystemLoader
from backend.app.core.logging import get_logger
from backend.app.core.emails.tasks import send_email_task

logger = get_logger()

email_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=True,
)

class EmailTemplate:
    template_name: str
    template_name_plain: str
    subject: str

    @classmethod
    async def send_email(
        cls, email_to: str | list[str], context: dict, subject_override: str | None = None
    ) -> None:
        try:
            recipients_list = [email_to] if isinstance(email_to, str) else email_to
            if not cls.template_name or not cls.template_name_plain:
                raise ValueError("Template names must be defined in the subclass.")
            html_template = email_env.get_template(cls.template_name)
            plain_template = email_env.get_template(cls.template_name_plain)
            html_content = html_template.render(**context)
            plain_content = plain_template.render(**context)
            task = send_email_task.delay(
                recipients=recipients_list,
                subject=subject_override or cls.subject,
                html_content=html_content,
                plain_content=plain_content,
            )
            logger.info(f"Email task queued for {recipients_list} with subject '{subject_override or cls.subject}'")
        except Exception as e:
            logger.error(f"Failed to queue email task for {recipients_list}: Error: {e}")