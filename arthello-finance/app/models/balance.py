import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BalanceSource(str, enum.Enum):
    API = "api"
    MANUAL = "manual"


class Balance(Base):
    """История остатков по счетам."""

    __tablename__ = "balances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    source: Mapped[BalanceSource] = mapped_column(
        Enum(BalanceSource, name="balance_source_enum"),
        default=BalanceSource.API,
        nullable=False,
    )

    account: Mapped["Account"] = relationship(back_populates="balances")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Balance account={self.account_id} {self.amount}{self.currency}>"
