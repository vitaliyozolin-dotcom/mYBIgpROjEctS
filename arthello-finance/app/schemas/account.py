from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.account import AccountType


class AccountBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    legal_entity: str = Field(..., min_length=1, max_length=255)
    bank_name: str | None = Field(None, max_length=255)
    account_number: str | None = Field(None, max_length=64)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    type: AccountType = AccountType.BANK


class AccountCreate(AccountBase):
    balance: Decimal = Field(default=Decimal("0.00"), ge=0)


class AccountUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    bank_name: str | None = Field(None, max_length=255)
    balance: Decimal | None = None
    is_active: bool | None = None


class AccountRead(AccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime
