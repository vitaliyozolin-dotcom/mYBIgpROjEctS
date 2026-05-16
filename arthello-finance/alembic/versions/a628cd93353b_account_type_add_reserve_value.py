"""account_type add RESERVE value

Revision ID: a628cd93353b
Revises: 7ccb961c5780
Create Date: 2026-05-16 19:06:47.118188

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a628cd93353b'
down_revision: Union[str, None] = '7ccb961c5780'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE не работает в транзакции на старых PG;
    # autocommit_block безопасен на 12+ и даёт IF NOT EXISTS.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE account_type_enum ADD VALUE IF NOT EXISTS 'RESERVE'")


def downgrade() -> None:
    # Postgres не умеет удалять значение enum. Оставляем 'RESERVE' в типе.
    pass
