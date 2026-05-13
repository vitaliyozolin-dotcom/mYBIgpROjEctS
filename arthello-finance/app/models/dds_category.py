import enum

from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DDSType(str, enum.Enum):
    IN = "in"
    OUT = "out"
    TRANSFER = "transfer"


class DDSCategory(Base):
    """Справочник статей ДДС (Движение Денежных Средств)."""

    __tablename__ = "dds_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[DDSType] = mapped_column(
        Enum(DDSType, name="dds_type_enum"),
        nullable=False,
    )
    priority_default: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<DDSCategory {self.code} {self.name} ({self.type.value})>"
