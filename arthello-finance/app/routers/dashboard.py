from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.models.payment import Payment, PaymentStatus
from app.schemas.dashboard import DashboardSummary, LegalEntitySummary

router = APIRouter(tags=["dashboard"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


async def _build_summary(db: AsyncSession) -> DashboardSummary:
    accounts_result = await db.execute(select(Account).where(Account.is_active.is_(True)))
    accounts = accounts_result.scalars().all()

    payments_result = await db.execute(select(Payment))
    payments = payments_result.scalars().all()

    today = date.today()
    first_of_month = today.replace(day=1)

    by_entity_balance: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    by_entity_count: dict[str, int] = defaultdict(int)
    for acc in accounts:
        by_entity_balance[acc.legal_entity] += acc.balance
        by_entity_count[acc.legal_entity] += 1

    by_entity_pending: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    by_entity_overdue: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))

    total_pending = Decimal("0.00")
    total_overdue = Decimal("0.00")
    total_paid_month = Decimal("0.00")

    for p in payments:
        if p.status == PaymentStatus.PENDING:
            total_pending += p.amount
            by_entity_pending[p.legal_entity] += p.amount
            if p.due_date and p.due_date < today:
                total_overdue += p.amount
                by_entity_overdue[p.legal_entity] += p.amount
        elif p.status == PaymentStatus.OVERDUE:
            total_overdue += p.amount
            by_entity_overdue[p.legal_entity] += p.amount
        elif p.status == PaymentStatus.PAID and p.paid_date and p.paid_date >= first_of_month:
            total_paid_month += p.amount

    entities = sorted(set(by_entity_balance) | set(by_entity_pending))
    by_legal_entity = [
        LegalEntitySummary(
            legal_entity=e,
            accounts_count=by_entity_count.get(e, 0),
            total_balance=by_entity_balance.get(e, Decimal("0.00")),
            pending_payments=by_entity_pending.get(e, Decimal("0.00")),
            overdue_payments=by_entity_overdue.get(e, Decimal("0.00")),
        )
        for e in entities
    ]

    total_balance = sum((a.balance for a in accounts), Decimal("0.00"))

    return DashboardSummary(
        total_balance=total_balance,
        accounts_count=len(accounts),
        total_pending=total_pending,
        total_overdue=total_overdue,
        total_paid_this_month=total_paid_month,
        by_legal_entity=by_legal_entity,
    )


@router.get("/api/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    return await _build_summary(db)


@router.get("/api/dashboard/upcoming", response_model=list[dict])
async def upcoming_payments(days: int = 14, db: AsyncSession = Depends(get_db)):
    from datetime import timedelta

    horizon = date.today() + timedelta(days=days)
    stmt = (
        select(Payment)
        .where(Payment.status == PaymentStatus.PENDING)
        .where(Payment.due_date <= horizon)
        .order_by(Payment.due_date.asc().nulls_last())
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [
        {
            "id": p.id,
            "counterparty": p.counterparty,
            "legal_entity": p.legal_entity,
            "amount": float(p.amount),
            "due_date": p.due_date.isoformat() if p.due_date else None,
            "purpose": p.purpose,
        }
        for p in items
    ]


@router.get("/", response_class=HTMLResponse)
async def dashboard_view(request: Request, db: AsyncSession = Depends(get_db)):
    summary = await _build_summary(db)
    accounts_count_total_q = await db.execute(select(func.count(Account.id)))
    accounts_total = accounts_count_total_q.scalar() or 0
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "summary": summary,
            "accounts_total": accounts_total,
        },
    )
