from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyRead

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("", response_model=list[CompanyRead])
async def list_companies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).order_by(Company.id))
    return result.scalars().all()


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(company_id: int, db: AsyncSession = Depends(get_db)):
    company = await db.get(Company, company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    return company


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(payload: CompanyCreate, db: AsyncSession = Depends(get_db)):
    company = Company(**payload.model_dump())
    db.add(company)
    await db.flush()
    await db.refresh(company)
    return company
