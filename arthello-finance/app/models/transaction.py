import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TransactionDirection(str, enum.Enum):
    IN = "in"
    OUT = "out"


class Transaction(Base):
    """История транзакций из банков."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    direction: Mapped[TransactionDirection] = mapped_column(
        Enum(TransactionDirection, name="transaction_direction_enum"),
        nullable=False,
    )

    counterparty: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    dds_category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    account: Mapped["Account"] = relationship(back_populates="transactions")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<Transaction {self.direction.value} {self.amount}₽ "
            f"at {self.transaction_date:%Y-%m-%d}>"
        )
