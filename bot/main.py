"""
Telegram бот CRM.
Две роли:
1. Менеджерский бот — уведомления о новых лидах, задачах (личный чат с ботом)
2. Клиентский чат — ИИ-ответы в нерабочее время в групповых чатах или личке с клиентом

Внутренний HTTP-сервер на :8001 принимает события от backend (новые лиды).
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from config import settings
from handlers.manager import router as manager_router
from handlers.ai_chat import get_ai_response, is_ai_time

logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()
dp.include_router(manager_router)

# Хранилище истории чатов для контекста ИИ (в памяти, для MVP достаточно)
chat_histories: dict[int, list[dict]] = {}

# ID чатов менеджеров — они получают уведомления о новых лидах
# Менеджер добавляется командой /start, потом admin вносит его telegram_id в CRM
manager_chat_ids: set[int] = set()


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_message(message: Message):
    """
    Обрабатывает текстовые сообщения от пользователей.
    Если сообщение в нерабочее время — ИИ отвечает.
    """
    chat_id = message.chat.id

    if not is_ai_time():
        return

    history = chat_histories.setdefault(chat_id, [])

    await bot.send_chat_action(chat_id, "typing")

    response = await get_ai_response(message.text, history)

    history.append({"role": "user", "content": message.text})
    history.append({"role": "assistant", "content": response})

    if len(history) > 20:
        chat_histories[chat_id] = history[-20:]

    await message.answer(response)


# Внутренний HTTP сервер для приёма событий от backend

app = FastAPI()


class NewLeadEvent(BaseModel):
    lead_id: int
    name: str
    phone: str | None = None
    source: str = "unknown"


@app.post("/internal/new-lead")
async def new_lead_event(event: NewLeadEvent):
    if not manager_chat_ids:
        return {"status": "no managers registered"}

    text = (
        f"🔔 Новый лид!\n\n"
        f"👤 {event.name}\n"
        f"📞 {event.phone or '—'}\n"
        f"📡 Источник: {event.source}\n\n"
        f"Открыть в CRM: http://localhost:3000/leads/{event.lead_id}"
    )

    for chat_id in manager_chat_ids:
        try:
            await bot.send_message(chat_id, text)
        except Exception:
            pass

    return {"status": "sent"}


@dp.message(F.text == "/start")
async def register_manager(message: Message):
    manager_chat_ids.add(message.chat.id)


async def run_bot():
    await dp.start_polling(bot)


async def run_server():
    config = uvicorn.Config(app, host="0.0.0.0", port=8001, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    await asyncio.gather(run_bot(), run_server())


if __name__ == "__main__":
    asyncio.run(main())
