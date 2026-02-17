import uuid
from datetime import datetime
from sqlmodel import Field, Column
from pydantic import computed_field
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy import func, text
from backend.app.auth.schema import BaseUserSchema, RoleChoicesSchema
from backend.app.core.config import settings


class User(BaseUserSchema, table=True):
    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
        ),
        default_factory=uuid.uuid4,
    )
    hashed_password: str
    failed_login_attempts: int = Field(default=0, sa_type=pg.SMALLINT)
    last_failed_login: datetime | None = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True))
    )
    otp: str = Field(max_length=6, default="")
    otp_expiary_time: datetime | None = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True))
    )
    preferred_language: str = Field(
        default=settings.DEFAULT_LANGUAGE,
        max_length=5,
        description="User's preferred language (ISO 639-1 code)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(),
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            onupdate=func.current_timestamp(),
        ),
    )

    @computed_field
    @property
    def full_name(self) -> str:
        full_name = f"{self.first_name} {self.middle_name + ' ' if self.middle_name else ''}{self.last_name}"
        return full_name.title().strip()

    def has_role(self, role: RoleChoicesSchema) -> bool:
        return self.role.value == role.value
