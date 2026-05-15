from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.account import Bank


class OAuthToken(Base):
    """OAuth-токены доступа к банковским API.

    Уникальный токен на пару (company_id, bank): при повторной авторизации
    запись обновляется, не плодя дубликаты.
    """

    __tablename__ = "oauth_tokens"
    __table_args__ = (
        UniqueConstraint("company_id", "bank", name="uq_oauth_tokens_company_bank"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bank: Mapped[Bank] = mapped_column(
        Enum(Bank, name="bank_enum"), nullable=False, index=True
    )

    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    company: Mapped["Company"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<OAuthToken company={self.company_id} bank={self.bank.value}>"
