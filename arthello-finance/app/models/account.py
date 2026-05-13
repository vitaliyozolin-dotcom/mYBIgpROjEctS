import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AccountType(str, enum.Enum):
    BANK = "bank"
    CASH = "cash"
    CARD = "card"
    DEPOSIT = "deposit"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    legal_entity: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, name="account_type_enum"),
        default=AccountType.BANK,
        nullable=False,
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(  # noqa: F821
        back_populates="account"
    )

    def __repr__(self) -> str:
        return f"<Account {self.legal_entity}/{self.name} balance={self.balance}>"
