from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime, func, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    source: Mapped[str] = mapped_column(String(50), default="manual")
    stage: Mapped[str] = mapped_column(String(50), default="new")
    budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=50)
    next_action: Mapped[str | None] = mapped_column(String(500), nullable=True)
    next_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_to: Mapped["User | None"] = relationship(back_populates="leads")  # noqa

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    comments: Mapped[list["Comment"]] = relationship(back_populates="lead", cascade="all, delete-orphan")  # noqa
    tasks: Mapped[list["Task"]] = relationship(back_populates="lead", cascade="all, delete-orphan")  # noqa
