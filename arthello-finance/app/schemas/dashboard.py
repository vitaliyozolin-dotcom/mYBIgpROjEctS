from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

Color = Literal["green", "yellow", "red"]


class AccountBalanceItem(BaseModel):
    name: str
    amount: Decimal
    color: Color


class CompanyBalanceBlock(BaseModel):
    company_slug: str | None
    company_name: str
    amount: Decimal
    accounts: list[AccountBalanceItem]


class UrgentPayment(BaseModel):
    id: int
    counterparty: str
    description: str
    amount: Decimal
    due_date: date | None
    priority: int
    dds_category: str | None
    dds_category_name: str | None
    company_name: str
    company_slug: str | None
    days_left: int | None
    can_pay: bool
    overdue: bool


class TotalsByPriority(BaseModel):
    p1: Decimal
    p2: Decimal
    p3: Decimal
    p4: Decimal


class DashboardSummary(BaseModel):
    total_balance: Decimal
    balances_by_company: list[CompanyBalanceBlock]
    urgent_payments: list[UrgentPayment]
    free_balance: Decimal
    totals_by_priority: TotalsByPriority
    alerts: list[str]
