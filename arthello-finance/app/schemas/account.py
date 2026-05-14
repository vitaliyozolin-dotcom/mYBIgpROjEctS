from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.account import AccountType, Bank


class AccountBase(BaseModel):
    company_id: int
    bank: Bank | None = None
    account_type: AccountType = AccountType.MAIN
    account_number: str | None = Field(None, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)


class AccountCreate(AccountBase):
    is_active: bool = True


class AccountUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    account_number: str | None = Field(None, max_length=64)
    is_active: bool | None = None


class AccountRead(AccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
