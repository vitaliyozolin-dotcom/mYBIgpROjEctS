from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def migrate_existing_schema(conn):
    """Мини-миграция для уже запущенных инсталляций без Alembic.

    create_all создаёт новые таблицы, но не добавляет новые колонки в существующие.
    Поэтому старый сервер мог падать на /api/leads после добавления tags/score/next_action/next_date.
    """
    await conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS tags JSON"))
    await conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS score INTEGER DEFAULT 50"))
    await conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS next_action VARCHAR(500)"))
    await conn.execute(text("ALTER TABLE leads ADD COLUMN IF NOT EXISTS next_date TIMESTAMP"))

    # Мягко переносим старые универсальные стадии в новую недвижимостную воронку.
    await conn.execute(text("UPDATE leads SET stage = 'selection' WHERE stage = 'proposal'"))
    await conn.execute(text("UPDATE leads SET stage = 'showing_scheduled' WHERE stage = 'negotiation'"))


async def init_db():
    async with engine.begin() as conn:
        from app.models import user, lead, comment, task, stage_history  # noqa
        await conn.run_sync(Base.metadata.create_all)
        await migrate_existing_schema(conn)
