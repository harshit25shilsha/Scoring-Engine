"""Track the admin that created each API key.

Revision ID: b7e4c2a1d9f0
Revises: 9d0a4ef5c9b2
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e4c2a1d9f0"
down_revision: Union[str, Sequence[str], None] = "9d0a4ef5c9b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("created_by_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_api_keys_created_by_id"), "api_keys", ["created_by_id"], unique=False)
    op.create_foreign_key(
        "fk_api_keys_created_by_id",
        "api_keys",
        "api_keys",
        ["created_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_api_keys_created_by_id", "api_keys", type_="foreignkey")
    op.drop_index(op.f("ix_api_keys_created_by_id"), table_name="api_keys")
    op.drop_column("api_keys", "created_by_id")