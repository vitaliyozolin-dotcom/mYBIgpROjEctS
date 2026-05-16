"""Идемпотентный seed реальных данных группы компаний ARTHELLO.

Запуск:
    python -m app.seeds

Повторный запуск безопасен — записи, добавленные ранее (по slug / code /
(company_id, name) / (company_id, counterparty+description)) пропускаются.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType, Bank
from app.models.balance import Balance, BalanceSource
from app.models.company import Company, CompanyType
from app.models.dds_category import DDSCategory, DDSType
from app.models.payment import PaymentQueue, PaymentStatus


COMPANIES: list[dict] = [
    {
        "name": "ООО АртХелло",
        "type": CompanyType.OOO,
        "slug": "atlas",
        "description": (
            "Филиал Атлас — 6 групп садика + начальная школа "
            "(1,2,3 класс, с сент.2026 добавится 4 класс)"
        ),
    },
    {
        "name": "ИП Тюрин Павел Олегович",
        "type": CompanyType.IP,
        "slug": "listvenный",
        "description": "Филиал Лиственный",
    },
    {
        "name": "ООО УК Детское образование",
        "type": CompanyType.OOO,
        "slug": "uk",
        "description": (
            "Управляющая компания группы ARTHELLO + юрлицо Школы 1-11 "
            "(Ленобласть, нач.школа, с сент.2026 средняя)"
        ),
    },
]


# (slug, bank | None, account_type, name, account_number, legacy_name)
# account_number — реальный номер счёта в Точке (нужен для матчинга /balances).
# legacy_name — старое имя строки (для миграции при переименовании счёта).
ACCOUNTS: list[tuple[str, Bank | None, AccountType, str, str | None, str | None]] = [
    # ООО АртХелло
    ("atlas", Bank.TOCHKA, AccountType.MAIN, "Атлас Точка основной", "40702810803500025668", None),
    ("atlas", Bank.TOCHKA, AccountType.TAX, "Атлас Точка налоги", "40702810403500027875", None),
    ("atlas", Bank.TBANK, AccountType.MAIN, "Атлас Тбанк основной", None, None),
    # Был "Атлас Тбанк ДБП" → реально это счёт в Точке, переименовываем.
    ("atlas", Bank.TOCHKA, AccountType.DBP, "Атлас Точка ДБП", "40702810520000192963", "Атлас Тбанк ДБП"),
    ("atlas", Bank.TOCHKA, AccountType.RESERVE, "Атлас Точка резервный", "40702810503270002143", None),
    ("atlas", None, AccountType.CASH, "Атлас касса нал", None, None),
    # ИП Тюрин Павел Олегович
    ("listvenный", Bank.TOCHKA, AccountType.MAIN, "Лиственный Точка основной", "40702810220000204973", None),
    ("listvenный", Bank.TBANK, AccountType.MAIN, "Лиственный Тбанк основной", None, None),
    ("listvenный", Bank.TOCHKA, AccountType.RESERVE, "Лиственный Точка резервный", "40702810020000236905", None),
    ("listvenный", None, AccountType.CASH, "Лиственный касса нал", None, None),
    # ООО УК Детское образование
    ("uk", Bank.TOCHKA, AccountType.MAIN, "УК Точка основной", "40702810520000212115", None),
    ("uk", Bank.TOCHKA, AccountType.TAX, "УК Точка налоги", None, None),
    ("uk", Bank.TOCHKA, AccountType.RESERVE, "УК Точка резервный", "40702810020000078781", None),
    ("uk", None, AccountType.CASH, "УК касса нал", None, None),
    ("uk", Bank.TOCHKA, AccountType.MAIN, "Школа 1-11 Точка основной", None, None),
]


# (code, name, type, priority_default)
DDS_CATEGORIES: list[tuple[str, str, DDSType, int | None]] = [
    # Доходы
    ("revenue_abonement", "Абонементы", DDSType.IN, None),
    ("revenue_sad", "Сад", DDSType.IN, None),
    ("revenue_individual", "Индивидуальные занятия", DDSType.IN, None),
    ("revenue_camp", "Лагерь", DDSType.IN, None),
    ("revenue_extra", "Доп.услуги", DDSType.IN, None),
    ("revenue_trial", "Пробное/Разовое", DDSType.IN, None),
    ("revenue_medical", "Медицинские услуги", DDSType.IN, None),
    ("revenue_dbp", "Ежегодный взнос (ДБП)", DDSType.IN, None),
    ("revenue_food_paid", "Питание в саду (оплата)", DDSType.IN, None),
    ("revenue_online", "Онлайн-занятия", DDSType.IN, None),
    ("revenue_school", "Школа 1-11 выручка", DDSType.IN, None),
    ("revenue_other", "Прочий доход", DDSType.IN, None),
    ("revenue_subsidy", "Субсидии", DDSType.IN, None),
    # Расходы — приоритет 1: КРИТИЧНО
    ("exp_salary_teachers", "ЗП воспитателей и педагогов", DDSType.OUT, 1),
    ("exp_salary_admin", "ЗП административного персонала", DDSType.OUT, 1),
    ("exp_salary_managers", "ЗП управляющих и директоров", DDSType.OUT, 1),
    ("exp_salary_kitchen", "ЗП поваров и кухни", DDSType.OUT, 1),
    ("exp_salary_other", "ЗП прочий персонал (охрана, водитель, уборщица)", DDSType.OUT, 1),
    ("exp_salary_marketing", "ЗП маркетолога и SMM", DDSType.OUT, 1),
    ("exp_salary_sales", "ЗП менеджера по продажам", DDSType.OUT, 1),
    ("exp_tax_fot", "Налоги с ФОТ (НДФЛ + страховые взносы)", DDSType.OUT, 1),
    ("exp_tax_usn", "УСН 7%", DDSType.OUT, 1),
    ("exp_tax_patent", "Патент", DDSType.OUT, 1),
    ("exp_rent", "Аренда", DDSType.OUT, 1),
    # Расходы — приоритет 2: ВАЖНО
    ("exp_food", "Питание (продукты для детей)", DDSType.OUT, 2),
    ("exp_utilities", "Коммунальные услуги", DDSType.OUT, 2),
    ("exp_bank_fee", "Банковское обслуживание и эквайринг", DDSType.OUT, 2),
    ("exp_credit_interest", "Проценты по кредитам, займам, лизингу", DDSType.OUT, 2),
    ("exp_security", "Охрана", DDSType.OUT, 2),
    ("exp_salary_teachers_const", "ЗП воспитателей постоянная часть", DDSType.OUT, 2),
    ("exp_pool", "Аренда дорожки бассейна", DDSType.OUT, 2),
    ("exp_trips", "Выезды и экскурсии", DDSType.OUT, 2),
    # Расходы — приоритет 3: ЖДУТ
    ("exp_marketing", "Маркетинг (бюджет + агентство)", DDSType.OUT, 3),
    ("exp_household", "Хозяйственные нужды", DDSType.OUT, 3),
    ("exp_communication", "Услуги связи и интернет", DDSType.OUT, 3),
    ("exp_stationery", "Канцелярские товары", DDSType.OUT, 3),
    ("exp_food_staff", "Продукты (вода, кофе для сотрудников)", DDSType.OUT, 3),
    ("exp_extra_services", "Расходы на доп.услуги (фото, аниматоры)", DDSType.OUT, 3),
    ("exp_garbage", "Вывоз ТБО", DDSType.OUT, 3),
    ("exp_maintenance", "Расходы на содержание и оформление помещений", DDSType.OUT, 3),
    ("exp_transport", "Перевозка персонала и доставка питания", DDSType.OUT, 3),
    ("exp_insurance", "Страхование сотрудников", DDSType.OUT, 3),
    ("exp_camp", "Расходы на лагерь/школу", DDSType.OUT, 3),
    ("exp_events", "Расходы на внутренние мероприятия", DDSType.OUT, 3),
    ("exp_fire", "Пожарная сигнализация", DDSType.OUT, 3),
    ("exp_medical", "Расходы на медуслуги", DDSType.OUT, 3),
    # Расходы — приоритет 4: НЕ СРОЧНО
    ("exp_inventory", "Инвентарь и оснащение", DDSType.OUT, 4),
    ("exp_software", "Программное обеспечение", DDSType.OUT, 4),
    ("exp_office", "Офисные расходы", DDSType.OUT, 4),
    ("exp_hr", "Найм персонала", DDSType.OUT, 4),
    ("exp_consulting", "Консалтинг и бухгалтерские услуги (взносы в УК)", DDSType.OUT, 4),
    ("exp_repr", "Представительские расходы", DDSType.OUT, 4),
    ("exp_corporate", "Корпоративные мероприятия", DDSType.OUT, 4),
    ("exp_transport_tax", "Транспортный налог", DDSType.OUT, 4),
    ("exp_business_trip", "Командировки", DDSType.OUT, 4),
    ("exp_car", "Обслуживание транспорта", DDSType.OUT, 4),
    ("exp_depreciation", "Амортизация", DDSType.OUT, 4),
    ("exp_penalties", "Штрафы и пени по налогам", DDSType.OUT, 4),
    ("exp_future", "Расходы будущих периодов (РБП)", DDSType.OUT, 4),
    ("exp_unexpected", "Непредвиденные расходы", DDSType.OUT, 4),
    # Межсчётные переводы
    ("transfer_to_tax", "Перевод на счёт налоги", DDSType.TRANSFER, None),
    ("transfer_to_dbp", "Перевод на счёт ДБП", DDSType.TRANSFER, None),
    ("transfer_between", "Перевод между своими счетами", DDSType.TRANSFER, None),
    ("transfer_loan", "Инвестиции/займы от учредителя", DDSType.TRANSFER, None),
]


# (account_name, amount RUB)
BALANCES: list[tuple[str, Decimal]] = [
    ("Атлас Точка основной", Decimal("280000")),
    ("Атлас Тбанк основной", Decimal("95000")),
    ("Атлас Точка налоги", Decimal("45000")),
    ("Атлас Точка ДБП", Decimal("120000")),
    ("Атлас касса нал", Decimal("15000")),
    ("Лиственный Точка основной", Decimal("85000")),
    ("Лиственный Тбанк основной", Decimal("30000")),
    ("Лиственный касса нал", Decimal("8000")),
    ("УК Точка основной", Decimal("55000")),
    ("УК Точка налоги", Decimal("18000")),
    ("Школа 1-11 Точка основной", Decimal("40000")),
]


# Очередь тестовых платежей.
# dds_code хранится в notes — модель не имеет отдельной FK на dds_categories.
PAYMENTS: list[dict] = [
    # priority 1 — критично
    {
        "slug": "atlas",
        "counterparty": "Арендодатель Атлас",
        "description": "Аренда Атлас",
        "dds_code": "exp_rent",
        "amount": Decimal("762000"),
        "due_days": 5,
        "priority": 1,
    },
    {
        "slug": "atlas",
        "counterparty": "Сотрудники (воспитатели)",
        "description": "ЗП воспитатели июнь",
        "dds_code": "exp_salary_teachers",
        "amount": Decimal("548000"),
        "due_days": 3,
        "priority": 1,
    },
    {
        "slug": "uk",
        "counterparty": "ИФНС",
        "description": "НДФЛ + страховые",
        "dds_code": "exp_tax_fot",
        "amount": Decimal("116000"),
        "due_days": 7,
        "priority": 1,
    },
    # priority 2 — важно
    {
        "slug": "atlas",
        "counterparty": "Управляющая компания ЖКХ",
        "description": "Коммунальные услуги май",
        "dds_code": "exp_utilities",
        "amount": Decimal("134000"),
        "due_days": 10,
        "priority": 2,
    },
    {
        "slug": "atlas",
        "counterparty": "Поставщик питания",
        "description": "Питание поставщик",
        "dds_code": "exp_food",
        "amount": Decimal("89000"),
        "due_days": 4,
        "priority": 2,
    },
    # priority 3 — ждут
    {
        "slug": "uk",
        "counterparty": "Маркетинговое агентство",
        "description": "Маркетинговое агентство май",
        "dds_code": "exp_marketing",
        "amount": Decimal("50000"),
        "due_days": 14,
        "priority": 3,
    },
    {
        "slug": "atlas",
        "counterparty": "Хозтовары",
        "description": "Хозяйственные расходы",
        "dds_code": "exp_household",
        "amount": Decimal("23000"),
        "due_days": 20,
        "priority": 3,
    },
    # priority 4 — не срочно
    {
        "slug": "uk",
        "counterparty": "SaaS-сервисы",
        "description": "Программное обеспечение",
        "dds_code": "exp_software",
        "amount": Decimal("7500"),
        "due_days": 30,
        "priority": 4,
    },
]


async def _seed_companies(session: AsyncSession) -> tuple[int, dict[str, int]]:
    added = 0
    slug_to_id: dict[str, int] = {}
    for c in COMPANIES:
        existing = await session.scalar(select(Company).where(Company.slug == c["slug"]))
        if existing is not None:
            slug_to_id[c["slug"]] = existing.id
            continue
        company = Company(
            name=c["name"],
            type=c["type"],
            slug=c["slug"],
            description=c["description"],
        )
        session.add(company)
        await session.flush()
        slug_to_id[c["slug"]] = company.id
        added += 1
    return added, slug_to_id


async def _find_account(
    session: AsyncSession,
    company_id: int,
    name: str,
    account_number: str | None,
    legacy_name: str | None,
) -> Account | None:
    """Найти существующий Account в порядке приоритета:
    1) по account_number (он UNIQUE),
    2) по (company_id, name),
    3) по (company_id, legacy_name) — для переименований.
    """

    if account_number:
        existing = await session.scalar(
            select(Account).where(Account.account_number == account_number)
        )
        if existing is not None:
            return existing

    existing = await session.scalar(
        select(Account).where(
            Account.company_id == company_id, Account.name == name
        )
    )
    if existing is not None:
        return existing

    if legacy_name:
        existing = await session.scalar(
            select(Account).where(
                Account.company_id == company_id, Account.name == legacy_name
            )
        )
        if existing is not None:
            return existing

    return None


async def _seed_accounts(
    session: AsyncSession, slug_to_id: dict[str, int]
) -> tuple[int, int, dict[str, int]]:
    """Upsert счетов. Возвращает (added, updated, name_to_id)."""

    added = 0
    updated = 0
    name_to_id: dict[str, int] = {}

    for slug, bank, acc_type, name, account_number, legacy_name in ACCOUNTS:
        company_id = slug_to_id[slug]
        existing = await _find_account(
            session, company_id, name, account_number, legacy_name
        )

        if existing is None:
            account = Account(
                company_id=company_id,
                bank=bank,
                account_type=acc_type,
                name=name,
                account_number=account_number,
                is_active=True,
            )
            session.add(account)
            await session.flush()
            name_to_id[name] = account.id
            added += 1
            continue

        # Обновляем поля, если они отличаются. Никогда не затираем
        # уже присвоенный account_number значением None.
        changed = False
        if existing.name != name:
            existing.name = name
            changed = True
        if existing.bank != bank:
            existing.bank = bank
            changed = True
        if existing.account_type != acc_type:
            existing.account_type = acc_type
            changed = True
        if account_number and existing.account_number != account_number:
            existing.account_number = account_number
            changed = True
        if changed:
            updated += 1

        name_to_id[name] = existing.id

    if added or updated:
        await session.flush()
    return added, updated, name_to_id


async def _seed_dds_categories(session: AsyncSession) -> int:
    added = 0
    for code, name, kind, prio in DDS_CATEGORIES:
        existing = await session.scalar(
            select(DDSCategory).where(DDSCategory.code == code)
        )
        if existing is not None:
            continue
        session.add(
            DDSCategory(code=code, name=name, type=kind, priority_default=prio)
        )
        added += 1
    await session.flush()
    return added


async def _seed_balances(
    session: AsyncSession, name_to_id: dict[str, int]
) -> int:
    added = 0
    for name, amount in BALANCES:
        account_id = name_to_id.get(name)
        if account_id is None:
            continue
        already = await session.scalar(
            select(Balance.id).where(Balance.account_id == account_id).limit(1)
        )
        if already is not None:
            continue
        session.add(
            Balance(
                account_id=account_id,
                amount=amount,
                currency="RUB",
                source=BalanceSource.MANUAL,
            )
        )
        added += 1
    await session.flush()
    return added


async def _seed_payments(
    session: AsyncSession, slug_to_id: dict[str, int]
) -> int:
    added = 0
    today = date.today()
    for p in PAYMENTS:
        company_id = slug_to_id[p["slug"]]
        existing = await session.scalar(
            select(PaymentQueue).where(
                PaymentQueue.company_id == company_id,
                PaymentQueue.counterparty == p["counterparty"],
                PaymentQueue.description == p["description"],
            )
        )
        if existing is not None:
            continue
        session.add(
            PaymentQueue(
                company_id=company_id,
                counterparty=p["counterparty"],
                description=p["description"],
                amount=p["amount"],
                due_date=today + timedelta(days=p["due_days"]),
                priority=p["priority"],
                status=PaymentStatus.PENDING,
                dds_code=p["dds_code"],
            )
        )
        added += 1
    await session.flush()
    return added


async def seed_all(session: AsyncSession) -> dict[str, int]:
    """Идемпотентно засеять все таблицы. Возвращает количество ВНОВЬ добавленных
    строк в каждой таблице."""

    companies_added, slug_to_id = await _seed_companies(session)
    accounts_added, accounts_updated, name_to_id = await _seed_accounts(
        session, slug_to_id
    )
    dds_added = await _seed_dds_categories(session)
    balances_added = await _seed_balances(session, name_to_id)
    payments_added = await _seed_payments(session, slug_to_id)

    return {
        "companies": companies_added,
        "accounts": accounts_added,
        "accounts_updated": accounts_updated,
        "dds_categories": dds_added,
        "balances": balances_added,
        "payment_queue": payments_added,
    }


if __name__ == "__main__":
    import asyncio

    from app.database import async_session_maker

    async def main():
        async with async_session_maker() as session:
            counts = await seed_all(session)
            await session.commit()
        print("Seeded (новых записей):")
        for table, n in counts.items():
            print(f"  {table:<16} +{n}")

    asyncio.run(main())
