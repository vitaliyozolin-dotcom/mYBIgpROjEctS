"""AI-прокси для CRM.

Ключ OpenAI хранится только на backend и никогда не попадает во frontend.
Frontend ходит в POST /api/ai/chat, backend вызывает OpenAI Responses API.
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.models.user import User
from app.services.auth import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/ai", tags=["ai"])

CRM_SYSTEM_PROMPT = """Ты — AI-директор по продажам внутри CRM для недвижимости «Инвест Недвижимость».
Твоя задача — помогать менеджеру довести лида до сделки, а не просто отвечать общими словами.

Формат ответов:
- кратко;
- конкретно;
- по-русски;
- с приоритетами;
- без воды;
- если просишь действие — формулируй его так, чтобы менеджер мог сразу выполнить.

Ты умеешь:
1. Давать краткое резюме лида.
2. Оценивать риск потери клиента.
3. Предлагать следующий лучший шаг.
4. Писать скрипт звонка.
5. Писать сообщение в WhatsApp/Telegram.
6. Объяснять, почему лид горячий или слабый.
7. Подсказывать, что спросить у клиента дальше.
"""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    system: str | None = None
    context: str | None = None


def _messages_to_input(messages: list[ChatMessage]) -> str:
    parts: list[str] = []
    for message in messages:
        role = "Менеджер" if message.role == "user" else "AI"
        parts.append(f"{role}: {message.content}")
    return "\n".join(parts)


@router.post("/chat")
async def ai_chat(req: ChatRequest, _: User = Depends(get_current_user)):
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="AI не настроен: укажите OPENAI_API_KEY в .env")

    system = req.system or CRM_SYSTEM_PROMPT
    if req.context:
        system += f"\n\nКонтекст CRM:\n{req.context}"

    user_input = _messages_to_input(req.messages)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.openai_model,
                    "instructions": system,
                    "input": user_input,
                    "max_output_tokens": 900,
                },
                timeout=45,
            )
            response.raise_for_status()
            data = response.json()
            text = data.get("output_text")

            if not text:
                output = data.get("output") or []
                chunks: list[str] = []
                for item in output:
                    for content in item.get("content", []) or []:
                        if content.get("type") in {"output_text", "text"} and content.get("text"):
                            chunks.append(content["text"])
                text = "\n".join(chunks).strip()

            return {"content": text or "AI не вернул текстовый ответ"}
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:500] if e.response is not None else str(e)
        raise HTTPException(status_code=502, detail=f"Ошибка OpenAI: {detail}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI не ответил вовремя")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ошибка AI: {str(e)}")
