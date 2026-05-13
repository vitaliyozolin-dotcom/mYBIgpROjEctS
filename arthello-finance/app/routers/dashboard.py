from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.models.balance import Balance
from app.models.company import Company
from app.models.payment import PaymentQueue, PaymentStatus
from app.schemas.dashboard import CompanySummary, DashboardSummary

router = APIRouter(tags=["dashboard"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


async def _latest_balances_by_account(db: AsyncSession) -> dict[int, Decimal]:
    """Последний известный остаток для каждого счёта."""

    stmt = select(Balance).order_by(Balance.account_id, Balance.recorded_at.desc())
    result = await db.execute(stmt)
    latest: dict[int, Decimal] = {}
    for b in result.scalars():
        if b.account_id not in latest:
            latest[b.account_id] = b.amount
    return latest


async def _build_summary(db: AsyncSession) -> DashboardSummary:
    companies_q = await db.execute(select(Company).order_by(Company.id))
    companies = companies_q.scalars().all()

    accounts_q = await db.execute(
        select(Account).where(Account.is_active.is_(True))
    )
    accounts = accounts_q.scalars().all()

    payments_q = await db.execute(select(PaymentQueue))
    payments = payments_q.scalars().all()

    latest = await _latest_balances_by_account(db)
    today = date.today()

    by_company_balance: dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
    by_company_accounts: dict[int, int] = defaultdict(int)
    for acc in accounts:
        by_company_balance[acc.company_id] += latest.get(acc.id, Decimal("0.00"))
        by_company_accounts[acc.company_id] += 1

    by_company_pending: dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
    by_company_overdue: dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
    total_pending = Decimal("0.00")
    total_overdue = Decimal("0.00")
    for p in payments:
        if p.status == PaymentStatus.PAID:
            continue
        total_pending += p.amount
        by_company_pending[p.company_id] += p.amount
        if p.due_date and p.due_date < today:
            total_overdue += p.amount
            by_company_overdue[p.company_id] += p.amount

    by_company = [
        CompanySummary(
            company_id=c.id,
            company_name=c.name,
            accounts_count=by_company_accounts.get(c.id, 0),
            total_balance=by_company_balance.get(c.id, Decimal("0.00")),
            pending_payments=by_company_pending.get(c.id, Decimal("0.00")),
            overdue_payments=by_company_overdue.get(c.id, Decimal("0.00")),
        )
        for c in companies
    ]

    total_balance = sum(latest.values(), Decimal("0.00"))

    return DashboardSummary(
        total_balance=total_balance,
        accounts_count=len(accounts),
        total_pending=total_pending,
        total_overdue=total_overdue,
        by_company=by_company,
    )


@router.get("/api/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    return await _build_summary(db)


@router.get("/", response_class=HTMLResponse)
async def dashboard_view(request: Request, db: AsyncSession = Depends(get_db)):
    summary = await _build_summary(db)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "summary": summary},
    )
