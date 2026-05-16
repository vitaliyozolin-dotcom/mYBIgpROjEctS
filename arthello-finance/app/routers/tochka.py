"""Эндпоинты Точка (Open Banking authorization_code flow + test)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.company import Company
from app.services.tochka import (
    BALANCES_PATH,
    TochkaError,
    create_consent,
    exchange_code_for_token,
    fetch_balances_raw,
    get_app_token,
    get_balances,
    upsert_user_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tochka"])


# ─── HMAC state ──────────────────────────────────────────────────────────────


def _sign_state(payload: dict) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(settings.SECRET_KEY.encode(), body, hashlib.sha256).digest()
    return (
        base64.urlsafe_b64encode(sig).decode().rstrip("=")
        + "."
        + base64.urlsafe_b64encode(body).decode().rstrip("=")
    )


def _b64_pad(s: str) -> str:
    return s + "=" * (-len(s) % 4)


def _verify_state(state: str) -> dict:
    try:
        sig_b64, body_b64 = state.split(".", 1)
        sig = base64.urlsafe_b64decode(_b64_pad(sig_b64))
        body = base64.urlsafe_b64decode(_b64_pad(body_b64))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"malformed state: {exc}")
    expected = hmac.new(settings.SECRET_KEY.encode(), body, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "state signature mismatch")
    return json.loads(body)


# ─── helpers ─────────────────────────────────────────────────────────────────


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


# ─── /login → шаги 1+2+3 ─────────────────────────────────────────────────────


@router.get("/api/auth/tochka/login")
async def tochka_login(
    company_slug: str = Query(default="atlas"),
    db: AsyncSession = Depends(get_db),
):
    """1) client_credentials → 2) consent → 3) редирект на authorize."""

    _ensure_configured()
    company = await _resolve_company(db, company_slug)

    try:
        app_token = await get_app_token()
        consent_id = await create_consent(app_token)
    except TochkaError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))

    state = _sign_state(
        {"cid": company.id, "n": secrets.token_hex(8), "consent": consent_id}
    )
    params = {
        "client_id": settings.TOCHKA_CLIENT_ID,
        "response_type": "code",
        "state": state,
        "redirect_uri": settings.TOCHKA_REDIRECT_URL,
        "scope": settings.TOCHKA_SCOPE,
        "consent_id": consent_id,
    }
    url = f"{settings.TOCHKA_AUTHORIZE_URL}?{urlencode(params)}"
    logger.info(
        "tochka: company=%s consent=%s → redirect to authorize",
        company.id,
        consent_id,
    )
    return RedirectResponse(url, status_code=302)


# ─── /callback → шаг 4 ───────────────────────────────────────────────────────


@router.get("/api/auth/tochka/callback")
async def tochka_callback(
    db: AsyncSession = Depends(get_db),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    if error:
        msg = error_description or error
        logger.warning("tochka: callback error=%s", msg)
        return RedirectResponse(
            f"/dashboard?bank=tochka&error={msg}", status_code=302
        )
    if not code or not state:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "missing code or state")

    state_payload = _verify_state(state)
    company_id = int(state_payload["cid"])

    company = await db.get(Company, company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "company from state not found")

    try:
        payload = await exchange_code_for_token(code)
        await upsert_user_token(db, company_id, payload)
    except TochkaError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))

    await db.commit()
    logger.info(
        "tochka: tokens saved for company=%s (%s)", company_id, company.name
    )
    return RedirectResponse("/dashboard?bank=tochka&connected=1", status_code=302)


# ─── /test-connection ────────────────────────────────────────────────────────


@router.get("/api/tochka/test-connection")
async def tochka_test_connection(
    company_slug: str = Query(default="atlas"),
    db: AsyncSession = Depends(get_db),
):
    """Тестовый запрос на /balances с user-токеном — сырой ответ Точки."""

    _ensure_configured()
    company = await _resolve_company(db, company_slug)

    try:
        response = await fetch_balances_raw(db, company.id)
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
            "url": f"{settings.TOCHKA_API_BASE}{BALANCES_PATH}",
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


# ─── /sync ───────────────────────────────────────────────────────────────────


@router.post("/api/tochka/sync")
async def tochka_sync(
    company_slug: str = Query(default="atlas"),
    db: AsyncSession = Depends(get_db),
):
    """Ручная синхронизация балансов: GET /balances → сохранить в БД."""

    _ensure_configured()
    company = await _resolve_company(db, company_slug)

    try:
        result = await get_balances(db, company.id)
        await db.commit()
    except TochkaError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))

    saved = result["saved"]
    saved_details = [
        {
            "account_id": b.account_id,
            "amount": float(b.amount),
            "currency": b.currency,
        }
        for b in saved
    ]

    return {
        "synced": True,
        "balances_updated": len(saved),
        "details": saved_details,
        "matching": {
            "tochka_account_ids": result["tochka_account_ids"],
            "db_account_numbers": result["db_account_numbers"],
            "matched": result["matched"],
            "no_match": result["no_match"],
        },
    }
