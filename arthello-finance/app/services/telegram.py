"""Отправка уведомлений в Telegram.

Если TELEGRAM_BOT_TOKEN пустой или равен "placeholder" — просто логируем,
не падаем. Идея — в dev и в неконфигурированных средах не блокировать API.
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TG_API = "https://api.telegram.org/bot{token}/sendMessage"


def _is_configured() -> bool:
    token = settings.TELEGRAM_BOT_TOKEN
    chat = settings.TELEGRAM_CHAT_ID
    if not token or not chat:
        return False
    if token.lower() in {"placeholder", "токен_от_botfather"}:
        return False
    return True


async def send_message(text: str) -> bool:
    """Отправить сообщение в Telegram. Возвращает True при успехе."""

    if not _is_configured():
        logger.info("telegram: not configured, skipping. text=%r", text)
        return False

    url = _TG_API.format(token=settings.TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        logger.warning("telegram: send failed: %s", exc)
        return False
    return True
