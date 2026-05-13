from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountRead])
async def list_accounts(
    legal_entity: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Account)
    if legal_entity is not None:
        stmt = stmt.where(Account.legal_entity == legal_entity)
    if is_active is not None:
        stmt = stmt.where(Account.is_active == is_active)
    stmt = stmt.order_by(Account.legal_entity, Account.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{account_id}", response_model=AccountRead)
async def get_account(account_id: int, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    return account


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(payload: AccountCreate, db: AsyncSession = Depends(get_db)):
    account = Account(**payload.model_dump())
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account


@router.patch("/{account_id}", response_model=AccountRead)
async def update_account(
    account_id: int,
    payload: AccountUpdate,
    db: AsyncSession = Depends(get_db),
):
    account = await db.get(Account, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(account, key, value)

    await db.flush()
    await db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    await db.delete(account)
    return None
