"""payment_queue dds_code column

Revision ID: 90e4c7fca85f
Revises: 54311550a030
Create Date: 2026-05-14 11:37:24.404565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '90e4c7fca85f'
down_revision: Union[str, None] = '54311550a030'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('payment_queue', sa.Column('dds_code', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_payment_queue_dds_code'), 'payment_queue', ['dds_code'], unique=False)
    op.create_foreign_key(
        'fk_payment_queue_dds_code',
        'payment_queue', 'dds_categories',
        ['dds_code'], ['code'],
        ondelete='SET NULL',
    )

    # Backfill из notes — старый сид клал "dds=<code>" в notes
    op.execute(
        """
        UPDATE payment_queue
        SET dds_code = substring(notes FROM 'dds=([a-z0-9_]+)')
        WHERE dds_code IS NULL
          AND notes IS NOT NULL
          AND notes LIKE 'dds=%'
        """
    )


def downgrade() -> None:
    op.drop_constraint('fk_payment_queue_dds_code', 'payment_queue', type_='foreignkey')
    op.drop_index(op.f('ix_payment_queue_dds_code'), table_name='payment_queue')
    op.drop_column('payment_queue', 'dds_code')
