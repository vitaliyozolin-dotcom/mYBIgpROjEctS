"""oauth_tokens table

Revision ID: 7ccb961c5780
Revises: 90e4c7fca85f
Create Date: 2026-05-15 11:45:29.713985

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


revision: str = '7ccb961c5780'
down_revision: Union[str, None] = '90e4c7fca85f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Тип bank_enum уже создан в init_schema — переиспользуем,
# а не пытаемся создать заново.
_bank_enum = ENUM('TOCHKA', 'TBANK', 'ALFA', name='bank_enum', create_type=False)


def upgrade() -> None:
    op.create_table('oauth_tokens',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('bank', _bank_enum, nullable=False),
    sa.Column('access_token', sa.Text(), nullable=False),
    sa.Column('refresh_token', sa.Text(), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('scope', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('company_id', 'bank', name='uq_oauth_tokens_company_bank')
    )
    op.create_index(op.f('ix_oauth_tokens_bank'), 'oauth_tokens', ['bank'], unique=False)
    op.create_index(op.f('ix_oauth_tokens_company_id'), 'oauth_tokens', ['company_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_oauth_tokens_company_id'), table_name='oauth_tokens')
    op.drop_index(op.f('ix_oauth_tokens_bank'), table_name='oauth_tokens')
    op.drop_table('oauth_tokens')
