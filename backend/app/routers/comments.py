from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.comment import Comment
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentOut
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/comments", tags=["comments"])


@router.get("/lead/{lead_id}", response_model=list[CommentOut])
async def get_comments(lead_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.lead_id == lead_id)
        .order_by(Comment.created_at)
    )
    return result.scalars().all()


@router.post("", response_model=CommentOut, status_code=201)
async def add_comment(
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = Comment(text=data.text, lead_id=data.lead_id, author_id=current_user.id)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    result = await db.execute(
        select(Comment).options(selectinload(Comment.author)).where(Comment.id == comment.id)
    )
    return result.scalar_one()


@router.delete("/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Комментарий не найден")
    if comment.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет прав")
    await db.delete(comment)
    await db.commit()
