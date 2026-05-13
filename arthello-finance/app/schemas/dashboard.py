from decimal import Decimal

from pydantic import BaseModel


class LegalEntitySummary(BaseModel):
    legal_entity: str
    accounts_count: int
    total_balance: Decimal
    pending_payments: Decimal
    overdue_payments: Decimal


class DashboardSummary(BaseModel):
    total_balance: Decimal
    accounts_count: int
    total_pending: Decimal
    total_overdue: Decimal
    total_paid_this_month: Decimal
    by_legal_entity: list[LegalEntitySummary]
