from pydantic import BaseModel, ConfigDict, Field

from app.models.dds_category import DDSType


class DDSCategoryBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    type: DDSType
    priority_default: int | None = Field(None, ge=1, le=4)


class DDSCategoryCreate(DDSCategoryBase):
    pass


class DDSCategoryRead(DDSCategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
