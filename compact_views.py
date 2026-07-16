from datetime import datetime

from category_detector import CATEGORY_EMOJI, detect_category_local, format_category_label, normalize_financial_category


def format_amount(amount: int | float) -> str:
    return f"{int(amount):,}".replace(",", " ")


def format_display_date(value: str) -> str:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:19], fmt).strftime("%d.%m")
        except ValueError:
            continue
    return value[:5]


def format_type_label(expense_type: str | None) -> str:
    if expense_type == "планова":
        return "Планова"
    if expense_type == "емоційна":
        return "Емоційна"
    return "Не вказано"


def format_expense_card(
    name: str,
    amount: int,
    date: str,
    expense_type: str | None,
    category: str | None,
) -> str:
    return "\n".join(
        [
            name.capitalize(),
            "",
            "💸 Ціна:",
            f"{format_amount(amount)} грн",
            "",
            "📂 Категорія:",
            format_category_label(normalize_financial_category(name, category)["category"]).split(maxsplit=1)[1],
            "",
            "📌 Тип:",
            format_type_label(expense_type),
            "",
            "📅 Дата:",
            format_display_date(date),
        ]
    )


def _expense_emoji(name: str, category: str | None) -> str:
    normalized = normalize_financial_category(name, category)["category"]
    detected = detect_category_local(name)
    if detected == "їжа" and "кава" in name.strip().lower():
        return "☕"
    if detected == "здоров’я":
        return "💊"
    if detected == "транспорт":
        return "🚕"
    if detected == "покупки":
        return "👗"
    return CATEGORY_EMOJI.get(normalized, "")


def format_compact_expense_row(
    index: int,
    name: str,
    amount: int,
    date: str,
    expense_type: str | None,
    category: str | None,
) -> str:
    emoji = _expense_emoji(name, category)
    prefix = f"{emoji} " if emoji else ""
    return (
        f"{index}. {prefix}{name.capitalize()} — {format_amount(amount)} грн "
        f"• {format_type_label(expense_type)} • {format_display_date(date)}"
    )


def format_save_confirmation(
    name: str,
    amount: int,
    category: str | None = None,
    expense_type: str | None = None,
) -> str:
    emoji = _expense_emoji(name, category)
    prefix = f"{emoji} " if emoji else ""
    line = f"{prefix}{name.capitalize()} — {format_amount(amount)} грн"
    if expense_type:
        line = f"{line} • {format_type_label(expense_type)}"
    return f"✅ Зафіксовано\n\n{line}"


def format_compact_expenses_list(
    expenses: list[tuple[int, str, int, str, str | None, str | None]],
    total_count: int,
    title: str | None = None,
    footer: str | None = None,
) -> str:
    lines = [title, ""] if title else []
    lines.append("📋 Витрати")

    for index, (_, name, amount, date, expense_type, category) in enumerate(expenses, start=1):
        lines.append(format_compact_expense_row(index, name, amount, date, expense_type, category))

    remaining = total_count - len(expenses)
    if remaining > 0:
        lines.extend(["", f"... ще {remaining} витрат"])

    total_sum = sum(amount for _, _, amount, _, _, _ in expenses)
    emotional_sum = sum(amount for _, _, amount, _, expense_type, _ in expenses if expense_type == "емоційна")
    lines.extend(["", f"💸 Разом: {format_amount(total_sum)} грн", f"🔥 Емоційні: {format_amount(emotional_sum)} грн"])

    if footer:
        lines.extend(["", footer])

    return "\n".join(lines).strip()
