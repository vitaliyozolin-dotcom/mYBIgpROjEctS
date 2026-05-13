import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TransactionKind(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    FEE = "fee"
    TRANSFER = "transfer"


class Transaction(Base):
    """Банковские транзакции / движение по счёту."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    external_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )

    kind: Mapped[TransactionKind] = mapped_column(
        Enum(TransactionKind, name="transaction_kind_enum"),
        default=TransactionKind.DEBIT,
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    balance_after: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    counterparty: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    counterparty_inn: Mapped[str | None] = mapped_column(String(16), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    account: Mapped["Account"] = relationship(back_populates="transactions")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<Transaction {self.kind.value} {self.amount}{self.currency} "
            f"at {self.occurred_at:%Y-%m-%d}>"
        )
