from datetime import datetime
from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    lead_id: int
    due_at: datetime | None = None
    assigned_to_id: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    due_at: datetime | None = None
    is_done: bool | None = None
    assigned_to_id: int | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    lead_id: int
    due_at: datetime | None
    is_done: bool
    assigned_to_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
