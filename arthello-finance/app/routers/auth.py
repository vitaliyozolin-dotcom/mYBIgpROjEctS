"""OAuth2 авторизация банков (пока — Точка)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.company import Company
from app.services.tochka import (
    AUTHORIZE_URL,
    DEFAULT_SCOPE,
    exchange_code_for_token,
    upsert_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


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


@router.get("/tochka/login")
async def tochka_login(
    company_slug: str = Query(default="atlas"),
    db: AsyncSession = Depends(get_db),
):
    """Старт OAuth-флоу Точки. Редиректит на их authorize-endpoint."""

    if not settings.TOCHKA_CLIENT_ID or not settings.TOCHKA_CLIENT_SECRET:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Tochka client credentials are not configured",
        )

    company = await db.scalar(select(Company).where(Company.slug == company_slug))
    if company is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"company slug={company_slug!r} not found"
        )

    state = _sign_state({"cid": company.id, "n": secrets.token_hex(8)})
    params = {
        "client_id": settings.TOCHKA_CLIENT_ID,
        "redirect_uri": settings.TOCHKA_REDIRECT_URL,
        "response_type": "code",
        "scope": DEFAULT_SCOPE,
        "state": state,
    }
    url = f"{AUTHORIZE_URL}?{urlencode(params)}"
    logger.info("tochka: redirecting company=%s to authorize URL", company.id)
    return RedirectResponse(url, status_code=302)


@router.get("/tochka/callback")
async def tochka_callback(
    request: Request,
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

    payload = await exchange_code_for_token(code)
    await upsert_token(db, company_id, payload, scope=DEFAULT_SCOPE)
    await db.commit()

    logger.info("tochka: token saved for company=%s (%s)", company_id, company.name)
    return RedirectResponse("/dashboard?bank=tochka&connected=1", status_code=302)
