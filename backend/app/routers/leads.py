from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.lead import Lead
from app.models.user import User
from app.schemas.lead import LeadCreate, LeadUpdate, LeadOut
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/leads", tags=["leads"])

LOAD_OPTS = [selectinload(Lead.assigned_to), selectinload(Lead.comments), selectinload(Lead.tasks)]


@router.get("", response_model=list[LeadOut])
async def list_leads(
    stage: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(Lead).options(*LOAD_OPTS).order_by(Lead.created_at.desc())
    if stage:
        q = q.where(Lead.stage == stage)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=LeadOut, status_code=201)
async def create_lead(data: LeadCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    lead = Lead(**data.model_dump())
    db.add(lead)
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
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Лид не найден")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)

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
