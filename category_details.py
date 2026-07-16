import sqlite3
from collections import defaultdict
from datetime import datetime
import re

from category_detector import NORMALIZED_CATEGORIES, format_category_label, normalize_financial_category

UKRAINIAN_MONTH_WORDS = {
    "січень", "лютий", "березень", "квітень", "травень", "червень",
    "липень", "серпень", "вересень", "жовтень", "листопад", "грудень",
    "січня", "лютого", "березня", "квітня", "травня", "червня",
    "липня", "серпня", "вересня", "жовтня", "листопада", "грудня",
}


def format_amount(amount: int | float) -> str:
    return f"{int(amount):,}".replace(",", " ")


def is_service_title(value: str | None) -> bool:
    title = str(value or "").strip()
    if not title:
        return True

    normalized = title.casefold()
    if normalized in {"інше", "other"}:
        return True
    if normalized in {category.casefold() for category in NORMALIZED_CATEGORIES}:
        return True
    formatted_categories = {
        format_category_label(category).split(maxsplit=1)[-1].casefold()
        for category in NORMALIZED_CATEGORIES
    }
    if normalized in formatted_categories:
        return True
    if normalized in UKRAINIAN_MONTH_WORDS:
        return True
    month_pattern = "|".join(re.escape(month) for month in UKRAINIAN_MONTH_WORDS)
    if re.fullmatch(rf"({month_pattern})\s+\d{{4}}", normalized):
        return True
    if re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", normalized):
        return True
    if re.fullmatch(r"\d{1,2}[.\-/]\d{1,2}([.\-/]\d{2,4})?", normalized):
        return True
    if re.fullmatch(rf"\d{{1,2}}\s+({month_pattern})", normalized):
        return True
    if re.fullmatch(rf"\d{{1,2}}\s+({month_pattern})\s+.+", normalized):
        return True
    if re.fullmatch(rf"\d{{1,2}}\s+({month_pattern})\s+[—-]\s+({month_pattern})", normalized):
        return True
    if re.fullmatch(rf"\d{{1,2}}\s+({month_pattern})\s+[—-]\s+\d{{1,2}}\s+({month_pattern})", normalized):
        return True

    return False


def expense_display_title(expense_title: str | None, raw_title: str | None, name: str | None) -> str:
    candidates = [expense_title, raw_title, name]
    for candidate in candidates:
        title = str(candidate or "").strip()
        if title and not is_service_title(title):
            return title
    return "Без назви"


def build_category_details(
    user_id: int,
    category: str,
    db_path: str = "expenses.db",
    limit: int = 12,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> str:
    normalized_category = normalize_financial_category(category)["category"]
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    if date_from is not None:
        conditions.append("datetime(date) >= datetime(?)")
        params.append(date_from.isoformat(sep=" ", timespec="seconds"))
    if date_to is not None:
        conditions.append("datetime(date) < datetime(?)")
        params.append(date_to.isoformat(sep=" ", timespec="seconds"))
    where = " AND ".join(conditions)

    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(expenses)").fetchall()}
        expense_title_select = "expense_title" if "expense_title" in columns else "NULL AS expense_title"
        rows = connection.execute(
            f"""
            SELECT {expense_title_select}, raw_title, name, amount, category, subcategory
            FROM expenses
            WHERE {where}
            ORDER BY id DESC
            """,
            tuple(params),
        ).fetchall()

    title_totals: defaultdict[str, int] = defaultdict(int)
    title_labels: dict[str, str] = {}
    for expense_title, raw_title, name, amount, saved_category, saved_subcategory in rows:
        title = expense_display_title(expense_title, raw_title, name)
        normalized_source = title if title != "Без назви" else str(raw_title or name or "")
        normalized = normalize_financial_category(normalized_source, saved_category, saved_subcategory)
        if normalized["category"] != normalized_category:
            continue
        print(
            "[DB] "
            f"action=category_details_item user_id={user_id} category={normalized_category} "
            f"expense_title={title!r} amount={int(amount or 0)}"
        )
        key = title.casefold()
        title_labels.setdefault(key, title)
        title_totals[key] += int(amount or 0)

    total = sum(title_totals.values())
    print(
        "[DB] "
        f"action=category_details user_id={user_id} category={normalized_category} "
        f"date_from={date_from.isoformat(sep=' ', timespec='seconds') if date_from else None} "
        f"date_to={date_to.isoformat(sep=' ', timespec='seconds') if date_to else None} "
        f"table=expenses db={db_path} rows_count={len(title_totals)}"
    )
    if total == 0:
        return f"{format_category_label(normalized_category)}\n\nДаних поки немає."

    lines = [
        format_category_label(normalized_category),
        "",
        f"💰 Разом: {format_amount(total)} грн",
        "",
    ]

    for key, amount in sorted(title_totals.items(), key=lambda item: item[1], reverse=True)[:limit]:
        lines.append(f"• {title_labels[key]} — {format_amount(amount)} грн")

    return "\n".join(lines)
