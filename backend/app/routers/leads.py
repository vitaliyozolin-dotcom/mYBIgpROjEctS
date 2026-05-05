import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.lead import Lead
from app.models.user import User
from app.models.stage_history import LeadStageHistory
from app.schemas.lead import LeadCreate, LeadUpdate, LeadOut
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/leads", tags=["leads"])

LOAD_OPTS = [selectinload(Lead.assigned_to), selectinload(Lead.comments), selectinload(Lead.tasks)]

STAGE_LABELS = {
    "new": "Новая заявка",
    "no_answer": "Не дозвонились",
    "contacted": "Первичный контакт",
    "qualified": "Квалификация",
    "selection": "Подбор объекта",
    "showing_scheduled": "Показ назначен",
    "showing_done": "Показ проведён",
    "booking": "Бронь / Аванс",
    "documents": "Документы / Ипотека",
    "won": "Сделка ✅",
    "lost": "Отказ / Архив ❌",
}

SCORE_RECALC_FIELDS = {"budget", "tags", "stage", "next_action", "next_date", "source"}


def calculate_lead_score(lead: Lead) -> int:
    """Расчётный score лида: деньги + намерение + стадия + дисциплина следующего шага."""
    score = 0
    budget = lead.budget or 0
    tags = lead.tags or []

    if budget >= 10_000_000:
        score += 25
    elif budget >= 5_000_000:
        score += 20
    elif budget >= 3_000_000:
        score += 12
    elif budget > 0:
        score += 5

    tag_points = {
        "Горячий": 20,
        "VIP": 15,
        "Ипотека": 15,
        "Инвестор": 10,
        "Срочно": 10,
        "Повторный": 8,
        "Корпоратив": 8,
        "Семья": 5,
    }
    score += sum(tag_points.get(tag, 0) for tag in tags)

    stage_points = {
        "new": 5,
        "no_answer": 0,
        "contacted": 8,
        "qualified": 12,
        "selection": 16,
        "showing_scheduled": 22,
        "showing_done": 24,
        "booking": 30,
        "documents": 32,
        "won": 100,
        "lost": 0,
    }
    if lead.stage == "won":
        return 100
    if lead.stage == "lost":
        return 0
    score += stage_points.get(lead.stage, 5)

    if lead.next_action:
        score += 5
    if lead.next_date:
        score += 5

    if lead.source in {"partners", "referral"}:
        score += 5

    return max(0, min(100, int(score)))


async def notify_stage_change(lead_name: str, lead_id: int, old_stage: str, new_stage: str):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://bot:8001/internal/stage-change",
                json={
                    "lead_id": lead_id,
                    "lead_name": lead_name,
                    "old_stage": STAGE_LABELS.get(old_stage, old_stage),
                    "new_stage": STAGE_LABELS.get(new_stage, new_stage),
                },
                timeout=5,
            )
    except Exception:
        pass


@router.get("", response_model=list[LeadOut])
async def list_leads(
    stage: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Lead).options(*LOAD_OPTS).order_by(Lead.created_at.desc())
    if stage:
        q = q.where(Lead.stage == stage)
    # Менеджер видит только свои лиды, админ — все
    if current_user.role == "manager":
        q = q.where(Lead.assigned_to_id == current_user.id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=LeadOut, status_code=201)
async def create_lead(
    data: LeadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead_data = data.model_dump()
    if not lead_data.get("assigned_to_id") and current_user.role == "manager":
        lead_data["assigned_to_id"] = current_user.id
    lead = Lead(**lead_data)
    lead.score = calculate_lead_score(lead)
    db.add(lead)
    await db.flush()
    db.add(LeadStageHistory(lead_id=lead.id, stage=lead.stage))
    await db.commit()
    await db.refresh(lead)
    result = await db.execute(select(Lead).options(*LOAD_OPTS).where(Lead.id == lead.id))
    return result.scalar_one()


@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(Lead).options(*LOAD_OPTS).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Лид не найден")
    return lead


@router.patch("/{lead_id}", response_model=LeadOut)
async def update_lead(
    lead_id: int,
    data: LeadUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Лид не найден")

    old_stage = lead.stage
    updates = data.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(lead, field, value)

    if SCORE_RECALC_FIELDS.intersection(updates.keys()):
        lead.score = calculate_lead_score(lead)

    if "stage" in updates and updates["stage"] != old_stage:
        db.add(LeadStageHistory(lead_id=lead.id, stage=updates["stage"]))
        background_tasks.add_task(
            notify_stage_change, lead.name, lead.id, old_stage, updates["stage"]
        )

    await db.commit()
    result = await db.execute(select(Lead).options(*LOAD_OPTS).where(Lead.id == lead_id))
    return result.scalar_one()


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(lead_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Лид не найден")
    await db.delete(lead)
    await db.commit()


@router.get("/{lead_id}/stage-history")
async def stage_history(lead_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(
        select(LeadStageHistory)
        .where(LeadStageHistory.lead_id == lead_id)
        .order_by(LeadStageHistory.entered_at)
    )
    rows = result.scalars().all()
    history = []
    for i, row in enumerate(rows):
        next_time = rows[i + 1].entered_at if i + 1 < len(rows) else None
        from datetime import datetime, timezone
        end = next_time or datetime.now(timezone.utc).replace(tzinfo=None)
        diff = end - row.entered_at.replace(tzinfo=None) if row.entered_at.tzinfo is None else end - row.entered_at
        days = diff.days
        hours = diff.seconds // 3600
        history.append({
            "stage": row.stage,
            "label": STAGE_LABELS.get(row.stage, row.stage),
            "entered_at": row.entered_at.isoformat(),
            "days": days,
            "hours": hours,
            "is_current": next_time is None,
        })
    return history
