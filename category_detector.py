import json
import os
import re
from difflib import SequenceMatcher
from functools import lru_cache

from openai import OpenAI


NORMALIZED_CATEGORIES = [
    "їжа",
    "транспорт",
    "покупки",
    "дім",
    "здоров’я",
    "діти",
    "розваги",
    "інше",
]

CATEGORY_EMOJI = {
    "їжа": "🍔",
    "транспорт": "🚕",
    "покупки": "🛍",
    "дім": "🏠",
    "здоров’я": "💊",
    "діти": "👶",
    "розваги": "🎮",
    "інше": "📦",
}

CATEGORY_SUBCATEGORIES = {
    "транспорт": ["бензин", "таксі", "сто", "транспорт"],
    "їжа": ["кава", "ресторан", "продукти", "фастфуд", "суші", "напої"],
    "здоров’я": ["ліки", "лікар", "стоматолог", "аналізи", "аптека"],
    "покупки": ["одяг", "техніка", "подарунки", "побутове", "магазин"],
    "дім": ["комуналка", "оренда", "меблі", "ремонт", "дім"],
    "діти": ["іграшки", "солодке", "ігри", "кишенькові", "школа", "одяг дітям"],
    "розваги": ["кіно", "ігри", "відпочинок", "музика", "спорт"],
    "інше": ["інше"],
}

SUBCATEGORY_TO_CATEGORY = {
    subcategory: category
    for category, subcategories in CATEGORY_SUBCATEGORIES.items()
    for subcategory in subcategories
}

CANONICAL_SUBCATEGORY_MAP = {
    "паливо": "бензин",
    "бенз": "бензин",
    "бензин": "бензин",
    "заправка": "бензин",
    "окко": "бензин",
    "wog": "бензин",
    "дизель": "бензин",
    "газ авто": "бензин",
    "таксі": "таксі",
    "уклон": "таксі",
    "uber": "таксі",
    "bolt": "таксі",
    "сто": "сто",
    "шиномонтаж": "сто",
    "ремонт авто": "сто",
    "метро": "транспорт",
    "автобус": "транспорт",
    "маршрутка": "транспорт",
    "електричка": "транспорт",
    "трамвай": "транспорт",
    "тролейбус": "транспорт",
    "поїзд": "транспорт",
    "поїздка": "транспорт",
    "проїзд": "транспорт",
    "кава": "кава",
    "капучино": "кава",
    "лате": "кава",
    "піца": "фастфуд",
    "бургер": "фастфуд",
    "мак": "фастфуд",
    "макдональдс": "фастфуд",
    "суші": "суші",
    "продукти": "продукти",
    "атб": "продукти",
    "сільпо": "продукти",
    "сильпо": "продукти",
    "ресторан": "ресторан",
    "кафе": "ресторан",
    "напої": "напої",
    "ліки": "ліки",
    "таблетки": "ліки",
    "вітаміни": "ліки",
    "лікар": "лікар",
    "лікарю": "лікар",
    "лікаря": "лікар",
    "клініка": "лікар",
    "аптека": "аптека",
    "стоматолог": "стоматолог",
    "аналіз": "аналізи",
    "аналізи": "аналізи",
    "одяг": "одяг",
    "плаття": "одяг",
    "взуття": "одяг",
    "техніка": "техніка",
    "подарунок": "подарунки",
    "подарунки": "подарунки",
    "побутове": "побутове",
    "магазин": "магазин",
}

CATEGORY_KEYWORDS = {
    "здоров’я": [
        "лікар",
        "лікарю",
        "лікаря",
        "лікарі",
        "ліки",
        "таблетки",
        "аптека",
        "стоматолог",
        "аналізи",
        "аналіз",
        "клініка",
        "мед",
        "вітаміни",
        "лікарня",
        "окуліст",
        "терапевт",
    ],
    "їжа": [
        "кава",
        "піца",
        "ресторан",
        "продукти",
        "суші",
        "мак",
        "макдональдс",
        "бургер",
        "обід",
        "вечеря",
        "сніданок",
        "фастфуд",
        "атб",
        "сільпо",
        "сильпо",
        "ашан",
        "новус",
        "напої",
        "перекус",
        "солодке",
    ],
    "транспорт": [
        "бензин",
        "паливо",
        "таксі",
        "уклон",
        "uber",
        "bolt",
        "метро",
        "автобус",
        "маршрутка",
        "електричка",
        "трамвай",
        "тролейбус",
        "поїзд",
        "поїздка",
        "транспорт",
        "проїзд",
        "парковка",
        "сто",
        "шиномонтаж",
        "дизель",
        "авто",
    ],
    "діти": [
        "дитячий",
        "дитина",
        "діти",
        "школа",
        "садок",
        "іграшка",
        "іграшки",
        "памперси",
        "підгузки",
        "кишенькові",
        "дитячий одяг",
        "одяг дітям",
        "шкільне",
    ],
    "дім": [
        "комуналка",
        "оренда",
        "світло",
        "газ",
        "вода",
        "інтернет",
        "ремонт",
        "дім",
        "побут",
        "меблі",
        "квартира",
        "будинок",
        "прибирання",
    ],
    "покупки": [
        "одяг",
        "взуття",
        "магазин",
        "техніка",
        "косметика",
        "подарунок",
        "подарунки",
        "покупка",
        "побутове",
        "розетка",
        "епіцентр",
    ],
    "розваги": [
        "кіно",
        "гра",
        "ігри",
        "бар",
        "концерт",
        "розваги",
        "відпочинок",
        "підписка",
        "netflix",
        "spotify",
        "музика",
        "спорт",
    ],
}

ALLOWED_CATEGORIES = set(NORMALIZED_CATEGORIES)
APOSTROPHES = str.maketrans({"ʼ": "'", "’": "'", "`": "'", "‘": "'"})


def normalize_text(value: str) -> str:
    value = value.lower().translate(APOSTROPHES)
    value = value.replace("ё", "е")
    value = re.sub(r"[^a-zа-яіїєґ0-9'\s]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_category_name(value: str | None) -> str | None:
    if not value:
        return None
    normalized = normalize_text(value)
    normalized = normalized.replace("здоров'я", "здоров’я")
    if normalized in ALLOWED_CATEGORIES:
        return normalized
    return None


def _stem(word: str) -> str:
    word = normalize_text(word)
    for suffix in (
        "ями",
        "ами",
        "ями",
        "ого",
        "ому",
        "ою",
        "ею",
        "ів",
        "ий",
        "ій",
        "их",
        "ах",
        "ях",
        "ою",
        "а",
        "у",
        "ю",
        "я",
        "и",
        "і",
        "е",
    ):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _keyword_variants(keyword: str) -> set[str]:
    normalized = normalize_text(keyword)
    return {normalized, _stem(normalized)}


def _is_match(token: str, keyword: str) -> bool:
    token = normalize_text(token)
    keyword = normalize_text(keyword)
    if not token or not keyword:
        return False
    if keyword in token:
        return True
    if len(token) >= 4 and token in keyword:
        return True
    token_stem = _stem(token)
    keyword_stem = _stem(keyword)
    if keyword_stem and keyword_stem in token_stem:
        return True
    if keyword_stem and len(token_stem) >= 4 and token_stem in keyword_stem:
        return True
    return SequenceMatcher(None, token_stem, keyword_stem).ratio() >= 0.84


def detect_category_local(title: str) -> str | None:
    normalized = normalize_text(title)
    if not normalized:
        return None

    tokens = normalized.split()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            keyword_normalized = normalize_text(keyword)
            if " " in keyword_normalized and keyword_normalized in normalized:
                return category
            if any(_is_match(token, variant) for token in tokens for variant in _keyword_variants(keyword)):
                return category

    return None


def detect_subcategory_local(title: str) -> str | None:
    normalized = normalize_text(title)
    if not normalized:
        return None

    tokens = normalized.split()
    for keyword, subcategory in CANONICAL_SUBCATEGORY_MAP.items():
        keyword_normalized = normalize_text(keyword)
        if " " in keyword_normalized and keyword_normalized in normalized:
            return subcategory
        if any(_is_match(token, variant) for token in tokens for variant in _keyword_variants(keyword)):
            return subcategory
    return None


def normalize_subcategory_name(value: str | None) -> str | None:
    if not value:
        return None
    normalized = normalize_text(value)
    if normalized in SUBCATEGORY_TO_CATEGORY:
        return normalized
    return detect_subcategory_local(normalized)


def normalize_category(category: str | None, title: str | None = None) -> str:
    direct = normalize_category_name(category)
    if direct:
        return direct
    detected_from_category = detect_category_local(category or "")
    if detected_from_category:
        return detected_from_category
    detected_from_title = detect_category_local(title or "")
    if detected_from_title:
        return detected_from_title
    return "інше"


def normalize_financial_category(
    raw_title: str,
    category: str | None = None,
    subcategory: str | None = None,
) -> dict[str, str]:
    title = raw_title.strip()
    canonical_subcategory = normalize_subcategory_name(subcategory) or detect_subcategory_local(title)
    canonical_category = normalize_category_name(category)

    if canonical_subcategory:
        canonical_category = SUBCATEGORY_TO_CATEGORY.get(canonical_subcategory, canonical_category)
    if not canonical_category:
        canonical_category = detect_category_local(title)
    if not canonical_category:
        gpt_result = detect_category_gpt(title)
        if gpt_result:
            canonical_category = gpt_result.get("category")
            canonical_subcategory = canonical_subcategory or gpt_result.get("subcategory")

    canonical_category = normalize_category_name(canonical_category) or "інше"
    canonical_subcategory = normalize_subcategory_name(canonical_subcategory) or (
        canonical_category if canonical_category == "інше" else canonical_category
    )

    return {
        "raw_title": title,
        "subcategory": canonical_subcategory,
        "category": canonical_category,
    }


def format_category_label(category: str | None) -> str:
    normalized = normalize_category(category)
    emoji = CATEGORY_EMOJI.get(normalized, "📦")
    return f"{emoji} {normalized.capitalize()}"


def format_subcategory_label(subcategory: str | None) -> str:
    normalized = normalize_subcategory_name(subcategory) or "інше"
    return normalized.capitalize()


@lru_cache(maxsize=512)
def detect_category_gpt(title: str) -> dict[str, str] | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        client = OpenAI(api_key=api_key, timeout=8)
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0,
            max_tokens=20,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Визнач фінансову категорію витрати. "
                        "Поверни тільки JSON: {\"category\":\"...\",\"subcategory\":\"...\"}. "
                        "Не створюй нових назв. "
                        "Категорії: їжа, транспорт, покупки, дім, здоров’я, діти, розваги, інше. "
                        "Підкатегорії: бензин, таксі, сто, транспорт, кава, ресторан, продукти, "
                        "фастфуд, суші, напої, ліки, лікар, стоматолог, аналізи, аптека, "
                        "одяг, техніка, подарунки, побутове, магазин, комуналка, оренда, меблі, ремонт, дім, "
                        "іграшки, солодке, ігри, кишенькові, школа, одяг дітям, кіно, відпочинок, музика, спорт, інше."
                    ),
                },
                {"role": "user", "content": title},
            ],
        )
        content = (response.choices[0].message.content or "").strip()
        try:
            payload = json.loads(content)
            category = normalize_category_name(str(payload.get("category") or ""))
            subcategory = normalize_subcategory_name(str(payload.get("subcategory") or ""))
        except json.JSONDecodeError:
            category = normalize_category_name(content)
            subcategory = None
        if not category and subcategory:
            category = SUBCATEGORY_TO_CATEGORY.get(subcategory)
        if category not in ALLOWED_CATEGORIES:
            return None
        return {"category": category, "subcategory": subcategory or category}
    except Exception as error:
        print(f"[CATEGORY GPT ERROR] {error}")
        return None


def detect_category(title: str) -> str:
    return normalize_financial_category(title)["category"]
