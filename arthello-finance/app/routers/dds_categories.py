from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.dds_category import DDSCategory, DDSType
from app.schemas.dds_category import DDSCategoryCreate, DDSCategoryRead

router = APIRouter(prefix="/api/dds-categories", tags=["dds"])


@router.get("", response_model=list[DDSCategoryRead])
async def list_categories(
    type_filter: DDSType | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(DDSCategory).order_by(DDSCategory.code)
    if type_filter:
        stmt = stmt.where(DDSCategory.type == type_filter)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=DDSCategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(payload: DDSCategoryCreate, db: AsyncSession = Depends(get_db)):
    category = DDSCategory(**payload.model_dump())
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


@router.get("/{category_id}", response_model=DDSCategoryRead)
async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    cat = await db.get(DDSCategory, category_id)
    if cat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    return cat
