from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.company import CompanyType


class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: CompanyType = CompanyType.OOO


class CompanyCreate(CompanyBase):
    pass


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
