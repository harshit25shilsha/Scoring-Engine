"""add score evidence field

Revision ID: 9c2f4b6d8a1e
Revises: ddb481e3b766
Create Date: 2026-08-17 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c2f4b6d8a1e'
down_revision: Union[str, Sequence[str], None] = 'ddb481e3b766'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('candidate_job_scores', sa.Column('evidence', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('candidate_job_scores', 'evidence')
