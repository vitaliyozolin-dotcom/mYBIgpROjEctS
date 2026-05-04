"""
ИИ-ассистент в чатах с клиентами.
В нерабочее время (20:00–09:00) отвечает от имени компании, не скрывая что это ИИ.
"""
from datetime import datetime, timezone
import anthropic
from config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = f"""Ты — ИИ-ассистент компании «{settings.company_name}».
Мы специализируемся на продаже готового арендного бизнеса (ГАБ) — недвижимости с действующими арендаторами.
Наше преимущество: объекты от 2 млн рублей при окупаемости 6–7 лет.

Правила:
1. Всегда представляйся как ИИ-ассистент компании, не притворяйся человеком.
2. Отвечай на вопросы об инвестиционной недвижимости, ГАБах, окупаемости, аренде.
3. Если вопрос требует личного менеджера — скажи, что передашь запрос, и попроси контакт.
4. Пиши кратко, по делу, дружелюбно. На русском языке.
5. Не называй конкретные объекты и цены без уточнения — только общие условия.

Типичные возражения и ответы:
- «Дорого» → объясни окупаемость и пассивный доход
- «Не понимаю как это работает» → объясни: покупаешь объект с уже работающим арендатором, получаешь арендную плату
- «А если арендатор уйдёт?» → расскажи о диверсификации и помощи в поиске новых арендаторов
"""


def is_ai_time() -> bool:
    now = datetime.now()
    hour = now.hour
    start = settings.ai_start_hour
    end = settings.ai_end_hour
    if start > end:
        return hour >= start or hour < end
    return start <= hour < end


async def get_ai_response(user_message: str, history: list[dict]) -> str:
    messages = history[-10:] + [{"role": "user", "content": user_message}]
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text
