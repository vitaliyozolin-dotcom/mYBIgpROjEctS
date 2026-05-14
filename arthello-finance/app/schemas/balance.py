from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.balance import BalanceSource


class BalanceCreate(BaseModel):
    account_id: int
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    source: BalanceSource = BalanceSource.API


class BalanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    amount: Decimal
    currency: str
    recorded_at: datetime
    source: BalanceSource
