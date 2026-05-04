"""
Webhook endpoints для сбора лидов с внешних источников.
Сайт, Авито, другие интеграции отправляют POST на /api/webhooks/lead.
"""
import httpx
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.lead import Lead
from app.schemas.lead import WebhookLead

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


async def notify_telegram(lead: Lead):
    """Отправляет уведомление в Telegram-бот о новом лиде."""
    from app.config import settings
    if not settings.telegram_bot_token:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"http://bot:8001/internal/new-lead",
                json={"lead_id": lead.id, "name": lead.name, "phone": lead.phone, "source": lead.source},
                timeout=5,
            )
    except Exception:
        pass


@router.post("/lead", status_code=201)
async def receive_lead(
    data: WebhookLead,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    source = data.source
    if data.utm_source:
        source = data.utm_source

    lead = Lead(
        name=data.name,
        phone=data.phone,
        email=data.email,
        source=source,
        notes=data.notes,
        stage="new",
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    background_tasks.add_task(notify_telegram, lead)

    return {"id": lead.id, "status": "created"}
