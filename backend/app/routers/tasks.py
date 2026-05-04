from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskOut
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/lead/{lead_id}", response_model=list[TaskOut])
async def get_tasks(lead_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(
        select(Task).where(Task.lead_id == lead_id).order_by(Task.due_at.nulls_last(), Task.created_at)
    )
    return result.scalars().all()


@router.get("/my", response_model=list[TaskOut])
async def my_tasks(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Task)
        .where(Task.assigned_to_id == current_user.id, Task.is_done == False)  # noqa
        .order_by(Task.due_at.nulls_last())
    )
    return result.scalars().all()


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = Task(**data.model_dump(), assigned_to_id=data.assigned_to_id or current_user.id)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(task_id: int, data: TaskUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task
