import asyncio
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from dotenv import load_dotenv

from ai_insights import build_stats_insight
from category_details import build_category_details
from category_detector import (
    NORMALIZED_CATEGORIES,
    format_category_label,
    normalize_financial_category,
)
from compact_views import format_compact_expenses_list, format_save_confirmation
from monthly_report import (
    build_category_drilldown,
    generate_month_categories,
    generate_month_report,
    get_month_report_categories,
    get_report_months,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH_RAW = os.getenv("DB_PATH", "expenses.db")
DB_PATH = DB_PATH_RAW if os.path.isabs(DB_PATH_RAW) else os.path.join(BASE_DIR, DB_PATH_RAW)
TABLES = {
    "users": "users",
    "expenses": "expenses",
    "payments_pending": "payments_pending",
}
ADMIN_USER_ID_RAW = os.getenv("ADMIN_USER_ID")
try:
    ADMIN_USER_ID = int(ADMIN_USER_ID_RAW) if ADMIN_USER_ID_RAW else None
except ValueError:
    ADMIN_USER_ID = None
MONO_CARD = os.getenv("MONO_CARD", "4441111007746765")
PRIVAT_CARD = os.getenv("PRIVAT_CARD", "5168752028189226")

ADD_EXPENSE_BUTTON = "➕ Додати витрату"
STATS_BUTTON = "📊 Статистика"
LIST_BUTTON = "📋 Список"
COMPARE_BUTTON = "📈 Порівняння"
REPORT_BUTTON = "📅 Звіт"
OTHER_BUTTON = "⚙️ Налаштування"
MANUAL_ADD_BUTTON = "✍️ Самостійно"
QUICK_ADD_BUTTON = "⚡ Швидкий вибір"

FOOD_BUTTON = "🍔 Їжа"
TRANSPORT_BUTTON = "🚕 Транспорт"
SHOPPING_BUTTON = "🛍 Покупки"
HOME_BUTTON = "🏠 Дім"
FUN_BUTTON = "🎮 Розваги"
HEALTH_BUTTON = "💊 Здоров’я"
KIDS_BUTTON = "👶 діти"

EDIT_BUTTON = "✏️ Редагувати"
DELETE_BUTTON = "🗑 Видалити"
MY_ACCESS_BUTTON = "💳 Мій доступ"
HOW_IT_WORKS_BUTTON = "❓ як це працює"
BACK_BUTTON = "🔙 Назад"
STATS_TODAY_BUTTON = "Сьогодні"
STATS_YESTERDAY_BUTTON = "Вчора"
STATS_WEEK_BUTTON = "Тиждень"
STATS_MONTH_BUTTON = "Місяць"
STATS_YEAR_BUTTON = "Рік"
STATS_ALL_BUTTON = "📊 За весь час"
STATS_RECOMMENDATIONS_BUTTON = "💡 Рекомендації"
CUSTOM_PERIOD_BUTTON = "📅 Обрати період"
STATS_BACK_BUTTON = "⬅️ Назад"

STATS_PERIOD_BUTTONS = {
    STATS_TODAY_BUTTON,
    STATS_YESTERDAY_BUTTON,
    STATS_WEEK_BUTTON,
    STATS_MONTH_BUTTON,
    STATS_YEAR_BUTTON,
    STATS_ALL_BUTTON,
    STATS_RECOMMENDATIONS_BUTTON,
    CUSTOM_PERIOD_BUTTON,
}
ADD_FLOW_NAVIGATION_BUTTONS = {
    ADD_EXPENSE_BUTTON,
    STATS_BUTTON,
    LIST_BUTTON,
    REPORT_BUTTON,
    OTHER_BUTTON,
    EDIT_BUTTON,
    DELETE_BUTTON,
    MY_ACCESS_BUTTON,
    HOW_IT_WORKS_BUTTON,
    *STATS_PERIOD_BUTTONS,
}

ERROR_FORMAT_MESSAGE = "Напиши витрату у форматі: кава 80"
HOW_IT_WORKS_TEXT = """❓ як це працює

цей бот допомагає зрозуміти, куди реально йдуть гроші.

не потрібно вести таблиці, рахувати вручну або згадувати ввечері, на що пішли кошти.

ти просто записуєш витрати протягом дня.

приклади:

кава 80
таксі 220
продукти 640
паливо 1200

бот збере ці витрати і покаже картину:
— скільки витрачено за день
— скільки за тиждень
— скільки за місяць
— яка частина витрат була планова
— яка частина була емоційна

---

що таке планова витрата?

📌 планова — це витрата, яку ти очікував.

наприклад:
— продукти
— дорога
— паливо
— ліки
— комунальні
— запланована покупка
— те, без чого сьогодні було складно обійтись

простими словами:
якщо ти приблизно знав, що ця витрата буде — це планова.

---

що таке емоційна витрата?

🔥 емоційна — це витрата, яку ти не планував.

наприклад:
— кава «просто захотілось»
— солодке
— дрібна покупка на емоціях
— зайвий одяг
— доставка, хоча можна було без неї
— покупка після стресу
— «побачив і купив»

простими словами:
якщо покупка була не обовʼязкова і більше про настрій — це емоційна.

---

а якщо я не знаю, що обрати?

це нормально.

не треба робити ідеально.

обирай той варіант, який ближчий по відчуттях.

головна ціль — не покарати себе за витрати, а побачити реальну картину.

навіть якщо інколи помилишся, загальна картина все одно буде корисною.

---

як користуватись щодня?

1. купив щось — одразу записав
2. вказав назву і суму
3. обрав тип: планова або емоційна
4. ввечері відкрив статистику
5. подивився, куди пішли гроші

найкраще записувати витрати одразу після покупки.
так ти не забудеш дрібниці.

саме дрібні витрати часто і створюють відчуття:
«ніби нічого не купував, а грошей немає».

---

що показує статистика?

📊 статистика показує:
— загальну суму витрат
— планові витрати
— емоційні витрати
— суму емоційних витрат
— порівняння з іншими періодами
— загальну поведінку по грошах

можна дивитись:
— сьогодні
— вчора
— тиждень
— місяць
— рік
— за весь час
— свій період від і до

---

що показує список?

📋 список — це всі твої витрати за обраний період.

там видно:
— назву
— суму
— категорію
— дату
— тип витрати

це корисно, коли треба згадати:
«а що саме я купував?»

---

що таке рекомендації?

🎯 рекомендації — це підказки на основі твоїх витрат.

бот дивиться:
— де найбільше витрат
— чи багато емоційних покупок
— чи ростуть витрати
— яка категорія забирає найбільше грошей

і дає просту пораду, що можна змінити.

не 20 порад одразу.
тільки кілька конкретних речей, з яких реально почати.

---

як отримати результат за 7 днів?

просто записуй витрати кожного дня.

через 7 днів ти вже побачиш:
— куди йде найбільше грошей
— які витрати повторюються
— де емоційні покупки
— що можна зменшити без болю
— де гроші «витікають» непомітно

бот не змушує економити на всьому.
він допомагає побачити, що саме варто контролювати.

---

головне правило:

не треба бути ідеальним.

треба просто фіксувати.

бо контроль починається не тоді, коли ти все заборонив собі.

контроль починається тоді, коли ти нарешті бачиш цифри."""

PERIOD_DAY = "day"
PERIOD_YESTERDAY = "yesterday"
PERIOD_WEEK = "week"
PERIOD_MONTH = "month"
PERIOD_YEAR = "year"
PERIOD_ALL = "all"
USERS_PER_PAGE = 10
CUSTOM_PERIOD_RECORD_LIMIT = 1000
UKRAINIAN_MONTHS = {
    1: "січня",
    2: "лютого",
    3: "березня",
    4: "квітня",
    5: "травня",
    6: "червня",
    7: "липня",
    8: "серпня",
    9: "вересня",
    10: "жовтня",
    11: "листопада",
    12: "грудня",
}
UKRAINIAN_MONTH_NAMES = {
    1: "січень",
    2: "лютий",
    3: "березень",
    4: "квітень",
    5: "травень",
    6: "червень",
    7: "липень",
    8: "серпень",
    9: "вересень",
    10: "жовтень",
    11: "листопад",
    12: "грудень",
}
UKRAINIAN_MONTH_WORDS = set(UKRAINIAN_MONTHS.values()) | set(UKRAINIAN_MONTH_NAMES.values())


def is_service_expense_title(value: str | None) -> bool:
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
    if normalized in {month.casefold() for month in UKRAINIAN_MONTH_WORDS}:
        return True
    month_pattern = "|".join(re.escape(month.casefold()) for month in UKRAINIAN_MONTH_WORDS)
    if re.fullmatch(rf"({month_pattern})\s+\d{{4}}", normalized):
        return True
    if re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", normalized):
        return True
    if re.fullmatch(r"\d{1,2}[.\-/]\d{1,2}([.\-/]\d{2,4})?", normalized):
        return True

    return bool(
        re.fullmatch(rf"\d{{1,2}}\s+({month_pattern})", normalized)
        or re.fullmatch(rf"\d{{1,2}}\s+({month_pattern})\s+.+", normalized)
        or re.fullmatch(rf"\d{{1,2}}\s+({month_pattern})\s+[—-]\s+({month_pattern})", normalized)
        or re.fullmatch(rf"\d{{1,2}}\s+({month_pattern})\s+[—-]\s+\d{{1,2}}\s+({month_pattern})", normalized)
    )


def safe_expense_title(*candidates: object) -> str:
    for candidate in candidates:
        title = str(candidate or "").strip()
        if title and not is_service_expense_title(title):
            return title
    return "Без назви"

CATEGORY_MENUS = {
    FOOD_BUTTON: ["☕ Кава", "🍕 Фастфуд", "🥗 Продукти", "🍽 Ресторан", "🍣 Суші", "🥤 Напої"],
    TRANSPORT_BUTTON: ["⛽ Бензин", "🔧 СТО", "🚕 Транспорт"],
    SHOPPING_BUTTON: ["👕 Одяг", "📱 Техніка", "🎁 Подарунки", "🧴 Побутове", "🛒 Магазин"],
    HOME_BUTTON: ["💡 Комуналка", "🏠 Оренда", "🪑 Меблі", "🧽 Дім", "🔨 Ремонт"],
    FUN_BUTTON: ["🎬 Кіно", "🎮 Ігри", "🍻 Відпочинок", "🎵 Музика", "⚽ Спорт"],
    HEALTH_BUTTON: ["💊 Ліки", "🩺 Лікар", "🦷 Стоматолог", "🏥 Аналізи", "🏋️ Спорт"],
    KIDS_BUTTON: ["🧸 Іграшки", "🍭 Солодке", "🎮 Ігри", "💸 Кишенькові", "📚 Школа", "👕 Одяг дітям"],
}
CATEGORY_BUTTONS = set(CATEGORY_MENUS)
SUBCATEGORY_TO_NAME = {
    button: re.sub(r"^[^\wА-Яа-яІіЇїЄєҐґ]+", "", button).strip().lower()
    for buttons in CATEGORY_MENUS.values()
    for button in buttons
}
CATEGORY_NAME_EMOJI = {
    name: button.split(maxsplit=1)[0]
    for button, name in SUBCATEGORY_TO_NAME.items()
}
CATEGORY_NAME_TAG = {}
for category_button, buttons in CATEGORY_MENUS.items():
    category_name = re.sub(r"^[^\wА-Яа-яІіЇїЄєҐґ]+", "", category_button).strip().lower()
    for button in buttons:
        CATEGORY_NAME_TAG[SUBCATEGORY_TO_NAME[button]] = category_name
CATEGORY_TAG_EMOJI = {
    "їжа": "🥗",
    "транспорт": "🚕",
    "покупки": "🛍",
    "дім": "🏠",
    "розваги": "🎮",
    "здоров’я": "💊",
    "діти": "👶",
}

router = Router()
EDITING_EXPENSES: dict[int, int] = {}
GRANT_ACCESS_DAYS: dict[int, int] = {}
QUICK_REPEAT_DATA: dict[int, dict[str, object]] = {}


class ExpenseStates(StatesGroup):
    add_menu = State()
    choosing_category = State()
    choosing_subcategory = State()
    waiting_amount = State()
    category_menu = State()
    subcategory_menu = State()
    waiting_expense_input = State()
    waiting_expense_name = State()
    waiting_expense_amount = State()
    waiting_for_amount = State()
    waiting_for_new_data = State()
    waiting_for_type = State()
    grant_waiting_user_id = State()
    waiting_message = State()
    stats_menu = State()
    list_menu = State()
    period_choice_menu = State()
    waiting_date_from = State()
    waiting_date_to = State()


def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADD_EXPENSE_BUTTON)],
            [KeyboardButton(text=STATS_BUTTON)],
            [KeyboardButton(text=OTHER_BUTTON)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Вибери дію...",
    )


def get_add_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MANUAL_ADD_BUTTON), KeyboardButton(text=QUICK_ADD_BUTTON)],
            [KeyboardButton(text=BACK_BUTTON)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Вибери спосіб...",
    )


def get_expense_input_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=STATS_BACK_BUTTON)],
        ],
        resize_keyboard=True,
        input_field_placeholder="кава 80",
    )


def quick_repeat_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Повторити", callback_data="quick_repeat")],
            [InlineKeyboardButton(text="➕ Ще витрата", callback_data="quick_more")],
            [InlineKeyboardButton(text="🏠 Головне меню", callback_data="quick_home")],
        ]
    )


def get_report_months_keyboard(months: list[tuple[int, int, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"report_month:{year}:{month}",
                )
            ]
            for year, month, label in months
        ]
    )


def get_selected_month_report_keyboard(year: int, month: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 По категоріях",
                    callback_data=f"report_categories:{year}:{month}",
                )
            ],
        ]
    )


def get_report_categories_keyboard(year: int, month: int, categories: list[str]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=format_category_label(category),
                callback_data=f"catdet:month:{year}:{month}:{category}",
            )
        ]
        for category in categories[:7]
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад до звіту",
                callback_data=f"report_month:{year}:{month}",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def category_details_keyboard(categories: list[tuple[str, int]], scope: str = "all") -> InlineKeyboardMarkup | None:
    rows = [
        [
            InlineKeyboardButton(
                text=f"🔎 Детальніше: {format_category_label(category)}",
                callback_data=f"catdet:{scope}:{category}",
            )
        ]
        for category, _ in categories[:3]
        if category
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def range_scope(date_from: datetime, date_to: datetime) -> str:
    return f"range:{date_from.strftime('%Y%m%d')}:{date_to.strftime('%Y%m%d')}"


def get_categories_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=FOOD_BUTTON), KeyboardButton(text=TRANSPORT_BUTTON)],
            [KeyboardButton(text=SHOPPING_BUTTON), KeyboardButton(text=HOME_BUTTON)],
            [KeyboardButton(text=FUN_BUTTON), KeyboardButton(text=HEALTH_BUTTON)],
            [KeyboardButton(text=KIDS_BUTTON)],
            [KeyboardButton(text=BACK_BUTTON)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Вибери категорію...",
    )


def get_other_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=HOW_IT_WORKS_BUTTON)],
            [KeyboardButton(text=EDIT_BUTTON), KeyboardButton(text=DELETE_BUTTON)],
            [KeyboardButton(text=MY_ACCESS_BUTTON)],
            [KeyboardButton(text=BACK_BUTTON)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Вибери дію...",
    )


def get_stats_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=STATS_TODAY_BUTTON), KeyboardButton(text=STATS_YESTERDAY_BUTTON)],
            [KeyboardButton(text=STATS_WEEK_BUTTON), KeyboardButton(text=STATS_MONTH_BUTTON)],
            [KeyboardButton(text=STATS_YEAR_BUTTON), KeyboardButton(text=STATS_ALL_BUTTON)],
            [KeyboardButton(text=STATS_RECOMMENDATIONS_BUTTON)],
            [KeyboardButton(text=CUSTOM_PERIOD_BUTTON)],
            [KeyboardButton(text=STATS_BACK_BUTTON)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Обери період...",
    )


def get_list_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=STATS_TODAY_BUTTON), KeyboardButton(text=STATS_YESTERDAY_BUTTON)],
            [KeyboardButton(text=STATS_WEEK_BUTTON), KeyboardButton(text=STATS_MONTH_BUTTON)],
            [KeyboardButton(text=STATS_ALL_BUTTON)],
            [KeyboardButton(text=CUSTOM_PERIOD_BUTTON)],
            [KeyboardButton(text=STATS_BACK_BUTTON)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Обери період...",
    )


def get_period_choice_keyboard(periods: list[dict[str, str]]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=period["label"])]
            for period in periods
        ] + [[KeyboardButton(text=STATS_BACK_BUTTON)]],
        resize_keyboard=True,
        input_field_placeholder="Обери період...",
    )


def get_stats_month_choice_keyboard(periods: list[dict[str, str]]) -> InlineKeyboardMarkup:
    rows = []
    for period in periods:
        date_from = datetime.fromisoformat(str(period["from"]))
        rows.append(
            [
                InlineKeyboardButton(
                    text=str(period["label"]).removeprefix("📅 ").strip(),
                    callback_data=f"stats_month:{date_from.year}-{date_from.month:02d}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="stats_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def period_years_keyboard(mode: str, years: list[int]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=str(year), callback_data=f"period_year_{mode}*{year}")]
            for year in years
        ] + [[InlineKeyboardButton(text="⬅️ назад", callback_data=f"period_back_{mode}")]]
    )


def period_months_keyboard(mode: str, year: int, months: list[int]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=UKRAINIAN_MONTH_NAMES[month],
                    callback_data=f"period_month*{mode}*{year}*{month}",
                )
            ]
            for month in months
        ] + [[InlineKeyboardButton(text="⬅️ назад", callback_data=f"period_back_years*{mode}")]]
    )


def period_days_keyboard(mode: str, year: int, month: int, days: list[int]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{day:02d} {UKRAINIAN_MONTHS[month]}",
                    callback_data=f"period_day_{mode}*{year}*{month}*{day}",
                )
            ]
            for day in days
        ] + [
            [InlineKeyboardButton(text="📅 весь місяць", callback_data=f"period_full_month*{mode}*{year}*{month}")],
            [InlineKeyboardButton(text="⬅️ назад", callback_data=f"period_back_months*{mode}*{year}")],
        ]
    )


def get_category_keyboard(category: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            *[[KeyboardButton(text=button)] for button in CATEGORY_MENUS[category]],
            [KeyboardButton(text=BACK_BUTTON)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Вибери підкатегорію...",
    )


def create_db() -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL,
                expense_title TEXT,
                amount INTEGER NOT NULL,
                date TEXT,
                type TEXT,
                category TEXT,
                subcategory TEXT,
                raw_title TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                is_paid INTEGER DEFAULT 0,
                access_until TEXT,
                created_at TEXT,
                last_active TEXT,
                last_notified TEXT,
                last_activity TEXT,
                last_reminder TEXT,
                reminded_1 INTEGER DEFAULT 0,
                reminded_expired INTEGER DEFAULT 0,
                last_remind_at INTEGER,
                expired_notified INTEGER DEFAULT 0,
                expiring_notified INTEGER DEFAULT 0,
                can_message INTEGER DEFAULT 1,
                send_fail_count INTEGER DEFAULT 0,
                last_auto_message_at INTEGER,
                trial_started_at INTEGER,
                shown_3_expenses_hint INTEGER DEFAULT 0,
                last_paywall_shown TEXT,
                last_support_sent_at INTEGER,
                support_active INTEGER DEFAULT 0,
                streak_days INTEGER DEFAULT 0,
                last_entry_date TEXT,
                bonus_used INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                badges TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS payments_pending (
                user_id INTEGER,
                username TEXT,
                tariff INTEGER,
                amount INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )
            """
        )

        columns = [row[1] for row in connection.execute("PRAGMA table_info(expenses)")]
        if "user_id" not in columns:
            connection.execute("ALTER TABLE expenses ADD COLUMN user_id INTEGER")
        if "name" not in columns and "title" in columns:
            connection.execute("ALTER TABLE expenses ADD COLUMN name TEXT NOT NULL DEFAULT ''")
            connection.execute("UPDATE expenses SET name = title WHERE name = ''")
        if "type" not in columns:
            connection.execute("ALTER TABLE expenses ADD COLUMN type TEXT")
        if "category" not in columns:
            connection.execute("ALTER TABLE expenses ADD COLUMN category TEXT")
        if "subcategory" not in columns:
            connection.execute("ALTER TABLE expenses ADD COLUMN subcategory TEXT")
        if "raw_title" not in columns:
            connection.execute("ALTER TABLE expenses ADD COLUMN raw_title TEXT")
        if "expense_title" not in columns:
            connection.execute("ALTER TABLE expenses ADD COLUMN expense_title TEXT")

        rows = connection.execute(
            "SELECT id, name, category, subcategory, raw_title, expense_title FROM expenses"
        ).fetchall()
        for expense_id, name, category, subcategory, raw_title, expense_title in rows:
            display_title = safe_expense_title(expense_title, raw_title, name)
            raw = display_title if display_title != "Без назви" else ""
            normalized = normalize_financial_category(raw, category, subcategory)
            connection.execute(
                """
                UPDATE expenses
                SET raw_title = ?, expense_title = ?, category = ?, subcategory = ?
                WHERE id = ?
                """,
                (
                    normalized["raw_title"],
                    display_title,
                    normalized["category"],
                    normalized["subcategory"],
                    expense_id,
                ),
            )

        user_columns = [row[1] for row in connection.execute("PRAGMA table_info(users)")]
        if "username" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN username TEXT")
        if "is_paid" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN is_paid INTEGER DEFAULT 0")
        if "access_until" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN access_until TEXT")
        if "created_at" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
            connection.execute(
                "UPDATE users SET created_at = COALESCE(last_activity, datetime('now','localtime')) WHERE created_at IS NULL"
            )
        if "last_active" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN last_active TEXT")
            connection.execute("UPDATE users SET last_active = last_activity WHERE last_active IS NULL")
        if "last_notified" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN last_notified TEXT")
        if "last_activity" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN last_activity TEXT")
        if "last_reminder" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN last_reminder TEXT")
        if "reminded_1" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN reminded_1 INTEGER DEFAULT 0")
        if "reminded_expired" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN reminded_expired INTEGER DEFAULT 0")
        if "last_remind_at" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN last_remind_at INTEGER")
        if "expired_notified" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN expired_notified INTEGER DEFAULT 0")
        if "expiring_notified" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN expiring_notified INTEGER DEFAULT 0")
        if "can_message" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN can_message INTEGER DEFAULT 1")
        if "send_fail_count" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN send_fail_count INTEGER DEFAULT 0")
        if "last_auto_message_at" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN last_auto_message_at INTEGER")
        if "trial_started_at" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN trial_started_at INTEGER")
        if "shown_3_expenses_hint" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN shown_3_expenses_hint INTEGER DEFAULT 0")
        if "last_paywall_shown" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN last_paywall_shown TEXT")
        if "last_support_sent_at" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN last_support_sent_at INTEGER")
        if "support_active" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN support_active INTEGER DEFAULT 0")
        if "streak_days" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN streak_days INTEGER DEFAULT 0")
        if "last_entry_date" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN last_entry_date TEXT")
        if "bonus_used" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN bonus_used INTEGER DEFAULT 0")
        if "xp" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0")
        if "level" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1")
        if "badges" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN badges TEXT")

        payment_columns = [row[1] for row in connection.execute("PRAGMA table_info(payments_pending)")]
        if "username" not in payment_columns:
            connection.execute("ALTER TABLE payments_pending ADD COLUMN username TEXT")
        if "tariff" not in payment_columns:
            connection.execute("ALTER TABLE payments_pending ADD COLUMN tariff INTEGER")
        if "status" not in payment_columns:
            connection.execute("ALTER TABLE payments_pending ADD COLUMN status TEXT DEFAULT 'pending'")


def update_user_activity(user_id: int, username: str | None = None) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO users (user_id, username, is_paid, created_at, last_active, last_activity, last_reminder)
            VALUES (?, ?, 0, datetime('now','localtime'), datetime('now','localtime'), datetime('now','localtime'), NULL)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                last_active = datetime('now','localtime'),
                last_activity = datetime('now','localtime')
            """,
            (user_id, username),
        )


def get_user(user_id: int) -> dict[str, Any]:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT user_id, username, is_paid, access_until, created_at, last_active,
                   last_notified, last_activity, last_reminder,
                   reminded_1, reminded_expired, last_remind_at,
                   expired_notified, expiring_notified, can_message,
                   trial_started_at, shown_3_expenses_hint, last_paywall_shown,
                   last_support_sent_at, support_active,
                   streak_days, last_entry_date, bonus_used,
                   xp, level, badges
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        if row is None:
            connection.execute(
                """
                INSERT INTO users (user_id, is_paid, created_at)
                VALUES (?, 0, datetime('now','localtime'))
                """,
                (user_id,),
            )
            row = connection.execute(
                """
                SELECT user_id, username, is_paid, access_until, created_at, last_active,
                       last_notified, last_activity, last_reminder,
                       reminded_1, reminded_expired, last_remind_at,
                       expired_notified, expiring_notified, can_message,
                       trial_started_at, shown_3_expenses_hint, last_paywall_shown,
                       last_support_sent_at, support_active,
                       streak_days, last_entry_date, bonus_used,
                       xp, level, badges
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

    return dict(row)


def has_access(user_or_id: dict[str, Any] | int) -> bool:
    user = get_user(user_or_id) if isinstance(user_or_id, int) else user_or_id
    user_id = int(user["user_id"])
    result = False
    if user["is_paid"] == 0:
        print(f"[ACCESS CHECK] user={user_id} result={result}")
        return result
    if user["access_until"] is None:
        print(f"[ACCESS CHECK] user={user_id} result={result}")
        return result
    result = datetime.now() <= datetime.fromisoformat(user["access_until"])
    print(f"[ACCESS CHECK] user={user_id} result={result}")
    return result


def check_access(user_id: int) -> bool:
    return has_access(get_user(user_id))


def should_show_paywall(user: dict[str, Any], force: bool = False) -> bool:
    if force:
        return True
    last_shown = user.get("last_paywall_shown")
    if not last_shown:
        return True
    return datetime.now() - datetime.fromisoformat(last_shown) >= timedelta(seconds=10)


def mark_paywall_shown(user_id: int) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "UPDATE users SET last_paywall_shown = ? WHERE user_id = ?",
            (datetime.now().isoformat(timespec="seconds"), user_id),
        )


def grant_access(user_id: int, days: int) -> str:
    access_until = (datetime.now() + timedelta(days=days)).isoformat(timespec="seconds")
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO users (user_id, is_paid, access_until)
            VALUES (?, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                is_paid = 1,
                access_until = excluded.access_until,
                last_notified = NULL,
                reminded_1 = 0,
                reminded_expired = 0,
                expiring_notified = 0,
                expired_notified = 0,
                send_fail_count = 0,
                last_auto_message_at = NULL,
                can_message = 1,
                last_paywall_shown = NULL
            """,
            (user_id, access_until),
        )
    print(f"[GRANT] user={user_id} days={days}")
    return access_until


def save_payment_pending(user_id: int, username: str, tariff: int) -> None:
    amount = 290 if tariff == 7 else 390 if tariff == 30 else 0
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO payments_pending (user_id, username, tariff, amount, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', datetime('now','localtime'))
            """,
            (user_id, username, tariff, amount),
        )


def get_pending_payment(user_id: int) -> dict[str, Any] | None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT user_id, username, tariff, amount, status, created_at
            FROM payments_pending
            WHERE user_id = ? AND status = 'pending'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def approve_payment(user_id: int, days: int) -> str:
    access_until = grant_access(user_id, days)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            UPDATE payments_pending
            SET status = 'approved'
            WHERE user_id = ? AND status = 'pending'
            """,
            (user_id,),
        )
    return access_until


def reject_payment(user_id: int) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            UPDATE payments_pending
            SET status = 'rejected'
            WHERE user_id = ? AND status = 'pending'
            """,
            (user_id,),
        )


def revoke_access(user_id: int) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            UPDATE users
            SET is_paid = 0,
                access_until = NULL,
                reminded_1 = 0,
                reminded_expired = 0
            WHERE user_id = ?
            """,
            (user_id,),
        )


def update_last_notified(user_id: int) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "UPDATE users SET last_notified = date('now','localtime') WHERE user_id = ?",
            (user_id,),
        )


def get_users_for_reminders() -> list[tuple[int, str | None, str | None]]:
    with sqlite3.connect(DB_PATH) as connection:
        return connection.execute(
            """
            SELECT user_id, last_activity, last_reminder
            FROM users
            WHERE is_paid = 1
              AND access_until IS NOT NULL
              AND datetime(access_until) >= datetime('now','localtime')
            """
        ).fetchall()


def update_last_reminder(user_id: int) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "UPDATE users SET last_reminder = date('now','localtime') WHERE user_id = ?",
            (user_id,),
        )


def access_until_to_timestamp(value: str | int | float | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    value_text = str(value)
    if value_text.isdigit():
        return int(value_text)
    parsed = parse_db_datetime(value_text)
    return int(parsed.timestamp()) if parsed else None


def get_all_users_for_auto_messages() -> list[dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT user_id, username, is_paid, access_until, last_active, created_at,
                   last_remind_at, expired_notified, expiring_notified, can_message,
                   send_fail_count, last_auto_message_at
            FROM users
            WHERE COALESCE(last_active, created_at) IS NOT NULL
            """
        ).fetchall()
    return [dict(row) for row in rows]


def update_last_remind(user_id: int, timestamp: int) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "UPDATE users SET last_remind_at = ? WHERE user_id = ?",
            (timestamp, user_id),
        )


def update_can_message(user_id: int, value: int) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "UPDATE users SET can_message = ? WHERE user_id = ?",
            (value, user_id),
        )


def increment_fail(user_id: int) -> int:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            UPDATE users
            SET send_fail_count = COALESCE(send_fail_count, 0) + 1
            WHERE user_id = ?
            """,
            (user_id,),
        )
        row = connection.execute(
            "SELECT COALESCE(send_fail_count, 0) FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return int(row[0]) if row else 0


def mark_auto_message_sent(user_id: int, timestamp: int) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            UPDATE users
            SET last_auto_message_at = ?,
                send_fail_count = 0
            WHERE user_id = ?
            """,
            (timestamp, user_id),
        )


def mark_expired_notified(user_id: int) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            UPDATE users
            SET expired_notified = 1,
                reminded_expired = 1
            WHERE user_id = ?
            """,
            (user_id,),
        )


def mark_expiring_soon_notified(user_id: int) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            UPDATE users
            SET expiring_notified = 1,
                reminded_1 = 1
            WHERE user_id = ?
            """,
            (user_id,),
        )


async def safe_auto_send(bot: Bot, user: dict[str, Any], text: str, now: int) -> bool:
    user_id = int(user["user_id"])
    try:
        await bot.send_message(user_id, text, reply_markup=payment_keyboard())
        mark_auto_message_sent(user_id, now)
        return True
    except Exception as e:
        print(f"[ERROR SEND] {user_id} -> {e}")

    await asyncio.sleep(2)
    try:
        await bot.send_message(user_id, text, reply_markup=payment_keyboard())
        mark_auto_message_sent(user_id, now)
        print(f"[AUTO] retry success user={user_id}")
        return True
    except Exception as e:
        fail_count = increment_fail(user_id)
        print(f"[ERROR SEND] {user_id} -> {e}")
        print(f"[AUTO] fail_count={fail_count} user={user_id}")
        if fail_count >= 5:
            update_can_message(user_id, 0)
            print(f"[AUTO] muted user={user_id}")
        return False


def get_users_for_access_reminders() -> list[dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT user_id, is_paid, access_until, reminded_1, reminded_expired
            FROM users
            WHERE is_paid = 1 AND access_until IS NOT NULL
            """
        ).fetchall()
    return [dict(row) for row in rows]


def mark_access_reminder(user_id: int, field: str) -> None:
    if field not in {"reminded_1", "reminded_expired"}:
        return
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(f"UPDATE users SET {field} = 1 WHERE user_id = ?", (user_id,))


async def check_access_reminder(bot: Bot, user: dict[str, Any]) -> None:
    access_until = user.get("access_until")
    if not access_until:
        return

    try:
        expires_at = datetime.fromisoformat(access_until)
    except ValueError:
        return

    now = datetime.now()
    user_id = int(user["user_id"])

    if expires_at < now and not user.get("reminded_expired"):
        print(f"[ACCESS EXPIRED] user={user_id}")
        try:
            await bot.send_message(
                user_id,
                build_expired_paywall_text(user_id),
                reply_markup=payment_keyboard(),
            )
            mark_access_reminder(user_id, "reminded_expired")
        except Exception as e:
            print(f"[ERROR] sending expired reminder: {e}")
        return

    if expires_at - now <= timedelta(days=1) and not user.get("reminded_1"):
        try:
            await bot.send_message(
                user_id,
                build_expiring_paywall_text(expires_at),
                reply_markup=payment_keyboard(),
            )
            mark_access_reminder(user_id, "reminded_1")
        except Exception as e:
            print(f"[ERROR] sending 1-day reminder: {e}")
        return

    if expires_at - now <= timedelta(days=1) and not user.get("reminded_1"):
        try:
            await bot.send_message(
                user_id,
                "доступ закінчується завтра ⏳\n👉 продовжити доступ",
                reply_markup=payment_keyboard(),
            )
            mark_access_reminder(user_id, "reminded_1")
        except Exception as e:
            print(f"[ERROR] sending 1-day reminder: {e}")


def get_yesterday_sum(user_id: int) -> int:
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses
            WHERE date(date) = date('now','-1 day','localtime')
              AND user_id = ?
            """,
            (user_id,),
        ).fetchone()
    return int(row[0])


def get_user_total_and_emotional(user_id: int) -> tuple[int, float]:
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            """
            SELECT
                COALESCE(SUM(amount), 0) AS total,
                COALESCE(SUM(CASE WHEN type = 'емоційна' THEN amount ELSE 0 END), 0) AS emotional
            FROM expenses
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    total = int(row[0])
    emotional = int(row[1])
    percent = emotional * 100 / total if total > 0 else 0
    return total, percent


def get_expired_period_stats(user_id: int) -> tuple[int, int]:
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            """
            SELECT
                COALESCE(SUM(amount), 0) AS total,
                COALESCE(SUM(CASE WHEN type = 'емоційна' THEN amount ELSE 0 END), 0) AS emotional
            FROM expenses
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    total = int(row[0])
    emotional = int(row[1])
    return total, emotional


def get_access_period_stats(user_id: int, access_until: datetime) -> tuple[int, int]:
    user = get_user(user_id)
    trial_started_at = access_until_to_timestamp(user.get("trial_started_at"))
    if trial_started_at is not None:
        from_dt = datetime.fromtimestamp(trial_started_at)
    else:
        now = datetime.now()
        total_days = max(1, (access_until - now).days)
        period_days = 30 if total_days > 7 else 7
        from_dt = now - timedelta(days=period_days)

    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            """
            SELECT
                COALESCE(SUM(amount), 0) AS total,
                COALESCE(SUM(CASE WHEN type = 'емоційна' THEN amount ELSE 0 END), 0) AS emotional
            FROM expenses
            WHERE user_id = ?
              AND datetime(date) >= datetime(?)
            """,
            (user_id, from_dt.isoformat(sep=" ", timespec="seconds")),
        ).fetchone()

    total = int(row[0])
    emotional = int(row[1])
    return total, emotional


def format_remaining_access(access_until: str | int | float | datetime | None) -> str:
    if access_until is None:
        return "доступ закінчився"

    if isinstance(access_until, datetime):
        expires_at = access_until
    elif isinstance(access_until, (int, float)):
        expires_at = datetime.fromtimestamp(access_until)
    else:
        expires_at = parse_db_datetime(str(access_until))

    now = datetime.now()
    if expires_at is None or expires_at <= now:
        return "доступ закінчився"

    diff = expires_at - now
    total_hours = max(1, int(diff.total_seconds() // 3600))
    days = total_hours // 24

    if days >= 2:
        return f"залишилось: {days} дні"
    if days == 1:
        return "залишилось: 1 день"

    return f"залишилось: {total_hours} год"


def build_expiring_paywall_text(access_until: str | int | float | datetime | None) -> str:
    remaining = format_remaining_access(access_until)
    if remaining == "доступ закінчився":
        return build_expired_paywall_text()

    return "\n".join(
        [
            "доступ скоро закінчиться ⏳",
            "",
            remaining,
            "",
            "і ти знову перестанеш бачити,",
            "куди йдуть гроші",
            "",
            "продовжи зараз 👇",
        ]
    )


def _legacy_build_expired_paywall_text(user_id: int | None = None) -> str:
    return (
        "доступ завершено\n\n"
        "продовжи доступ, щоб не втратити контроль над витратами."
    )


def build_expired_paywall_text(user_id: int | None = None) -> str:
    return "\n".join(
        [
            "доступ закінчився ⏳",
            "",
            "щоб знову бачити статистику витрат,",
            "продовжи доступ 👇",
        ]
    )


def build_my_access_text(user_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
    user = get_user(user_id)
    access_until = parse_db_datetime(user.get("access_until"))
    now = datetime.now()
    active = bool(int(user.get("is_paid") or 0) == 1 and access_until and access_until > now)
    days_left = int((access_until.timestamp() - now.timestamp()) // 86400) if access_until else 0
    print(f"[ACCESS] user={user_id} active={active} days_left={days_left}")

    if active and access_until is not None:
        total_sum, emotional_sum = get_access_period_stats(user_id, access_until)
        lines = [
            "💳 Мій доступ",
            "",
            f"📅 Дійсний до: {format_date_ua(access_until)}",
            "",
            f"⏳ Залишилось: {days_left} днів",
            "",
            "📊 За цей період:",
        ]
        if total_sum > 0:
            lines.extend(
                [
                    f"💸 витрати: {format_amount(total_sum)} грн",
                    f"🔥 емоційні: {format_amount(emotional_sum)} грн",
                ]
            )
        else:
            lines.append("витрат ще немає — але це швидко зміниться 👀")
        return "\n".join(lines), None

    if access_until is not None:
        return (
            "\n".join(
                [
                    "💳 доступ завершено",
                    "",
                    "але ти вже побачив(ла), куди реально йдуть гроші",
                    "",
                    "це і є точка, де починаються зміни",
                    "",
                    "👉 продовжи доступ, щоб не втратити контроль",
                ]
            ),
            pay_access_keyboard(),
        )

    return (
        "\n".join(
            [
                "ти ще не підключив(ла) доступ",
                "",
                "але вже через 3–5 днів ти почнеш бачити",
                "де саме зникають гроші",
            ]
        ),
        InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 підключити доступ", callback_data="pay_info")]
            ]
        ),
    )


def amount_personalization_text(total_sum: int) -> str:
    if total_sum < 1000:
        return (
            "це поки невеликі витрати 👌\n\n"
            "але саме з них починається звичка\n"
            "яка потім зʼїдає великі суми"
        )
    if total_sum <= 5000:
        return (
            "ти вже витрачаєш відчутно 👀\n\n"
            "і найцікавіше — ти навіть не помічаєш де саме"
        )
    if total_sum <= 15000:
        return (
            "ти реально втрачаєш гроші 💸\n\n"
            "і це не «трошки»\n\n"
            "це системно"
        )
    return (
        "це вже серйозно\n\n"
        "за місяць це може бути як ще одна зарплата\n\n"
        "і питання не в доході\n"
        "а в контролі"
    )


def access_cta_text() -> str:
    return "саме це можна змінити 👇\n👉 продовжити доступ"


def payment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 7 днів — 290 грн", callback_data="buy_7")],
            [InlineKeyboardButton(text="🔥 30 днів — 390 грн", callback_data="buy_30")],
            [InlineKeyboardButton(text="✅ я оплатив", callback_data="paid")],
        ]
    )


def pay_access_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 7 днів — 290 грн", callback_data="buy_7")],
            [InlineKeyboardButton(text="🔥 30 днів — 390 грн", callback_data="buy_30")],
        ]
    )


def admin_payment_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ підтвердити 7 днів", callback_data=f"confirm_7_{user_id}")],
            [InlineKeyboardButton(text="✅ підтвердити 30 днів", callback_data=f"confirm_30_{user_id}")],
            [InlineKeyboardButton(text="❌ відхилити", callback_data=f"reject_{user_id}")],
        ]
    )


async def send_payment_request_to_admin(bot: Bot, user_id: int, username: str | None, tariff: int) -> None:
    if ADMIN_USER_ID is None or ADMIN_USER_ID <= 0:
        print("ADMIN_USER_ID не заданий")
        return

    username_text = f"@{username}" if username else "без username"
    tariff_line = f"\nтариф: {tariff} днів" if tariff in {7, 30} else ""
    message = (
        "новий запит на доступ 💰\n\n"
        f"user_id: {user_id}\n"
        f"username: {username_text}"
        f"{tariff_line}\n\n"
        "перевір оплату"
    )
    keyboard = admin_payment_keyboard(user_id)

    print(f"[ADMIN] send request → {ADMIN_USER_ID}")
    try:
        # адмін повинен написати /start боту перед тестом
        await bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=message,
            reply_markup=keyboard,
        )
        print(f"[ADMIN] ✅ delivered for user {user_id}")
    except Exception as e:
        print(f"[ADMIN] ❌ error: {e}")


def payment_text(days: int | None = None) -> str:
    if days is not None:
        return "\n".join(
            [
                "для оплати:",
                "",
                f"mono: {MONO_CARD}",
                f"privat: {PRIVAT_CARD}",
                "",
                "після оплати натисни «я оплатив»",
            ]
        )

    return "\n".join(
        [
            "доступ до бота платний 👇",
            "",
            "7 днів — 290 грн",
            "🔥 30 днів — 390 грн",
            "",
            "30 днів вигідніше — різниця лише 100 грн.",
            "",
            "обери варіант:",
        ]
    )


def paid_keyboard(days: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ я оплатив", callback_data=f"paid_{days}")]
        ]
    )


def unpaid_text() -> str:
    return payment_text()


def expired_text(user_id: int) -> str:
    return build_expired_paywall_text(user_id)


def is_admin(user_id: int) -> bool:
    return bool(ADMIN_USER_ID) and str(user_id) == str(ADMIN_USER_ID)


def parse_db_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def format_crm_datetime(value: str | None) -> str:
    parsed = parse_db_datetime(value)
    return format_datetime_ua(parsed) if parsed else "—"


def format_crm_date(value: str | None) -> str:
    parsed = parse_db_datetime(value)
    return format_date_ua(parsed) if parsed else "—"


def crm_user_has_access(user: dict[str, Any]) -> bool:
    if int(user.get("is_paid") or 0) != 1:
        return False
    expires_at = parse_db_datetime(user.get("access_until"))
    return bool(expires_at and expires_at > datetime.now())


def crm_status(user: dict[str, Any]) -> str:
    return "✅ активний" if crm_user_has_access(user) else "❌ без доступу"


def get_users_count() -> tuple[int, int, int]:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT is_paid, access_until FROM users"
        ).fetchall()

    total = len(rows)
    active = sum(1 for row in rows if crm_user_has_access(dict(row)))
    return total, active, total - active


def get_users_page(page: int) -> tuple[list[dict[str, Any]], int, int, int]:
    total, active, inactive = get_users_count()
    max_page = max(1, (total + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
    page = max(1, min(page, max_page))
    offset = (page - 1) * USERS_PER_PAGE

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT user_id, username, is_paid, access_until, created_at, last_active
            FROM users
            ORDER BY datetime(COALESCE(created_at, '1970-01-01 00:00:00')) DESC
            LIMIT ? OFFSET ?
            """,
            (USERS_PER_PAGE, offset),
        ).fetchall()

    return [dict(row) for row in rows], page, max_page, active


def get_crm_user(user_id: int) -> dict[str, Any] | None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT user_id, username, is_paid, access_until, created_at, last_active, last_activity
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def get_broadcast_unpaid_users(now: int) -> list[int]:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT user_id, is_paid, access_until, can_message, last_auto_message_at
            FROM users
            WHERE COALESCE(can_message, 1) = 1
            """
        ).fetchall()

    user_ids = []
    for row in rows:
        user = dict(row)
        access_until = access_until_to_timestamp(user.get("access_until"))
        has_active_access = int(user.get("is_paid") or 0) == 1 and access_until and access_until > now
        if has_active_access:
            continue
        last_auto_message_at = user.get("last_auto_message_at")
        if last_auto_message_at is not None and now - int(last_auto_message_at) < 86400:
            continue
        user_ids.append(int(user["user_id"]))
    return user_ids


def users_page_keyboard(page: int, max_page: int) -> InlineKeyboardMarkup | None:
    buttons = []
    row = []
    if page > 1:
        row.append(InlineKeyboardButton(text="⬅️ назад", callback_data=f"users_page_{page - 1}"))
    if page < max_page:
        row.append(InlineKeyboardButton(text="➡️ вперед", callback_data=f"users_page_{page + 1}"))
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None


def user_manage_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ видати 7 днів", callback_data=f"grant_7_{user_id}")],
            [InlineKeyboardButton(text="✅ видати 30 днів", callback_data=f"grant_30_{user_id}")],
            [InlineKeyboardButton(text="❌ забрати доступ", callback_data=f"revoke_{user_id}")],
            [InlineKeyboardButton(text="✉️ написати клієнту", callback_data=f"message_{user_id}")],
            [InlineKeyboardButton(text="🔁 нагадати оплату", callback_data=f"template_remind_{user_id}")],
            [InlineKeyboardButton(text="⚠️ доступ закінчився", callback_data=f"template_expired_{user_id}")],
            [InlineKeyboardButton(text="🎁 спец пропозиція", callback_data=f"template_offer_{user_id}")],
        ]
    )


def get_crm_template_text(template: str) -> str | None:
    templates = {
        "remind": (
            "ти не завершив оплату 👇\n\n"
            "щоб продовжити контроль витрат\n"
            "просто оплати доступ\n\n"
            f"👉 MONO: {MONO_CARD}\n"
            f"👉 PRIVAT: {PRIVAT_CARD}\n\n"
            "після оплати натисни «я оплатив»"
        ),
        "expired": (
            "доступ до бота закінчився 👇\n\n"
            "ти вже бачиш, куди реально йдуть гроші\n\n"
            "саме це — початок заощаджень\n\n"
            "щоб не втратити контроль:\n"
            "👉 продовжити доступ"
        ),
        "offer": (
            "сьогодні можна дешевше 👇\n\n"
            "7 днів — 250 грн замість 290\n"
            "30 днів — 350 грн замість 390\n\n"
            "👉 напиши «хочу»"
        ),
    }
    return templates.get(template)


def build_users_page_text(page: int) -> tuple[str, InlineKeyboardMarkup | None]:
    users, page, max_page, active = get_users_page(page)
    total, _, inactive = get_users_count()
    lines = [
        f"👥 користувачі (сторінка {page})",
        "",
        f"всього: {total}",
        f"активних: {active}",
        f"без доступу: {inactive}",
        "",
    ]

    if not users:
        lines.append("користувачів ще немає")
        return "\n".join(lines), None

    for index, user in enumerate(users, start=1):
        username = user.get("username") or "—"
        if username != "—" and not username.startswith("@"):
            username = f"@{username}"
        lines.extend(
            [
                f"{index}. {user['user_id']}",
                username,
                f"статус: {crm_status(user)}",
                f"до: {format_crm_date(user.get('access_until'))}",
                "",
            ]
        )

    return "\n".join(lines).strip(), users_page_keyboard(page, max_page)


def build_user_detail_text(user: dict[str, Any]) -> str:
    username = user.get("username") or "—"
    if username != "—" and not username.startswith("@"):
        username = f"@{username}"
    return "\n".join(
        [
            "👤 користувач",
            "",
            f"id: {user['user_id']}",
            f"username: {username}",
            "",
            f"статус: {crm_status(user)}",
            f"доступ до: {format_crm_date(user.get('access_until'))}",
            "",
            f"остання активність: {format_crm_datetime(user.get('last_active') or user.get('last_activity'))}",
        ]
    )


async def send_paywall_message(target: Message | CallbackQuery, user: dict[str, Any], force: bool = False) -> None:
    if not should_show_paywall(user, force=force):
        if isinstance(target, CallbackQuery):
            await target.answer()
        return

    text = unpaid_text()
    if user["is_paid"] and user["access_until"]:
        text = expired_text(int(user["user_id"]))
        update_last_notified(int(user["user_id"]))
        if not user.get("reminded_expired"):
            mark_access_reminder(int(user["user_id"]), "reminded_expired")
    mark_paywall_shown(int(user["user_id"]))

    if isinstance(target, CallbackQuery):
        if target.message is not None:
            await target.message.answer(text, reply_markup=payment_keyboard())
        await target.answer()
    else:
        await target.answer(text, reply_markup=payment_keyboard())


class UserActivityMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user is None:
            try:
                return await handler(event, data)
            except Exception as e:
                print(f"[ERROR] {e}")
                raise

        username = f"@{user.username}" if user.username else "без username"

        try:
            update_user_activity(user.id, user.username)

            if isinstance(event, Message) and event.text:
                print(f"[USER] id={user.id} username={username} text={event.text}")
                if event.text.startswith("/broadcast_unpaid") and is_admin(user.id):
                    return await handler(event, data)
                state = data.get("state")
                current_state = await state.get_state() if isinstance(state, FSMContext) else None
                if current_state == ExpenseStates.waiting_message.state and is_admin(user.id):
                    return await handler(event, data)
                if event.text.startswith(("/users", "/user")) and is_admin(user.id):
                    return await handler(event, data)
                if event.text.startswith("/grant") and is_admin(user.id):
                    return await handler(event, data)
                if user.id in GRANT_ACCESS_DAYS and is_admin(user.id):
                    return await handler(event, data)
                if event.text.startswith("/test_admin") and is_admin(user.id):
                    return await handler(event, data)
                if event.text.strip().lower() == "я оплатив":
                    return await handler(event, data)

            if isinstance(event, CallbackQuery) and event.data:
                print(f"[USER] id={user.id} username={username} callback={event.data}")
                if (
                    event.data.startswith((
                        "users_page_",
                        "grant_7_",
                        "grant_30_",
                        "revoke_",
                        "message_",
                        "template_remind_",
                        "template_expired_",
                        "template_offer_",
                    ))
                    and is_admin(user.id)
                ):
                    return await handler(event, data)
                if event.data in {"pay_info", "paid", "buy_7", "buy_30", "paid_7", "paid_30"}:
                    return await handler(event, data)
                if (
                    event.data.startswith(("confirm_7_", "confirm_30_", "reject_"))
                    and is_admin(user.id)
                ):
                    return await handler(event, data)

            user_data = get_user(user.id)
            if not check_access(user.id):
                force = isinstance(event, Message) and bool(event.text and event.text.startswith("/start"))
                await send_paywall_message(event, user_data, force=force)
                return None

            bot = data.get("bot")
            if isinstance(bot, Bot):
                await check_access_reminder(bot, user_data)

            return await handler(event, data)
        except Exception as e:
            print(f"[ERROR] {e}")
            raise


def parse_amount(text: str | None) -> int | None:
    if text is None:
        return None
    text = text.strip()
    if not re.fullmatch(r"\d+", text):
        return None
    amount = int(text)
    return amount if amount > 0 else None


def parse_smart_expense_input(text: str | None) -> tuple[str | None, int | None] | None:
    if text is None:
        return None

    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return None

    if re.fullmatch(r"\d+", text):
        return None, parse_amount(text)

    matches = list(re.finditer(r"\d+", text))
    if not matches:
        return text, None

    match = matches[-1]
    amount = int(match.group())
    name = text[: match.start()].strip()
    name = re.sub(r"\s+", " ", name)

    return (name or None), (amount if amount > 0 else None)


def looks_like_period_choice_text(text: str | None) -> bool:
    if text is None:
        return False

    value = re.sub(r"^[^\wА-Яа-яІіЇїЄєҐґ]+", "", text.strip().lower())
    months = "|".join(re.escape(month) for month in UKRAINIAN_MONTH_NAMES.values())
    month_days = "|".join(re.escape(month) for month in UKRAINIAN_MONTHS.values())
    return bool(
        re.fullmatch(rf"({months})\s+\d{{4}}", value)
        or re.fullmatch(rf"\d{{2}}\s+({month_days})\s+[—-]\s+\d{{2}}\s+({month_days})", value)
        or re.fullmatch(rf"\d{{2}}\s+({month_days})", value)
    )


def parse_expense(text: str | None) -> tuple[str, int] | None:
    parsed = parse_smart_expense_input(text)
    if parsed is None:
        return None

    name, amount = parsed
    if not name or not amount:
        return None
    return name, amount


def save_expense(
    name: str,
    amount: int,
    user_id: int | None = None,
    category: str | None = None,
) -> int:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    if not isinstance(amount, int) or not amount:
        raise ValueError("amount must be a non-empty number")

    now = datetime.now().isoformat(timespec="seconds")
    raw_text = name.strip()
    expense_title = safe_expense_title(raw_text)
    if expense_title == "Без назви":
        print(f"[TITLE WARNING] invalid expense title user_id={user_id} raw_text={raw_text!r}")
    normalized = normalize_financial_category(expense_title if expense_title != "Без назви" else raw_text, category)
    print(
        "[DB] "
        f"action=save_expense user_id={user_id} raw_text={raw_text!r} "
        f"expense_title={expense_title!r} amount={amount} "
        f"category={normalized['category']} date={now}"
    )

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            """
            INSERT INTO expenses (user_id, name, expense_title, raw_title, amount, date, category, subcategory)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                raw_text,
                expense_title,
                normalized["raw_title"],
                amount,
                now,
                normalized["category"],
                normalized["subcategory"],
            ),
        )
        return cursor.lastrowid


def get_expense(expense_id: int, user_id: int | None = None) -> tuple[str, int, str | None] | None:
    query = "SELECT name, amount, type FROM expenses WHERE id = ?"
    params: tuple[object, ...] = (expense_id,)
    if user_id is not None:
        query += " AND user_id = ?"
        params = (expense_id, user_id)

    with sqlite3.connect(DB_PATH) as connection:
        return connection.execute(query, params).fetchone()


def update_expense(expense_id: int, name: str, amount: int, user_id: int | None = None) -> None:
    raw_text = name.strip()
    expense_title = safe_expense_title(raw_text)
    if expense_title == "Без назви":
        print(f"[TITLE WARNING] invalid edited expense title user_id={user_id} raw_text={raw_text!r}")
    normalized = normalize_financial_category(expense_title if expense_title != "Без назви" else raw_text)
    query = "UPDATE expenses SET name = ?, expense_title = ?, raw_title = ?, amount = ?, category = ?, subcategory = ? WHERE id = ?"
    params: tuple[object, ...] = (
        raw_text,
        expense_title,
        normalized["raw_title"],
        amount,
        normalized["category"],
        normalized["subcategory"],
        expense_id,
    )
    if user_id is not None:
        query += " AND user_id = ?"
        params = (*params, user_id)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(query, params)


def update_expense_type(expense_id: int, expense_type: str, user_id: int | None = None) -> None:
    query = "UPDATE expenses SET type = ? WHERE id = ?"
    params: tuple[object, ...] = (expense_type, expense_id)
    if user_id is not None:
        query += " AND user_id = ?"
        params = (expense_type, expense_id, user_id)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(query, params)


def delete_expenses_by_period(period: str, user_id: int) -> None:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    if period != PERIOD_ALL:
        period_conditions, period_params = get_period_datetime_conditions(period)
        conditions.extend(period_conditions)
        params.extend(period_params)
    query = f"DELETE FROM expenses {where_from_conditions(conditions)}"

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(query, tuple(params))


def month_bounds(value: datetime) -> tuple[datetime, datetime]:
    start = value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    return start, next_month


def current_week_bounds(value: datetime | None = None) -> tuple[datetime, datetime]:
    now = value or datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start, next_month = month_bounds(day_start)
    week_start = day_start - timedelta(days=day_start.weekday())
    week_end = week_start + timedelta(days=7)
    return max(week_start, month_start), min(week_end, next_month)


def format_numeric_day(value: datetime) -> str:
    return value.strftime("%d.%m")


def format_period_date(value: datetime) -> str:
    return f"{value.day:02d} {UKRAINIAN_MONTHS[value.month]}"


def week_periods_for_month(value: datetime | None = None) -> list[dict[str, str]]:
    now = value or datetime.now()
    month_start, next_month = month_bounds(now)
    month_end = next_month - timedelta(days=1)
    first_monday = month_start + timedelta(days=(7 - month_start.weekday()) % 7)

    periods: list[dict[str, str]] = []
    start = first_monday
    while start < next_month:
        end = min(start + timedelta(days=6), month_end)
        label = f"{format_period_date(start)} — {format_period_date(end)}"
        periods.append(
            {
                "label": label,
                "from": start.isoformat(timespec="seconds"),
                "to": (end + timedelta(days=1)).isoformat(timespec="seconds"),
            }
        )
        start += timedelta(days=7)
    return periods


def month_periods(count: int = 3) -> list[dict[str, str]]:
    current_start, _ = month_bounds(datetime.now())
    periods: list[dict[str, str]] = []
    start = current_start
    for _ in range(count):
        _, next_month = month_bounds(start)
        label = f"📅 {UKRAINIAN_MONTH_NAMES[start.month]} {start.year}"
        periods.append(
            {
                "label": label,
                "from": start.isoformat(timespec="seconds"),
                "to": next_month.isoformat(timespec="seconds"),
            }
        )
        start = (start - timedelta(days=1)).replace(day=1)
    return periods


def get_selected_period_conditions(date_from: datetime, date_to: datetime) -> tuple[list[str], list[object]]:
    return (
        ["datetime(date) >= datetime(?)", "datetime(date) < datetime(?)"],
        [
            date_from.isoformat(sep=" ", timespec="seconds"),
            date_to.isoformat(sep=" ", timespec="seconds"),
        ],
    )


def get_period_years(user_id: int) -> list[int]:
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT CAST(strftime('%Y', date) AS INTEGER) AS year
            FROM expenses
            WHERE user_id = ?
              AND date IS NOT NULL
            ORDER BY year DESC
            """,
            (user_id,),
        ).fetchall()
    return [int(row[0]) for row in rows if row[0] is not None]


def get_period_months(user_id: int, year: int) -> list[int]:
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT CAST(strftime('%m', date) AS INTEGER) AS month
            FROM expenses
            WHERE user_id = ?
              AND strftime('%Y', date) = ?
              AND date IS NOT NULL
            ORDER BY month ASC
            """,
            (user_id, str(year)),
        ).fetchall()
    return [int(row[0]) for row in rows if row[0] is not None]


def get_period_days(user_id: int, year: int, month: int) -> list[int]:
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT CAST(strftime('%d', date) AS INTEGER) AS day
            FROM expenses
            WHERE user_id = ?
              AND strftime('%Y', date) = ?
              AND strftime('%m', date) = ?
              AND date IS NOT NULL
            ORDER BY day ASC
            """,
            (user_id, str(year), f"{month:02d}"),
        ).fetchall()
    return [int(row[0]) for row in rows if row[0] is not None]


def get_period_datetime_conditions(period: str) -> tuple[list[str], list[object]]:
    conditions: list[str] = []
    params: list[object] = []
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == PERIOD_DAY:
        conditions.append("datetime(date) >= datetime(?)")
        params.append(today_start.isoformat(sep=" ", timespec="seconds"))
    elif period == PERIOD_YESTERDAY:
        yesterday_start = today_start - timedelta(days=1)
        conditions.append("datetime(date) >= datetime(?)")
        conditions.append("datetime(date) < datetime(?)")
        params.extend(
            [
                yesterday_start.isoformat(sep=" ", timespec="seconds"),
                today_start.isoformat(sep=" ", timespec="seconds"),
            ]
        )
    elif period == PERIOD_WEEK:
        week_start, week_end = current_week_bounds(now)
        conditions.append("datetime(date) >= datetime(?)")
        conditions.append("datetime(date) < datetime(?)")
        params.extend(
            [
                week_start.isoformat(sep=" ", timespec="seconds"),
                week_end.isoformat(sep=" ", timespec="seconds"),
            ]
        )
    elif period == PERIOD_MONTH:
        month_start, next_month = month_bounds(now)
        conditions.append("datetime(date) >= datetime(?)")
        conditions.append("datetime(date) < datetime(?)")
        params.extend(
            [
                month_start.isoformat(sep=" ", timespec="seconds"),
                next_month.isoformat(sep=" ", timespec="seconds"),
            ]
        )
    elif period == PERIOD_YEAR:
        conditions.append("datetime(date) >= datetime(?)")
        params.append((now - timedelta(days=365)).isoformat(sep=" ", timespec="seconds"))

    return conditions, params


def get_custom_datetime_conditions(date_from: datetime, date_to: datetime) -> tuple[list[str], list[object]]:
    start = date_from.replace(hour=0, minute=0, second=0, microsecond=0)
    end = date_to.replace(hour=23, minute=59, second=59, microsecond=0)
    return (
        ["datetime(date) >= datetime(?)", "datetime(date) <= datetime(?)"],
        [
            start.isoformat(sep=" ", timespec="seconds"),
            end.isoformat(sep=" ", timespec="seconds"),
        ],
    )


def where_from_conditions(conditions: list[str]) -> str:
    return f"WHERE {' AND '.join(conditions)}" if conditions else ""


def log_db_read(
    action: str,
    user_id: int | None,
    period: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    category: str | None = None,
    rows_count: int | None = None,
) -> None:
    parts = [
        f"action={action}",
        f"user_id={user_id}",
        f"period={period}",
        f"date_from={date_from.isoformat(sep=' ', timespec='seconds') if date_from else None}",
        f"date_to={date_to.isoformat(sep=' ', timespec='seconds') if date_to else None}",
        f"category={category}",
        f"table={TABLES['expenses']}",
        f"db={DB_PATH}",
        f"rows_count={rows_count}",
    ]
    print("[DB] " + " ".join(parts))


def get_expenses_by_conditions(
    conditions: list[str],
    params: list[object],
    limit: int = 20,
) -> list[tuple[int, str, int, str, str | None, str | None]]:
    where = where_from_conditions(conditions)
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            f"""
            SELECT id, expense_title, raw_title, name, amount, date, type, category
            FROM expenses
            {where}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
    return [
        (expense_id, safe_expense_title(expense_title, raw_title, name), amount, date, expense_type, category)
        for expense_id, expense_title, raw_title, name, amount, date, expense_type, category in rows
    ]


def get_expenses_count_by_conditions(
    conditions: list[str],
    params: list[object],
    max_records: int | None = None,
) -> int:
    where = where_from_conditions(conditions)
    if max_records is None:
        query = f"SELECT COUNT(*) FROM expenses {where}"
        query_params = tuple(params)
    else:
        query = f"""
            SELECT COUNT(*)
            FROM (
                SELECT id
                FROM expenses
                {where}
                ORDER BY id DESC
                LIMIT ?
            )
        """
        query_params = (*params, max_records)

    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(query, query_params).fetchone()
    return int(row[0])


def get_stats_by_conditions(
    conditions: list[str],
    params: list[object],
    max_records: int | None = None,
) -> tuple[int, int, int, int]:
    where = where_from_conditions(conditions)
    if max_records is None:
        source = f"expenses {where}"
        query_params = tuple(params)
    else:
        source = f"""
            (
                SELECT amount, type
                FROM expenses
                {where}
                ORDER BY id DESC
                LIMIT ?
            )
        """
        query_params = (*params, max_records)

    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            f"""
            SELECT
                COALESCE(SUM(amount), 0) AS total,
                COALESCE(SUM(CASE WHEN type = 'планова' THEN amount ELSE 0 END), 0) AS planned,
                COALESCE(SUM(CASE WHEN type = 'емоційна' THEN amount ELSE 0 END), 0) AS emotional,
                COUNT(*) AS count
            FROM {source}
            """,
            query_params,
        ).fetchone()

    return int(row[0]), int(row[1]), int(row[2]), int(row[3])


def count_expenses(user_id: int | None = None) -> int:
    query = "SELECT COUNT(*) FROM expenses"
    params: tuple[object, ...] = ()
    if user_id is not None:
        query += " WHERE user_id = ?"
        params = (user_id,)

    with sqlite3.connect(DB_PATH) as connection:
        return int(connection.execute(query, params).fetchone()[0])


def get_expenses(period: str, user_id: int, limit: int = 20) -> list[tuple[int, str, int, str, str | None, str | None]]:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    period_conditions, period_params = get_period_datetime_conditions(period)
    conditions.extend(period_conditions)
    params.extend(period_params)

    return get_expenses_by_conditions(conditions, params, limit)


def get_expenses_count(period: str, user_id: int) -> int:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    period_conditions, period_params = get_period_datetime_conditions(period)
    conditions.extend(period_conditions)
    params.extend(period_params)

    return get_expenses_count_by_conditions(conditions, params)


def get_stats(period: str, user_id: int | None = None) -> tuple[int, int, int, int]:
    conditions, params = get_period_datetime_conditions(period)

    if user_id is not None:
        conditions.append("user_id = ?")
        params.append(user_id)

    result = get_stats_by_conditions(conditions, params)
    log_db_read("get_stats", user_id, period=period, rows_count=result[3])
    return result


def get_custom_expenses(
    user_id: int,
    date_from: datetime,
    date_to: datetime,
    limit: int = 10,
) -> list[tuple[int, str, int, str, str | None, str | None]]:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    date_conditions, date_params = get_custom_datetime_conditions(date_from, date_to)
    conditions.extend(date_conditions)
    params.extend(date_params)

    return get_expenses_by_conditions(conditions, params, min(limit, CUSTOM_PERIOD_RECORD_LIMIT))


def get_custom_expenses_count(user_id: int, date_from: datetime, date_to: datetime) -> int:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    date_conditions, date_params = get_custom_datetime_conditions(date_from, date_to)
    conditions.extend(date_conditions)
    params.extend(date_params)

    return get_expenses_count_by_conditions(conditions, params, CUSTOM_PERIOD_RECORD_LIMIT)


def get_custom_stats(user_id: int, date_from: datetime, date_to: datetime) -> tuple[int, int, int, int]:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    date_conditions, date_params = get_custom_datetime_conditions(date_from, date_to)
    conditions.extend(date_conditions)
    params.extend(date_params)

    result = get_stats_by_conditions(conditions, params, CUSTOM_PERIOD_RECORD_LIMIT)
    log_db_read("get_custom_stats", user_id, date_from=date_from, date_to=date_to, rows_count=result[3])
    return result


def get_selected_stats(user_id: int, date_from: datetime, date_to: datetime) -> tuple[int, int, int, int]:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    date_conditions, date_params = get_selected_period_conditions(date_from, date_to)
    conditions.extend(date_conditions)
    params.extend(date_params)
    result = get_stats_by_conditions(conditions, params, CUSTOM_PERIOD_RECORD_LIMIT)
    log_db_read("get_selected_stats", user_id, date_from=date_from, date_to=date_to, rows_count=result[3])
    return result


def get_selected_expenses(
    user_id: int,
    date_from: datetime,
    date_to: datetime,
    limit: int = 10,
) -> list[tuple[int, str, int, str, str | None, str | None]]:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    date_conditions, date_params = get_selected_period_conditions(date_from, date_to)
    conditions.extend(date_conditions)
    params.extend(date_params)
    return get_expenses_by_conditions(conditions, params, limit)


def get_selected_expenses_count(user_id: int, date_from: datetime, date_to: datetime) -> int:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    date_conditions, date_params = get_selected_period_conditions(date_from, date_to)
    conditions.extend(date_conditions)
    params.extend(date_params)
    return get_expenses_count_by_conditions(conditions, params, CUSTOM_PERIOD_RECORD_LIMIT)


def get_today_expenses(user_id: int) -> list[tuple[str, int]]:
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            """
            SELECT expense_title, raw_title, name, amount
            FROM expenses
            WHERE date(date) = date('now','localtime')
              AND user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()
    return [
        (safe_expense_title(expense_title, raw_title, name), int(amount or 0))
        for expense_title, raw_title, name, amount in rows
    ]


def get_today_yesterday_totals(user_id: int | None = None) -> tuple[int, int]:
    user_filter = "WHERE user_id = ?" if user_id is not None else ""
    params: tuple[object, ...] = (user_id,) if user_id is not None else ()

    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            f"""
            SELECT
                COALESCE(SUM(CASE WHEN date(date) = date('now','localtime') THEN amount ELSE 0 END), 0) AS today,
                COALESCE(SUM(CASE WHEN date(date) = date('now','-1 day','localtime') THEN amount ELSE 0 END), 0) AS yesterday
            FROM expenses
            {user_filter}
            """,
            params,
        ).fetchone()

    return int(row[0]), int(row[1])


def get_period_conditions(period: str, user_id: int | None = None) -> tuple[str, tuple[object, ...]]:
    conditions = []
    params: list[object] = []

    if period == PERIOD_DAY:
        conditions.append("date(date) = date('now','localtime')")
    elif period == PERIOD_WEEK:
        conditions.append("date(date) >= date('now','-7 day','localtime')")

    if user_id is not None:
        conditions.append("user_id = ?")
        params.append(user_id)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where, tuple(params)


def build_insights(period: str, user_id: int | None) -> list[str]:
    if user_id is None:
        return []

    where, params = get_period_conditions(period, user_id)

    with sqlite3.connect(DB_PATH) as connection:
        count = int(
            connection.execute(
                f"SELECT COUNT(*) FROM expenses {where}",
                params,
            ).fetchone()[0]
        )
        if count < 3:
            return []

        top = connection.execute(
            f"""
            SELECT name, SUM(amount) AS total
            FROM expenses
            {where}
            GROUP BY name
            ORDER BY total DESC
            LIMIT 1
            """,
            params,
        ).fetchone()

        emotional_sum = int(
            connection.execute(
                f"""
                SELECT COALESCE(SUM(amount), 0)
                FROM expenses
                {where} {"AND" if where else "WHERE"} type = 'емоційна'
                """,
                params,
            ).fetchone()[0]
        )
        total_sum = int(
            connection.execute(
                f"SELECT COALESCE(SUM(amount), 0) FROM expenses {where}",
                params,
            ).fetchone()[0]
        )

        frequent = connection.execute(
            f"""
            SELECT name, COUNT(*) AS cnt
            FROM expenses
            {where}
            GROUP BY name
            ORDER BY cnt DESC
            LIMIT 1
            """,
            params,
        ).fetchone()

    lines = ["", "📊 Інсайти:"]

    if top is not None:
        lines.append(f"🔥 Найбільше витрат: {top[0]} — {format_amount(int(top[1]))} грн")

    if total_sum > 0:
        emotional_percent = emotional_sum * 100 / total_sum
        if emotional_percent > 50:
            lines.append(
                f"⚠️ емоційні витрати — {format_amount(emotional_sum)} грн\n"
                "ти витрачаєш імпульсивно"
            )

    if frequent is not None:
        name, cnt = frequent
        if int(cnt) > 3:
            lines.append(f"💡 Найчастіше: {name} ({int(cnt)} разів)")

    return lines if len(lines) > 2 else []


def format_amount(amount: int | float) -> str:
    if isinstance(amount, float) and amount.is_integer():
        return str(int(amount))
    return str(amount)


def format_percent(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}"


def format_type(expense_type: str | None) -> str:
    if expense_type == "планова":
        return "Планова"
    if expense_type == "емоційна":
        return "Емоційна"
    return "Не вказано"


def format_type_badge(expense_type: str | None) -> str:
    if expense_type == "планова":
        return " (📌 Планова)"
    if expense_type == "емоційна":
        return " (🔥 Емоційна)"
    return ""


def format_list_type_emoji(expense_type: str | None) -> str:
    if expense_type == "емоційна":
        return " 🔥"
    if expense_type == "планова":
        return " 📌"
    return ""


def format_date_ua(value: datetime) -> str:
    return f"{value.day:02d} {UKRAINIAN_MONTHS[value.month]}"


def format_date_range_ua(date_from: datetime, date_to: datetime) -> str:
    if date_from.date() == date_to.date():
        return format_date_ua(date_from)
    if date_from.month == date_to.month and date_from.year == date_to.year:
        return f"{date_from.day:02d}–{date_to.day:02d} {UKRAINIAN_MONTHS[date_from.month]}"
    return f"{format_date_ua(date_from)} — {format_date_ua(date_to)}"


def format_datetime_ua(value: datetime, relative: bool = False) -> str:
    date_text = format_date_ua(value)
    if relative:
        today = datetime.now().date()
        value_date = value.date()
        if value_date == today:
            date_text = "сьогодні"
        elif value_date == today - timedelta(days=1):
            date_text = "вчора"
    return f"{date_text} • {value.strftime('%H:%M')}"


def format_expense_datetime(value: str) -> str:
    parsed = parse_db_datetime(value)
    return format_datetime_ua(parsed, relative=False) if parsed else value


def format_expense_title(name: str) -> str:
    normalized = name.strip().lower()
    emoji = CATEGORY_NAME_EMOJI.get(normalized)
    return f"{emoji} {name}" if emoji else name


def format_expense_category(name: str, category: str | None = None) -> str | None:
    tag = normalize_financial_category(name, category)["category"]
    if tag == "інше" and not category:
        tag = CATEGORY_NAME_TAG.get(name.strip().lower())
    if not tag:
        return None
    return format_category_label(tag)


def parse_period_date(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        return datetime.strptime(text.strip(), "%d.%m.%Y")
    except ValueError:
        return None


def custom_period_title(date_from: datetime, date_to: datetime) -> str:
    return (
        f"📅 {format_date_range_ua(date_from, date_to)}\n"
        "ось куди реально пішли гроші 👇"
    )


def custom_period_extra_text(
    user_id: int,
    date_from: datetime,
    date_to: datetime,
    current_total: int,
) -> str:
    lines: list[str] = []
    try:
        period_delta = date_to - date_from
        previous_from = date_from - period_delta
        previous_to = date_from
        previous_total, _, _, _ = get_custom_stats(user_id, previous_from, previous_to)

        if previous_total > 0:
            diff = abs(current_total - previous_total)
            if current_total > previous_total:
                lines.append(f"це +{format_amount(diff)} грн 📈\nтрохи рознесло 😏")
            elif current_total < previous_total:
                lines.append(f"це -{format_amount(diff)} грн 💪\nти починаєш контролювати витрати")
            else:
                lines.append("витрати стабільні\nале це теж сигнал")
    except Exception as e:
        print(f"[ERROR] custom period compare: {e}")

    try:
        if check_access(user_id):
            lines.extend(
                [
                    "ти вже бачиш різницю",
                    "👉 просто продовжуй фіксувати витрати",
                ]
            )
        else:
            lines.extend(
                [
                    "саме так виглядає контроль 👀",
                    "👉 продовжи доступ і не зливай гроші далі",
                ]
            )
    except Exception as e:
        print(f"[ERROR] custom period CTA: {e}")

    return "\n\n".join(lines)


def period_label(period: str) -> str:
    labels = {
        PERIOD_DAY: "сьогодні",
        PERIOD_YESTERDAY: "вчора",
        PERIOD_WEEK: "тиждень",
        PERIOD_MONTH: "місяць",
        PERIOD_YEAR: "рік",
        PERIOD_ALL: "весь час",
    }
    return labels.get(period, "період")


def stats_period_title(period: str) -> str:
    now = datetime.now()
    if period == PERIOD_DAY:
        return f"📊 Сьогодні {format_numeric_day(now)}"
    if period == PERIOD_YESTERDAY:
        return f"📊 Вчора {format_numeric_day(now - timedelta(days=1))}"
    if period == PERIOD_WEEK:
        week_start, week_end = current_week_bounds(now)
        return f"📊 Тиждень {format_numeric_day(week_start)}–{format_numeric_day(week_end - timedelta(days=1))}"
    if period == PERIOD_MONTH:
        return f"📊 Місяць {UKRAINIAN_MONTH_NAMES[now.month]}"
    if period == PERIOD_YEAR:
        return "📊 Рік"
    if period == PERIOD_ALL:
        return "📊 За весь час"
    return "📊 Статистика"


def stats_analysis(emotional_percent: float, count: int, total_sum: int) -> list[str]:
    lines = []

    if emotional_percent > 50:
        lines.append(
            "ти витрачаєш багато імпульсивно 🔥\n\n"
            "саме тут і «зникають» гроші"
        )
    elif emotional_percent >= 20:
        lines.append(
            "у тебе вже є контроль 👌\n"
            "але ще є куди покращити"
        )
    else:
        lines.append(
            "це вже рівень 💪\n"
            "більшість навіть не доходить сюди"
        )

    if count < 3:
        lines.append("ℹ️ Додай ще витрат для точнішої статистики")

    lines.append(amount_personalization_text(total_sum))
    lines.append(access_cta_text())

    return lines


def compare_today_with_yesterday(user_id: int | None = None) -> str | None:
    today, yesterday = get_today_yesterday_totals(user_id)

    if yesterday == 0:
        return None

    difference = abs(today - yesterday)
    if today > yesterday:
        return f"📈 Ти витрачаєш більше ніж вчора на {format_amount(difference)} грн"
    if today < yesterday:
        return f"📉 Ти витрачаєш менше ніж вчора на {format_amount(difference)} грн"
    return "⚖️ Витрати такі ж як і вчора"


def simple_daily_comparison(user_id: int | None = None) -> str | None:
    today, yesterday = get_today_yesterday_totals(user_id)
    if yesterday == 0:
        return None
    if today > yesterday:
        return "ти витрачаєш більше ніж вчора ⚠️"
    if today < yesterday:
        return "сьогодні витрати менші 👍"
    return None


def expense_micro_insight(user_id: int | None, amount: int) -> str | None:
    if user_id is None:
        return None

    try:
        today_sum, yesterday_sum = get_today_yesterday_totals(user_id)
        if yesterday_sum > 0 and today_sum > yesterday_sum:
            return "ти вже витратив більше ніж вчора 📈"
        if yesterday_sum > 0 and today_sum < yesterday_sum:
            return "менше ніж вчора 💪"

        if today_sum > 0 and amount > 0:
            if today_sum != amount:
                return f"ця витрата: {format_amount(amount)} грн із {format_amount(today_sum)} грн сьогодні"

        if today_sum > 0:
            return f"це вже {format_amount(today_sum)} грн сьогодні"
    except Exception as e:
        print(f"[ERROR] micro insight: {e}")

    return None


def build_compare_text(user_id: int | None = None) -> str:
    today, yesterday = get_today_yesterday_totals(user_id)

    if yesterday == 0:
        return "ℹ️ Немає даних за вчора для порівняння"

    lines = [
        f"📈 Сьогодні: {format_amount(today)} грн",
        f"📊 Вчора: {format_amount(yesterday)} грн",
        "",
    ]

    if today > yesterday:
        difference = today - yesterday
        lines.append(f"⚠️ Ти витрачаєш більше ніж вчора на {format_amount(difference)} грн")
    elif today < yesterday:
        difference = yesterday - today
        lines.append(f"✅ Ти витрачаєш менше ніж вчора на {format_amount(difference)} грн")
    else:
        lines.append("⚖️ Витрати такі ж як і вчора")

    return "\n".join(lines)


async def check_users(bot: Bot) -> None:
    today = datetime.now().date()
    now = int(time.time())
    current_hour = datetime.now().hour
    if current_hour < 10 or current_hour >= 21:
        print("[AUTO] skipped by quiet hours")
        return

    for user in get_all_users_for_auto_messages():
        user_id = int(user["user_id"])
        last_active = access_until_to_timestamp(user.get("last_active") or user.get("created_at"))
        access_until = access_until_to_timestamp(user.get("access_until"))
        is_expired = bool(access_until and access_until < now and not int(user.get("expired_notified") or 0))

        if not int(user.get("can_message") if user.get("can_message") is not None else 1):
            print(f"[AUTO] skipped (cannot message) user={user_id}")
            continue

        if last_active is not None and now - last_active > 30 * 86400:
            print(f"[AUTO] skipped (inactive) user={user_id}")
            continue

        if is_expired:
            if await safe_auto_send(
                bot,
                user,
                build_expired_paywall_text(user_id),
                now,
            ):
                mark_expired_notified(user_id)
                print(f"[AUTO] expired sent user={user_id}")
            continue

        last_auto_message_at = user.get("last_auto_message_at")
        if last_auto_message_at is not None and now - int(last_auto_message_at) < 3600:
            print(f"[AUTO] cooldown skip user={user_id}")
            continue

        if (
            access_until
            and 0 < access_until - now < 86400
            and not int(user.get("expiring_notified") or 0)
        ):
            if await safe_auto_send(
                bot,
                user,
                build_expiring_paywall_text(access_until),
                now,
            ):
                mark_expiring_soon_notified(user_id)
                print(f"[AUTO] expiring sent user={user_id}")
            continue

        if (
            access_until
            and 0 < access_until - now < 86400
            and not int(user.get("expiring_notified") or 0)
        ):
            if await safe_auto_send(
                bot,
                user,
                (
                    "доступ скоро закінчиться ⏳\n\n"
                    "і ти знову перестанеш бачити\n"
                    "куди йдуть гроші\n\n"
                    "продовжи зараз 👇\n"
                    "👉 оплатити"
                ),
                now,
            ):
                mark_expiring_soon_notified(user_id)
                print(f"[AUTO] expiring sent user={user_id}")
            continue

        if not int(user.get("is_paid") or 0):
            last_remind_at = user.get("last_remind_at")
            if last_remind_at is None or now - int(last_remind_at) > 86400:
                if await safe_auto_send(
                    bot,
                    user,
                    (
                        "ти не завершив оплату 👇\n\n"
                        "і швидше за все\n"
                        "гроші знову пішли «в нікуди»\n\n"
                        "поверни контроль 👇\n"
                        "👉 оплатити доступ"
                    ),
                    now,
                ):
                    update_last_remind(user_id, now)
                    print(f"[AUTO] remind sent → {user_id}")
            continue

    for user_id, last_activity, last_reminder in get_users_for_reminders():
        if not last_activity:
            continue
        if last_reminder and last_reminder[:10] == today.isoformat():
            continue

        activity_date = datetime.strptime(last_activity[:10], "%Y-%m-%d").date()
        inactive_days = (today - activity_date).days
        if inactive_days < 1:
            continue

        if inactive_days >= 3:
            text = "🚨 Ти втрачаєш контроль над грошима"
        elif inactive_days >= 2:
            text = "⚠️ Ти вже 2 дні без контролю витрат"
        else:
            yesterday_sum = get_yesterday_sum(user_id)
            if yesterday_sum > 0:
                text = (
                    f"📊 Вчора ти витратив {format_amount(yesterday_sum)} грн\n"
                    "Сьогодні ще нічого не записано 👀"
                )
            else:
                text = "💸 Ти ще не записав витрати сьогодні"

        try:
            await bot.send_message(user_id, text, reply_markup=get_main_keyboard())
        except Exception:
            continue

        update_last_reminder(user_id)


async def scheduler(bot: Bot) -> None:
    while True:
        await check_users(bot)
        await asyncio.sleep(3600)


async def reminder_loop(bot: Bot) -> None:
    await scheduler(bot)


def build_stats_text(period: str, user_id: int | None = None) -> str | None:
    total, planned, emotional, _ = get_stats(period, user_id)

    if total == 0 and period not in {PERIOD_DAY, PERIOD_WEEK}:
        return None

    if period in {PERIOD_DAY, PERIOD_WEEK}:
        return format_short_stats_text(
            stats_period_title(period),
            total,
            emotional,
            get_top_categories_for_period(period, user_id) if user_id is not None else None,
        )

    return format_reply_stats_text(
        stats_period_title(period),
        total,
        planned,
        emotional,
        get_largest_expense(period, user_id) if user_id is not None else None,
        get_top_categories_for_period(period, user_id) if user_id is not None else None,
    )


def format_short_stats_text(
    title: str,
    total: int,
    emotional: int,
    top_categories: list[tuple[str, int]] | None = None,
) -> str:
    top_categories = top_categories or []
    lines = [
        title,
        "",
        "💸 Всього:",
        f"{format_amount(total)} грн",
        "",
    ]
    if top_categories:
        lines.append("📁 Основні категорії:")
        for category, amount in top_categories[:3]:
            lines.append(f"• {format_category_label(category)} — {format_amount(amount)} грн")
        lines.append("")

    lines.extend(["Емоційні:", f"{format_amount(emotional)} грн"])
    return "\n".join(lines)


def format_reply_stats_text(
    title: str,
    total: int,
    planned: int,
    emotional: int,
    largest_expense: tuple[str, int] | None = None,
    top_categories: list[tuple[str, int]] | None = None,
) -> str:
    if total == 0:
        return (
            f"{title}\n\n"
            "за цей період витрат немає"
        )

    emotional_percent = emotional * 100 / total
    top_categories = top_categories or []
    lines = [
        title,
        "",
        "💸 Всього:",
        f"{format_amount(total)} грн",
        "",
    ]
    if top_categories:
        lines.extend(["📁 Основні категорії:"])
        for category, amount in top_categories[:3]:
            lines.append(f"• {format_category_label(category)} — {format_amount(amount)} грн")
        lines.append("")

    lines.extend(["Емоційні:", f"{format_amount(emotional)} грн", ""])

    if largest_expense is not None:
        name, amount = largest_expense
        lines.extend(["💰 Найбільша покупка:", f"{name} — {format_amount(amount)} грн", ""])

    if top_categories:
        leader, _ = top_categories[0]
        lines.append(f"👀 Найбільше грошей зараз пішло на {format_category_label(leader)}.")

    insight = build_stats_insight(total, emotional_percent, top_categories)
    if insight:
        lines.extend(["", insight])

    return "\n".join(lines)


def build_reply_stats_text(period: str, user_id: int) -> str:
    total, planned, emotional, _ = get_stats(period, user_id)
    print(f"[STATS] period={period} user={user_id}")

    if period in {PERIOD_DAY, PERIOD_WEEK}:
        return format_short_stats_text(
            stats_period_title(period),
            total,
            emotional,
            get_top_categories_for_period(period, user_id),
        )

    return format_reply_stats_text(
        stats_period_title(period),
        total,
        planned,
        emotional,
        get_largest_expense(period, user_id),
        get_top_categories_for_period(period, user_id),
    )


def build_custom_stats_text(user_id: int, date_from: datetime, date_to: datetime) -> str:
    total, planned, emotional, _ = get_custom_stats(user_id, date_from, date_to)
    lines = [
        format_reply_stats_text(
            custom_period_title(date_from, date_to),
            total,
            planned,
            emotional,
            get_largest_expense_for_selected(user_id, date_from, date_to),
            get_top_categories_for_selected(user_id, date_from, date_to),
        )
    ]
    extra_text = custom_period_extra_text(user_id, date_from, date_to, total)
    if extra_text:
        lines.extend(["", extra_text])
    return "\n".join(lines)


def build_selected_stats_text(user_id: int, label: str, date_from: datetime, date_to: datetime) -> str:
    total, planned, emotional, _ = get_selected_stats(user_id, date_from, date_to)
    return format_reply_stats_text(
        label,
        total,
        planned,
        emotional,
        get_largest_expense_for_selected(user_id, date_from, date_to),
        get_top_categories_for_selected(user_id, date_from, date_to),
    )


def build_short_selected_stats_text(user_id: int, title: str, date_from: datetime, date_to: datetime) -> str:
    total, _, emotional, _ = get_selected_stats(user_id, date_from, date_to)
    return format_short_stats_text(
        title,
        total,
        emotional,
        get_top_categories_for_selected(user_id, date_from, date_to),
    )


def build_month_stats_text(user_id: int, year: int, month: int) -> str:
    date_from, date_to = month_bounds(datetime(year, month, 1))
    title = f"📊 {UKRAINIAN_MONTH_NAMES[month].capitalize()} {year}"
    total, planned, emotional, _ = get_selected_stats(user_id, date_from, date_to)
    top_categories = get_top_categories_for_selected(user_id, date_from, date_to)

    if total == 0:
        return format_short_stats_text(title, total, emotional, [])

    return format_reply_stats_text(
        title,
        total,
        planned,
        emotional,
        get_largest_expense_for_selected(user_id, date_from, date_to),
        top_categories,
    )


def get_top_category_by_conditions(conditions: list[str], params: list[object]) -> tuple[str, int] | None:
    categories = get_top_categories_by_conditions(conditions, params, limit=1)
    return categories[0] if categories else None


def get_top_category(user_id: int) -> tuple[str, int] | None:
    return get_top_category_by_conditions(["user_id = ?"], [user_id])


def get_top_category_for_period(period: str, user_id: int) -> tuple[str, int] | None:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    period_conditions, period_params = get_period_datetime_conditions(period)
    conditions.extend(period_conditions)
    params.extend(period_params)
    return get_top_category_by_conditions(conditions, params)


def get_previous_month_total(user_id: int) -> int | None:
    now = datetime.now()
    previous_to = now - timedelta(days=30)
    previous_from = now - timedelta(days=60)
    total, _, _, count = get_custom_stats(user_id, previous_from, previous_to)
    return total if count > 0 else None


def get_largest_expense_by_conditions(conditions: list[str], params: list[object]) -> tuple[str, int] | None:
    where = where_from_conditions(conditions)
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            f"""
            SELECT expense_title, raw_title, name, amount
            FROM expenses
            {where}
            ORDER BY amount DESC
            LIMIT 1
            """,
            tuple(params),
        ).fetchone()

    if row is None:
        return None
    expense_title, raw_title, name, amount = row
    return safe_expense_title(expense_title, raw_title, name), int(amount)


def get_largest_expense(period: str, user_id: int) -> tuple[str, int] | None:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    period_conditions, period_params = get_period_datetime_conditions(period)
    conditions.extend(period_conditions)
    params.extend(period_params)
    return get_largest_expense_by_conditions(conditions, params)


def get_largest_expense_for_selected(user_id: int, date_from: datetime, date_to: datetime) -> tuple[str, int] | None:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    date_conditions, date_params = get_selected_period_conditions(date_from, date_to)
    conditions.extend(date_conditions)
    params.extend(date_params)
    return get_largest_expense_by_conditions(conditions, params)


def get_top_category_for_selected(user_id: int, date_from: datetime, date_to: datetime) -> tuple[str, int] | None:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    date_conditions, date_params = get_selected_period_conditions(date_from, date_to)
    conditions.extend(date_conditions)
    params.extend(date_params)
    return get_top_category_by_conditions(conditions, params)


def get_top_categories_by_conditions(
    conditions: list[str],
    params: list[object],
    limit: int = 3,
) -> list[tuple[str, int]]:
    where = where_from_conditions(conditions)
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            f"""
            SELECT category, COALESCE(NULLIF(expense_title, ''), NULLIF(raw_title, ''), name) AS title, amount
            FROM expenses
            {where}
            """,
            tuple(params),
        ).fetchall()

    totals: dict[str, int] = {}
    for category, title, amount in rows:
        normalized = normalize_financial_category(str(title or ""), category)["category"]
        totals[normalized] = totals.get(normalized, 0) + int(amount or 0)

    return sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]


def get_top_categories_for_period(period: str, user_id: int, limit: int = 3) -> list[tuple[str, int]]:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    period_conditions, period_params = get_period_datetime_conditions(period)
    conditions.extend(period_conditions)
    params.extend(period_params)
    categories = get_top_categories_by_conditions(conditions, params, limit)
    log_db_read("get_top_categories", user_id, period=period, rows_count=len(categories))
    return categories


def get_top_categories_for_selected(
    user_id: int,
    date_from: datetime,
    date_to: datetime,
    limit: int = 3,
) -> list[tuple[str, int]]:
    conditions = ["user_id = ?"]
    params: list[object] = [user_id]
    date_conditions, date_params = get_selected_period_conditions(date_from, date_to)
    conditions.extend(date_conditions)
    params.extend(date_params)
    categories = get_top_categories_by_conditions(conditions, params, limit)
    log_db_read("get_top_categories", user_id, date_from=date_from, date_to=date_to, rows_count=len(categories))
    return categories


def build_recommendations_text(user_id: int) -> str:
    try:
        month_total, _, emotional, count = get_stats(PERIOD_MONTH, user_id)
        print(f"[STATS] period=recommendations user={user_id}")

        if count < 5 or month_total == 0:
            return (
                "🎯 рекомендації\n\n"
                "поки даних замало для точних рекомендацій.\n\n"
                "запиши хоча б 5–7 витрат, і я покажу, де саме починають зникати гроші."
            )

        recommendations: list[str] = []

        emotional_percent = emotional * 100 / month_total
        if emotional_percent > 50:
            recommendations.append(
                "\n".join(
                    [
                        f"1. 🔥 емоційні витрати — {format_amount(emotional)} грн",
                        "",
                        "чому це важливо:",
                        "коли емоційних витрат багато, бюджет важче контролювати.",
                        "",
                        "що це означає:",
                        "більшість грошей зараз витрачається імпульсивно, а не по плану.",
                        "часто саме такі витрати створюють відчуття: «гроші просто зникають».",
                        "",
                        "що зробити:",
                        "перед покупкою зроби коротку паузу і запитай себе: «мені це реально потрібно чи просто хочеться зараз?»",
                    ]
                )
            )

        top_category = get_top_category_for_period(PERIOD_MONTH, user_id)
        if top_category is not None:
            category, top_sum = top_category
            if category.strip().lower() != "інше":
                number = len(recommendations) + 1
                recommendations.append(
                    "\n".join(
                        [
                            f"{number}. {format_category_label(category)} — {format_amount(top_sum)} грн за місяць",
                            "",
                            "чому це важливо:",
                            "це одна з найбільших регулярних витрат.",
                            "",
                            "що це означає:",
                            "на дистанції навіть невеликі повторювані покупки сильно впливають на загальну суму.",
                            "",
                            "що зробити:",
                            "спробуй поставити собі мʼякий ліміт на цю категорію на наступні 7 днів.",
                        ]
                    )
                )

        previous_total = get_previous_month_total(user_id)
        if previous_total is not None and month_total > previous_total:
            number = len(recommendations) + 1
            recommendations.append(
                "\n".join(
                    [
                        f"{number}. витрати стали більшими, ніж у попередньому періоді",
                        "",
                        "чому це важливо:",
                        "якщо ріст не помітити одразу, він швидко стає новою нормою.",
                        "",
                        "що це означає:",
                        "гроші почали витікати швидше.",
                        "",
                        "що зробити:",
                        "відкрий список витрат і знайди 1–2 покупки, які можна було не робити.",
                    ]
                )
            )

        if not recommendations:
            return (
                "🎯 рекомендації\n\n"
                "зараз немає різких сигналів.\n\n"
                "продовжуй фіксувати витрати — так рекомендації стануть точнішими."
            )

        return "\n\n".join(
            [
                "🎯 рекомендації",
                *recommendations[:3],
                "обери одну річ і спробуй сьогодні.",
            ]
        )
    except Exception as e:
        print(f"[ERROR] recommendations: {e}")
        return "не вдалося показати рекомендації"


def saved_expense_text(name: str, amount: int, expense_type: str | None = None) -> str:
    lines = [
        "зафіксував",
        "",
        f"💸 {name} — {format_amount(amount)} грн",
    ]
    if expense_type is not None:
        lines.append(f"📌 Тип: {format_type(expense_type)}")
    return "\n".join(lines)


def fixed_expense_text(name: str, amount: int) -> str:
    return format_save_confirmation(name, amount)


async def handle_navigation_from_add_flow(message: Message, state: FSMContext) -> bool:
    text = message.text
    if text not in ADD_FLOW_NAVIGATION_BUTTONS:
        return False

    if message.from_user:
        print(f"[ADD MODE] user={message.from_user.id} interrupted by {text}")
        EDITING_EXPENSES.pop(message.from_user.id, None)

    if text == STATS_BUTTON:
        await send_stats_period_menu(message, state)
        return True

    if text == LIST_BUTTON:
        await send_list_period_menu(message, state)
        return True

    if text in STATS_PERIOD_BUTTONS:
        await state.set_state(ExpenseStates.stats_menu)
        if text == STATS_TODAY_BUTTON:
            await send_reply_stats(message, PERIOD_DAY)
        elif text == STATS_YESTERDAY_BUTTON:
            await send_reply_stats(message, PERIOD_YESTERDAY)
        elif text == STATS_WEEK_BUTTON:
            await send_period_choice_menu(message, state, "stats", "week")
        elif text == STATS_MONTH_BUTTON:
            await send_period_choice_menu(message, state, "stats", "month")
        elif text == STATS_YEAR_BUTTON:
            await send_reply_stats(message, PERIOD_YEAR)
        elif text == STATS_ALL_BUTTON:
            await send_reply_stats(message, PERIOD_ALL)
        elif text == CUSTOM_PERIOD_BUTTON and message.from_user is not None:
            await send_period_year_menu(message, "stats", message.from_user.id)
        elif text == STATS_RECOMMENDATIONS_BUTTON and message.from_user is not None:
            await message.answer(
                build_recommendations_text(message.from_user.id),
                reply_markup=get_stats_keyboard(),
                disable_notification=True,
            )
        return True

    await state.clear()
    if text == ADD_EXPENSE_BUTTON:
        await state.set_state(ExpenseStates.add_menu)
        await message.answer("Як додати витрату?", reply_markup=get_add_keyboard(), disable_notification=True)
    elif text == OTHER_BUTTON:
        await message.answer("⚙️ Налаштування", reply_markup=get_other_keyboard(), disable_notification=True)
    else:
        await message.answer("Головне меню", reply_markup=get_main_keyboard(), disable_notification=True)
    return True


def expense_type_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Планова",
                    callback_data=f"expense_type:{expense_id}:планова",
                ),
                InlineKeyboardButton(
                    text="Емоційна",
                    callback_data=f"expense_type:{expense_id}:емоційна",
                ),
            ]
        ]
    )


def edit_type_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Замінити на планову",
                    callback_data=f"edit_type:{expense_id}:планова",
                ),
                InlineKeyboardButton(
                    text="🔥 Замінити на емоційну",
                    callback_data=f"edit_type:{expense_id}:емоційна",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="➡️ Залишити як є",
                    callback_data=f"edit_type:{expense_id}:keep",
                ),
            ],
        ]
    )


def stats_period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 За день", callback_data=f"stats:{PERIOD_DAY}"),
                InlineKeyboardButton(text="📊 За тиждень", callback_data=f"stats:{PERIOD_WEEK}"),
            ],
            [
                InlineKeyboardButton(text="📈 За весь час", callback_data=f"stats:{PERIOD_ALL}"),
            ],
        ]
    )


def list_period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 За день", callback_data=f"list:{PERIOD_DAY}"),
                InlineKeyboardButton(text="📊 За тиждень", callback_data=f"list:{PERIOD_WEEK}"),
            ],
            [
                InlineKeyboardButton(text="📈 За весь час", callback_data=f"list:{PERIOD_ALL}"),
            ],
        ]
    )


def edit_period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Сьогодні", callback_data=f"edit_period:{PERIOD_DAY}"),
                InlineKeyboardButton(text="⏪ Вчора", callback_data=f"edit_period:{PERIOD_YESTERDAY}"),
            ],
            [
                InlineKeyboardButton(text="📊 За тиждень", callback_data=f"edit_period:{PERIOD_WEEK}"),
                InlineKeyboardButton(text="📆 За місяць", callback_data=f"edit_period:{PERIOD_MONTH}"),
            ],
        ]
    )


def delete_period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Сьогодні", callback_data=f"delete_period:{PERIOD_DAY}"),
                InlineKeyboardButton(text="⏪ Вчора", callback_data=f"delete_period:{PERIOD_YESTERDAY}"),
            ],
            [
                InlineKeyboardButton(text="📊 За тиждень", callback_data=f"delete_period:{PERIOD_WEEK}"),
                InlineKeyboardButton(text="📆 За місяць", callback_data=f"delete_period:{PERIOD_MONTH}"),
            ],
            [
                InlineKeyboardButton(text="📈 За весь час", callback_data=f"delete_period:{PERIOD_ALL}"),
            ],
        ]
    )


def delete_confirm_keyboard(period: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Так", callback_data=f"confirm_delete:{period}"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_delete"),
            ]
        ]
    )


def edit_one_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редагувати",
                    callback_data=f"edit_expense:{expense_id}",
                )
            ]
        ]
    )


async def send_list_period_menu(message: Message, state: FSMContext | None = None) -> None:
    if state is not None:
        await state.set_state(ExpenseStates.list_menu)
    await message.answer("📋 Список витрат", reply_markup=get_list_keyboard(), disable_notification=True)


def build_expenses_list_text(
    expenses: list[tuple[int, str, int, str, str | None, str | None]],
    total_count: int,
    title: str | None = None,
    footer: str | None = None,
) -> str:
    return format_compact_expenses_list(expenses, total_count, title=title, footer=footer)


async def send_expenses_list(message: Message, period: str, user_id: int) -> None:
    print(f"[LIST] period={period} user={user_id}")
    expenses = get_expenses(period, user_id, limit=10)
    total_count = get_expenses_count(period, user_id)

    if not expenses:
        await message.answer(
            "за цей період поки нічого немає\n\n"
            "або ти не витрачав(ла)\n"
            "або просто не зафіксував(ла) 👀",
            reply_markup=get_list_keyboard(),
            disable_notification=True,
        )
        return

    await message.answer(
        build_expenses_list_text(expenses, total_count),
        reply_markup=get_list_keyboard(),
        disable_notification=True,
    )


async def send_custom_expenses_list(
    message: Message,
    user_id: int,
    date_from: datetime,
    date_to: datetime,
) -> None:
    expenses = get_custom_expenses(user_id, date_from, date_to, limit=10)
    total_count = get_custom_expenses_count(user_id, date_from, date_to)
    title = custom_period_title(date_from, date_to)
    current_total, _, _, _ = get_custom_stats(user_id, date_from, date_to)
    footer = custom_period_extra_text(user_id, date_from, date_to, current_total)

    if not expenses:
        lines = [
            title,
            "",
            "за цей період поки нічого немає",
            "",
            "або ти не витрачав(ла)",
            "або просто не зафіксував(ла) 👀",
        ]
        if footer:
            lines.extend(["", footer])
        await message.answer(
            "\n".join(lines),
            reply_markup=get_list_keyboard(),
            disable_notification=True,
        )
        return

    await message.answer(
        build_expenses_list_text(expenses, total_count, title=title, footer=footer),
        reply_markup=get_list_keyboard(),
        disable_notification=True,
    )


async def send_selected_expenses_list(
    message: Message,
    user_id: int,
    label: str,
    date_from: datetime,
    date_to: datetime,
) -> None:
    expenses = get_selected_expenses(user_id, date_from, date_to, limit=10)
    total_count = get_selected_expenses_count(user_id, date_from, date_to)
    title = f"📅 {label}"

    if not expenses:
        await message.answer(
            f"{title}\n\n"
            "за цей період поки нічого немає\n\n"
            "або ти не витрачав(ла)\n"
            "або просто не зафіксував(ла) 👀",
            reply_markup=get_list_keyboard(),
            disable_notification=True,
        )
        return

    await message.answer(
        build_expenses_list_text(expenses, total_count, title=title),
        reply_markup=get_list_keyboard(),
        disable_notification=True,
    )


async def send_stats_period_menu(message: Message, state: FSMContext | None = None) -> None:
    if state is not None:
        await state.set_state(ExpenseStates.stats_menu)
    await message.answer("Обери період статистики:", reply_markup=get_stats_keyboard(), disable_notification=True)


async def send_edit_expense_menu(message: Message) -> None:
    await message.answer("Оберіть період для редагування:", reply_markup=edit_period_keyboard(), disable_notification=True)


async def send_edit_expenses_by_period(message: Message, period: str, user_id: int) -> None:
    expenses = get_expenses(period, user_id, limit=10)

    if not expenses:
        await message.answer("📭 Немає витрат", reply_markup=get_other_keyboard(), disable_notification=True)
        return

    await message.answer(f"Витрати за {period_label(period)}:", reply_markup=get_other_keyboard(), disable_notification=True)
    for index, (expense_id, name, amount, date, expense_type, category_name) in enumerate(expenses, start=1):
        await message.answer(
            f"{index}. {name} — {format_amount(amount)} грн{format_type_badge(expense_type)}\n"
            f"{format_expense_category(name, category_name) or 'інше'}\n"
            f"📅 {format_expense_datetime(date)}",
            reply_markup=edit_one_keyboard(expense_id),
            disable_notification=True,
        )


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    if message.from_user is not None and not check_access(message.from_user.id):
        await message.answer(unpaid_text(), reply_markup=payment_keyboard())
        return

    await message.answer(
        "привіт 👋\n"
        "\n"
        "здається, що гроші просто зникають?\n\n"
        "спойлер: вони не зникають\n"
        "ти просто їх не помічаєш\n\n"
        "давай покажу 👇\n\n"
        "напиши першу витрату\n"
        "наприклад: кава 80",
        reply_markup=get_main_keyboard(),
    )


@router.message(Command("grant"))
async def grant_handler(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) != 2 or parts[1] not in {"7", "30"}:
        await message.answer("Формат: /grant 7 або /grant 30")
        return

    days = int(parts[1])
    GRANT_ACCESS_DAYS[message.from_user.id] = days
    await state.set_state(ExpenseStates.grant_waiting_user_id)
    await message.answer("введи user_id")


@router.message(ExpenseStates.grant_waiting_user_id)
async def grant_user_id_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    user_id_text = (message.text or "").strip()
    if not user_id_text.isdigit():
        await message.answer("введи user_id числом")
        return

    days = GRANT_ACCESS_DAYS.pop(message.from_user.id, 0)
    if days not in {7, 30}:
        await state.clear()
        await message.answer("Спочатку введи /grant 7 або /grant 30")
        return

    user_id = int(user_id_text)
    grant_access(user_id, days)
    await state.clear()
    await message.answer("доступ видано ✅")
    try:
        await bot.send_message(user_id, "доступ відкрито 🚀", reply_markup=get_main_keyboard())
    except Exception as e:
        print("ERROR sending grant message to user:", e)


@router.message(Command("test_admin"))
async def test_admin_handler(message: Message, bot: Bot) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return
    if ADMIN_USER_ID is None or ADMIN_USER_ID <= 0:
        print("ADMIN_USER_ID не заданий")
        return

    print(f"send to admin: {ADMIN_USER_ID}")
    try:
        # адмін повинен написати /start боту перед тестом
        await bot.send_message(
            chat_id=ADMIN_USER_ID,
            text="тест — якщо ти це бачиш, все працює ✅",
        )
    except Exception as e:
        print("ERROR sending to admin:", e)


@router.message(Command("users"))
async def users_handler(message: Message) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    page = 1
    print(f"[CRM] open users page={page}")
    text, keyboard = build_users_page_text(page)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("users_page_"))
async def users_page_handler(callback: CallbackQuery) -> None:
    if callback.from_user is None or not is_admin(callback.from_user.id):
        await callback.answer()
        return
    if callback.data is None:
        await callback.answer()
        return

    page_text = callback.data.removeprefix("users_page_")
    page = int(page_text) if page_text.isdigit() else 1
    page = max(1, page)
    print(f"[CRM] open users page={page}")
    text, keyboard = build_users_page_text(page)

    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.message(Command("user"))
async def user_detail_handler(message: Message) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /user 1558522346")
        return

    user_id = int(parts[1])
    print(f"[CRM] open user={user_id}")
    user = get_crm_user(user_id)
    if not user:
        await message.answer("користувач не знайдений")
        return

    await message.answer(build_user_detail_text(user), reply_markup=user_manage_keyboard(user_id))


@router.callback_query(F.data.startswith(("grant_7_", "grant_30_", "revoke_")))
async def crm_access_action_handler(callback: CallbackQuery, bot: Bot) -> None:
    if callback.data is None or callback.from_user is None:
        await callback.answer()
        return
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return

    if callback.data.startswith("grant_7_"):
        user_id = int(callback.data.removeprefix("grant_7_"))
        days = 7
    elif callback.data.startswith("grant_30_"):
        user_id = int(callback.data.removeprefix("grant_30_"))
        days = 30
    else:
        user_id = int(callback.data.removeprefix("revoke_"))
        user = get_crm_user(user_id)
        if not user:
            if callback.message is not None:
                await callback.message.answer("користувач не знайдений")
            await callback.answer()
            return

        revoke_access(user_id)
        if callback.message is not None:
            await callback.message.answer("оновлено")
        try:
            await bot.send_message(user_id, "доступ вимкнено")
        except Exception as e:
            print(f"[ERROR] CRM revoke notify user={user_id}: {e}")
        await callback.answer()
        return

    user = get_crm_user(user_id)
    if not user:
        if callback.message is not None:
            await callback.message.answer("користувач не знайдений")
        await callback.answer()
        return

    print(f"[CRM] grant {days} → {user_id}")
    grant_access(user_id, days)
    if callback.message is not None:
        await callback.message.answer("оновлено")
    try:
        await bot.send_message(user_id, "доступ оновлено 🚀", reply_markup=get_main_keyboard())
    except Exception as e:
        print(f"[ERROR] CRM grant notify user={user_id}: {e}")
    await callback.answer()


@router.message(Command("broadcast_unpaid"))
async def broadcast_unpaid_handler(message: Message, bot: Bot) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    now = int(time.time())
    user_ids = get_broadcast_unpaid_users(now)
    text = "\n".join(
        [
            "вчора ти ще фіксував витрати",
            "",
            "сьогодні вже ні",
            "",
            "і саме тут гроші знову починають «зникати»",
            "",
            "поверни контроль 👇",
            "👉 оплатити доступ",
        ]
    )

    sent = 0
    errors = 0
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, text, reply_markup=payment_keyboard())
            mark_auto_message_sent(user_id, now)
            sent += 1
            print(f"[BROADCAST] sent → {user_id}")
        except Exception as e:
            errors += 1
            print(f"[BROADCAST] error → {user_id}: {e}")

    await message.answer(f"розсилка завершена\nвідправлено: {sent}\nпомилок: {errors}")


@router.callback_query(F.data.startswith("message_"))
async def crm_message_start_handler(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.from_user is None:
        await callback.answer()
        return
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return

    user_id_text = callback.data.removeprefix("message_")
    if not user_id_text.isdigit():
        if callback.message is not None:
            await callback.message.answer("помилка")
        await callback.answer()
        return

    target_user_id = int(user_id_text)
    user = get_crm_user(target_user_id)
    if not user:
        if callback.message is not None:
            await callback.message.answer("помилка")
        await callback.answer()
        return

    await state.set_state(ExpenseStates.waiting_message)
    await state.update_data(target_user_id=target_user_id)
    if callback.message is not None:
        await callback.message.answer("введи повідомлення для клієнта")
    await callback.answer()


@router.callback_query(F.data.startswith(("template_remind_", "template_expired_", "template_offer_")))
async def crm_template_handler(callback: CallbackQuery, bot: Bot) -> None:
    if callback.data is None or callback.from_user is None:
        await callback.answer()
        return
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return

    template = ""
    user_id_text = ""
    if callback.data.startswith("template_remind_"):
        template = "remind"
        user_id_text = callback.data.removeprefix("template_remind_")
    elif callback.data.startswith("template_expired_"):
        template = "expired"
        user_id_text = callback.data.removeprefix("template_expired_")
    elif callback.data.startswith("template_offer_"):
        template = "offer"
        user_id_text = callback.data.removeprefix("template_offer_")

    if not user_id_text.isdigit():
        if callback.message is not None:
            await callback.message.answer("помилка")
        await callback.answer()
        return

    target_user_id = int(user_id_text)
    user = get_crm_user(target_user_id)
    template_text = get_crm_template_text(template)
    if not user or template_text is None:
        if callback.message is not None:
            await callback.message.answer("помилка")
        await callback.answer()
        return

    try:
        await bot.send_message(chat_id=target_user_id, text=template_text)
        print(f"[CRM TEMPLATE] sent → {target_user_id}")
        if callback.message is not None:
            await callback.message.answer("шаблон відправлено ✅")
    except Exception as e:
        print("[CRM TEMPLATE ERROR]", e)
        if callback.message is not None:
            await callback.message.answer("не вдалося відправити")
    await callback.answer()


@router.message(ExpenseStates.waiting_message)
async def crm_message_send_handler(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.from_user is None or not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    if not isinstance(target_user_id, int):
        await state.clear()
        await message.answer("помилка")
        return

    user = get_crm_user(target_user_id)
    if not user:
        await state.clear()
        await message.answer("помилка")
        return

    try:
        await bot.send_message(chat_id=target_user_id, text=message.text or "")
        print(f"[CRM] admin sent message → {target_user_id}")
        await message.answer("повідомлення відправлено ✅")
    except Exception as e:
        print("[CRM MESSAGE ERROR]", e)
        await message.answer("не вдалося відправити")
    finally:
        await state.clear()


@router.message(Command("list"))
async def list_handler(message: Message, state: FSMContext) -> None:
    await send_list_period_menu(message, state)


@router.message(Command("stats"))
async def stats_handler(message: Message, state: FSMContext) -> None:
    await send_stats_period_menu(message, state)


@router.message(Command("today"))
async def today_handler(message: Message) -> None:
    if message.from_user is None:
        return
    expenses = get_today_expenses(message.from_user.id)

    if not expenses:
        await message.answer("📭 Немає витрат", reply_markup=get_main_keyboard())
        return

    total = sum(amount for _, amount in expenses)
    lines = [
        "За сьогодні:",
        f"Сума: {format_amount(total)} грн",
        "",
        "Витрати:",
    ]

    for index, (name, amount) in enumerate(expenses, start=1):
        lines.append(f"{index}. {name} — {format_amount(amount)} грн")

    await message.answer("\n".join(lines), reply_markup=get_main_keyboard())


def strip_button_label(text: str) -> str:
    return re.sub(r"^[^\wА-Яа-яІіЇїЄєҐґ]+", "", text).strip()


def quick_expense_added_text(display_title: str, amount: int) -> str:
    return (
        "✅ Витрату додано\n\n"
        f"{display_title} — {format_amount(amount)} грн"
    )


@router.message(ExpenseStates.add_menu, F.text.in_(ADD_FLOW_NAVIGATION_BUTTONS))
@router.message(ExpenseStates.choosing_category, F.text.in_(ADD_FLOW_NAVIGATION_BUTTONS))
@router.message(ExpenseStates.choosing_subcategory, F.text.in_(ADD_FLOW_NAVIGATION_BUTTONS))
@router.message(ExpenseStates.category_menu, F.text.in_(ADD_FLOW_NAVIGATION_BUTTONS))
@router.message(ExpenseStates.subcategory_menu, F.text.in_(ADD_FLOW_NAVIGATION_BUTTONS))
@router.message(ExpenseStates.waiting_amount, F.text.in_(ADD_FLOW_NAVIGATION_BUTTONS))
@router.message(ExpenseStates.waiting_for_amount, F.text.in_(ADD_FLOW_NAVIGATION_BUTTONS))
@router.message(ExpenseStates.waiting_expense_input, F.text.in_(ADD_FLOW_NAVIGATION_BUTTONS))
@router.message(ExpenseStates.waiting_expense_amount, F.text.in_(ADD_FLOW_NAVIGATION_BUTTONS))
async def add_flow_navigation_handler(message: Message, state: FSMContext) -> None:
    await handle_navigation_from_add_flow(message, state)


@router.message(ExpenseStates.choosing_category, F.text.in_(CATEGORY_BUTTONS))
@router.message(ExpenseStates.category_menu, F.text.in_(CATEGORY_BUTTONS))
async def category_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(ExpenseStates.choosing_subcategory)
    await state.update_data(category=message.text)
    await message.answer(f"{message.text}:", reply_markup=get_category_keyboard(message.text))


@router.message(ExpenseStates.choosing_subcategory, F.text.in_(set(SUBCATEGORY_TO_NAME)))
@router.message(ExpenseStates.subcategory_menu, F.text.in_(set(SUBCATEGORY_TO_NAME)))
async def subcategory_handler(message: Message, state: FSMContext) -> None:
    expense_name = SUBCATEGORY_TO_NAME[message.text]
    data = await state.get_data()
    category_button = data.get("category")
    category_name = strip_button_label(category_button).lower() if isinstance(category_button, str) else None
    await state.update_data(
        expense_name=expense_name,
        expense_display=message.text,
        expense_category=category_name,
    )
    await state.set_state(ExpenseStates.waiting_amount)
    await message.answer("Введи суму 💸", reply_markup=get_expense_input_keyboard())


@router.message(ExpenseStates.waiting_amount, F.text == STATS_BACK_BUTTON)
@router.message(ExpenseStates.waiting_amount, F.text == BACK_BUTTON)
@router.message(ExpenseStates.waiting_for_amount, F.text == BACK_BUTTON)
async def amount_back_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(ExpenseStates.choosing_subcategory)
    data = await state.get_data()
    category = data.get("category")
    if isinstance(category, str) and category in CATEGORY_MENUS:
        await message.answer(f"{category}:", reply_markup=get_category_keyboard(category))
    else:
        await state.set_state(ExpenseStates.choosing_category)
        await message.answer("Оберіть категорію:", reply_markup=get_categories_keyboard())


@router.message(ExpenseStates.waiting_amount)
@router.message(ExpenseStates.waiting_for_amount)
async def amount_handler(message: Message, state: FSMContext) -> None:
    amount = parse_amount(message.text)
    if amount is None:
        await message.answer("Введи тільки суму (наприклад: 80)", reply_markup=get_expense_input_keyboard())
        return

    data = await state.get_data()
    name = data.get("expense_name")
    display_title = data.get("expense_display")
    category = data.get("expense_category")
    await state.clear()

    if not isinstance(name, str) or not name:
        await message.answer(ERROR_FORMAT_MESSAGE, reply_markup=get_main_keyboard())
        return

    user_id = message.from_user.id if message.from_user else None
    expense_id = save_expense(name, amount, user_id, category if isinstance(category, str) else None)
    if user_id is not None:
        QUICK_REPEAT_DATA[user_id] = {
            "name": name,
            "display": display_title if isinstance(display_title, str) else name,
            "amount": amount,
            "category": category if isinstance(category, str) else None,
        }
    await message.answer("Оберіть тип витрати:", reply_markup=expense_type_keyboard(expense_id))


@router.message(F.text == ADD_EXPENSE_BUTTON)
async def add_expense_button_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(ExpenseStates.add_menu)
    if message.from_user:
        EDITING_EXPENSES.pop(message.from_user.id, None)
    await message.answer("Як додати витрату?", reply_markup=get_add_keyboard())


@router.message(ExpenseStates.waiting_expense_input, F.text == STATS_BACK_BUTTON)
@router.message(ExpenseStates.waiting_expense_input, F.text == BACK_BUTTON)
@router.message(ExpenseStates.waiting_expense_amount, F.text == STATS_BACK_BUTTON)
@router.message(ExpenseStates.waiting_expense_amount, F.text == BACK_BUTTON)
async def expense_input_back_handler(message: Message, state: FSMContext) -> None:
    if message.from_user:
        print(f"[ADD MODE] user={message.from_user.id} cancelled")
    await state.clear()
    await message.answer("повернув у головне меню", reply_markup=get_main_keyboard(), disable_notification=True)


@router.message(ExpenseStates.waiting_expense_input)
async def expense_input_handler(message: Message, state: FSMContext) -> None:
    blocked_buttons = {
        ADD_EXPENSE_BUTTON,
        STATS_BUTTON,
        LIST_BUTTON,
        COMPARE_BUTTON,
        REPORT_BUTTON,
        OTHER_BUTTON,
        MANUAL_ADD_BUTTON,
        QUICK_ADD_BUTTON,
        EDIT_BUTTON,
        DELETE_BUTTON,
        MY_ACCESS_BUTTON,
        HOW_IT_WORKS_BUTTON,
    }
    if message.text in blocked_buttons:
        await message.answer(
            "спочатку введи витрату або натисни «⬅️ назад»",
            reply_markup=get_expense_input_keyboard(),
        )
        return
    if looks_like_period_choice_text(message.text):
        await state.clear()
        await message.answer(
            "Це кнопка статистики. Обери період у розділі 📊 Статистика.",
            reply_markup=get_stats_keyboard(),
            disable_notification=True,
        )
        return

    parsed = parse_smart_expense_input(message.text)
    if parsed is None:
        await message.answer("Напиши назву витрати або суму", reply_markup=get_expense_input_keyboard())
        return

    name, amount = parsed
    if name and amount:
        user_id = message.from_user.id if message.from_user else None
        expense_id = save_expense(name, amount, user_id)
        await state.clear()
        if user_id is not None:
            print(f"[ADD MODE] user={user_id} expense saved")
        await message.answer("Оберіть тип витрати:", reply_markup=expense_type_keyboard(expense_id))
        return

    if name and amount is None:
        await state.set_state(ExpenseStates.waiting_expense_amount)
        await state.update_data(expense_name=name)
        await message.answer("💸 Введи суму", reply_markup=get_expense_input_keyboard())
        return

    await message.answer("Спочатку напиши назву витрати", reply_markup=get_expense_input_keyboard())


@router.message(ExpenseStates.waiting_expense_amount)
async def expense_amount_input_handler(message: Message, state: FSMContext) -> None:
    if looks_like_period_choice_text(message.text):
        await state.clear()
        await message.answer(
            "Це кнопка статистики. Обери період у розділі 📊 Статистика.",
            reply_markup=get_stats_keyboard(),
            disable_notification=True,
        )
        return

    amount = parse_amount(message.text)
    if amount is None:
        await message.answer("💸 Введи суму", reply_markup=get_expense_input_keyboard())
        return

    data = await state.get_data()
    name = data.get("expense_name")
    if not isinstance(name, str) or not name.strip():
        await state.set_state(ExpenseStates.waiting_expense_input)
        await message.answer("Спочатку напиши назву витрати", reply_markup=get_expense_input_keyboard())
        return

    user_id = message.from_user.id if message.from_user else None
    expense_id = save_expense(name, amount, user_id)
    await state.clear()
    if user_id is not None:
        print(f"[ADD MODE] user={user_id} expense saved")
    await message.answer("Оберіть тип витрати:", reply_markup=expense_type_keyboard(expense_id))


@router.message(F.text == MANUAL_ADD_BUTTON)
async def manual_add_button_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(ExpenseStates.waiting_expense_input)
    if message.from_user:
        print(f"[ADD MODE] user={message.from_user.id} entered")
    await message.answer(
        "Напиши витрату\n\n"
        "Можна так:\n"
        "кава 80\n"
        "або окремо:\n"
        "кава\n"
        "80\n\n"
        "якщо передумав — натисни «⬅️ назад»",
        reply_markup=get_expense_input_keyboard(),
    )


@router.message(F.text == QUICK_ADD_BUTTON)
async def quick_add_button_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(ExpenseStates.choosing_category)
    await message.answer("Оберіть категорію:", reply_markup=get_categories_keyboard())


@router.message(F.text == STATS_BUTTON)
async def stats_button_handler(message: Message, state: FSMContext) -> None:
    await send_stats_period_menu(message, state)


async def send_reply_stats(message: Message, period: str) -> None:
    try:
        if message.from_user is None:
            return
        top_categories = get_top_categories_for_period(period, message.from_user.id)
        reply_markup = get_stats_keyboard()
        if period not in {PERIOD_DAY, PERIOD_WEEK}:
            reply_markup = category_details_keyboard(top_categories, f"period:{period}") or get_stats_keyboard()
        await message.answer(
            build_reply_stats_text(period, message.from_user.id),
            reply_markup=reply_markup,
            disable_notification=True,
        )
    except Exception as e:
        print(f"[ERROR] stats period={period}: {e}")
        await message.answer("не вдалося показати статистику", reply_markup=get_stats_keyboard(), disable_notification=True)


async def ask_custom_period(message: Message, state: FSMContext, mode: str) -> None:
    await state.set_state(ExpenseStates.waiting_date_from)
    await state.update_data(mode=mode)
    keyboard = get_stats_keyboard() if mode == "stats" else get_list_keyboard()
    await message.answer(
        "введи дату «від»\n"
        "формат: 04.05.2026",
        reply_markup=keyboard,
        disable_notification=True,
    )


async def send_period_year_menu(message: Message, mode: str, user_id: int) -> None:
    years = get_period_years(user_id)
    print(f"[PERIOD MENU] mode={mode} user={user_id} step=year")
    if not years:
        keyboard = get_stats_keyboard() if mode == "stats" else get_list_keyboard()
        await message.answer(
            "поки немає витрат для вибору періоду\n\n"
            "спочатку додай кілька витрат 👇",
            reply_markup=keyboard,
            disable_notification=True,
        )
        return

    await message.answer("Обери рік:", reply_markup=period_years_keyboard(mode, years), disable_notification=True)


async def send_period_choice_menu(message: Message, state: FSMContext, mode: str, kind: str) -> None:
    periods = week_periods_for_month() if kind == "week" else month_periods()
    if mode == "stats" and kind == "month":
        await state.set_state(ExpenseStates.stats_menu)
        await state.update_data(mode=mode, choice_kind=kind)
        await message.answer("Обери місяць:", reply_markup=get_stats_month_choice_keyboard(periods), disable_notification=True)
        return

    await state.set_state(ExpenseStates.period_choice_menu)
    await state.update_data(mode=mode, choice_kind=kind, periods=periods)
    await message.answer(
        "Обери тиждень:" if kind == "week" else "Обери місяць:",
        reply_markup=get_period_choice_keyboard(periods),
        disable_notification=True,
    )


@router.message(ExpenseStates.stats_menu, F.text == STATS_TODAY_BUTTON)
async def stats_today_button_handler(message: Message) -> None:
    await send_reply_stats(message, PERIOD_DAY)


@router.message(ExpenseStates.stats_menu, F.text == STATS_YESTERDAY_BUTTON)
async def stats_yesterday_button_handler(message: Message) -> None:
    await send_reply_stats(message, PERIOD_YESTERDAY)


@router.message(ExpenseStates.stats_menu, F.text == STATS_WEEK_BUTTON)
async def stats_week_button_handler(message: Message, state: FSMContext) -> None:
    await send_period_choice_menu(message, state, "stats", "week")


@router.message(ExpenseStates.stats_menu, F.text == STATS_MONTH_BUTTON)
async def stats_month_button_handler(message: Message, state: FSMContext) -> None:
    await send_period_choice_menu(message, state, "stats", "month")


@router.message(ExpenseStates.stats_menu, F.text == STATS_YEAR_BUTTON)
async def stats_year_button_handler(message: Message) -> None:
    await send_reply_stats(message, PERIOD_YEAR)


@router.message(ExpenseStates.stats_menu, F.text == STATS_ALL_BUTTON)
async def stats_all_button_handler(message: Message) -> None:
    await send_reply_stats(message, PERIOD_ALL)


@router.message(ExpenseStates.stats_menu, F.text == CUSTOM_PERIOD_BUTTON)
async def stats_custom_period_button_handler(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    await send_period_year_menu(message, "stats", message.from_user.id)


@router.message(ExpenseStates.stats_menu, F.text == STATS_RECOMMENDATIONS_BUTTON)
async def stats_recommendations_button_handler(message: Message) -> None:
    try:
        if message.from_user is None:
            return
        await message.answer(
            build_recommendations_text(message.from_user.id),
            reply_markup=get_stats_keyboard(),
            disable_notification=True,
        )
    except Exception as e:
        print(f"[ERROR] stats recommendations: {e}")
        await message.answer("не вдалося показати рекомендації", reply_markup=get_stats_keyboard(), disable_notification=True)


@router.message(ExpenseStates.stats_menu, F.text == STATS_BACK_BUTTON)
async def stats_back_button_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Головне меню", reply_markup=get_main_keyboard(), disable_notification=True)


@router.message(F.text == LIST_BUTTON)
async def list_button_handler(message: Message, state: FSMContext) -> None:
    await send_list_period_menu(message, state)


async def send_reply_list(message: Message, period: str) -> None:
    try:
        if message.from_user is None:
            return
        await send_expenses_list(message, period, message.from_user.id)
    except Exception as e:
        print(f"[ERROR] list period={period}: {e}")
        await message.answer("не вдалося показати список", reply_markup=get_list_keyboard(), disable_notification=True)


@router.message(ExpenseStates.list_menu, F.text == STATS_TODAY_BUTTON)
async def list_today_button_handler(message: Message) -> None:
    await send_reply_list(message, PERIOD_DAY)


@router.message(ExpenseStates.list_menu, F.text == STATS_YESTERDAY_BUTTON)
async def list_yesterday_button_handler(message: Message) -> None:
    await send_reply_list(message, PERIOD_YESTERDAY)


@router.message(ExpenseStates.list_menu, F.text == STATS_WEEK_BUTTON)
async def list_week_button_handler(message: Message, state: FSMContext) -> None:
    await send_period_choice_menu(message, state, "list", "week")


@router.message(ExpenseStates.list_menu, F.text == STATS_MONTH_BUTTON)
async def list_month_button_handler(message: Message, state: FSMContext) -> None:
    await send_period_choice_menu(message, state, "list", "month")


@router.message(ExpenseStates.list_menu, F.text == STATS_ALL_BUTTON)
async def list_all_button_handler(message: Message) -> None:
    await send_reply_list(message, PERIOD_ALL)


@router.message(ExpenseStates.list_menu, F.text == CUSTOM_PERIOD_BUTTON)
async def list_custom_period_button_handler(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    await send_period_year_menu(message, "list", message.from_user.id)


@router.message(ExpenseStates.list_menu, F.text == STATS_BACK_BUTTON)
async def list_back_button_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Головне меню", reply_markup=get_main_keyboard(), disable_notification=True)


@router.message(ExpenseStates.period_choice_menu, F.text == STATS_BACK_BUTTON)
async def period_choice_back_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    mode = data.get("mode")
    if mode == "stats":
        await state.set_state(ExpenseStates.stats_menu)
        await message.answer("Обери період статистики:", reply_markup=get_stats_keyboard(), disable_notification=True)
        return

    await state.set_state(ExpenseStates.list_menu)
    await message.answer("📋 Список витрат", reply_markup=get_list_keyboard(), disable_notification=True)


@router.message(ExpenseStates.period_choice_menu)
async def period_choice_handler(message: Message, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return

        data = await state.get_data()
        periods = data.get("periods")
        if not isinstance(periods, list):
            await state.clear()
            await message.answer("не вдалося знайти періоди", reply_markup=get_main_keyboard(), disable_notification=True)
            return

        selected = next(
            (period for period in periods if isinstance(period, dict) and period.get("label") == message.text),
            None,
        )
        if selected is None:
            await message.answer("обери період кнопкою", reply_markup=get_period_choice_keyboard(periods), disable_notification=True)
            return

        label = str(selected["label"])
        date_from = datetime.fromisoformat(str(selected["from"]))
        date_to = datetime.fromisoformat(str(selected["to"]))
        mode = data.get("mode")
        print(
            f"[PERIOD] user={message.from_user.id} "
            f"from={date_from.date().isoformat()} "
            f"to={(date_to - timedelta(days=1)).date().isoformat()} "
            f"mode={mode}"
        )

        if mode == "stats":
            await state.set_state(ExpenseStates.stats_menu)
            top_categories = get_top_categories_for_selected(message.from_user.id, date_from, date_to)
            if data.get("choice_kind") == "week":
                title = f"📊 Тиждень {format_numeric_day(date_from)}–{format_numeric_day(date_to - timedelta(days=1))}"
                await message.answer(
                    build_short_selected_stats_text(message.from_user.id, title, date_from, date_to),
                    reply_markup=get_stats_keyboard(),
                    disable_notification=True,
                )
                return
            if data.get("choice_kind") == "month":
                label = f"📊 Місяць {UKRAINIAN_MONTH_NAMES[date_from.month]}"
            await message.answer(
                build_selected_stats_text(message.from_user.id, label, date_from, date_to),
                reply_markup=category_details_keyboard(top_categories, range_scope(date_from, date_to)) or get_stats_keyboard(),
                disable_notification=True,
            )
            return

        await state.set_state(ExpenseStates.list_menu)
        await send_selected_expenses_list(message, message.from_user.id, label, date_from, date_to)
    except Exception as e:
        print(f"[ERROR] selected period: {e}")
        await message.answer("не вдалося показати період", reply_markup=get_main_keyboard(), disable_notification=True)


@router.message(ExpenseStates.waiting_date_from, F.text == STATS_BACK_BUTTON)
@router.message(ExpenseStates.waiting_date_to, F.text == STATS_BACK_BUTTON)
async def custom_period_back_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    mode = data.get("mode")
    if mode == "stats":
        await state.set_state(ExpenseStates.stats_menu)
        await message.answer("Обери період статистики:", reply_markup=get_stats_keyboard(), disable_notification=True)
        return

    await state.set_state(ExpenseStates.list_menu)
    await message.answer("📋 Список витрат", reply_markup=get_list_keyboard(), disable_notification=True)


@router.message(ExpenseStates.waiting_date_from)
async def custom_period_from_handler(message: Message, state: FSMContext) -> None:
    try:
        data = await state.get_data()
        keyboard = get_stats_keyboard() if data.get("mode") == "stats" else get_list_keyboard()
        date_from = parse_period_date(message.text)
        if date_from is None:
            await message.answer(
                "не зрозумів дату\n"
                "введи у форматі: 04.05.2026",
                reply_markup=keyboard,
                disable_notification=True,
            )
            return

        await state.update_data(date_from=date_from.date().isoformat())
        await state.set_state(ExpenseStates.waiting_date_to)
        await message.answer(
            "введи дату «до»\n"
            "формат: 10.05.2026",
            reply_markup=keyboard,
            disable_notification=True,
        )
    except Exception as e:
        print(f"[ERROR] period date_from: {e}")
        await message.answer("не вдалося прочитати дату", reply_markup=get_main_keyboard(), disable_notification=True)


@router.message(ExpenseStates.waiting_date_to)
async def custom_period_to_handler(message: Message, state: FSMContext) -> None:
    try:
        if message.from_user is None:
            return

        date_to = parse_period_date(message.text)
        data = await state.get_data()
        mode = data.get("mode")
        keyboard = get_stats_keyboard() if mode == "stats" else get_list_keyboard()

        if date_to is None:
            await message.answer(
                "не зрозумів дату\n"
                "введи у форматі: 10.05.2026",
                reply_markup=keyboard,
                disable_notification=True,
            )
            return

        date_from_raw = data.get("date_from")
        if not isinstance(date_from_raw, str):
            await state.clear()
            await message.answer("не вдалося знайти дату «від»", reply_markup=get_main_keyboard(), disable_notification=True)
            return

        date_from = datetime.fromisoformat(date_from_raw)
        if date_to.date() < date_from.date():
            await message.answer(
                "дата «до» не може бути раніше «від»",
                reply_markup=keyboard,
                disable_notification=True,
            )
            return

        user_id = message.from_user.id
        await state.update_data(date_to=date_to.date().isoformat())
        print(
            f"[PERIOD] user={user_id} "
            f"from={date_from.date().isoformat()} "
            f"to={date_to.date().isoformat()} "
            f"mode={mode}"
        )

        if mode == "stats":
            await state.set_state(ExpenseStates.stats_menu)
            top_categories = get_top_categories_for_selected(user_id, date_from, date_to)
            await message.answer(
                build_custom_stats_text(user_id, date_from, date_to),
                reply_markup=category_details_keyboard(top_categories, range_scope(date_from, date_to)) or get_stats_keyboard(),
                disable_notification=True,
            )
            return

        await state.set_state(ExpenseStates.list_menu)
        await send_custom_expenses_list(message, user_id, date_from, date_to)
    except Exception as e:
        print(f"[ERROR] period custom: {e}")
        await message.answer("не вдалося показати період", reply_markup=get_main_keyboard(), disable_notification=True)


@router.callback_query(F.data.startswith("period_back_"))
async def period_menu_back_handler(callback: CallbackQuery) -> None:
    if callback.data is None or callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    parts = callback.data.split("*")
    action = parts[0]
    user_id = callback.from_user.id

    if action in {"period_back_stats", "period_back_list"}:
        mode = "stats" if action == "period_back_stats" else "list"
        keyboard = get_stats_keyboard() if mode == "stats" else get_list_keyboard()
        text = "Обери період статистики:" if mode == "stats" else "📋 Список витрат"
        await callback.message.answer(text, reply_markup=keyboard, disable_notification=True)
        await callback.answer()
        return

    if action == "period_back_years" and len(parts) == 2:
        mode = parts[1]
        years = get_period_years(user_id)
        print(f"[PERIOD MENU] mode={mode} user={user_id} step=year")
        await callback.message.edit_text("Обери рік:", reply_markup=period_years_keyboard(mode, years))
        await callback.answer()
        return

    if action == "period_back_months" and len(parts) == 3:
        mode = parts[1]
        year = int(parts[2])
        months = get_period_months(user_id, year)
        print(f"[PERIOD MENU] mode={mode} user={user_id} step=month")
        await callback.message.edit_text(
            f"Обери місяць {year}:",
            reply_markup=period_months_keyboard(mode, year, months),
        )
        await callback.answer()
        return

    await callback.answer()


@router.callback_query(F.data.startswith("period_year_"))
async def period_year_handler(callback: CallbackQuery) -> None:
    if callback.data is None or callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    payload = callback.data.removeprefix("period_year_")
    mode, year_text = payload.split("*", maxsplit=1)
    year = int(year_text)
    months = get_period_months(callback.from_user.id, year)
    print(f"[PERIOD MENU] mode={mode} user={callback.from_user.id} step=month")

    if not months:
        await callback.message.edit_text(
            "поки немає витрат для вибору періоду\n\n"
            "спочатку додай кілька витрат 👇",
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"Обери місяць {year}:",
        reply_markup=period_months_keyboard(mode, year, months),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("period_month*"))
async def period_month_handler(callback: CallbackQuery) -> None:
    if callback.data is None or callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    _, mode, year_text, month_text = callback.data.split("*", maxsplit=3)
    year = int(year_text)
    month = int(month_text)
    days = get_period_days(callback.from_user.id, year, month)
    print(f"[PERIOD MENU] mode={mode} user={callback.from_user.id} step=day")

    if not days:
        await callback.message.edit_text(
            "поки немає витрат для вибору періоду\n\n"
            "спочатку додай кілька витрат 👇",
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"Обери дату за {UKRAINIAN_MONTH_NAMES[month]} {year}:",
        reply_markup=period_days_keyboard(mode, year, month, days),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("period_day_"))
async def period_day_handler(callback: CallbackQuery) -> None:
    if callback.data is None or callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    payload = callback.data.removeprefix("period_day_")
    mode, year_text, month_text, day_text = payload.split("*", maxsplit=3)
    year = int(year_text)
    month = int(month_text)
    day = int(day_text)
    date_from = datetime(year, month, day)
    date_to = date_from + timedelta(days=1)
    label = f"{day:02d} {UKRAINIAN_MONTHS[month]}"
    user_id = callback.from_user.id
    print(f"[PERIOD MENU] mode={mode} user={user_id} step=result")

    await callback.message.edit_reply_markup(reply_markup=None)
    if mode == "stats":
        today = datetime.now().date()
        title = (
            f"📊 Сьогодні {format_numeric_day(date_from)}"
            if date_from.date() == today
            else f"📊 {format_numeric_day(date_from)}"
        )
        await callback.message.answer(
            build_short_selected_stats_text(user_id, title, date_from, date_to),
            reply_markup=get_stats_keyboard(),
            disable_notification=True,
        )
    else:
        await send_selected_expenses_list(callback.message, user_id, label, date_from, date_to)
    await callback.answer()


@router.callback_query(F.data.startswith("period_full_month*"))
async def period_full_month_handler(callback: CallbackQuery) -> None:
    if callback.data is None or callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    _, mode, year_text, month_text = callback.data.split("*", maxsplit=3)
    year = int(year_text)
    month = int(month_text)
    date_from, date_to = month_bounds(datetime(year, month, 1))
    label = f"📊 Місяць {UKRAINIAN_MONTH_NAMES[month]}"
    user_id = callback.from_user.id
    print(f"[PERIOD MENU] mode={mode} user={user_id} step=result")

    await callback.message.edit_reply_markup(reply_markup=None)
    if mode == "stats":
        top_categories = get_top_categories_for_selected(user_id, date_from, date_to)
        await callback.message.answer(
            build_selected_stats_text(user_id, label, date_from, date_to),
            reply_markup=category_details_keyboard(top_categories, f"month:{year}:{month}") or get_stats_keyboard(),
            disable_notification=True,
        )
    else:
        await send_selected_expenses_list(callback.message, user_id, label, date_from, date_to)
    await callback.answer()


@router.message(F.text == COMPARE_BUTTON)
async def compare_button_handler(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    await message.answer(build_compare_text(user_id), reply_markup=get_main_keyboard(), disable_notification=True)


@router.message(F.text == REPORT_BUTTON)
async def report_button_handler(message: Message) -> None:
    if message.from_user is None:
        return

    months = get_report_months(message.from_user.id, DB_PATH)
    if not months:
        await message.answer(
            "Поки немає витрат для місячного звіту.\n\nСпочатку додай кілька витрат 👇",
            reply_markup=get_main_keyboard(),
            disable_notification=True,
        )
        return

    await message.answer("Обери місяць для звіту:", reply_markup=get_report_months_keyboard(months), disable_notification=True)


@router.callback_query(F.data.startswith("report_month:"))
async def report_month_handler(callback: CallbackQuery, bot: Bot) -> None:
    if callback.data is None or callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    _, year_text, month_text = callback.data.split(":", maxsplit=2)
    year = int(year_text)
    month = int(month_text)
    await bot.send_chat_action(callback.message.chat.id, "typing")
    loading = await callback.message.answer("🤖 Формую звіт...", disable_notification=True)

    try:
        report = await generate_month_report(callback.from_user.id, DB_PATH, year, month)
        await loading.edit_text(report, reply_markup=get_selected_month_report_keyboard(year, month))
    except Exception as e:
        print(f"[REPORT ERROR] user={callback.from_user.id}: {e}")
        await loading.edit_text("Місячний звіт тимчасово недоступний 😔")
    await callback.answer()


@router.callback_query(F.data.startswith("report_categories:"))
async def report_categories_handler(callback: CallbackQuery) -> None:
    if callback.data is None or callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    _, year_text, month_text = callback.data.split(":", maxsplit=2)
    year = int(year_text)
    month = int(month_text)

    try:
        text = await generate_month_categories(callback.from_user.id, DB_PATH, year, month)
        categories = get_month_report_categories(callback.from_user.id, DB_PATH, year, month)
        await callback.message.answer(
            text,
            reply_markup=get_report_categories_keyboard(year, month, categories),
            disable_notification=True,
        )
    except Exception as e:
        print(f"[REPORT CATEGORIES ERROR] user={callback.from_user.id}: {e}")
        await callback.message.answer("Розбивка по категоріях тимчасово недоступна 😔", disable_notification=True)
    await callback.answer()


@router.callback_query(F.data.startswith("stats_month:"))
async def stats_month_callback_handler(callback: CallbackQuery, state: FSMContext) -> None:
    current_state = await state.get_state()
    print(
        f"[CALLBACK] handler=stats_month user_id={callback.from_user.id if callback.from_user else None} "
        f"data={callback.data} current_state={current_state}"
    )
    if callback.data is None or callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    await state.clear()
    _, month_key = callback.data.split(":", maxsplit=1)
    year_text, month_text = month_key.split("-", maxsplit=1)
    year = int(year_text)
    month = int(month_text)
    date_from, date_to = month_bounds(datetime(year, month, 1))
    top_categories = get_top_categories_for_selected(callback.from_user.id, date_from, date_to)
    text = build_month_stats_text(callback.from_user.id, year, month)
    reply_markup = category_details_keyboard(top_categories, f"month:{year}:{month}") if top_categories else None

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(text, reply_markup=reply_markup or get_stats_keyboard(), disable_notification=True)
    await callback.answer()


@router.callback_query(F.data == "stats_back")
async def stats_back_callback_handler(callback: CallbackQuery, state: FSMContext) -> None:
    current_state = await state.get_state()
    print(
        f"[CALLBACK] handler=stats_back user_id={callback.from_user.id if callback.from_user else None} "
        f"data={callback.data} current_state={current_state}"
    )
    await state.clear()
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Обери період статистики:", reply_markup=get_stats_keyboard(), disable_notification=True)
    await callback.answer()


@router.callback_query(F.data.startswith("report_cat:"))
async def report_category_drilldown_handler(callback: CallbackQuery) -> None:
    if callback.data is None or callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    _, year_text, month_text, category = callback.data.split(":", maxsplit=3)
    year = int(year_text)
    month = int(month_text)

    try:
        text = build_category_drilldown(callback.from_user.id, category, DB_PATH, year, month)
        await callback.message.answer(
            text,
            reply_markup=get_report_categories_keyboard(
                year,
                month,
                get_month_report_categories(callback.from_user.id, DB_PATH, year, month),
            ),
            disable_notification=True,
        )
    except Exception as e:
        print(f"[REPORT CATEGORY DETAIL ERROR] user={callback.from_user.id}: {e}")
        await callback.message.answer("Деталізація категорії тимчасово недоступна 😔", disable_notification=True)
    await callback.answer()


@router.callback_query(F.data.startswith("catdet:"))
async def category_details_handler(callback: CallbackQuery, state: FSMContext) -> None:
    current_state = await state.get_state()
    print(
        f"[CALLBACK] handler=category_details user_id={callback.from_user.id if callback.from_user else None} "
        f"data={callback.data} current_state={current_state}"
    )
    if callback.data is None or callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    parts = callback.data.split(":")
    date_from = None
    date_to = None
    category = ""
    if len(parts) >= 3 and parts[1] == "period":
        period = parts[2]
        category = ":".join(parts[3:])
        now = datetime.now()
        if period == PERIOD_DAY:
            date_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
            date_to = date_from + timedelta(days=1)
        elif period == PERIOD_YESTERDAY:
            date_to = now.replace(hour=0, minute=0, second=0, microsecond=0)
            date_from = date_to - timedelta(days=1)
        elif period == PERIOD_WEEK:
            date_from, date_to = current_week_bounds(now)
        elif period == PERIOD_MONTH:
            date_from, date_to = month_bounds(now)
        elif period == PERIOD_YEAR:
            date_to = now
            date_from = now - timedelta(days=365)
    elif len(parts) >= 5 and parts[1] == "range":
        date_from = datetime.strptime(parts[2], "%Y%m%d")
        date_to = datetime.strptime(parts[3], "%Y%m%d")
        category = ":".join(parts[4:])
    elif len(parts) >= 5 and parts[1] == "month":
        year = int(parts[2])
        month = int(parts[3])
        date_from, date_to = month_bounds(datetime(year, month, 1))
        category = ":".join(parts[4:])
    elif len(parts) >= 3 and parts[1] == "all":
        category = ":".join(parts[2:])

    if not category:
        await callback.answer()
        return

    try:
        log_db_read(
            "category_details",
            callback.from_user.id,
            date_from=date_from,
            date_to=date_to,
            category=category,
        )
        await callback.message.answer(
            build_category_details(callback.from_user.id, category, DB_PATH, date_from=date_from, date_to=date_to),
            reply_markup=get_main_keyboard(),
            disable_notification=True,
        )
    except Exception as e:
        print(f"[CATEGORY DETAILS ERROR] user={callback.from_user.id}: {e}")
        await callback.message.answer("Деталі категорії тимчасово недоступні 😔", disable_notification=True)
    await callback.answer()


@router.message(F.text == OTHER_BUTTON)
async def other_button_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("⚙️ Налаштування", reply_markup=get_other_keyboard(), disable_notification=True)


@router.callback_query(F.data.in_({"quick_repeat", "quick_more", "quick_home"}))
async def quick_add_action_handler(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    user_id = callback.from_user.id

    if callback.data == "quick_home":
        await state.clear()
        await callback.message.answer("Головне меню", reply_markup=get_main_keyboard(), disable_notification=True)
        await callback.answer()
        return

    if callback.data == "quick_more":
        await state.set_state(ExpenseStates.choosing_category)
        await callback.message.answer("Оберіть категорію:", reply_markup=get_categories_keyboard(), disable_notification=True)
        await callback.answer()
        return

    data = QUICK_REPEAT_DATA.get(user_id)
    if not data:
        await callback.message.answer("Немає витрати для повтору", reply_markup=get_main_keyboard(), disable_notification=True)
        await callback.answer()
        return

    name = str(data["name"])
    display = str(data["display"])
    amount = int(data["amount"])
    category = data.get("category")
    expense_id = save_expense(name, amount, user_id, category if isinstance(category, str) else None)
    await callback.message.answer("Оберіть тип витрати:", reply_markup=expense_type_keyboard(expense_id))
    await callback.answer()


@router.message(F.text == BACK_BUTTON)
async def back_button_handler(message: Message, state: FSMContext) -> None:
    if message.from_user:
        EDITING_EXPENSES.pop(message.from_user.id, None)

    current_state = await state.get_state()
    if current_state in {ExpenseStates.choosing_subcategory.state, ExpenseStates.subcategory_menu.state}:
        await state.set_state(ExpenseStates.choosing_category)
        await message.answer("Оберіть категорію:", reply_markup=get_categories_keyboard(), disable_notification=True)
        return

    if current_state in {ExpenseStates.choosing_category.state, ExpenseStates.category_menu.state}:
        await state.set_state(ExpenseStates.add_menu)
        await message.answer("Як додати витрату?", reply_markup=get_add_keyboard(), disable_notification=True)
        return

    await state.clear()
    await message.answer("Головне меню", reply_markup=get_main_keyboard(), disable_notification=True)


@router.message(F.text == EDIT_BUTTON)
async def edit_button_handler(message: Message) -> None:
    await send_edit_expense_menu(message)


@router.message(F.text == DELETE_BUTTON)
async def delete_button_handler(message: Message) -> None:
    await message.answer("Оберіть період для видалення:", reply_markup=delete_period_keyboard(), disable_notification=True)


@router.message(F.text == MY_ACCESS_BUTTON)
async def my_access_button_handler(message: Message) -> None:
    try:
        if message.from_user is None:
            return
        text, keyboard = build_my_access_text(message.from_user.id)
        await message.answer(text, reply_markup=keyboard or get_other_keyboard(), disable_notification=True)
    except Exception as e:
        print(f"[ERROR] my access: {e}")
        await message.answer("не вдалося показати доступ", reply_markup=get_other_keyboard(), disable_notification=True)


@router.message(F.text == HOW_IT_WORKS_BUTTON)
async def how_it_works_button_handler(message: Message) -> None:
    await message.answer(
        HOW_IT_WORKS_TEXT,
        reply_markup=get_other_keyboard(),
    )


@router.callback_query(F.data.startswith("expense_type:"))
async def expense_type_handler(callback: CallbackQuery, state: FSMContext) -> None:
    current_state = await state.get_state()
    print(
        f"[CALLBACK] handler=expense_type user_id={callback.from_user.id if callback.from_user else None} "
        f"data={callback.data} current_state={current_state}"
    )
    if callback.data is None:
        await callback.answer()
        return

    _, expense_id_text, expense_type = callback.data.split(":", maxsplit=2)
    expense_id = int(expense_id_text)
    user_id = callback.from_user.id if callback.from_user else None
    update_expense_type(expense_id, expense_type, user_id)
    expense = get_expense(expense_id, user_id)

    if callback.message is not None and expense is not None:
        try:
            await callback.message.delete()
        except Exception:
            await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            format_save_confirmation(expense[0], expense[1], expense_type=expense[2]),
            reply_markup=get_main_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data.in_({"pay_info", "buy_7", "buy_30"}))
async def buy_handler(callback: CallbackQuery) -> None:
    days = 7 if callback.data == "buy_7" else 30 if callback.data == "buy_30" else 0
    if callback.message is not None:
        await callback.message.answer(payment_text(days), reply_markup=paid_keyboard(days))
    await callback.answer()


@router.callback_query(F.data.in_({"paid", "paid_7", "paid_30"}))
async def paid_handler(callback: CallbackQuery, bot: Bot) -> None:
    if callback.from_user is None:
        await callback.answer()
        return

    print(f"[PAYMENT] user {callback.from_user.id} clicked 'paid'")
    days = 7 if callback.data == "paid_7" else 30 if callback.data == "paid_30" else 0
    username = callback.from_user.username
    username_text = f"@{username}" if username else "без username"
    save_payment_pending(callback.from_user.id, username_text, days)

    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "дякую 🙌\n\n"
            "перевірю оплату і відкрию доступ протягом 1–5 хвилин."
        )

    try:
        await send_payment_request_to_admin(bot, callback.from_user.id, username, days)
    except Exception as error:
        print(f"ERROR: failed to send payment request to admin: {error}")

    await callback.answer()


@router.message(F.text.func(lambda text: text.strip().lower() == "я оплатив"))
async def paid_text_handler(message: Message, bot: Bot) -> None:
    if message.from_user is None:
        return

    print(f"[PAYMENT] user {message.from_user.id} clicked 'paid'")
    username = message.from_user.username
    username_text = f"@{username}" if username else "без username"
    save_payment_pending(message.from_user.id, username_text, 0)
    await message.answer(
        "дякую 🙌\n\n"
        "перевірю оплату і відкрию доступ протягом 1–5 хвилин."
    )

    try:
        await send_payment_request_to_admin(bot, message.from_user.id, username, 0)
    except Exception as error:
        print(f"ERROR: failed to send payment request to admin: {error}")


@router.callback_query(F.data.startswith(("confirm_7_", "confirm_30_", "reject_")))
async def admin_payment_action_handler(callback: CallbackQuery, bot: Bot) -> None:
    if callback.data is None or callback.from_user is None:
        await callback.answer()
        return
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return

    if callback.data.startswith("confirm_7_"):
        user_id = int(callback.data.removeprefix("confirm_7_"))
        days = 7
        expected_amount = 290
    elif callback.data.startswith("confirm_30_"):
        user_id = int(callback.data.removeprefix("confirm_30_"))
        days = 30
        expected_amount = 390
    else:
        user_id = int(callback.data.removeprefix("reject_"))
        pending = get_pending_payment(user_id)
        reject_payment(user_id)
        await bot.send_message(
            user_id,
            "не знайшов оплату 😔\nперевір ще раз або напиши мені",
            reply_markup=payment_keyboard(),
        )
        if callback.message is not None:
            await callback.message.edit_reply_markup(reply_markup=None)
            username = pending["username"] if pending else f"user_id {user_id}"
            await callback.message.answer(f"❌ запит відхилено\nuser: {username}")
        await callback.answer()
        return

    pending = get_pending_payment(user_id)
    warning = ""
    username = f"user_id {user_id}"
    if pending is not None:
        username = pending["username"] or username
        if int(pending["amount"]) not in {0, expected_amount}:
            warning = "⚠️ сума не відповідає тарифу\n"

    access_until = approve_payment(user_id, days)
    await bot.send_message(
        user_id,
        "доступ активовано ✅\n\n"
        f"період: {days} днів\n"
        f"до: {format_date_ua(datetime.fromisoformat(access_until))}\n\n"
        "напиши першу витрату:\n"
        "кава 80",
        reply_markup=get_main_keyboard(),
    )
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f"{warning}✅ доступ видано\nuser: {username}\nперіод: {days} днів"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("stats:"))
async def stats_period_handler(callback: CallbackQuery, state: FSMContext) -> None:
    current_state = await state.get_state()
    print(
        f"[CALLBACK] handler=stats_period user_id={callback.from_user.id if callback.from_user else None} "
        f"data={callback.data} current_state={current_state}"
    )
    if callback.data is None:
        await callback.answer()
        return

    await state.clear()
    _, period = callback.data.split(":", maxsplit=1)
    user_id = callback.from_user.id if callback.from_user else None
    text = build_stats_text(period, user_id)

    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        if text is None:
            await callback.message.answer("📭 Немає витрат", reply_markup=get_main_keyboard(), disable_notification=True)
        else:
            top_categories = get_top_categories_for_period(period, user_id) if user_id is not None else []
            reply_markup = get_main_keyboard()
            if period not in {PERIOD_DAY, PERIOD_WEEK}:
                reply_markup = category_details_keyboard(top_categories, f"period:{period}") or get_main_keyboard()
            await callback.message.answer(
                text,
                reply_markup=reply_markup,
                disable_notification=True,
            )
    await callback.answer()


@router.callback_query(F.data.startswith("list:"))
async def list_period_handler(callback: CallbackQuery) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return

    _, period = callback.data.split(":", maxsplit=1)
    user_id = callback.from_user.id if callback.from_user else None
    if user_id is None:
        await callback.answer()
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await send_expenses_list(callback.message, period, user_id)
    await callback.answer()


@router.callback_query(F.data.startswith("edit_period:"))
async def edit_period_handler(callback: CallbackQuery) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return

    _, period = callback.data.split(":", maxsplit=1)
    user_id = callback.from_user.id if callback.from_user else None
    if user_id is None:
        await callback.answer()
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await send_edit_expenses_by_period(callback.message, period, user_id)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_period:"))
async def delete_period_handler(callback: CallbackQuery) -> None:
    if callback.data is None:
        await callback.answer()
        return

    _, period = callback.data.split(":", maxsplit=1)
    text = f"⚠️ Ти впевнений що хочеш видалити витрати за {period_label(period)}?"

    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(text, reply_markup=delete_confirm_keyboard(period), disable_notification=True)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_delete_handler(callback: CallbackQuery) -> None:
    if callback.data is None:
        await callback.answer()
        return

    _, period = callback.data.split(":", maxsplit=1)
    user_id = callback.from_user.id if callback.from_user else None
    if user_id is None:
        await callback.answer()
        return
    delete_expenses_by_period(period, user_id)

    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        if count_expenses(user_id) == 0:
            await callback.message.answer("🗑 Усі витрати видалені", reply_markup=get_main_keyboard(), disable_notification=True)
        else:
            await callback.message.answer("🗑 Дані видалено ✅", reply_markup=get_other_keyboard(), disable_notification=True)
    await callback.answer()


@router.callback_query(F.data == "cancel_delete")
async def cancel_delete_handler(callback: CallbackQuery) -> None:
    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Скасовано", reply_markup=get_other_keyboard(), disable_notification=True)
    await callback.answer()


@router.callback_query(F.data.startswith("edit_expense:"))
async def edit_expense_handler(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.from_user is None:
        await callback.answer()
        return

    _, expense_id = callback.data.split(":", maxsplit=1)
    expense_id_int = int(expense_id)
    if get_expense(expense_id_int, callback.from_user.id) is None:
        await callback.answer()
        return

    await state.update_data(editing_expense_id=expense_id_int)
    await state.set_state(ExpenseStates.waiting_for_new_data)

    if callback.message is not None:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Введи нову назву і суму (наприклад: кава 100)",
            reply_markup=get_main_keyboard(),
            disable_notification=True,
        )
    await callback.answer()


@router.message(ExpenseStates.waiting_for_new_data)
async def edit_new_data_handler(message: Message, state: FSMContext) -> None:
    expense = parse_expense(message.text)
    if expense is None:
        await message.answer(
            "Введи нову назву і суму (наприклад: кава 100)",
            reply_markup=get_main_keyboard(),
            disable_notification=True,
        )
        return

    name, amount = expense
    data = await state.get_data()
    expense_id = data.get("editing_expense_id")
    if not isinstance(expense_id, int):
        await state.clear()
        await message.answer(
            "Не вдалося знайти витрату для редагування",
            reply_markup=get_main_keyboard(),
            disable_notification=True,
        )
        return

    if message.from_user is None:
        await state.clear()
        return
    user_id = message.from_user.id
    update_expense(expense_id, name, amount, user_id)
    await state.update_data(editing_name=name, editing_amount=amount)
    await state.set_state(ExpenseStates.waiting_for_type)
    await message.answer("Обери тип витрати", reply_markup=edit_type_keyboard(expense_id))


@router.callback_query(ExpenseStates.waiting_for_type, F.data.startswith("edit_type:"))
async def edit_type_handler(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        await callback.answer()
        return

    _, expense_id_text, expense_type = callback.data.split(":", maxsplit=2)
    expense_id = int(expense_id_text)

    if callback.from_user is None:
        await state.clear()
        await callback.answer()
        return

    user_id = callback.from_user.id
    if expense_type != "keep":
        update_expense_type(expense_id, expense_type, user_id)

    expense = get_expense(expense_id, user_id)
    await state.clear()

    if callback.message is not None and expense is not None:
        name, amount, saved_type = expense
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "\n".join(
                [
                    "✅ Витрату оновлено",
                    f"💸 {name} — {format_amount(amount)} грн",
                    f"📌 Тип: {format_type(saved_type)}",
                ]
            ),
            reply_markup=get_main_keyboard(),
        )

    await callback.answer()


@router.message(F.text.in_(STATS_PERIOD_BUTTONS))
async def loose_stats_period_button_handler(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    await state.set_state(ExpenseStates.stats_menu)
    if message.text == STATS_TODAY_BUTTON:
        await send_reply_stats(message, PERIOD_DAY)
    elif message.text == STATS_YESTERDAY_BUTTON:
        await send_reply_stats(message, PERIOD_YESTERDAY)
    elif message.text == STATS_WEEK_BUTTON:
        await send_period_choice_menu(message, state, "stats", "week")
    elif message.text == STATS_MONTH_BUTTON:
        await send_period_choice_menu(message, state, "stats", "month")
    elif message.text == STATS_YEAR_BUTTON:
        await send_reply_stats(message, PERIOD_YEAR)
    elif message.text == STATS_ALL_BUTTON:
        await send_reply_stats(message, PERIOD_ALL)
    elif message.text == CUSTOM_PERIOD_BUTTON:
        await send_period_year_menu(message, "stats", message.from_user.id)
    elif message.text == STATS_RECOMMENDATIONS_BUTTON:
        await message.answer(
            build_recommendations_text(message.from_user.id),
            reply_markup=get_stats_keyboard(),
            disable_notification=True,
        )


@router.message(F.text & ~F.text.startswith("/"))
async def text_handler(message: Message, state: FSMContext) -> None:
    if looks_like_period_choice_text(message.text):
        await state.clear()
        await message.answer("Обери період у розділі 📊 Статистика.", reply_markup=get_stats_keyboard(), disable_notification=True)
        return

    parsed = parse_smart_expense_input(message.text)
    if parsed is None:
        await message.answer("Напиши назву витрати або суму", reply_markup=get_main_keyboard())
        return

    name, amount = parsed
    if name and amount:
        user_id = message.from_user.id if message.from_user else None
        expense_id = save_expense(name, amount, user_id)
        await message.answer("Оберіть тип витрати:", reply_markup=expense_type_keyboard(expense_id))
        return

    if name and amount is None:
        await state.set_state(ExpenseStates.waiting_expense_amount)
        await state.update_data(expense_name=name)
        await message.answer("💸 Введи суму", reply_markup=get_expense_input_keyboard())
        return

    await message.answer("Спочатку напиши назву витрати", reply_markup=get_main_keyboard())


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Додай TELEGRAM_BOT_TOKEN у .env")

    print("[START] bot started")
    print(f"[ADMIN] id = {ADMIN_USER_ID}")
    print(f"[DB] path = {DB_PATH}")
    if not ADMIN_USER_ID:
        print("[ERROR] ADMIN_USER_ID is not set")

    create_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.message.middleware(UserActivityMiddleware())
    dp.callback_query.middleware(UserActivityMiddleware())
    dp.include_router(router)

    asyncio.create_task(scheduler(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
