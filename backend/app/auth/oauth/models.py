import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects import postgresql as pg
from sqlmodel import Column, Field, SQLModel


class UserProvider(SQLModel, table=True):
    """Tracks external OAuth providers linked to a user account."""

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_id",
            name="uq_user_providers_provider_provider_id",
        ),
    )

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        default_factory=uuid.uuid4,
    )
    user_uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    provider: str = Field(max_length=50)
    provider_id: str = Field(max_length=255)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )
