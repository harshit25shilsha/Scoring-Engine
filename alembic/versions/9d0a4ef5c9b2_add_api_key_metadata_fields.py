"""Add API key metadata fields

Revision ID: 9d0a4ef5c9b2
Revises: fa9eac278162
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9d0a4ef5c9b2'
down_revision: Union[str, Sequence[str], None] = '9c2f4b6d8a1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('api_keys', sa.Column('key_prefix', sa.String(length=12), nullable=True))
    op.add_column('api_keys', sa.Column('status', sa.String(length=20), nullable=True, server_default='active'))
    op.add_column('api_keys', sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE api_keys SET key_prefix = substr(key_hash, 1, 8) WHERE key_prefix IS NULL")
    op.execute("UPDATE api_keys SET status = 'active' WHERE status IS NULL")

    op.alter_column('api_keys', 'key_prefix', nullable=False)
    op.alter_column('api_keys', 'status', nullable=False)

    op.create_index(op.f('ix_api_keys_key_prefix'), 'api_keys', ['key_prefix'], unique=False)
    op.create_index(op.f('ix_api_keys_status'), 'api_keys', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_api_keys_status'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_key_prefix'), table_name='api_keys')
    op.drop_column('api_keys', 'revoked_at')
    op.drop_column('api_keys', 'status')
    op.drop_column('api_keys', 'key_prefix')
