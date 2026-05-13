from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.transaction import TransactionDirection


class TransactionBase(BaseModel):
    account_id: int
    external_id: str = Field(..., min_length=1, max_length=128)
    amount: Decimal = Field(..., gt=0)
    direction: TransactionDirection
    counterparty: str | None = Field(None, max_length=255)
    purpose: str | None = None
    dds_category: str | None = Field(None, max_length=128)
    transaction_date: datetime


class TransactionCreate(TransactionBase):
    pass


class TransactionRead(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    imported_at: datetime
