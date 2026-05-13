from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.payment import PaymentStatus


class PaymentQueueBase(BaseModel):
    company_id: int
    counterparty: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    due_date: date | None = None
    priority: int = Field(default=3, ge=1, le=4)
    notes: str | None = None


class PaymentQueueCreate(PaymentQueueBase):
    status: PaymentStatus = PaymentStatus.PENDING


class PaymentQueueUpdate(BaseModel):
    status: PaymentStatus | None = None
    priority: int | None = Field(None, ge=1, le=4)
    amount: Decimal | None = Field(None, gt=0)
    due_date: date | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    paid_at: datetime | None = None
    notes: str | None = None


class PaymentQueueRead(PaymentQueueBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: PaymentStatus
    approved_by: str | None
    approved_at: datetime | None
    paid_at: datetime | None
    created_at: datetime
