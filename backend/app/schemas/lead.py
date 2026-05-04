from datetime import datetime
from pydantic import BaseModel
from app.schemas.user import UserOut


class LeadCreate(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    telegram_username: str | None = None
    telegram_chat_id: str | None = None
    source: str = "manual"
    stage: str = "new"
    budget: int | None = None
    notes: str | None = None
    assigned_to_id: int | None = None


class LeadUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    telegram_username: str | None = None
    source: str | None = None
    stage: str | None = None
    budget: int | None = None
    notes: str | None = None
    assigned_to_id: int | None = None


class LeadOut(BaseModel):
    id: int
    name: str
    phone: str | None
    email: str | None
    telegram_username: str | None
    source: str
    stage: str
    budget: int | None
    notes: str | None
    assigned_to: UserOut | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebhookLead(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    source: str = "website"
    notes: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
