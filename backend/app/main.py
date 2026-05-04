from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.models import user, lead, comment, task  # noqa: must load before routers
from app.routers import auth, leads, comments, tasks, webhooks
from app.services.auth import hash_password
from sqlalchemy import select


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await create_default_admin()
    yield


async def create_default_admin():
    """Создаёт первого администратора если пользователей ещё нет."""
    from app.database import AsyncSessionLocal
    from app.models.user import User
    import os

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        if result.first():
            return

        admin = User(
            name="Администратор",
            email=os.getenv("ADMIN_EMAIL", "admin@crm.local"),
            hashed_password=hash_password(os.getenv("ADMIN_PASSWORD", "admin123")),
            role="admin",
        )
        db.add(admin)
        await db.commit()


app = FastAPI(title="CRM — Инвест Недвижимость", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(leads.router)
app.include_router(comments.router)
app.include_router(tasks.router)
app.include_router(webhooks.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
