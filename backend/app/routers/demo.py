from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.lead import Lead
from app.models.task import Task
from app.models.comment import Comment
from app.models.stage_history import LeadStageHistory
from app.models.user import User
from app.routers.leads import calculate_lead_score
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/demo", tags=["demo"])

DEMO_LEADS = [
    {
        "name": "Алексей Морозов",
        "phone": "+7 999 123-45-67",
        "email": "morozov@mail.ru",
        "source": "instagram",
        "stage": "showing_scheduled",
        "budget": 7800000,
        "tags": ["Горячий", "Семья", "Ипотека"],
        "next_action": "Подтвердить показ двух объектов",
        "next_date_offset_hours": 4,
        "property_type": "2-комнатная квартира",
        "location": "Север города / рядом с метро",
        "rooms": "2к",
        "desired_area": "55–70 м²",
        "purchase_goal": "Для семьи, переезд в течение месяца",
        "payment_method": "Ипотека + первоначальный взнос",
        "mortgage_status": "Предварительно одобрена",
        "purchase_timeline": "1 месяц",
        "main_objection": "Боится переплатить за район",
        "notes": "Хочет тихий двор, хорошую школу рядом и не первый этаж.",
    },
    {
        "name": "Мария Соколова",
        "phone": "+7 977 555-11-22",
        "email": "sokolova@gmail.com",
        "source": "website",
        "stage": "qualified",
        "budget": 12500000,
        "tags": ["VIP", "Ипотека"],
        "next_action": "Подготовить подборку домов у воды",
        "next_date_offset_hours": 22,
        "property_type": "Загородный дом",
        "location": "Северное направление / 30–45 минут от города",
        "rooms": "3–4 спальни",
        "desired_area": "120–180 м²",
        "purchase_goal": "Дом для постоянного проживания",
        "payment_method": "Ипотека",
        "mortgage_status": "Одобрение в процессе",
        "purchase_timeline": "2–3 месяца",
        "main_objection": "Сомневается по обслуживанию дома зимой",
        "notes": "Важно показать не только дом, но и инфраструктуру района.",
    },
    {
        "name": "Игорь Зайцев",
        "phone": "+7 901 888-33-44",
        "email": "zaitsev@yandex.ru",
        "source": "avito",
        "stage": "no_answer",
        "budget": 3200000,
        "tags": ["Срочно"],
        "next_action": None,
        "next_date_offset_hours": None,
        "property_type": "Студия",
        "location": "Любая локация, главное цена",
        "rooms": "Студия",
        "desired_area": "от 24 м²",
        "purchase_goal": "Первая квартира",
        "payment_method": "Ипотека",
        "mortgage_status": "Не уточнено",
        "purchase_timeline": "Срочно",
        "main_objection": "Очень ограниченный бюджет",
        "notes": "Не дозвонились два раза. Нужен короткий WhatsApp с 2 вариантами.",
    },
    {
        "name": "Татьяна Белова",
        "phone": "+7 916 222-77-88",
        "email": "belova@corp.ru",
        "source": "partners",
        "stage": "booking",
        "budget": 18000000,
        "tags": ["VIP", "Инвестор", "Повторный", "Горячий"],
        "next_action": "Согласовать условия аванса и бронь",
        "next_date_offset_hours": 2,
        "property_type": "Коммерческое помещение / ГАБ",
        "location": "Проходная локация, первый этаж",
        "rooms": "open space",
        "desired_area": "80–150 м²",
        "purchase_goal": "Инвестиция под аренду",
        "payment_method": "Собственные средства",
        "mortgage_status": "Не требуется",
        "purchase_timeline": "1–2 недели",
        "main_objection": "Хочет понять реальную доходность",
        "notes": "Корпоративная покупка на юрлицо. Нужны цифры по окупаемости.",
    },
    {
        "name": "Сергей Новиков",
        "phone": "+7 925 444-55-66",
        "email": "novikov@biz.ru",
        "source": "telegram",
        "stage": "documents",
        "budget": 9400000,
        "tags": ["Семья", "Горячий"],
        "next_action": "Запросить недостающие документы",
        "next_date_offset_hours": 7,
        "property_type": "3-комнатная квартира",
        "location": "Юг города, рядом с парком",
        "rooms": "3к",
        "desired_area": "75–90 м²",
        "purchase_goal": "Расширение жилплощади",
        "payment_method": "Продажа старой квартиры + доплата",
        "mortgage_status": "Не требуется",
        "purchase_timeline": "До конца месяца",
        "main_objection": "Боится не успеть продать старую квартиру",
        "notes": "Хороший контакт, решение принимает вместе с супругой.",
    },
    {
        "name": "Ольга Кузнецова",
        "phone": "+7 911 777-20-10",
        "email": "olga.k@mail.ru",
        "source": "referral",
        "stage": "selection",
        "budget": 6500000,
        "tags": ["Повторный"],
        "next_action": "Отправить 5 объектов и уточнить приоритет района",
        "next_date_offset_hours": 12,
        "property_type": "1-комнатная квартира",
        "location": "Центр или Петроградская сторона",
        "rooms": "1к",
        "desired_area": "38–50 м²",
        "purchase_goal": "Квартира для дочери",
        "payment_method": "Собственные средства + небольшой кредит",
        "mortgage_status": "Возможно",
        "purchase_timeline": "1–2 месяца",
        "main_objection": "Не хочет старый фонд без ремонта",
        "notes": "Пришла по рекомендации. Важно не давить, а вести экспертно.",
    },
]

@router.post("/seed")
async def seed_demo_data(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(func.count(Lead.id)))
    existing_count = result.scalar_one()
    if existing_count > 0:
        return {"created": 0, "message": "В базе уже есть лиды, демо-данные не добавлены"}

    now = datetime.utcnow()
    created = 0
    for index, original in enumerate(DEMO_LEADS):
        item = dict(original)
        offset = item.pop("next_date_offset_hours")
        lead = Lead(
            **item,
            next_date=now + timedelta(hours=offset) if offset is not None else None,
            last_contact_at=now - timedelta(hours=2 + index * 5),
            assigned_to_id=current_user.id,
        )
        lead.score = calculate_lead_score(lead)
        db.add(lead)
        await db.flush()

        db.add(LeadStageHistory(lead_id=lead.id, stage="new", entered_at=now - timedelta(days=4 + index)))
        if lead.stage != "new":
            db.add(LeadStageHistory(lead_id=lead.id, stage=lead.stage, entered_at=now - timedelta(hours=8 + index)))

        db.add(Task(
            lead_id=lead.id,
            assigned_to_id=current_user.id,
            title=lead.next_action or "Вернуть клиента в контакт",
            due_at=lead.next_date or now + timedelta(hours=24),
            is_done=False,
        ))
        db.add(Comment(
            lead_id=lead.id,
            author_id=current_user.id,
            text=f"Демо-комментарий: {lead.notes or 'клиент добавлен для проверки CRM.'}",
        ))
        created += 1

    await db.commit()
    return {"created": created, "message": f"Добавлено демо-лидов: {created}"}
