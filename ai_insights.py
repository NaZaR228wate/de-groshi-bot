from typing import Any


def build_stats_insight(total: int, emotional_percent: float, top_categories: list[tuple[str, int]]) -> str:
    if total <= 0:
        return ""

    leader = top_categories[0][0] if top_categories else None

    if emotional_percent >= 50:
        if leader:
            return f"Багато імпульсивних витрат, найбільше тисне категорія {leader} 👀"
        return "Багато імпульсивних витрат. Тут варто придивитись уважніше 👀"

    if emotional_percent >= 25:
        if leader:
            return f"Основний фокус зараз — {leader}. Емоційні витрати помітні, але не критичні."
        return "Емоційні витрати помітні, але загалом картина контрольована."

    if leader:
        return f"Основні витрати виглядають регулярними. Найбільше зараз йде на {leader}."

    return "Витрати виглядають досить спокійно. Емоційних покупок небагато 👌"


def build_month_ai_summary(report: dict[str, Any]) -> str:
    if not report.get("transactions_count") and not report.get("transactions"):
        return "Даних поки мало для точного висновку."

    categories = report.get("top_categories") or []
    emotional = report.get("emotional_percent", 0)
    if categories:
        leader = categories[0].get("name") if isinstance(categories[0], dict) else categories[0][0]
        if emotional >= 50:
            return f"Головний напрям витрат — {leader}. Емоційна частка висока, тому частину покупок варто переглянути."
        return f"Найбільше грошей йде на {leader}. Загальна структура виглядає досить зрозуміло."

    return "Витрати є, але категорій поки замало для сильного висновку."
