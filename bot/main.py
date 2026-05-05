"""
Telegram CRM-бот.
- Личный чат с менеджером: /start регистрирует, бот шлёт уведомления о новых лидах и смене стадий
- Клиентские чаты: ИИ-ответы в нерабочее время (20:00–09:00)
- Внутренний HTTP-сервер :8001 принимает события от backend
"""
import asyncio
import json
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from config import settings
from handlers.ai_chat import get_ai_response, is_ai_time

logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()

# Хранилище ID чатов менеджеров — сохраняется в файл между перезапусками
MANAGERS_FILE = Path("/app/managers.json")
chat_histories: dict[int, list[dict]] = {}


def load_managers() -> set[int]:
    try:
        return set(json.loads(MANAGERS_FILE.read_text()))
    except Exception:
        return set()


def save_managers(ids: set[int]):
    try:
        MANAGERS_FILE.write_text(json.dumps(list(ids)))
    except Exception:
        pass


manager_chat_ids: set[int] = load_managers()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    manager_chat_ids.add(message.chat.id)
    save_managers(manager_chat_ids)
    await message.answer(
        "👋 Привет! Ты подключён к CRM.\n\n"
        "Буду присылать уведомления о:\n"
        "• Новых лидах\n"
        "• Смене стадии в воронке\n\n"
        f"Зарегистрировано менеджеров: {len(manager_chat_ids)}"
    )


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_client_message(message: Message):
    """ИИ отвечает клиентам в нерабочее время."""
    if not is_ai_time():
        return
    chat_id = message.chat.id
    history = chat_histories.setdefault(chat_id, [])
    await bot.send_chat_action(chat_id, "typing")
    try:
        response = await get_ai_response(message.text, history)
        history.append({"role": "user", "content": message.text})
        history.append({"role": "assistant", "content": response})
        if len(history) > 20:
            chat_histories[chat_id] = history[-20:]
        await message.answer(response)
    except Exception as e:
        logging.error(f"AI error: {e}")


# ─── Internal HTTP server ───────────────────────────────────────────────────

app = FastAPI()


class NewLeadEvent(BaseModel):
    lead_id: int
    name: str
    phone: str | None = None
    source: str = "unknown"


class StageChangeEvent(BaseModel):
    lead_id: int
    lead_name: str
    old_stage: str
    new_stage: str


async def broadcast(text: str):
    for chat_id in list(manager_chat_ids):
        try:
            await bot.send_message(chat_id, text, parse_mode="HTML")
        except Exception as e:
            logging.warning(f"Failed to send to {chat_id}: {e}")


@app.post("/internal/new-lead")
async def new_lead_event(event: NewLeadEvent):
    text = (
        f"🔔 <b>Новый лид!</b>\n\n"
        f"👤 {event.name}\n"
        f"📞 {event.phone or '—'}\n"
        f"📡 Источник: {event.source}\n\n"
        f"Открыть: http://136.244.96.159:3000/leads/{event.lead_id}"
    )
    await broadcast(text)
    return {"status": "sent", "managers": len(manager_chat_ids)}


@app.post("/internal/stage-change")
async def stage_change_event(event: StageChangeEvent):
    text = (
        f"🔄 <b>Смена стадии</b>\n\n"
        f"👤 {event.lead_name}\n"
        f"<i>{event.old_stage}</i> → <b>{event.new_stage}</b>\n\n"
        f"Открыть: http://136.244.96.159:3000/leads/{event.lead_id}"
    )
    await broadcast(text)
    return {"status": "sent"}


# ─── Run ────────────────────────────────────────────────────────────────────

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
