"""
Команды для менеджеров CRM в личном чате с ботом.
"""
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
import httpx
from config import settings

router = Router()

CRM_URL = settings.backend_url


@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "👋 Привет! Я CRM-бот компании.\n\n"
        "Я буду присылать тебе уведомления о новых лидах.\n\n"
        "Команды:\n"
        "/my_tasks — мои задачи\n"
        "/new_leads — новые лиды"
    )


@router.message(Command("new_leads"))
async def new_leads(message: Message):
    try:
        # Для команд бота нужен токен — в реальности авторизация через API
        # Сейчас показываем заглушку с ссылкой на CRM
        await message.answer(
            "📋 Открой CRM для просмотра лидов:\n"
            "http://localhost:3000"
        )
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
