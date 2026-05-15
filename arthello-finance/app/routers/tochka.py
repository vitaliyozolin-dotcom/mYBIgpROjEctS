"""Эндпоинты для Точки.

Точка использует Client Credentials Flow: пользователь нигде ничего не
авторизует — токен получаем напрямую из client_id/client_secret через
POST {TOCHKA_TOKEN_URL}. Поэтому здесь нет /login и /callback — только
один шаг подключения (получить и сохранить токен) и тестовый эндпоинт.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.company import Company
from app.services.tochka import (
    ACCOUNTS_PATH,
    TochkaError,
    fetch_accounts_raw,
    get_or_refresh_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tochka"])


async def _resolve_company(db: AsyncSession, company_slug: str) -> Company:
    company = await db.scalar(select(Company).where(Company.slug == company_slug))
    if company is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"company slug={company_slug!r} not found"
        )
    return company


def _ensure_configured() -> None:
    if not settings.TOCHKA_CLIENT_ID or not settings.TOCHKA_CLIENT_SECRET:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "TOCHKA_CLIENT_ID / TOCHKA_CLIENT_SECRET are not configured",
        )


@router.get("/api/auth/tochka/connect")
async def tochka_connect(
    company_slug: str = Query(default="atlas"),
    db: AsyncSession = Depends(get_db),
):
    """Получить (или обновить) client_credentials-токен Точки для компании.

    Идемпотентно: если токен ещё живой — отдаём существующий expires_at.
    """

    _ensure_configured()
    company = await _resolve_company(db, company_slug)

    try:
        token = await get_or_refresh_token(db, company.id)
    except TochkaError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))

    await db.commit()

    return {
        "status": "connected",
        "company_id": company.id,
        "company_slug": company.slug,
        "company_name": company.name,
        "token_type": "Bearer",
        "scope": token.scope,
        "expires_at": token.expires_at.isoformat() if token.expires_at else None,
    }


@router.get("/api/tochka/test-connection")
async def tochka_test_connection(
    company_slug: str = Query(default="atlas"),
    db: AsyncSession = Depends(get_db),
):
    """Сходить на /accounts с токеном компании и вернуть сырой ответ Точки."""

    _ensure_configured()
    company = await _resolve_company(db, company_slug)

    try:
        response = await fetch_accounts_raw(db, company.id)
    except TochkaError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))

    await db.commit()

    ctype = response.headers.get("content-type", "")
    if "application/json" in ctype:
        try:
            body: object = response.json()
        except json.JSONDecodeError:
            body = response.text[:5000]
    else:
        body = response.text[:5000]

    return {
        "request": {
            "method": "GET",
            "url": f"{settings.TOCHKA_API_BASE}{ACCOUNTS_PATH}",
        },
        "response": {
            "status_code": response.status_code,
            "ok": response.is_success,
            "headers": {
                "content-type": ctype or None,
                "server": response.headers.get("server"),
                "x-request-id": response.headers.get("x-request-id"),
            },
            "body": body,
        },
    }
