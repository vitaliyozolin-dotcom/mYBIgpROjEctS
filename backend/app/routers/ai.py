"""AI-прокси: проксирует запросы к Anthropic Claude через бэкенд.
API-ключ хранится только на сервере и никогда не передаётся клиенту.
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.models.user import User
from app.services.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/ai", tags=["ai"])

CRM_SYSTEM_PROMPT = """Ты — умный AI-ассистент CRM-системы для продажи недвижимости «Инвест Недвижимость».
Помогаешь менеджерам анализировать лиды, давать рекомендации по работе с клиентами.
Компания продаёт готовый арендный бизнес (ГАБ) от 2 млн ₽, окупаемость 6–7 лет.
Отвечай кратко и конкретно на русском языке. Используй эмодзи для наглядности."""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    system: str | None = None
    context: str | None = None


@router.post("/chat")
async def ai_chat(req: ChatRequest, _: User = Depends(get_current_user)):
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="AI не настроен: укажите ANTHROPIC_API_KEY в .env")

    system = req.system or CRM_SYSTEM_PROMPT
    if req.context:
        system += f"\n\nКонтекст текущей сессии:\n{req.context}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1000,
                    "system": system,
                    "messages": [m.model_dump() for m in req.messages],
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            text = data.get("content", [{}])[0].get("text", "Нет ответа")
            return {"content": text}
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI не ответил вовремя")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ошибка AI: {str(e)}")
