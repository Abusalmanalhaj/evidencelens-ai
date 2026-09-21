"""Add evidence page and verification provenance fields."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("evidence_pages", sa.JSON(), nullable=True))
    op.add_column("assessments", sa.Column("source_page_verified", sa.Boolean(), nullable=True))
    op.add_column("assessments", sa.Column("verification_status", sa.String(32), nullable=True))
    op.execute("UPDATE assessments SET source_page_verified = 0 WHERE source_page_verified IS NULL")
    op.execute("UPDATE assessments SET verification_status = 'deck_only' WHERE verification_status IS NULL")


def downgrade() -> None:
    op.drop_column("assessments", "verification_status")
    op.drop_column("assessments", "source_page_verified")
    op.drop_column("assessments", "evidence_pages")
