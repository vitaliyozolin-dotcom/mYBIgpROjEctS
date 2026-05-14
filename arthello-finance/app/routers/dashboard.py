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
from app.models.dds_category import DDSCategory
from app.models.payment import PaymentQueue, PaymentStatus
from app.schemas.dashboard import (
    AccountBalanceItem,
    Color,
    CompanyBalanceBlock,
    DashboardSummary,
    TotalsByPriority,
    UrgentPayment,
)

router = APIRouter(tags=["dashboard"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _color_for(amount: Decimal) -> Color:
    if amount < Decimal("50000"):
        return "red"
    if amount <= Decimal("200000"):
        return "yellow"
    return "green"


def _fmt_money(value: Decimal) -> str:
    return f"{int(value):,}".replace(",", " ")


async def _latest_balances_by_account(db: AsyncSession) -> dict[int, Decimal]:
    """Последний known баланс по каждому счёту."""

    stmt = select(Balance).order_by(Balance.account_id, Balance.recorded_at.desc())
    result = await db.execute(stmt)
    latest: dict[int, Decimal] = {}
    for b in result.scalars():
        if b.account_id not in latest:
            latest[b.account_id] = b.amount
    return latest


async def build_summary(db: AsyncSession) -> DashboardSummary:
    today = date.today()

    companies_q = await db.execute(select(Company).order_by(Company.id))
    companies = companies_q.scalars().all()

    accounts_q = await db.execute(
        select(Account).where(Account.is_active.is_(True)).order_by(Account.id)
    )
    accounts = accounts_q.scalars().all()

    latest = await _latest_balances_by_account(db)

    payments_q = await db.execute(
        select(PaymentQueue)
        .where(PaymentQueue.status == PaymentStatus.PENDING)
        .order_by(PaymentQueue.due_date.asc().nulls_last(), PaymentQueue.priority.asc())
    )
    pending_payments = payments_q.scalars().all()

    dds_q = await db.execute(select(DDSCategory))
    dds_by_code: dict[str, DDSCategory] = {c.code: c for c in dds_q.scalars()}
    company_by_id: dict[int, Company] = {c.id: c for c in companies}

    accounts_by_company: dict[int, list[Account]] = defaultdict(list)
    for acc in accounts:
        accounts_by_company[acc.company_id].append(acc)

    balances_by_company: list[CompanyBalanceBlock] = []
    total_balance = Decimal("0.00")
    for c in companies:
        comp_accounts = accounts_by_company.get(c.id, [])
        items: list[AccountBalanceItem] = []
        comp_total = Decimal("0.00")
        for acc in comp_accounts:
            amount = latest.get(acc.id, Decimal("0.00"))
            items.append(
                AccountBalanceItem(
                    name=acc.name, amount=amount, color=_color_for(amount)
                )
            )
            comp_total += amount
        balances_by_company.append(
            CompanyBalanceBlock(
                company_slug=c.slug,
                company_name=c.name,
                amount=comp_total,
                accounts=items,
            )
        )
        total_balance += comp_total

    totals = {1: Decimal("0.00"), 2: Decimal("0.00"), 3: Decimal("0.00"), 4: Decimal("0.00")}
    for p in pending_payments:
        if p.priority in totals:
            totals[p.priority] += p.amount

    free_balance = total_balance - totals[1]

    urgent: list[UrgentPayment] = []
    for p in pending_payments:
        if p.priority not in (1, 2):
            continue
        days_left = (p.due_date - today).days if p.due_date else None
        overdue = days_left is not None and days_left < 0
        cat = dds_by_code.get(p.dds_code) if p.dds_code else None
        company = company_by_id.get(p.company_id)
        urgent.append(
            UrgentPayment(
                id=p.id,
                counterparty=p.counterparty,
                description=p.description,
                amount=p.amount,
                due_date=p.due_date,
                priority=p.priority,
                dds_category=p.dds_code,
                dds_category_name=cat.name if cat else None,
                company_name=company.name if company else f"company#{p.company_id}",
                company_slug=company.slug if company else None,
                days_left=days_left,
                can_pay=p.amount <= total_balance,
                overdue=overdue,
            )
        )

    alerts: list[str] = []
    if free_balance < 0:
        alerts.append(
            f"🔴 Свободный остаток отрицательный: -{_fmt_money(abs(free_balance))} ₽"
        )
    for p in urgent:
        if p.overdue:
            alerts.append(
                f"🔴 {p.counterparty} — ПРОСРОЧЕНО на {abs(p.days_left)} дн. "
                f"({_fmt_money(p.amount)} ₽)"
            )
        elif p.days_left is not None and p.days_left <= 5:
            alerts.append(
                f"⚠️ {p.counterparty} — {p.days_left} дн. до оплаты "
                f"({_fmt_money(p.amount)} ₽)"
            )

    return DashboardSummary(
        total_balance=total_balance,
        balances_by_company=balances_by_company,
        urgent_payments=urgent,
        free_balance=free_balance,
        totals_by_priority=TotalsByPriority(
            p1=totals[1], p2=totals[2], p3=totals[3], p4=totals[4]
        ),
        alerts=alerts,
    )


@router.get("/api/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    return await build_summary(db)


@router.get("/", response_class=HTMLResponse)
async def dashboard_index(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})
