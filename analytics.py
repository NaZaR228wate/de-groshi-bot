import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from category_details import expense_display_title
from category_detector import format_category_label, normalize_financial_category


MONTHS = {
    "січня": 1,
    "січень": 1,
    "лютого": 2,
    "лютий": 2,
    "березня": 3,
    "березень": 3,
    "квітня": 4,
    "квітень": 4,
    "травня": 5,
    "травень": 5,
    "червня": 6,
    "червень": 6,
    "липня": 7,
    "липень": 7,
    "серпня": 8,
    "серпень": 8,
    "вересня": 9,
    "вересень": 9,
    "жовтня": 10,
    "жовтень": 10,
    "листопада": 11,
    "листопад": 11,
    "грудня": 12,
    "грудень": 12,
}


def parse_db_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    for candidate in (value, value.replace("T", " ")):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            pass

    try:
        return datetime.strptime(value[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def parse_period(text: str | None, action: str | None = None) -> tuple[datetime | None, datetime | None, str]:
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    normalized = (text or "").strip().lower()

    if action == "week":
        return today - timedelta(days=6), today + timedelta(days=1), "останні 7 днів"

    if "сьогодні" in normalized:
        return today, today + timedelta(days=1), "сьогодні"
    if "вчора" in normalized:
        start = today - timedelta(days=1)
        return start, today, "вчора"
    if "останні 7" in normalized:
        return today - timedelta(days=6), today + timedelta(days=1), "останні 7 днів"
    if "тиждень" in normalized:
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=7), "цей тиждень"
    if "місяць" in normalized:
        start = today.replace(day=1)
        end = start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
        return start, end, "цей місяць"

    match = re.search(r"з\s+(\d{1,2})\s+по\s+(\d{1,2})(?:\s+([а-яіїєґ]+))?", normalized)
    if match:
        start_day = int(match.group(1))
        end_day = int(match.group(2))
        month = MONTHS.get(match.group(3) or "", now.month)
        try:
            start = datetime(now.year, month, start_day)
            end = datetime(now.year, month, end_day) + timedelta(days=1)
            return start, end, f"з {start_day} по {end_day} {list(MONTHS.keys())[list(MONTHS.values()).index(month)]}"
        except ValueError:
            return None, None, "останні витрати"

    return None, None, "останні витрати"


def get_user_expenses_for_ai(user_id: int, db_path: str = "expenses.db") -> list[dict[str, Any]]:
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
        if has_expense_title and has_raw_title:
            title_select = "COALESCE(NULLIF(expense_title, ''), NULLIF(raw_title, ''), name)"
        elif has_expense_title:
            title_select = "COALESCE(NULLIF(expense_title, ''), name)"
        elif has_raw_title:
            title_select = "COALESCE(NULLIF(raw_title, ''), name)"
        else:
            title_select = "name"
        rows = connection.execute(
            f"""
            SELECT {title_select} AS title, amount, type, date{category_select}{subcategory_select}
            FROM expenses
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 100
            """,
            (user_id,),
        ).fetchall()

    expenses: list[dict[str, Any]] = []
    for row in rows:
        title = expense_display_title(row[0], None, None)
        normalized = normalize_financial_category(title, row[4], row[5])
        item = {
            "title": title,
            "amount": int(row[1] or 0),
            "type": row[2],
            "date": row[3],
            "category": normalized["category"],
            "subcategory": normalized["subcategory"],
        }
        expenses.append(item)
    return expenses


def filter_expenses_by_period(
    expenses: list[dict[str, Any]],
    date_from: datetime | None,
    date_to: datetime | None,
) -> list[dict[str, Any]]:
    if date_from is None or date_to is None:
        return expenses

    filtered = []
    for expense in expenses:
        parsed = parse_db_datetime(str(expense.get("date") or ""))
        if parsed and date_from <= parsed < date_to:
            filtered.append(expense)
    return filtered


def calculate_total_spent(expenses: list[dict[str, Any]]) -> int:
    return sum(int(expense.get("amount") or 0) for expense in expenses)


def calculate_emotional_percent(expenses: list[dict[str, Any]]) -> dict[str, float | int]:
    total = calculate_total_spent(expenses)
    emotional = sum(
        int(expense.get("amount") or 0)
        for expense in expenses
        if str(expense.get("type") or "").lower() == "емоційна"
    )
    return {
        "emotional_sum": emotional,
        "emotional_percent": round(emotional * 100 / total, 1) if total else 0,
    }


def calculate_top_categories(expenses: list[dict[str, Any]], limit: int = 3) -> list[list[Any]]:
    totals: defaultdict[str, int] = defaultdict(int)
    for expense in expenses:
        category = normalize_financial_category(
            str(expense.get("title") or ""),
            str(expense.get("category") or ""),
            str(expense.get("subcategory") or ""),
        )["category"]
        totals[category] += int(expense.get("amount") or 0)
    return [[category, amount] for category, amount in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]]


def calculate_biggest_expenses(expenses: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    sorted_expenses = sorted(expenses, key=lambda expense: int(expense.get("amount") or 0), reverse=True)
    return [
        {
            "title": expense.get("title"),
            "amount": int(expense.get("amount") or 0),
            "type": expense.get("type"),
            "date": expense.get("date"),
        }
        for expense in sorted_expenses[:limit]
    ]


def calculate_spending_trends(
    current_expenses: list[dict[str, Any]],
    previous_expenses: list[dict[str, Any]],
) -> dict[str, Any]:
    current_total = calculate_total_spent(current_expenses)
    previous_total = calculate_total_spent(previous_expenses)
    diff = current_total - previous_total

    if previous_total == 0:
        direction = "no_previous_data"
        percent_change = None
    elif diff > 0:
        direction = "up"
        percent_change = round(diff * 100 / previous_total, 1)
    elif diff < 0:
        direction = "down"
        percent_change = round(abs(diff) * 100 / previous_total, 1)
    else:
        direction = "same"
        percent_change = 0

    daily: defaultdict[str, int] = defaultdict(int)
    for expense in current_expenses:
        parsed = parse_db_datetime(str(expense.get("date") or ""))
        if parsed:
            daily[parsed.date().isoformat()] += int(expense.get("amount") or 0)

    return {
        "current_total": current_total,
        "previous_total": previous_total,
        "difference": abs(diff),
        "direction": direction,
        "percent_change": percent_change,
        "daily_totals": dict(sorted(daily.items())),
    }


def calculate_period_stats(
    expenses: list[dict[str, Any]],
    period_label: str,
    previous_expenses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    total_spent = calculate_total_spent(expenses)
    emotional = calculate_emotional_percent(expenses)
    planned_sum = sum(
        int(expense.get("amount") or 0)
        for expense in expenses
        if str(expense.get("type") or "").lower() == "планова"
    )
    counts = Counter(str(expense.get("title") or "без назви").strip().lower() for expense in expenses)

    return {
        "period": period_label,
        "total_spent": total_spent,
        "planned_sum": planned_sum,
        "emotional_sum": emotional["emotional_sum"],
        "emotional_percent": emotional["emotional_percent"],
        "top_categories": calculate_top_categories(expenses),
        "largest_expenses": calculate_biggest_expenses(expenses),
        "largest_expense": calculate_biggest_expenses(expenses, limit=1)[0] if expenses else None,
        "transactions_count": len(expenses),
        "repeated_expenses": [
            {"title": title, "count": count}
            for title, count in counts.most_common(5)
            if count > 1
        ],
        "trends": calculate_spending_trends(expenses, previous_expenses or []),
    }


def build_ai_analytics(
    user_id: int,
    question: str,
    db_path: str = "expenses.db",
    action: str | None = None,
) -> dict[str, Any]:
    all_expenses = get_user_expenses_for_ai(user_id, db_path)
    date_from, date_to, period_label = parse_period(question, action)
    current_expenses = filter_expenses_by_period(all_expenses, date_from, date_to)

    previous_expenses: list[dict[str, Any]] = []
    if date_from and date_to:
        delta = date_to - date_from
        previous_expenses = filter_expenses_by_period(all_expenses, date_from - delta, date_from)

    return calculate_period_stats(current_expenses, period_label, previous_expenses)


def build_local_analysis(analytics: dict[str, Any]) -> str:
    if analytics["transactions_count"] == 0:
        return "Даних поки мало для точного аналізу."

    lines = [
        f"За період: {analytics['period']}",
        f"Всього: {analytics['total_spent']} грн",
        f"Емоційні: {analytics['emotional_sum']} грн",
    ]

    top_categories = analytics.get("top_categories") or []
    if top_categories:
        lines.append("")
        lines.append("Куди йдуть гроші:")
        for index, (category, amount) in enumerate(top_categories[:3], start=1):
            lines.append(f"{index}. {format_category_label(category)} — {amount} грн")

    largest = analytics.get("largest_expense")
    if largest:
        lines.append("")
        lines.append(f"Найбільша витрата: {largest['title']} — {largest['amount']} грн")

    return "\n".join(lines)
