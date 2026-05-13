from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import PaymentCreate, PaymentRead, PaymentUpdate

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("", response_model=list[PaymentRead])
async def list_payments(
    legal_entity: str | None = None,
    status_filter: PaymentStatus | None = None,
    due_before: date | None = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Payment)
    if legal_entity:
        stmt = stmt.where(Payment.legal_entity == legal_entity)
    if status_filter:
        stmt = stmt.where(Payment.status == status_filter)
    if due_before:
        stmt = stmt.where(Payment.due_date <= due_before)
    stmt = stmt.order_by(Payment.due_date.asc().nulls_last(), Payment.id.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(payment_id: int, db: AsyncSession = Depends(get_db)):
    payment = await db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    return payment


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(payload: PaymentCreate, db: AsyncSession = Depends(get_db)):
    payment = Payment(**payload.model_dump())
    db.add(payment)
    await db.flush()
    await db.refresh(payment)
    return payment


@router.patch("/{payment_id}", response_model=PaymentRead)
async def update_payment(
    payment_id: int,
    payload: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
):
    payment = await db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(payment, key, value)

    if data.get("status") == PaymentStatus.PAID and payment.paid_date is None:
        payment.paid_date = date.today()

    await db.flush()
    await db.refresh(payment)
    return payment


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(payment_id: int, db: AsyncSession = Depends(get_db)):
    payment = await db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    await db.delete(payment)
    return None
