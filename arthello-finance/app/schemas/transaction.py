from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.transaction import TransactionKind


class TransactionBase(BaseModel):
    account_id: int
    kind: TransactionKind = TransactionKind.DEBIT
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    counterparty: str | None = Field(None, max_length=255)
    counterparty_inn: str | None = Field(None, max_length=16)
    description: str | None = None
    occurred_at: datetime


class TransactionCreate(TransactionBase):
    external_id: str | None = Field(None, max_length=128)
    balance_after: Decimal | None = None


class TransactionRead(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str | None
    balance_after: Decimal | None
    created_at: datetime
