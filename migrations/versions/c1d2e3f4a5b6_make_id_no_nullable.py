"""make_id_no_nullable

Make ``user.id_no`` nullable so that Google OAuth users can be created
without a national ID.  The field is collected later during KYC
(Know Your Customer).  Direct registrations still require it because
``UserCreateSchema`` overrides the field to be non-nullable at the API layer.

Revision ID: c1d2e3f4a5b6
Revises: aad4cbf2eb88
Create Date: 2026-02-27 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "aad4cbf2eb88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("user", "id_no", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    # WARNING: fails if any row has id_no = NULL.
    # Backfill or delete those rows before running downgrade.
    op.alter_column("user", "id_no", existing_type=sa.Integer(), nullable=False)
