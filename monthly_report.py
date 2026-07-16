import asyncio
import json
import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from openai import OpenAI

from category_details import expense_display_title as clean_expense_display_title
from category_detector import format_category_label, normalize_financial_category


MONTH_NAMES = {
    1: "Січень",
    2: "Лютий",
    3: "Березень",
    4: "Квітень",
    5: "Травень",
    6: "Червень",
    7: "Липень",
    8: "Серпень",
    9: "Вересень",
    10: "Жовтень",
    11: "Листопад",
    12: "Грудень",
}

MONTH_REPORT_PROMPT = """
Ти фінансовий AI-аналітик.

Тобі передали готовий місячний звіт у JSON.
Не рахуй сам.
Не вигадуй дані.

Зроби короткий, структурований звіт українською:
- місяць
- всього витрат
- категорії
- емоційні витрати
- найбільша покупка
- 1 короткий висновок

Стиль: спокійний, сучасний, лаконічний.
Без полотна тексту.
Не використовуй відсотки у відповіді. Пиши суми в грн.
"""


def _month_bounds(value: datetime) -> tuple[datetime, datetime]:
    start = value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def _format_amount(amount: int | float) -> str:
    return f"{int(amount):,}".replace(",", " ")


def _expense_display_title(expense_title: str | None, raw_title: str | None, name: str | None = None) -> str:
    return clean_expense_display_title(expense_title, raw_title, name)


def _get_month_expenses(user_id: int, db_path: str, year: int, month: int) -> list[dict[str, Any]]:
    month_start, next_month = _month_bounds(datetime(year, month, 1))
    with sqlite3.connect(db_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(expenses)").fetchall()
        }
        has_category = "category" in columns
        has_subcategory = "subcategory" in columns
        has_expense_title = "expense_title" in columns
        has_raw_title = "raw_title" in columns
        category_select = ", category" if has_category else ", NULL AS category"
        subcategory_select = ", subcategory" if has_subcategory else ", NULL AS subcategory"
        expense_title_select = ", expense_title" if has_expense_title else ", NULL AS expense_title"
        raw_title_select = ", raw_title" if has_raw_title else ", NULL AS raw_title"
        rows = connection.execute(
            f"""
            SELECT name, amount, type, date{category_select}{subcategory_select}{expense_title_select}{raw_title_select}
            FROM expenses
            WHERE user_id = ?
              AND datetime(date) >= datetime(?)
              AND datetime(date) < datetime(?)
            ORDER BY id DESC
            """,
            (
                user_id,
                month_start.isoformat(sep=" ", timespec="seconds"),
                next_month.isoformat(sep=" ", timespec="seconds"),
            ),
        ).fetchall()

    expenses = []
    for row in rows:
        title = _expense_display_title(row[6], row[7], row[0])
        normalized = normalize_financial_category(title, row[4], row[5])
        expenses.append(
            {
                "title": title,
                "amount": int(row[1] or 0),
                "type": row[2],
                "date": row[3],
                "category": normalized["category"],
                "subcategory": normalized["subcategory"],
            }
        )
    return expenses


def get_report_months(user_id: int, db_path: str = "expenses.db", limit: int = 6) -> list[tuple[int, int, str]]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT
                   CAST(strftime('%Y', date) AS INTEGER) AS year,
                   CAST(strftime('%m', date) AS INTEGER) AS month
            FROM expenses
            WHERE user_id = ?
              AND date IS NOT NULL
            ORDER BY year DESC, month DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    return [
        (int(year), int(month), f"{MONTH_NAMES[int(month)].lower()} {int(year)}")
        for year, month in rows
        if year and month
    ]


def build_month_report_data(
    user_id: int,
    db_path: str = "expenses.db",
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    expenses = _get_month_expenses(user_id, db_path, year, month)
    month_start, _ = _month_bounds(datetime(year, month, 1))
    previous_month_date = month_start - timedelta(days=1)
    previous_expenses = _get_month_expenses(user_id, db_path, previous_month_date.year, previous_month_date.month)
    total = sum(expense["amount"] for expense in expenses)
    previous_total = sum(expense["amount"] for expense in previous_expenses)
    emotional = sum(
        expense["amount"]
        for expense in expenses
        if str(expense.get("type") or "").lower() == "емоційна"
    )

    category_totals: defaultdict[str, int] = defaultdict(int)
    for expense in expenses:
        category = normalize_financial_category(
            str(expense.get("title") or ""),
            str(expense.get("category") or ""),
            str(expense.get("subcategory") or ""),
        )["category"]
        category_totals[category] += int(expense["amount"])

    top_categories = [
        {
            "name": name,
            "amount": amount,
            "percent": round(amount * 100 / total, 1) if total else 0,
        }
        for name, amount in sorted(category_totals.items(), key=lambda item: item[1], reverse=True)
    ]

    largest_expense = None
    if expenses:
        largest = max(expenses, key=lambda expense: expense["amount"])
        largest_expense = {
            "title": largest["title"],
            "amount": largest["amount"],
        }

    return {
        "month": f"{MONTH_NAMES[month]} {year}",
        "total_spent": total,
        "transactions": len(expenses),
        "emotional_sum": emotional,
        "emotional_percent": round(emotional * 100 / total, 1) if total else 0,
        "top_categories": top_categories,
        "largest_expense": largest_expense,
        "transactions_count": len(expenses),
        "trend": {
            "previous_total": previous_total,
            "difference": total - previous_total,
            "percent": round((total - previous_total) * 100 / previous_total, 1) if previous_total else None,
        },
    }


def build_month_report_fallback(report: dict[str, Any]) -> str:
    if report["transactions"] == 0:
        return (
            f"📅 {report['month']}\n\n"
            "Даних за цей місяць поки мало для звіту."
        )

    lines = [
        f"📅 {report['month']}",
        "",
        "💸 Всього витрат:",
        f"{_format_amount(report['total_spent'])} грн",
        "",
        "📊 По категоріях:",
    ]

    for category in report["top_categories"][:5]:
        lines.append(
            f"• {format_category_label(category['name'])} — {_format_amount(category['amount'])} грн"
        )

    lines.extend(
        [
            "",
            "🔥 Емоційні витрати:",
            f"{_format_amount(report.get('emotional_sum', 0))} грн",
        ]
    )

    largest = report.get("largest_expense")
    if largest:
        lines.extend(
            [
                "",
                "💰 Найбільша покупка:",
                f"{largest['title']} — {_format_amount(largest['amount'])} грн",
            ]
        )

    if report["top_categories"]:
        first = report["top_categories"][0]
        lines.extend(
            [
                "",
                f"👀 Найбільше грошей зараз йде на {format_category_label(first['name'])}.",
            ]
        )

    trend = report.get("trend") or {}
    if trend.get("difference"):
        sign = "+" if trend["difference"] > 0 else "-"
        lines.extend(
            [
                "",
                "📈 У порівнянні з минулим місяцем:",
                f"{sign}{_format_amount(abs(trend['difference']))} грн",
            ]
        )

    return "\n".join(lines)


def build_categories_breakdown(report: dict[str, Any]) -> str:
    if report["transactions"] == 0:
        return "Даних за цей місяць поки мало для розбивки."

    lines = [
        f"📊 Категорії за {report['month']}",
        "",
    ]
    for index, category in enumerate(report["top_categories"], start=1):
        lines.append(
            f"{index}. {format_category_label(category['name'])} — {_format_amount(category['amount'])} грн"
        )
    return "\n".join(lines)


def get_month_report_categories(
    user_id: int,
    db_path: str = "expenses.db",
    year: int | None = None,
    month: int | None = None,
) -> list[str]:
    report = build_month_report_data(user_id, db_path, year, month)
    return [str(category["name"]) for category in report["top_categories"]]


def build_category_drilldown(
    user_id: int,
    category: str,
    db_path: str = "expenses.db",
    year: int | None = None,
    month: int | None = None,
) -> str:
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    normalized_category = normalize_financial_category(category)["category"]
    expenses = [
        expense
        for expense in _get_month_expenses(user_id, db_path, year, month)
        if normalize_financial_category(
            str(expense.get("title") or ""),
            str(expense.get("category") or ""),
            str(expense.get("subcategory") or ""),
        )["category"] == normalized_category
    ]

    if not expenses:
        return f"{format_category_label(normalized_category)}\n\nДаних за цю категорію поки немає."

    title_totals: dict[str, int] = {}
    title_labels: dict[str, str] = {}
    for expense in expenses:
        title = str(expense.get("title") or "").strip() or "Інше"
        key = title.casefold()
        title_labels.setdefault(key, title)
        title_totals[key] = title_totals.get(key, 0) + int(expense.get("amount") or 0)

    total = sum(title_totals.values())
    lines = [
        f"{format_category_label(normalized_category)}",
        "",
        f"💰 Разом: {_format_amount(total)} грн",
        "",
    ]
    for key, amount in sorted(title_totals.items(), key=lambda item: item[1], reverse=True)[:12]:
        lines.append(f"• {title_labels[key]} — {_format_amount(amount)} грн")
    return "\n".join(lines)


def _remove_percent_fields(value):
    if isinstance(value, dict):
        return {
            key: _remove_percent_fields(item)
            for key, item in value.items()
            if "percent" not in key
        }
    if isinstance(value, list):
        return [_remove_percent_fields(item) for item in value]
    return value


def _ask_gpt_month_report(api_key: str, report: dict[str, Any]) -> str:
    client = OpenAI(api_key=api_key, timeout=25)
    prompt_report = _remove_percent_fields(report)
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.3,
        max_tokens=300,
        messages=[
            {"role": "system", "content": MONTH_REPORT_PROMPT},
            {
                "role": "user",
                "content": (
                    "Готовий місячний звіт у JSON:\n"
                    f"{json.dumps(prompt_report, ensure_ascii=False)}"
                ),
            },
        ],
    )
    message = response.choices[0].message.content
    return message.strip() if message else build_month_report_fallback(report)


async def generate_month_report(
    user_id: int,
    db_path: str = "expenses.db",
    year: int | None = None,
    month: int | None = None,
) -> str:
    report = await asyncio.to_thread(build_month_report_data, user_id, db_path, year, month)
    fallback = build_month_report_fallback(report)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_ask_gpt_month_report, api_key, report),
            timeout=30,
        )
    except Exception as error:
        print(f"[MONTH REPORT FALLBACK] {error}")
        return fallback


async def generate_month_categories(
    user_id: int,
    db_path: str = "expenses.db",
    year: int | None = None,
    month: int | None = None,
) -> str:
    report = await asyncio.to_thread(build_month_report_data, user_id, db_path, year, month)
    return build_categories_breakdown(report)
