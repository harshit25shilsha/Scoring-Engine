"""add embeddings columns via pgvector
Revision ID: 7d855c53f60c
Revises: 4239acaa891b
Create Date: 2026-07-23 12:51:20.527844
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision: str = '7d855c53f60c'
down_revision: Union[str, Sequence[str], None] = '4239acaa891b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('job_processed', sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=True))
    op.add_column('resume_processed', sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('resume_processed', 'embedding')
    op.drop_column('job_processed', 'embedding')