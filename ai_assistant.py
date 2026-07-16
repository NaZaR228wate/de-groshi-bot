import asyncio
import json
import os
import re
from typing import Literal

from openai import OpenAI

from ai_cache import get_cached_response, set_cached_response
from analytics import build_ai_analytics, build_local_analysis
from prompts import AI_ASSISTANT_SYSTEM_PROMPT


AI_MODEL = "gpt-4.1-mini"
AI_TIMEOUT_SECONDS = 25
AI_RETRIES = 2
MAX_MEMORY_MESSAGES = 10
MAX_TOKENS = 220

Intent = Literal["greeting", "casual", "finance_question", "recommendation", "period_analysis"]

_MEMORY: dict[int, list[dict[str, str]]] = {}

CASUAL_RESPONSES = {
    "привіт": "Привіт 👋",
    "вітаю": "Привіт 👋",
    "добрий день": "Добрий день 👋",
    "доброго дня": "Доброго дня 👋",
    "дякую": "Завжди радий допомогти 🙂",
    "спасибі": "Завжди радий допомогти 🙂",
    "ок": "👌",
    "окей": "👌",
    "ясно": "👌",
    "зрозумів": "👌",
    "зрозуміло": "👌",
    "супер": "Супер 🙂",
    "👍": "👍",
    "👌": "👌",
}

AI_ACTION_PROMPTS = {
    "where": "куди йдуть гроші",
    "emotional": "проаналізуй емоційні покупки",
    "biggest": "покажи найбільші витрати",
    "week": "проаналізуй останні 7 днів",
    "trends": "покажи тренди витрат",
}


def detect_intent(text: str | None) -> Intent:
    normalized = (text or "").strip().lower()
    compact = re.sub(r"\s+", " ", normalized)

    if compact in {"привіт", "вітаю", "добрий день", "доброго дня", "hello", "hi"}:
        return "greeting"

    if compact in CASUAL_RESPONSES or compact in {"як справи", "як ти", "що робиш"}:
        return "casual"

    if any(word in compact for word in ("рекоменд", "порад", "оптиміз", "зеконом", "економ")):
        return "recommendation"

    if any(
        word in compact
        for word in (
            "сьогодні",
            "вчора",
            "тиждень",
            "місяць",
            "останні 7",
            "з ",
            "по ",
        )
    ) and any(word in compact for word in ("витрат", "грош", "аналіз", "скільки", "статист")):
        return "period_analysis"

    if any(
        word in compact
        for word in (
            "куди",
            "гроші",
            "витрач",
            "витрат",
            "скільки",
            "аналіз",
            "статист",
            "категор",
            "емоцій",
            "планов",
            "найбіль",
            "топ",
            "повтор",
            "динамік",
            "тренд",
        )
    ):
        return "finance_question"

    return "casual"


def get_local_response(text: str | None, intent: Intent) -> str | None:
    normalized = (text or "").strip().lower()
    compact = re.sub(r"\s+", " ", normalized)

    if compact in CASUAL_RESPONSES:
        return CASUAL_RESPONSES[compact]

    if intent == "greeting":
        return "Привіт 👋"

    if compact in {"як справи", "як ти"}:
        return "Все добре. Можу подивитись твої витрати, якщо хочеш 🙂"

    if intent == "casual":
        return "👌"

    return None


def _remember(user_id: int, role: str, content: str) -> None:
    messages = _MEMORY.setdefault(user_id, [])
    messages.append({"role": role, "content": content[:900]})
    del messages[:-MAX_MEMORY_MESSAGES]


def _cache_key(user_id: int, question: str, action: str | None) -> str:
    normalized = re.sub(r"\s+", " ", question.strip().lower())
    return f"{user_id}:{action or 'chat'}:{normalized}"


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


def _ask_openai(
    api_key: str,
    question: str,
    analytics: dict,
    memory: list[dict[str, str]],
) -> str:
    client = OpenAI(api_key=api_key, timeout=AI_TIMEOUT_SECONDS)
    prompt_analytics = _remove_percent_fields(analytics)
    response = client.chat.completions.create(
        model=AI_MODEL,
        temperature=0.3,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": AI_ASSISTANT_SYSTEM_PROMPT},
            *memory,
            {
                "role": "user",
                "content": (
                    "Питання користувача:\n"
                    f"{question}\n\n"
                    "Готова аналітика з Python у JSON:\n"
                    f"{json.dumps(prompt_analytics, ensure_ascii=False)}"
                ),
            },
        ],
    )
    message = response.choices[0].message.content
    return message.strip() if message else build_local_analysis(analytics)


async def ask_ai_assistant(
    user_id: int,
    question: str,
    db_path: str = "expenses.db",
    action: str | None = None,
) -> str:
    if action:
        question = AI_ACTION_PROMPTS.get(action, question)

    intent = detect_intent(question)
    local_response = get_local_response(question, intent)
    if local_response is not None and intent in {"greeting", "casual"} and action is None:
        _remember(user_id, "user", question)
        _remember(user_id, "assistant", local_response)
        return local_response

    analytics = await asyncio.to_thread(build_ai_analytics, user_id, question, db_path, action)
    fallback = build_local_analysis(analytics)

    cache_key = _cache_key(user_id, question, action)
    cached = get_cached_response(cache_key)
    if cached is not None:
        return cached

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        set_cached_response(cache_key, fallback)
        return fallback

    memory = _MEMORY.get(user_id, [])[-MAX_MEMORY_MESSAGES:]
    last_error: Exception | None = None

    for attempt in range(AI_RETRIES):
        try:
            answer = await asyncio.wait_for(
                asyncio.to_thread(_ask_openai, api_key, question, analytics, memory),
                timeout=AI_TIMEOUT_SECONDS + 5,
            )
            _remember(user_id, "user", question)
            _remember(user_id, "assistant", answer)
            set_cached_response(cache_key, answer)
            return answer
        except Exception as error:
            last_error = error
            if attempt + 1 < AI_RETRIES:
                await asyncio.sleep(1)

    print(f"[AI FALLBACK] {last_error}")
    set_cached_response(cache_key, fallback)
    return fallback
