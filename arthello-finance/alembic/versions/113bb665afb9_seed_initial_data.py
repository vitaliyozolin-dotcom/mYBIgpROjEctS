"""seed initial data

Revision ID: 113bb665afb9
Revises: 1b0e6089052d
Create Date: 2026-05-13 23:21:29.564403

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "113bb665afb9"
down_revision: Union[str, None] = "1b0e6089052d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Структура группы ARTHELLO: (название, тип ЮЛ, [(банк, тип счёта, имя счёта), ...])
COMPANIES_WITH_ACCOUNTS: list[tuple[str, str, list[tuple[str, str, str]]]] = [
    (
        "АХ",
        "OOO",
        [
            ("tochka", "main", "АХ Точка основной"),
            ("tochka", "tax", "АХ Точка налоги"),
            ("tbank", "main", "АХ Тбанк основной"),
            ("tbank", "dbp", "АХ Тбанк ДБП"),
        ],
    ),
    (
        "ИП",
        "IP",
        [
            ("tochka", "main", "ИП Точка"),
            ("tbank", "main", "ИП Тбанк"),
        ],
    ),
    (
        "УК",
        "OOO",
        [("tochka", "main", "УК Точка")],
    ),
    *[
        (f"Школа {i}", "OOO", [("tochka", "main", f"Школа {i} Точка")])
        for i in range(1, 12)
    ],
    (
        "Atlas",
        "OOO",
        [("tochka", "main", "Atlas Точка")],
    ),
]

DDS_CATEGORIES: list[tuple[str, str, str, int | None]] = [
    ("rent", "Аренда", "out", 1),
    ("leasing", "Лизинг", "out", 1),
    ("salary", "Зарплата", "out", 1),
    ("taxes", "Налоги", "out", 1),
    ("client_income", "Поступления от клиентов", "in", None),
    ("dbp_income", "ДБП поступления", "in", None),
    ("household", "Хозрасходы", "out", 4),
]


def upgrade() -> None:
    bind = op.get_bind()

    companies_table = sa.table(
        "companies",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("type", sa.Enum("OOO", "IP", name="company_type_enum")),
    )
    accounts_table = sa.table(
        "accounts",
        sa.column("company_id", sa.Integer),
        sa.column("bank", sa.Enum("TOCHKA", "TBANK", "ALFA", name="bank_enum")),
        sa.column(
            "account_type",
            sa.Enum("MAIN", "TAX", "DBP", "CASH", name="account_type_enum"),
        ),
        sa.column("name", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    dds_table = sa.table(
        "dds_categories",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("type", sa.Enum("IN", "OUT", "TRANSFER", name="dds_type_enum")),
        sa.column("priority_default", sa.Integer),
    )

    for company_name, company_type, accounts in COMPANIES_WITH_ACCOUNTS:
        result = bind.execute(
            companies_table.insert()
            .values(name=company_name, type=company_type)
            .returning(companies_table.c.id)
        )
        company_id = result.scalar_one()

        rows = [
            {
                "company_id": company_id,
                "bank": bank.upper(),
                "account_type": account_type.upper(),
                "name": name,
                "is_active": True,
            }
            for bank, account_type, name in accounts
        ]
        if rows:
            bind.execute(accounts_table.insert(), rows)

    dds_rows = [
        {
            "code": code,
            "name": name,
            "type": kind.upper(),
            "priority_default": prio,
        }
        for code, name, kind, prio in DDS_CATEGORIES
    ]
    bind.execute(dds_table.insert(), dds_rows)


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM dds_categories"))
    bind.execute(sa.text("DELETE FROM accounts"))
    bind.execute(sa.text("DELETE FROM companies"))
