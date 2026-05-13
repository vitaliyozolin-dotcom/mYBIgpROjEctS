from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.payment import PaymentQueue, PaymentStatus
from app.schemas.payment import (
    PaymentQueueCreate,
    PaymentQueueRead,
    PaymentQueueUpdate,
)

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("", response_model=list[PaymentQueueRead])
async def list_payments(
    company_id: int | None = None,
    status_filter: PaymentStatus | None = None,
    priority: int | None = None,
    due_before: date | None = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PaymentQueue)
    if company_id is not None:
        stmt = stmt.where(PaymentQueue.company_id == company_id)
    if status_filter:
        stmt = stmt.where(PaymentQueue.status == status_filter)
    if priority is not None:
        stmt = stmt.where(PaymentQueue.priority == priority)
    if due_before:
        stmt = stmt.where(PaymentQueue.due_date <= due_before)
    stmt = stmt.order_by(
        PaymentQueue.priority.asc(),
        PaymentQueue.due_date.asc().nulls_last(),
        PaymentQueue.id.desc(),
    ).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{payment_id}", response_model=PaymentQueueRead)
async def get_payment(payment_id: int, db: AsyncSession = Depends(get_db)):
    payment = await db.get(PaymentQueue, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    return payment


@router.post("", response_model=PaymentQueueRead, status_code=status.HTTP_201_CREATED)
async def create_payment(payload: PaymentQueueCreate, db: AsyncSession = Depends(get_db)):
    payment = PaymentQueue(**payload.model_dump())
    db.add(payment)
    await db.flush()
    await db.refresh(payment)
    return payment


@router.patch("/{payment_id}", response_model=PaymentQueueRead)
async def update_payment(
    payment_id: int,
    payload: PaymentQueueUpdate,
    db: AsyncSession = Depends(get_db),
):
    payment = await db.get(PaymentQueue, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(payment, key, value)

    if data.get("status") == PaymentStatus.PAID and payment.paid_at is None:
        payment.paid_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(payment)
    return payment


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(payment_id: int, db: AsyncSession = Depends(get_db)):
    payment = await db.get(PaymentQueue, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    await db.delete(payment)
    return None
