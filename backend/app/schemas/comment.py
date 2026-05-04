from datetime import datetime
from pydantic import BaseModel
from app.schemas.user import UserOut


class CommentCreate(BaseModel):
    text: str
    lead_id: int


class CommentOut(BaseModel):
    id: int
    text: str
    lead_id: int
    author: UserOut | None
    created_at: datetime

    model_config = {"from_attributes": True}
