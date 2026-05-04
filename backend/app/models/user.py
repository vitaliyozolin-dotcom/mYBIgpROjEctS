from sqlalchemy import String, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="manager")  # manager | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True)

    leads: Mapped[list["Lead"]] = relationship(back_populates="assigned_to")  # noqa
    comments: Mapped[list["Comment"]] = relationship(back_populates="author")  # noqa
    tasks: Mapped[list["Task"]] = relationship(back_populates="assigned_to")  # noqa
