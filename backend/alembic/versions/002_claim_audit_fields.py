"""Add claim provenance and evidence-quality fields.

Revision ID: 002
Revises: 001
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("claims", sa.Column("source_pages", sa.JSON(), nullable=True))
    op.add_column("claims", sa.Column("claim_basis", sa.String(32), nullable=True))
    op.add_column("claims", sa.Column("claim_kind", sa.String(32), nullable=True))
    op.add_column("assessments", sa.Column("evidence_relevance", sa.Float(), nullable=True))
    op.add_column("assessments", sa.Column("evidence_sufficiency", sa.Float(), nullable=True))
    op.execute("UPDATE assessments SET evidence_relevance = 0 WHERE evidence_relevance IS NULL")
    op.execute("UPDATE assessments SET evidence_sufficiency = 0 WHERE evidence_sufficiency IS NULL")


def downgrade() -> None:
    op.drop_column("assessments", "evidence_sufficiency")
    op.drop_column("assessments", "evidence_relevance")
    op.drop_column("claims", "claim_kind")
    op.drop_column("claims", "claim_basis")
    op.drop_column("claims", "source_pages")
