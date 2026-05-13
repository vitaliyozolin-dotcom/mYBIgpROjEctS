import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentDirection(str, enum.Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class Payment(Base):
    """Платежи и кредиторская задолженность (КЗ)."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )

    counterparty: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    legal_entity: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    direction: Mapped[PaymentDirection] = mapped_column(
        Enum(PaymentDirection, name="payment_direction_enum"),
        default=PaymentDirection.OUTGOING,
        nullable=False,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum"),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)

    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    invoice_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    account: Mapped["Account | None"] = relationship(back_populates="payments")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<Payment {self.counterparty} {self.amount}{self.currency} "
            f"status={self.status.value}>"
        )
