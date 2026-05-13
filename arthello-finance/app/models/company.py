import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CompanyType(str, enum.Enum):
    OOO = "OOO"
    IP = "IP"


class Company(Base):
    """Юридические лица группы ARTHELLO."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    type: Mapped[CompanyType] = mapped_column(
        Enum(CompanyType, name="company_type_enum"),
        default=CompanyType.OOO,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    accounts: Mapped[list["Account"]] = relationship(  # noqa: F821
        back_populates="company", cascade="all, delete-orphan"
    )
    payments: Mapped[list["PaymentQueue"]] = relationship(  # noqa: F821
        back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Company {self.name} ({self.type.value})>"
