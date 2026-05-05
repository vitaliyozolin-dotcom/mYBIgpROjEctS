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
    tags: list[str] | None = None
    score: int = 50
    next_action: str | None = None
    next_date: datetime | None = None
    last_contact_at: datetime | None = None
    property_type: str | None = None
    location: str | None = None
    rooms: str | None = None
    desired_area: str | None = None
    purchase_goal: str | None = None
    payment_method: str | None = None
    mortgage_status: str | None = None
    purchase_timeline: str | None = None
    main_objection: str | None = None
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
    tags: list[str] | None = None
    score: int | None = None
    next_action: str | None = None
    next_date: datetime | None = None
    last_contact_at: datetime | None = None
    property_type: str | None = None
    location: str | None = None
    rooms: str | None = None
    desired_area: str | None = None
    purchase_goal: str | None = None
    payment_method: str | None = None
    mortgage_status: str | None = None
    purchase_timeline: str | None = None
    main_objection: str | None = None
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
    tags: list[str] | None = None
    score: int = 50
    next_action: str | None = None
    next_date: datetime | None = None
    last_contact_at: datetime | None = None
    property_type: str | None = None
    location: str | None = None
    rooms: str | None = None
    desired_area: str | None = None
    purchase_goal: str | None = None
    payment_method: str | None = None
    mortgage_status: str | None = None
    purchase_timeline: str | None = None
    main_objection: str | None = None
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
