import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Bank(str, enum.Enum):
    TOCHKA = "tochka"
    TBANK = "tbank"
    ALFA = "alfa"


class AccountType(str, enum.Enum):
    MAIN = "main"
    TAX = "tax"
    DBP = "dbp"
    CASH = "cash"
    RESERVE = "reserve"


class Account(Base):
    """Банковские счета компаний."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bank: Mapped[Bank | None] = mapped_column(
        Enum(Bank, name="bank_enum"), nullable=True, index=True
    )
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, name="account_type_enum"),
        default=AccountType.MAIN,
        nullable=False,
    )
    account_number: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship(back_populates="accounts")  # noqa: F821
    balances: Mapped[list["Balance"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Account {self.name} bank={self.bank.value}>"
