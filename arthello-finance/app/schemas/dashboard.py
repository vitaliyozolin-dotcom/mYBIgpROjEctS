from decimal import Decimal

from pydantic import BaseModel


class CompanySummary(BaseModel):
    company_id: int
    company_name: str
    accounts_count: int
    total_balance: Decimal
    pending_payments: Decimal
    overdue_payments: Decimal


class DashboardSummary(BaseModel):
    total_balance: Decimal
    accounts_count: int
    total_pending: Decimal
    total_overdue: Decimal
    by_company: list[CompanySummary]
