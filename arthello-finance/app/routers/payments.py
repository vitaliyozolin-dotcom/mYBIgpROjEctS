import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.company import Company
from app.models.dds_category import DDSCategory
from app.models.payment import PaymentQueue, PaymentStatus
from app.schemas.payment import (
    PaymentApproveBody,
    PaymentDeferBody,
    PaymentQueueCreate,
    PaymentQueueRead,
    PaymentQueueUpdate,
)
from app.services.telegram import send_message as tg_send

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("", response_model=list[PaymentQueueRead])
async def list_payments(
    status: PaymentStatus | None = None,
    priority: int | None = None,
    company_slug: str | None = None,
    due_before: date | None = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PaymentQueue)
    if company_slug is not None:
        stmt = stmt.join(Company).where(Company.slug == company_slug)
    if status is not None:
        stmt = stmt.where(PaymentQueue.status == status)
    if priority is not None:
        stmt = stmt.where(PaymentQueue.priority == priority)
    if due_before is not None:
        stmt = stmt.where(PaymentQueue.due_date <= due_before)
    stmt = stmt.order_by(
        PaymentQueue.due_date.asc().nulls_last(),
        PaymentQueue.priority.asc(),
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


@router.post("/{payment_id}/approve", response_model=PaymentQueueRead)
async def approve_payment(
    payment_id: int,
    body: PaymentApproveBody,
    db: AsyncSession = Depends(get_db),
):
    payment = await db.get(
        PaymentQueue,
        payment_id,
        options=[selectinload(PaymentQueue.company)],
    )
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")

    payment.status = PaymentStatus.APPROVED
    payment.approved_by = body.approved_by
    payment.approved_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(payment)

    dds_name = payment.dds_code or "—"
    if payment.dds_code:
        cat = await db.scalar(
            select(DDSCategory).where(DDSCategory.code == payment.dds_code)
        )
        if cat is not None:
            dds_name = cat.name

    company_name = payment.company.name if payment.company else f"company#{payment.company_id}"
    amount_fmt = f"{int(payment.amount):,}".replace(",", " ")
    text = (
        f"✅ Подтверждён: {payment.counterparty} — {amount_fmt} ₽\n"
        f"\U0001f4c1 {dds_name} | \U0001f3e2 {company_name}\n"
        f"\U0001f464 {body.approved_by}"
    )
    await tg_send(text)
    return payment


@router.post("/{payment_id}/defer", response_model=PaymentQueueRead)
async def defer_payment(
    payment_id: int,
    body: PaymentDeferBody,
    db: AsyncSession = Depends(get_db),
):
    payment = await db.get(PaymentQueue, payment_id)
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")

    base_date = payment.due_date or date.today()
    payment.due_date = base_date + timedelta(days=body.days)
    payment.status = PaymentStatus.DEFERRED
    if body.note:
        prefix = (payment.notes + "\n") if payment.notes else ""
        payment.notes = f"{prefix}[deferred +{body.days}d] {body.note}"

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
