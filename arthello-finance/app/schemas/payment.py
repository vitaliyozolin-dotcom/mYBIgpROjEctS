from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.payment import PaymentDirection, PaymentStatus


class PaymentBase(BaseModel):
    counterparty: str = Field(..., min_length=1, max_length=255)
    legal_entity: str = Field(..., min_length=1, max_length=255)
    purpose: str = Field(..., min_length=1)
    category: str | None = Field(None, max_length=128)
    direction: PaymentDirection = PaymentDirection.OUTGOING
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    due_date: date | None = None
    invoice_number: str | None = Field(None, max_length=64)
    notes: str | None = None


class PaymentCreate(PaymentBase):
    account_id: int | None = None
    status: PaymentStatus = PaymentStatus.PENDING


class PaymentUpdate(BaseModel):
    status: PaymentStatus | None = None
    paid_date: date | None = None
    amount: Decimal | None = Field(None, gt=0)
    notes: str | None = None
    account_id: int | None = None


class PaymentRead(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int | None
    status: PaymentStatus
    paid_date: date | None
    created_at: datetime
    updated_at: datetime
