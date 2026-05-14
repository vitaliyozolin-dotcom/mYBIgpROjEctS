# ARTHELLO Finance Dashboard

Финансовый дашборд группы компаний **ARTHELLO** (сеть детских садов и школ).
Отслеживание остатков по счетам, кредиторской задолженности (КЗ) и платежей по
юридическим лицам группы.

## Стек

- **FastAPI** + **Uvicorn**
- **SQLAlchemy 2.0** (async) + **asyncpg**
- **PostgreSQL**
- **Alembic** — миграции
- **APScheduler** — cron-задачи (синхронизация с банками, отметка просрочек, отчёты)
- **Pydantic v2** — схемы
- **Jinja2** — простой HTML-дашборд

## Структура

```
arthello-finance/
├── app/
│   ├── main.py          # FastAPI app, CORS, роутеры, lifespan со scheduler
│   ├── config.py        # настройки из .env (pydantic-settings)
│   ├── database.py      # async engine, async_session_maker, get_db
│   ├── models/          # SQLAlchemy: Account, Payment, Transaction
│   ├── schemas/         # Pydantic v2 модели
│   ├── routers/         # accounts, payments, dashboard
│   ├── services/        # bank_sync, scheduler
│   └── templates/       # dashboard.html
├── alembic/             # миграции
├── alembic.ini
├── requirements.txt
├── .env.example
├── Procfile             # Railway: web + release
└── railway.toml
```

## Быстрый старт (локально)

```bash
cd arthello-finance
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# отредактируйте DATABASE_URL, SECRET_KEY, TELEGRAM_BOT_TOKEN

# создать первую миграцию по моделям
alembic revision --autogenerate -m "init"
alembic upgrade head

uvicorn app.main:app --reload
```

Открыть:
- Дашборд: <http://localhost:8000/>
- OpenAPI: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

## API

| Метод | URL | Назначение |
|-------|-----|------------|
| GET / POST | `/api/accounts` | список / создание счёта |
| GET / PATCH / DELETE | `/api/accounts/{id}` | работа со счётом |
| GET / POST | `/api/payments` | платежи и КЗ |
| GET / PATCH / DELETE | `/api/payments/{id}` | работа с платежом |
| GET | `/api/dashboard/summary` | агрегированная сводка |
| GET | `/api/dashboard/upcoming?days=14` | ближайшие платежи |

## Cron-задачи (APScheduler)

| Job | Расписание | Действие |
|-----|------------|----------|
| `bank_sync` | каждые `BANK_SYNC_INTERVAL_MINUTES` мин. | синхронизация выписок |
| `mark_overdue` | ежедневно в 01:00 | пометить просроченные платежи |
| `daily_report` | ежедневно в `DAILY_REPORT_HOUR` | сводка дня |

## Деплой на Railway

1. Подключите репозиторий к Railway.
2. Добавьте PostgreSQL плагин — он установит `DATABASE_URL`. Замените схему на
   `postgresql+asyncpg://...`.
3. Заполните остальные переменные из `.env.example`.
4. Railway использует `railway.toml` / `Procfile`: миграции применяются на
   `release`/старте, затем поднимается `uvicorn`.
