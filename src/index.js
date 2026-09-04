const TELEGRAM_API = "https://api.telegram.org/bot";
const CURRENCY = "грн";

// Єдине джерело тарифів. Наступна зміна цін/строків — тільки тут.
const TARIFFS = [
  { days: 30, price: 299, label: "30 днів" },
  { days: 180, price: 599, label: "180 днів (6 міс)" },
  { days: 365, price: 1100, label: "365 днів (рік)" }
];
const TARIFF_BY_DAYS = new Map(TARIFFS.map((tariff) => [tariff.days, tariff]));

const MAIN_KEYBOARD = {
  keyboard: [
    [{ text: "➕ Додати витрату" }],
    [{ text: "📊 Статистика" }, { text: "💰 Бюджет" }],
    [{ text: "✏️ Керувати витратами" }],
    [{ text: "💳 Мій доступ" }]
  ],
  resize_keyboard: true,
  is_persistent: true,
  input_field_placeholder: "Введи витрату або обери дію…"
};
// MAIN_KEYBOARD носять лише «якірні» повідомлення, які ніколи не видаляються
// (/start, підсумок мультидодавання, «Доступ відкрито», тижневий cron-звіт):
// видалення повідомлення-носія знімає reply-клавіатуру в клієнті.
// Службові повідомлення reply-клавіатуру НЕ несуть.
const ADD_EXPENSE_SHORT_HINT = "✍️ Напиши витрату: назва і сума, наприклад: кава 80";

const CRON_DAILY = "0 7 * * *";
const CRON_WEEKLY = "0 17 * * SUN";
const CRON_MONO = "*/2 * * * *";
const WAITING_FOR_STATS_PERIOD = "waiting_for_stats_period";
const STATS_PERIOD_PROMPT = [
  "Введи період у форматі:",
  "",
  "04.07-10.07",
  "",
  "або",
  "",
  "04.07.2026-10.07.2026"
].join("\n");
const STATS_PERIOD_ERROR = [
  "Не зрозумів період.",
  "",
  "Напиши так:",
  "04.07-10.07",
  "",
  "або:",
  "04.07.2026-10.07.2026"
].join("\n");

const ADD_EXPENSE_HINT = [
  "✍️ Просто напиши витрату:",
  "продукти 300",
  "",
  "Кілька одразу — через кому або з нового рядка:",
  "кава 80, таксі 150",
  "",
  "З копійками:",
  "кава 149.50",
  "",
  "Заднім числом:",
  "вчора інтернет 200"
].join("\n");

const CATEGORY_LABELS = {
  food: "🍔 Їжа",
  transport: "🚕 Транспорт",
  shopping: "🛍 Покупки",
  home: "🏠 Дім",
  health: "💊 Здоров’я",
  kids: "👶 Діти",
  education: "📚 Навчання",
  fun: "🎮 Розваги",
  other: "📦 Інше"
};

const SUBCATEGORIES = {
  food: [
    ["coffee", "☕ Кава"],
    ["fastfood", "🍕 Фастфуд"],
    ["groceries", "🥗 Продукти"],
    ["restaurant", "🍽 Ресторан"],
    ["sushi", "🍣 Суші"],
    ["drinks", "🥤 Напої"]
  ],
  transport: [
    ["fuel", "⛽ Бензин"],
    ["service", "🔧 СТО"],
    ["transport", "🚕 Транспорт"]
  ],
  shopping: [
    ["clothes", "👕 Одяг"],
    ["tech", "📱 Техніка"],
    ["gifts", "🎁 Подарунки"],
    ["household", "🧴 Побутове"],
    ["shop", "🛒 Магазин"]
  ],
  home: [
    ["utilities", "💡 Комуналка"],
    ["rent", "🏠 Оренда"],
    ["furniture", "🪑 Меблі"],
    ["home", "🧽 Дім"],
    ["repair", "🔨 Ремонт"]
  ],
  health: [
    ["medicine", "💊 Ліки"],
    ["doctor", "🩺 Лікар"],
    ["dentist", "🦷 Стоматолог"],
    ["tests", "🏥 Аналізи"],
    ["sport", "🏋️ Спорт"]
  ],
  kids: [
    ["toys", "🧸 Іграшки"],
    ["sweets", "🍭 Солодке"],
    ["games", "🎮 Ігри"],
    ["pocket", "💸 Кишенькові"],
    ["school", "📚 Школа"],
    ["kids_clothes", "👕 Одяг дітям"]
  ],
  education: [
    ["courses", "🎓 Курси"],
    ["tutor", "👨‍🏫 Репетитор"],
    ["books", "📕 Підручники"],
    ["stationery", "✏️ Канцтовари"],
    ["driving", "🚗 Автошкола"],
    ["languages", "🗣 Мовні курси"]
  ],
  fun: [
    ["cinema", "🎬 Кіно"],
    ["games", "🎮 Ігри"],
    ["rest", "🍻 Відпочинок"],
    ["music", "🎵 Музика"],
    ["sport", "⚽ Спорт"]
  ]
};

const SUBCATEGORY_TITLES = Object.fromEntries(
  Object.entries(SUBCATEGORIES).flatMap(([category, items]) =>
    items.map(([key, label]) => [`${category}:${key}`, stripEmoji(label).toLowerCase()])
  )
);

// Єдине джерело правил категоризації. Доповнювати — тільки тут.
//   brands  — назви мереж/сервісів (найвищий пріоритет),
//   phrases — багатослівні маркери («корм для кота»),
//   ru      — русизми й суржик (та сама вага, що корені),
//   roots   — корені слів; матчаться як ПРЕФІКС токена, тому «кав» ловить
//             «кава/кави/каву»,
//   exact   — слова, що матчаться лише цілком (щоб «газ» не ловив «газету»,
//             «бар» — «барбер», а «сто» — «столик»).
// Порядок категорій — тайбрейкер при однаковій вазі збігу.
const CATEGORY_RULES = {
  health: {
    brands: ["аптека доброго дня", "подорожник", "анц", "бажаємо здоровя"],
    phrases: ["прийом лікаря", "візит до лікаря", "здача аналізів", "запис до лікаря"],
    // Русизми й суржик — люди пишуть по-різному.
    ru: ["лекарств", "аптеч", "врач", "болниц", "зубной", "стрижк"],
    // Послуги догляду — сюди ж (це догляд за собою, а не речі).
    roots: ["лік", "таблет", "аптек", "стоматолог", "аналіз", "клінік", "медиц", "медич", "зуб", "вітамін", "терапевт", "педіатр", "окуляр", "лінз", "масаж", "психолог", "щеплен", "стрижк", "манікюр", "педикюр", "барбер", "косметолог", "спа", "епіляц", "брів", "перукар"]
  },
  // Навчання стоїть ВИЩЕ за kids і містить лише однозначні освітні маркери
  // («автошкол», «мовн»), тож голе «школа» лишається в Діти.
  education: {
    phrases: ["мовна школа", "школа програмування", "курси водіння", "оплата за навчання", "підготовка до нмт", "оплата за курси"],
    ru: ["обучен", "образован", "курс", "репетитор", "университет", "учебник", "тетрад", "канцтовар"],
    roots: ["навчанн", "освіт", "курс", "репетитор", "університет", "інститут", "коледж", "автошкол", "підручник", "канцтовар", "канцеляр", "зошит", "лекці", "семінар", "тренінг", "вебінар", "студент", "іспит", "диплом", "мовн", "duolingo", "coursera", "udemy", "prometheus"]
  },
  transport: {
    brands: ["wog", "okko", "окко", "shell", "shel", "bolt", "болт", "uklon", "uklon", "уклон", "uber", "убер", "socar", "укрнафта"],
    phrases: ["квитки на потяг", "квиток на потяг", "мийка авто", "страховка авто", "техогляд авто", "проїзд у метро", "заправка авто", "ремонт авто"],
    ru: ["бензін", "заправк", "такси", "проезд", "автобус", "поезд", "билет", "парковк", "мойка", "штраф"],
    exact: ["сто"],
    roots: ["бензин", "бенз", "паливо", "заправ", "окко", "wog", "таксі", "uber", "uklon", "уклон", "bolt", "болт", "метро", "автобус", "маршрутк", "електричк", "потяг", "поїзд", "квиток", "квитк", "шиномонтаж", "автомийк", "мийк", "парковк", "паркув", "стоянк", "автоцивілк", "страховк", "транспорт", "штраф", "евакуатор", "техогляд", "автосервіс", "шини", "олив"]
  },
  kids: {
    phrases: ["оплата за садок", "плата за садок", "шкільні обіди", "форма для школи", "внески в школу", "гурток малювання"],
    ru: ["детск", "ребенк", "игрушк", "садик", "подгузник", "школьн"],
    roots: ["дит", "діт", "школ", "шкіл", "садок", "садоч", "садк", "кишеньков", "іграш", "англійськ", "гурток", "гуртк", "памперс", "підгузк", "шоколадк", "солодк"]
  },
  food: {
    brands: [
      "атб", "сільпо", "сильпо", "novus", "новус", "ашан", "auchan", "varus", "варус",
      "fozzy", "фоззі", "фора", "метро кеш", "megamarket", "мегамаркет",
      "mcdonalds", "макдональдз", "макдоналдс", "мак", "kfc", "домінос", "dominos",
      "пузата хата", "львівські круасани", "aroma kava", "арома кава", "glovo", "глово",
      "bolt food", "болт фуд", "raketa", "ракета", "wolt", "сушия", "sushiya"
    ],
    phrases: ["кава з собою", "бізнес ланч", "їжа на виніс", "обід на роботі", "продукти на тиждень"],
    ru: ["продукт", "хлеб", "молок", "мясо", "конфет", "печенье", "чипс", "мороженое", "кофе", "еда", "обед", "ужин", "завтрак"],
    exact: ["чай"],
    roots: ["кав", "піц", "продукт", "ресторан", "кафе", "їдальн", "суші", "шаурм", "бургер", "морозив", "макдон", "mcdonald", "kfc", "атб", "сільпо", "сильпо", "новус", "novus", "варус", "фора", "ашан", "їж", "обід", "вечер", "сніданок", "напій", "напо", "хліб", "молок", "мясо", "овоч", "фрукт", "торт", "випічк", "бакалі", "чіпс", "снек", "шоколад", "цукерк", "печив", "жуйк", "сухарик", "горішк", "йогурт", "сир", "яйц", "крупа", "макарон", "олія", "цукор", "сіль", "сік", "вафл", "перекус"]
  },
  shopping: {
    brands: [
      "rozetka", "розетка", "епіцентр", "epicentr", "comfy", "комфі", "foxtrot", "фокстрот",
      "aliexpress", "алиэкспресс", "нова пошта", "новапошта", "укрпошта", "ukrposhta",
      "jysk", "юск", "ikea", "sinsay", "reserved", "zara", "hm", "temu", "prom ua"
    ],
    phrases: ["корм для кота", "корм для собаки", "зубна паста", "туалетний папір", "засіб для прання"],
    ru: ["одежд", "обув", "магазин", "подарок", "косметик", "духи", "шампун", "техник", "покупк", "сигарет"],
    roots: ["одяг", "одеж", "плаття", "сукн", "взутт", "кросівк", "куртк", "джинс", "футболк", "технік", "телевізор", "ноутбук", "навушник", "подарун", "квіт", "косметик", "парфум", "шампун", "магазин", "побутов", "хімі", "rozetka", "розетк", "aliexpress", "покупк", "сигарет", "цигарк", "зубна", "паста", "гель", "мило", "дезодорант", "бритв", "корм", "наповнювач", "іграшка коту"]
  },
  fun: {
    // Стрімінг і розваги — те, від чого можна відмовитись завтра.
    brands: [
      "netflix", "нетфлікс", "spotify", "спотіфай", "youtube premium", "ютуб преміум",
      "megogo", "мегого", "steam", "стім", "playstation", "плейстейшн", "psn",
      "apple music", "apple tv", "hbo", "hbo max", "disney", "disney plus",
      "multiplex", "мультиплекс", "планета кіно", "planeta kino", "xbox", "twitch"
    ],
    phrases: ["квитки в кіно", "квиток у кіно", "похід у кіно", "абонемент у спортзал"],
    ru: ["кино", "театр", "концерт", "игр", "отдых", "музык", "спортзал", "бассейн", "пив", "вино", "подписк"],
    exact: ["бар"],
    roots: ["кіно", "театр", "концерт", "ігр", "гейм", "playstation", "steam", "відпочинок", "музик", "клуб", "боулінг", "квест", "хобі", "книг", "спортзал", "абонемент", "басейн", "розваг", "пив", "вино"]
  },
  home: {
    // Дім — без чого квартира не функціонує (зв'язок і комуналка сюди).
    brands: ["київстар", "kyivstar", "vodafone", "водафон", "lifecell", "лайфселл", "starlink", "старлінк", "ukrtelecom", "укртелеком", "yasno", "ясно", "нафтогаз"],
    phrases: ["пральний порошок", "мішки для сміття", "домашній інтернет", "комунальні послуги", "плата за світло", "оренда квартири"],
    ru: ["комуналк", "аренд", "квартир", "свет", "вода", "отоплен", "мусор", "мебел", "ремонт", "порошок", "лампочк", "батарейк", "салфетк", "пакет"],
    exact: ["газ", "дім", "вода"],
    roots: ["комунал", "оренд", "квартплат", "квартир", "будинок", "інтернет", "internet", "wifi", "звязок", "мобільн", "телефон", "поповненн", "київстар", "kyivstar", "lifecell", "лайф", "vodafone", "водафон", "світло", "електро", "опаленн", "сміття", "домофон", "охорон", "меблі", "ремонт", "підписк", "батарейк", "лампочк", "лампа", "порошок", "серветк", "пакет", "мішки для сміття", "губк", "швабр", "відро", "посуд", "рушник", "постіл", "штор", "цвях", "інструмент"]
  },
  // Банківські операції — свідомо «Інше», щоб не перекошувати інші категорії.
  other: {
    brands: ["monobank", "монобанк", "приват", "privat", "privatbank", "sense bank", "sense superapp"],
    phrases: ["обслуговування картки", "комісія за переказ", "конвертація валюти"],
    roots: ["комісі", "переказ", "конвертаці"]
  }
};

// Вага збігу: точний бренд > фраза > корінь слова > нечіткий (одруківка).
const MATCH_RANK = { brand: 3, phrase: 2, root: 1, fuzzy: 0 };

// Індекси будуються один раз при старті ізоляту, а не на кожну витрату.
const PHRASE_ENTRIES = [];            // багатослівні маркери
const ROOT_INDEX = new Map();         // корінь -> { category, rank }
const ROOTS_BY_LENGTH = new Map();    // довжина -> корені (для fuzzy)

function normalizeForMatch(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/['’`ʼ]/g, "")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function addCategoryEntry(text, category, kind, exactOnly = false) {
  const value = normalizeForMatch(text);
  if (!value) return;
  if (value.includes(" ")) {
    PHRASE_ENTRIES.push({ text: value, category, rank: MATCH_RANK[kind] });
    return;
  }
  if (!ROOT_INDEX.has(value)) ROOT_INDEX.set(value, { category, rank: MATCH_RANK[kind], exactOnly });
  if (value.length >= 5 && !exactOnly) {
    const bucket = ROOTS_BY_LENGTH.get(value.length) || [];
    bucket.push(value);
    ROOTS_BY_LENGTH.set(value.length, bucket);
  }
}

for (const [category, rules] of Object.entries(CATEGORY_RULES)) {
  for (const brand of rules.brands || []) addCategoryEntry(brand, category, "brand");
  for (const phrase of rules.phrases || []) addCategoryEntry(phrase, category, "phrase");
  for (const word of rules.exact || []) addCategoryEntry(word, category, "root", true);
  for (const root of rules.roots || []) addCategoryEntry(root, category, "root");
  for (const root of rules.ru || []) addCategoryEntry(root, category, "root");
}
// Довші фрази перевіряємо першими — «bolt food» має виграти в «bolt».
PHRASE_ENTRIES.sort((a, b) => b.text.length - a.text.length);

const MONTHS = [
  "січень", "лютий", "березень", "квітень", "травень", "червень",
  "липень", "серпень", "вересень", "жовтень", "листопад", "грудень"
];

const MONTHS_GENITIVE = [
  "січня", "лютого", "березня", "квітня", "травня", "червня",
  "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"
];

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true });
    }
    // monobank-webhook: тіло НЕ авторитетне (немає підпису) — лише тригер. Відповідаємо
    // 200 одразу (mono має 5с), а звірку робимо асинхронно проти виписки з mono API.
    if (env.MONO_WEBHOOK_SECRET && url.pathname === `/mono/${env.MONO_WEBHOOK_SECRET}`) {
      if (request.method === "GET") {
        // monobank шле GET-перевірку при реєстрації webhook — має отримати 200.
        return json({ ok: true });
      }
      if (request.method === "POST") {
        let body = null;
        try {
          body = await request.json();
        } catch (error) {
          console.log("[MONO_ERROR]", { action: "parse_body", error: String(error) });
          return json({ ok: true });
        }
        ctx.waitUntil(
          handleMonoWebhook(env, body).catch((error) =>
            console.log("[MONO_ERROR]", { action: "handle", error: String(error) })
          )
        );
        return json({ ok: true });
      }
      return json({ ok: true });
    }
    if (request.method !== "POST" || url.pathname !== "/webhook") {
      return new Response("Not found", { status: 404 });
    }
    // Fail-closed: без налаштованого секрета webhook не приймає нічого,
    // інакше будь-хто може підробити update із from.id адміна.
    if (!env.WEBHOOK_SECRET) {
      console.log("[WEBHOOK] WEBHOOK_SECRET не заданий — запит відхилено");
      return new Response("Forbidden", { status: 403 });
    }
    const token = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
    if (token !== env.WEBHOOK_SECRET) {
      return new Response("Forbidden", { status: 403 });
    }

    // Завжди відповідаємо 200: на не-2xx Telegram повторює той самий update,
    // і частково оброблене повідомлення вставляється вдруге.
    let update;
    try {
      update = await request.json();
    } catch (error) {
      console.log("[WEBHOOK_ERROR]", { action: "parse_body", error: String(error) });
      return json({ ok: true });
    }
    try {
      if (update?.update_id && !(await claimUpdate(env.DB, update.update_id))) {
        console.log("[WEBHOOK]", { skip: "duplicate", update_id: update.update_id });
        return json({ ok: true });
      }
      await handleUpdate(update, env);
    } catch (error) {
      console.log("[WEBHOOK_ERROR]", { update_id: update?.update_id, error: String(error) });
    }
    return json({ ok: true });
  },

  async scheduled(controller, env) {
    console.log("[CRON]", { cron: controller.cron });
    // Страхувальна сітка: вебхук міг не дійти або впертись у throttle — добираємо виписку.
    if (controller.cron === CRON_MONO) {
      await pollJarAndGrant(env);
      return;
    }
    if (controller.cron === CRON_WEEKLY) {
      await sendWeeklyReports(env);
      return;
    }
    await sendAccessReminders(env);
    await cleanupProcessedUpdates(env.DB);
    await cleanupPendingExpenses(env.DB);
    await cleanupMonoProcessed(env.DB);
    if (kyivNow().date.slice(8, 10) === "01") {
      await sendMonthlyReports(env);
    }
  }
};

// true — update ще не оброблявся і його щойно "захоплено"; false — дубль від retry.
async function claimUpdate(db, updateId) {
  try {
    const result = await db.prepare(
      "INSERT OR IGNORE INTO processed_updates (update_id, processed_at) VALUES (?, ?)"
    ).bind(updateId, kyivNow().datetime).run();
    return Number(result.meta?.changes || 0) > 0;
  } catch (error) {
    // Таблиці може ще не бути (міграцію не застосовано) — тоді не блокуємо обробку.
    console.log("[WEBHOOK_ERROR]", { action: "claim_update", error: String(error) });
    return true;
  }
}

// ── monobank авто-підтвердження (варіант B: webhook = тригер, дані з mono API) ──
const MONO_API = "https://api.monobank.ua";

// Тіло webhook не авторитетне — лише перевіряємо, що подія стосується нашої банки
// й це вхідне поповнення, після чого тягнемо авторитетну виписку.
async function handleMonoWebhook(env, body) {
  const account = body?.data?.account;
  const item = body?.data?.statementItem;
  if (account !== env.MONO_JAR_ID) return;         // не наша банка (напр., списання з картки)
  if (!item || Number(item.amount) <= 0) return;   // не вхідне поповнення
  await pollJarAndGrant(env);
}

// Тягне виписку банки з mono API і обробляє нові зарахування.
// Пулли throttle до 1/60с, щоб не впертись у ліміт 429.
async function pollJarAndGrant(env) {
  if (!env.MONO_TOKEN || !env.MONO_JAR_ID) {
    console.log("[MONO_ERROR]", { action: "poll", error: "MONO_TOKEN/MONO_JAR_ID не задані" });
    return;
  }
  if (!(await hasFreshPendingPayment(env.DB))) return;  // нікому нічого підтверджувати
  if (!(await claimMonoPoll(env.DB))) {
    console.log("[MONO]", { skip: "poll throttled (<60s)" });
    return;
  }
  const from = Math.floor(Date.now() / 1000) - 24 * 3600;
  const resp = await fetch(`${MONO_API}/personal/statement/${env.MONO_JAR_ID}/${from}`, {
    headers: { "X-Token": env.MONO_TOKEN }
  });
  if (!resp.ok) {
    console.log("[MONO_ERROR]", { action: "statement", status: resp.status });
    return;
  }
  const items = await resp.json().catch(() => null);
  if (!Array.isArray(items)) {
    console.log("[MONO_ERROR]", { action: "statement", error: "unexpected payload" });
    return;
  }
  for (const item of items) {
    await processJarItem(env, item);
  }
}

// Один рядок виписки → доступ, лише якщо: зараховано (hold=false), вхідне (amount>0),
// валюта UAH, є код активної заявки, і сума покриває тариф. Дедуп по statementItem.id.
async function processJarItem(env, item) {
  const txId = item?.id;
  if (!txId) return;
  if (item.hold === true) return;                                      // ще не зараховано — НЕ грантимо
  if (Number(item.amount) <= 0) return;                                // не вхідне
  if (item.currencyCode && Number(item.currencyCode) !== 980) return;  // не гривня
  const code = extractPaymentCode(item.comment);
  if (!code) return;

  const payment = await env.DB.prepare(
    "SELECT id, user_id, amount, tariff_days FROM payments WHERE code = ? AND status = 'pending' ORDER BY id DESC LIMIT 1"
  ).bind(code).first();
  if (!payment) {
    console.log("[MONO]", { tx: txId, code, skip: "no pending payment" });
    return;
  }
  // item.amount у копійках, payment.amount у грн; переплату дозволяємо, недоплату — ні.
  if (Number(item.amount) < Number(payment.amount) * 100) {
    console.log("[MONO]", { tx: txId, code, skip: "amount too low", got: Number(item.amount), need: Number(payment.amount) * 100 });
    return;
  }
  // Дедуп: той самий переказ не активує доступ двічі.
  if (!(await claimMonoTx(env.DB, txId))) {
    console.log("[MONO]", { tx: txId, skip: "already processed" });
    return;
  }
  const targetUserId = String(payment.user_id);
  const days = Number(payment.tariff_days);
  const accessUntil = await grantAccess(env, targetUserId, days, "mono");
  await env.DB.prepare("UPDATE payments SET status = 'paid', paid_at = ?, comment = ? WHERE id = ?")
    .bind(kyivNow().datetime, `mono ${txId}`, payment.id).run();
  await sendMessage(env, targetUserId, `Доступ відкрито 🚀\n\nДо: ${formatHumanDate(accessUntil)}`, MAIN_KEYBOARD, true);
  console.log("[MONO]", { tx: txId, code, user_id: targetUserId, tariff_days: days, status: "auto-paid" });
}

function extractPaymentCode(comment) {
  const match = /DG-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{4}/i.exec(String(comment || ""));
  return match ? match[0].toUpperCase() : null;
}

// Атомарний дедуп транзакцій: true — щойно застовпили; false — вже було (або таблиці нема).
async function claimMonoTx(db, txId) {
  try {
    const result = await db.prepare(
      "INSERT OR IGNORE INTO mono_processed (tx_id, processed_at) VALUES (?, ?)"
    ).bind(String(txId), kyivNow().datetime).run();
    return Number(result.meta?.changes || 0) > 0;
  } catch (error) {
    // Без таблиці не ризикуємо подвійним грантом — краще пропустити (адмін підтвердить вручну).
    console.log("[MONO_ERROR]", { action: "claim_tx", error: String(error) });
    return false;
  }
}

// Throttle пуллів до 1/60с (ліміт mono statement — 429 при частіших запитах).
async function claimMonoPoll(db) {
  const now = Math.floor(Date.now() / 1000);
  try {
    await db.prepare("INSERT OR IGNORE INTO mono_poll (id, last_pull_at) VALUES (1, 0)").run();
    // Одна атомарна умовна UPDATE: два паралельні виклики не можуть обидва виграти.
    const result = await db.prepare(
      "UPDATE mono_poll SET last_pull_at = ? WHERE id = 1 AND last_pull_at <= ?"
    ).bind(now, now - 60).run();
    return Number(result.meta?.changes || 0) > 0;
  } catch (error) {
    console.log("[MONO_ERROR]", { action: "claim_poll", error: String(error) });
    return false;
  }
}

// Виписка покриває лише 24 год, тож старіші заявки однаково не зіставити.
async function hasFreshPendingPayment(db) {
  try {
    const cutoff = `${formatDate(addDays(parseDate(kyivNow().date), -1))} 00:00:00`;
    const row = await db.prepare(
      "SELECT 1 FROM payments WHERE status = 'pending' AND created_at >= ? LIMIT 1"
    ).bind(cutoff).first();
    return Boolean(row);
  } catch (error) {
    console.log("[MONO_ERROR]", { action: "has_pending", error: String(error) });
    return true;  // не знаємо — краще опитати, ніж загубити платіж
  }
}

async function cleanupMonoProcessed(db) {
  try {
    const cutoff = `${formatDate(addDays(parseDate(kyivNow().date), -40))} 00:00:00`;
    await db.prepare("DELETE FROM mono_processed WHERE processed_at < ?").bind(cutoff).run();
  } catch (error) {
    console.log("[CRON_ERROR]", { action: "cleanup_mono_processed", error: String(error) });
  }
}

// Telegram повторює доставку лічені хвилини, тож 2 днів історії достатньо.
async function cleanupProcessedUpdates(db) {
  try {
    const cutoff = `${formatDate(addDays(parseDate(kyivNow().date), -2))} 00:00:00`;
    await db.prepare("DELETE FROM processed_updates WHERE processed_at < ?").bind(cutoff).run();
  } catch (error) {
    console.log("[CRON_ERROR]", { action: "cleanup_processed_updates", error: String(error) });
  }
}

async function handleUpdate(update, env) {
  if (update.message) {
    await handleMessage(update.message, env);
    return;
  }
  if (update.callback_query) {
    await handleCallback(update.callback_query, env);
  }
}

// Тапи по цих кнопках-меню лишають у чаті повідомлення юзера — його прибираємо.
const MENU_BUTTONS = new Set([
  "⬅️ Назад",
  "➕ Додати витрату",
  "💰 Бюджет",
  "📊 Статистика",
  "📅 Обрати період",
  "✏️ Керувати витратами",
  "✏️ Редагувати витрату",
  "🗑 Видалити витрату",
  "💳 Мій доступ"
]);
// Відповіді на промпти (сума, бюджет, період, редагування) — теж службові.
const PROMPT_REPLY_STATES = new Set([
  WAITING_FOR_STATS_PERIOD,
  "waiting_amount",
  "waiting_edit_input",
  "waiting_budget"
]);

// Прибирає вхідне повідомлення юзера; помилку глушимо (бот міг не мати прав
// на видалення або юзер уже видалив сам). Текст витрати сюди не потрапляє.
async function deleteIncomingMessage(env, chatId, messageId) {
  if (!messageId) return;
  try {
    await deleteMessage(env, chatId, messageId);
  } catch (error) {
    console.log("[MSG_DELETE_ERROR]", { error: String(error) });
  }
}

async function handleMessage(message, env) {
  const userId = String(message.from?.id || "");
  const chatId = String(message.chat?.id || "");
  const messageId = message.message_id;
  const text = String(message.text || "").trim();
  const telegramUser = message.from || {};
  const username = telegramUser.username || "";

  console.log("[MSG]", { user_id: userId, text });
  const user = await upsertUser(env.DB, userId, chatId, telegramUser, env);

  if (text === "/start") {
    await clearState(env.DB, userId);
    console.log("[USER]", { user_id: userId, username, action: "register_or_login" });
    if (user?.status === "blocked") {
      await sendMessage(env, chatId, "Доступ обмежено", undefined, true);
      return;
    }
    if (isAdmin(env, userId) || hasActiveAccess(user)) {
      await sendMessage(env, chatId, startText(user), MAIN_KEYBOARD);
    } else {
      await sendMessage(env, chatId, `${startText(user)}\n\n${await paywallText(env, user)}`, paymentKeyboard(), true);
    }
    return;
  }

  if (text === "/admin") {
    await handleAdminCommand(env, userId, chatId);
    return;
  }

  if (text.startsWith("/grant") || text.startsWith("/block") || text.startsWith("/unblock")) {
    await handleAdminTextCommand(env, userId, chatId, text);
    return;
  }

  if (["я оплатив", "оплатив", "paid"].includes(text.toLowerCase())) {
    // Цей хендлер стоїть до ensureAccess, тож блокування треба перевірити тут окремо.
    if (user?.status === "blocked") {
      await sendMessage(env, chatId, "Доступ обмежено", undefined, true);
      return;
    }
    // Тариф береться з заявки, створеної кнопкою тарифу, — без вигаданих сум.
    const pending = await getPendingPayment(env.DB, userId);
    if (!pending) {
      await sendMessage(env, chatId, "Спочатку обери тариф 👇", paymentKeyboard(), true);
      return;
    }
    await sendMessage(env, chatId, "Заявку на оплату передано на перевірку", paymentKeyboard(), true);
    await notifyAdmins(env, userId, username, pending);
    return;
  }

  if (!(await ensureAccess(env, userId, chatId))) return;

  // Тап по кнопці меню: прибираємо повідомлення юзера, лишається одне службове.
  if (MENU_BUTTONS.has(text)) {
    await deleteIncomingMessage(env, chatId, messageId);
  }

  if (text === "⬅️ Назад") {
    await clearState(env.DB, userId);
    // Клавіатура persistent і так внизу — просто прибираємо службове, без нового повідомлення.
    await deleteServiceMessage(env, userId);
    return;
  }

  if (text === "➕ Додати витрату") {
    await clearState(env.DB, userId);
    // Повна інструкція — лише тим, хто ще нічого не записав; решті короткий рядок.
    const experienced = await userHasExpenses(env.DB, userId);
    await sendServiceMessage(env, chatId, userId, experienced ? ADD_EXPENSE_SHORT_HINT : ADD_EXPENSE_HINT, addExpenseHelpKeyboard(experienced));
    return;
  }

  if (text === "💰 Бюджет") {
    await clearState(env.DB, userId);
    await sendBudgetView(env, chatId, userId);
    return;
  }

  if (text === "📊 Статистика") {
    await clearState(env.DB, userId);
    await sendServiceMessage(env, chatId, userId, "Обери період статистики:", statsKeyboard());
    return;
  }

  if (text === "📅 Обрати період") {
    await setState(env.DB, userId, WAITING_FOR_STATS_PERIOD, {});
    await sendServiceMessage(env, chatId, userId, STATS_PERIOD_PROMPT);
    return;
  }

  if (text === "✏️ Керувати витратами") {
    await clearState(env.DB, userId);
    await sendServiceMessage(env, chatId, userId, manageExpensesText(), manageExpensesKeyboard());
    return;
  }

  if (text === "💳 Мій доступ") {
    await clearState(env.DB, userId);
    await sendAccessView(env, chatId, userId);
    return;
  }

  if (text === "✏️ Редагувати витрату") {
    await clearState(env.DB, userId);
    await sendManageDates(env, chatId, userId, "edit");
    return;
  }

  if (text === "🗑 Видалити витрату") {
    await clearState(env.DB, userId);
    await sendManageDates(env, chatId, userId, "delete");
    return;
  }

  const state = await getState(env.DB, userId);
  // Відповідь на промпт (сума/бюджет/період/редагування) — службова, прибираємо.
  // Вільний текст витрати не має активного стану і сюди не потрапляє.
  if (PROMPT_REPLY_STATES.has(state?.state)) {
    await deleteIncomingMessage(env, chatId, messageId);
  }
  if (state?.state === WAITING_FOR_STATS_PERIOD) {
    await handleStatsPeriodInput(env, chatId, userId, text);
    return;
  }
  if (state?.state === "waiting_amount") {
    await handleAmountInput(env, chatId, userId, text, state.data);
    return;
  }
  if (state?.state === "waiting_edit_input") {
    await handleEditExpenseInput(env, chatId, userId, text, state.data);
    return;
  }
  if (state?.state === "waiting_budget") {
    await handleBudgetInput(env, chatId, userId, text);
    return;
  }

  // Немає активного кроку — будь-який вільний текст сприймаємо як спробу додати витрату,
  // без обов'язкового натискання «➕ Додати витрату».
  await handleManualExpenseInput(env, chatId, userId, text);
}

async function handleCallback(callback, env) {
  const data = callback.data || "";
  const userId = String(callback.from?.id || "");
  const chatId = String(callback.message?.chat?.id || "");
  const messageId = callback.message?.message_id;

  console.log("[CALLBACK]", { user_id: userId, callback_data: data, handler_name: "handleCallback" });
  await answerCallback(env, callback.id);
  await upsertUser(env.DB, userId, chatId, callback.from || {}, env);

  if (!(await ensureAccess(env, userId, chatId, data))) return;

  if (data.startsWith("admin:")) {
    await handleAdminCallback(env, userId, chatId, messageId, data);
    return;
  }

  if (data.startsWith("manage_dates:")) {
    const mode = data.split(":")[1];
    await clearState(env.DB, userId);
    await showManageDates(env, chatId, messageId, userId, mode);
    return;
  }

  if (data.startsWith("manage_day:")) {
    const [, mode, date] = data.split(":");
    await clearState(env.DB, userId);
    await showManageDay(env, chatId, messageId, userId, mode, date);
    return;
  }

  if (data.startsWith("manage_edit:")) {
    const expenseId = Number(data.split(":")[1]);
    const expense = await getExpenseById(env.DB, userId, expenseId);
    if (!expense) {
      await editMessage(env, chatId, messageId, "Витрату не знайдено");
      return;
    }
    await setState(env.DB, userId, "waiting_edit_input", { expense_id: expenseId });
    await editMessage(
      env, chatId, messageId,
      `✏️ Редагування\n\n${capitalize(expense.expense_title)} — ${formatAmount(expense.amount)} ${CURRENCY}\n\nНапиши нову назву і суму, наприклад:\n${expense.expense_title} ${expense.amount}`
    );
    return;
  }

  if (data.startsWith("manage_delete:")) {
    const expenseId = Number(data.split(":")[1]);
    const expense = await getExpenseById(env.DB, userId, expenseId);
    if (!expense) {
      await editMessage(env, chatId, messageId, "Витрату не знайдено");
      return;
    }
    const deleted = await deleteExpense(env.DB, userId, expenseId);
    const text = deleted
      ? `🗑 Видалено\n\n${capitalize(expense.expense_title)} — ${formatAmount(expense.amount)} ${CURRENCY}`
      : "Витрату не знайдено";
    await editMessage(env, chatId, messageId, text, {
      inline_keyboard: [[{ text: "⬅️ До списку", callback_data: `manage_dates:delete` }]]
    });
    return;
  }

  if (data === "stats") {
    await clearState(env.DB, userId);
    await editMessage(env, chatId, messageId, "Обери період статистики:", statsKeyboard());
    return;
  }

  if (data === "stats:custom") {
    await setState(env.DB, userId, WAITING_FOR_STATS_PERIOD, {});
    await editMessage(env, chatId, messageId, STATS_PERIOD_PROMPT);
    return;
  }

  if (data.startsWith("stats:")) {
    await clearState(env.DB, userId);
    const period = data.split(":")[1];
    if (period === "month") {
      await editMessage(env, chatId, messageId, "Обери місяць:", await monthKeyboard(env.DB, userId));
      return;
    }
    const range = getPeriodRange(period);
    await showStats(env, chatId, messageId, userId, range, period);
    return;
  }

  if (data.startsWith("stats_month:")) {
    await clearState(env.DB, userId);
    const month = data.split(":")[1];
    const range = getMonthRange(month);
    await showStats(env, chatId, messageId, userId, range, `month:${month}`);
    return;
  }

  if (data.startsWith("stats_detail:")) {
    await clearState(env.DB, userId);
    const detail = parseDetailCallback(data);
    if (!detail) return;
    await showCategoryDetails(env, chatId, messageId, userId, detail);
    return;
  }

  if (data.startsWith("stats_detail_custom:")) {
    const category = data.slice("stats_detail_custom:".length);
    const range = await getLastStatsRange(env.DB, userId);
    if (!range || !CATEGORY_LABELS[category]) {
      await clearState(env.DB, userId);
      await editMessage(env, chatId, messageId, "Період застарів. Обери його ще раз:", statsKeyboard());
      return;
    }
    await showCustomCategoryDetails(env, chatId, messageId, userId, category, range);
    return;
  }

  if (data === "stats_custom_back") {
    const range = await getLastStatsRange(env.DB, userId);
    if (!range) {
      await clearState(env.DB, userId);
      await editMessage(env, chatId, messageId, "Період застарів. Обери його ще раз:", statsKeyboard());
      return;
    }
    await showCustomStats(env, chatId, messageId, userId, range);
    return;
  }

  if (data === "stats_main_back") {
    await clearState(env.DB, userId);
    await deleteMessage(env, chatId, messageId);
    await forgetServiceMessage(env.DB, userId, messageId);
    return;
  }

  if (data === "stats_back") {
    await clearState(env.DB, userId);
    await editMessage(env, chatId, messageId, "Обери період статистики:", statsKeyboard());
    return;
  }

  if (data === "add_quick") {
    await editMessage(env, chatId, messageId, "Обери категорію:", quickCategoryKeyboard());
    return;
  }

  if (data === "quick_categories_back") {
    const experienced = await userHasExpenses(env.DB, userId);
    await editMessage(env, chatId, messageId, experienced ? ADD_EXPENSE_SHORT_HINT : ADD_EXPENSE_HINT, addExpenseHelpKeyboard(experienced));
    return;
  }

  if (data === "add_examples") {
    await editMessage(env, chatId, messageId, ADD_EXPENSE_HINT, addExpenseHelpKeyboard(false));
    return;
  }

  if (data.startsWith("quick_cat:")) {
    const category = data.split(":")[1];
    await editMessage(env, chatId, messageId, "Обери витрату:", quickSubcategoryKeyboard(category));
    return;
  }

  if (data.startsWith("quick_sub:")) {
    const [, category, subcategory] = data.split(":");
    const title = SUBCATEGORY_TITLES[`${category}:${subcategory}`] || "витрата";
    await setState(env.DB, userId, "waiting_amount", { expense_title: title, category });
    await editMessage(env, chatId, messageId, `Введи суму 💸\n\n${capitalize(title)}`);
    return;
  }

  if (data.startsWith("type_choice:")) {
    const [, expenseType, pendingIdText] = data.split(":");
    const pendingId = Number(pendingIdText);
    // Старі картки без id у callback_data теж потрапляють сюди — для них pendingId = NaN.
    if (!["planned", "emotional"].includes(expenseType) || !pendingId) {
      await editMessage(env, chatId, messageId, "Це повідомлення застаріло. Напиши витрату ще раз 👇");
      return;
    }
    const pending = await claimPendingExpense(env.DB, userId, pendingId);
    if (!pending) {
      await editMessage(env, chatId, messageId, "Це повідомлення застаріло. Напиши витрату ще раз 👇");
      return;
    }
    const expenseId = await insertExpense(env.DB, {
      user_id: userId,
      chat_id: chatId,
      expense_title: pending.expense_title,
      amount: pending.amount,
      category: pending.category,
      expense_type: expenseType,
      expense_date: pending.expense_date
    });
    const expense = await getExpenseById(env.DB, userId, expenseId);
    const budget = await budgetWarning(env.DB, userId, expense.expense_date);
    await editMessage(env, chatId, messageId, expenseCardText(expense, budget), expenseCardKeyboard(expense));
    return;
  }

  if (data.startsWith("exp_type:")) {
    const expenseId = Number(data.split(":")[1]);
    const expense = await getExpenseById(env.DB, userId, expenseId);
    if (!expense) {
      await editMessage(env, chatId, messageId, "Витрату не знайдено");
      return;
    }
    const newType = expense.expense_type === "emotional" ? "planned" : "emotional";
    await env.DB.prepare("UPDATE expenses SET expense_type = ? WHERE user_id = ? AND id = ?")
      .bind(newType, userId, expenseId).run();
    const updated = { ...expense, expense_type: newType };
    const budget = await budgetWarning(env.DB, userId, updated.expense_date);
    await editMessage(env, chatId, messageId, expenseCardText(updated, budget), expenseCardKeyboard(updated));
    return;
  }

  if (data.startsWith("exp_cat:")) {
    const expenseId = Number(data.split(":")[1]);
    const expense = await getExpenseById(env.DB, userId, expenseId);
    if (!expense) {
      await editMessage(env, chatId, messageId, "Витрату не знайдено");
      return;
    }
    await editMessage(env, chatId, messageId, `Обери категорію для «${capitalize(expense.expense_title)}»:`, expenseCategoryPicker(expenseId));
    return;
  }

  if (data.startsWith("exp_setcat:")) {
    const [, idText, category] = data.split(":");
    const expenseId = Number(idText);
    const expense = await getExpenseById(env.DB, userId, expenseId);
    if (!expense) {
      await editMessage(env, chatId, messageId, "Витрату не знайдено");
      return;
    }
    await env.DB.prepare("UPDATE expenses SET category = ? WHERE user_id = ? AND id = ?")
      .bind(category, userId, expenseId).run();
    await saveCategoryOverride(env.DB, userId, expense.expense_title, category);
    const updated = { ...expense, category };
    const budget = await budgetWarning(env.DB, userId, updated.expense_date);
    await editMessage(env, chatId, messageId, expenseCardText(updated, budget), expenseCardKeyboard(updated));
    return;
  }

  if (data.startsWith("exp_card:")) {
    const expenseId = Number(data.split(":")[1]);
    const expense = await getExpenseById(env.DB, userId, expenseId);
    if (!expense) {
      await editMessage(env, chatId, messageId, "Витрату не знайдено");
      return;
    }
    const budget = await budgetWarning(env.DB, userId, expense.expense_date);
    await editMessage(env, chatId, messageId, expenseCardText(expense, budget), expenseCardKeyboard(expense));
    return;
  }

  if (data === "budget_set") {
    await setState(env.DB, userId, "waiting_budget", {});
    await editMessage(env, chatId, messageId, "💰 Напиши суму бюджету на місяць, наприклад 20000");
    return;
  }

  if (data === "budget_clear") {
    await setMonthlyBudget(env.DB, userId, null);
    await clearState(env.DB, userId);
    await editMessage(env, chatId, messageId, "Бюджет прибрано. Можеш встановити новий у меню «💰 Бюджет».");
    return;
  }

  if (data === "access_extend") {
    const pending = await getPendingPayment(env.DB, userId);
    await editMessage(env, chatId, messageId, tariffBlock(env, pending), paymentKeyboard());
    return;
  }

  if (data.startsWith("buy_")) {
    const days = Number(data.split("_")[1]);
    const tariff = TARIFF_BY_DAYS.get(days);
    if (!tariff) return;
    const code = await ensurePendingPayment(env.DB, userId, tariff.price, tariff.days);
    await editMessage(env, chatId, messageId, paymentText(env, tariff, code), paidKeyboard(days));
    return;
  }

  if (data === "paid" || data.startsWith("paid_")) {
    const chosenDays = data.includes("_") ? Number(data.split("_")[1]) : 0;
    const chosen = TARIFF_BY_DAYS.get(chosenDays);
    if (chosen) {
      await ensurePendingPayment(env.DB, userId, chosen.price, chosen.days);
    }
    // Голий "paid" тарифу не несе — беремо актуальну (єдину) заявку юзера.
    const pending = await getPendingPayment(env.DB, userId);
    if (!pending) {
      await editMessage(env, chatId, messageId, "Спочатку обери тариф 👇", paymentKeyboard());
      return;
    }
    await editMessage(env, chatId, messageId, "Дякую 🙌\n\nПеревірю оплату і відкрию доступ протягом 1–5 хвилин.");
    await notifyAdmins(env, userId, callback.from?.username || "", pending);
    return;
  }

  if (data.startsWith("paycfm_") || data.startsWith("payrej_") || data.startsWith("confirm_") || data.startsWith("reject_")) {
    await handleAdminPaymentAction(env, callback, data);
  }
}

async function handleAdminCommand(env, userId, chatId) {
  if (!isAdmin(env, userId)) {
    await sendMessage(env, chatId, "Немає доступу", undefined, true);
    return;
  }
  await sendMessage(env, chatId, "Адмін-панель:", adminKeyboard(), true);
}

async function handleAdminTextCommand(env, adminId, chatId, text) {
  if (!isAdmin(env, adminId)) {
    await sendMessage(env, chatId, "Немає доступу", undefined, true);
    return;
  }

  const [command, targetUserId, daysText] = text.split(/\s+/);
  if (!targetUserId) {
    await sendMessage(env, chatId, "Формат:\n/grant user_id 30\n/block user_id\n/unblock user_id", undefined, true);
    return;
  }

  if (command === "/block") {
    await env.DB.prepare("UPDATE users SET status = 'blocked' WHERE user_id = ?").bind(targetUserId).run();
    await sendMessage(env, chatId, "Користувача заблоковано", undefined, true);
    return;
  }

  if (command === "/unblock") {
    await env.DB.prepare("UPDATE users SET status = 'active' WHERE user_id = ?").bind(targetUserId).run();
    await sendMessage(env, chatId, "Користувача розблоковано", undefined, true);
    return;
  }

  if (command === "/grant") {
    const days = Number(daysText || TARIFFS[0].days);
    if (!TARIFF_BY_DAYS.has(days)) {
      await sendMessage(env, chatId, `Дні мають бути: ${TARIFFS.map((t) => t.days).join(", ")}`, undefined, true);
      return;
    }
    const targetUser = await getUser(env.DB, targetUserId);
    if (!targetUser) {
      await sendMessage(env, chatId, "Користувача не знайдено", undefined, true);
      return;
    }
    const currentEnd = targetUser.access_until && hasActiveAccess(targetUser)
      ? parseDate(String(targetUser.access_until).slice(0, 10))
      : parseDate(kyivNow().date);
    const until = addDays(currentEnd, days);
    const accessUntil = `${formatDate(until)} 23:59:59`;
    await env.DB.prepare(
      "UPDATE users SET access_until = ?, tariff = ?, status = 'active' WHERE user_id = ?"
    ).bind(accessUntil, `${days}_days`, targetUserId).run();
    console.log("[ADMIN]", { action: "grant", admin_id: adminId, user_id: targetUserId, days });
    await sendMessage(env, chatId, "Доступ видано", undefined, true);
    await sendMessage(env, targetUserId, "Доступ відкрито 🚀", MAIN_KEYBOARD, true);
  }
}

async function handleAdminCallback(env, userId, chatId, messageId, data) {
  if (!isAdmin(env, userId)) return;
  const section = data.split(":")[1];
  if (section === "users") {
    await editMessage(env, chatId, messageId, await adminUsersText(env.DB), adminKeyboard());
    return;
  }
  if (section === "payments") {
    await editMessage(env, chatId, messageId, await adminPaymentsText(env.DB), adminKeyboard());
    return;
  }
  if (section === "access") {
    await editMessage(env, chatId, messageId, await adminAccessText(env.DB), adminKeyboard());
    return;
  }
  if (section === "blocked") {
    await editMessage(env, chatId, messageId, await adminBlockedText(env.DB), adminKeyboard());
  }
}

async function adminUsersText(db) {
  const rows = await db.prepare(
    `SELECT user_id, username, first_name, status, access_until
     FROM users
     ORDER BY id DESC
     LIMIT 20`
  ).all();
  const users = rows.results || [];
  if (!users.length) return "👥 Користувачів ще немає";
  return [
    "👥 Користувачі",
    "",
    ...users.map((user, index) =>
      `${index + 1}. ${user.user_id}\n@${user.username || "—"}\nстатус: ${user.status || "active"}\nдо: ${user.access_until || "—"}`
    )
  ].join("\n\n");
}

async function adminPaymentsText(db) {
  const rows = await db.prepare(
    `SELECT user_id, amount, tariff_days, status, created_at
     FROM payments
     ORDER BY id DESC
     LIMIT 20`
  ).all();
  const payments = rows.results || [];
  if (!payments.length) return "💳 Оплат ще немає";
  return [
    "💳 Оплати",
    "",
    ...payments.map((payment, index) =>
      `${index + 1}. user_id: ${payment.user_id}\n${payment.amount} грн / ${payment.tariff_days} днів\nстатус: ${payment.status}\n${payment.created_at}`
    )
  ].join("\n\n");
}

async function adminAccessText(db) {
  const rows = await db.prepare(
    `SELECT user_id, username, access_until, tariff, status
     FROM users
     WHERE access_until IS NOT NULL
     ORDER BY access_until DESC
     LIMIT 20`
  ).all();
  const users = rows.results || [];
  if (!users.length) return "⏳ Активних доступів ще немає";
  return [
    "⏳ Доступи",
    "",
    ...users.map((user, index) =>
      `${index + 1}. ${user.user_id} @${user.username || "—"}\nтариф: ${user.tariff || "—"}\nстатус: ${user.status || "active"}\nдо: ${user.access_until}`
    )
  ].join("\n\n");
}

async function adminBlockedText(db) {
  const rows = await db.prepare(
    `SELECT user_id, username, first_name
     FROM users
     WHERE status = 'blocked'
     ORDER BY id DESC
     LIMIT 20`
  ).all();
  const users = rows.results || [];
  if (!users.length) return "🚫 Заблокованих немає";
  return [
    "🚫 Заблоковані",
    "",
    ...users.map((user, index) => `${index + 1}. ${user.user_id} @${user.username || "—"} ${user.first_name || ""}`)
  ].join("\n");
}

async function handleManualExpenseInput(env, chatId, userId, text) {
  const { date, items } = parseExpensesMessage(text);
  if (!items.length) {
    await sendServiceMessage(env, chatId, userId, "Не зрозумів 🤔 Напиши: назва і сума, наприклад: кава 80", examplesKeyboard());
    return;
  }

  if (items.length === 1) {
    const parsed = items[0];
    if (!parsed || (!parsed.title && !parsed.amount)) {
      await sendServiceMessage(env, chatId, userId, "Не зрозумів 🤔 Напиши: назва і сума, наприклад: кава 80", examplesKeyboard());
      return;
    }
    if (parsed.title && !parsed.amount) {
      const category = await detectCategorySmart(env.DB, userId, parsed.title);
      await setState(env.DB, userId, "waiting_amount", { expense_title: parsed.title, category, date });
      await sendServiceMessage(env, chatId, userId, `💸 Введи суму для «${capitalize(parsed.title)}»`);
      return;
    }
    if (!parsed.title) {
      await sendServiceMessage(env, chatId, userId, "Спочатку напиши назву витрати, наприклад: кава 80");
      return;
    }
    const category = await detectCategorySmart(env.DB, userId, parsed.title);
    await askExpenseType(env, chatId, userId, {
      expense_title: parsed.title,
      amount: parsed.amount,
      category,
      date
    });
    return;
  }

  const missing = items.filter((item) => !item || !item.title || !item.amount);
  if (missing.length) {
    await sendServiceMessage(
      env, chatId, userId,
      "У деяких витратах не бачу назву або суму. Напиши кожну як «назва сума», наприклад:\nкава 80, таксі 150"
    );
    return;
  }

  const saved = [];
  for (const item of items) {
    const category = await detectCategorySmart(env.DB, userId, item.title);
    await insertExpense(env.DB, {
      user_id: userId,
      chat_id: chatId,
      expense_title: item.title,
      amount: item.amount,
      category,
      expense_type: "planned",
      expense_date: date
    });
    saved.push({ ...item, category });
  }

  const total = saved.reduce((sum, item) => sum + item.amount, 0);
  const lines = [
    `✅ Зафіксовано ${pluralExpenses(saved.length)}${date ? ` за ${formatShortDate(parseDate(date))}` : ""}:`,
    "",
    ...saved.map((item) => `• ${capitalize(item.title)} — ${formatAmount(item.amount)} ${CURRENCY} (${formatCategory(item.category)})`),
    "",
    `💸 Разом: ${formatAmount(total)} ${CURRENCY}`,
    "",
    "Записано як планові — тип кожної можна змінити в «✏️ Керувати витратами»."
  ];
  const budget = await budgetWarning(env.DB, userId, date);
  if (budget) lines.push("", budget);
  // Підсумок мультидодавання — історія (як картка), але службовий промпт прибираємо.
  await deleteServiceMessage(env, userId);
  await sendMessage(env, chatId, lines.join("\n"), MAIN_KEYBOARD, true);
}

async function handleAmountInput(env, chatId, userId, text, data) {
  const amount = parseAmount(text);
  if (!amount) {
    await sendServiceMessage(env, chatId, userId, "Введи тільки суму, наприклад 300 або 149.50");
    return;
  }
  await askExpenseType(env, chatId, userId, {
    expense_title: data.expense_title,
    amount,
    category: data.category,
    date: data.date
  });
}

// Показує картку витрати одразу з двома кнопками "Планова"/"Емоційна".
// Кожна очікувана витрата — окремий рядок у pending_expenses, а її id вшитий у
// callback_data: кілька карток поспіль не затирають одна одну, як це було зі станом.
async function askExpenseType(env, chatId, userId, data) {
  const category = data.category || await detectCategorySmart(env.DB, userId, data.expense_title);
  await clearState(env.DB, userId);
  // Картка витрати — історія, вона не трекається; службовий промпт перед нею зникає.
  await deleteServiceMessage(env, userId);
  const pendingId = await insertPendingExpense(env.DB, {
    user_id: userId,
    chat_id: chatId,
    expense_title: data.expense_title,
    amount: data.amount,
    category,
    expense_date: data.date || null
  });
  const dateLabel = data.date ? ` • 📅 ${formatShortDate(parseDate(data.date))}` : "";
  const text = [
    `💸 ${capitalize(data.expense_title)} — ${formatAmount(data.amount)} ${CURRENCY}`,
    `${formatCategory(category)}${dateLabel}`,
    "",
    "Обери тип витрати:"
  ].join("\n");
  await sendMessage(env, chatId, text, {
    inline_keyboard: [[
      { text: "📌 Планова", callback_data: `type_choice:planned:${pendingId}` },
      { text: "🔥 Емоційна", callback_data: `type_choice:emotional:${pendingId}` }
    ]]
  }, true);
}

async function insertPendingExpense(db, pending) {
  const result = await db.prepare(
    `INSERT INTO pending_expenses (user_id, chat_id, expense_title, amount, category, expense_date, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?)`
  ).bind(
    pending.user_id,
    pending.chat_id,
    pending.expense_title,
    Number(pending.amount),
    pending.category,
    pending.expense_date,
    kyivNow().datetime
  ).run();
  return Number(result.meta?.last_row_id || 0);
}

// Атомарне захоплення: з двох конкурентних тапів по кнопках картки DELETE
// пройде (changes=1) лише в одного — другий отримає null і "застаріло".
async function claimPendingExpense(db, userId, pendingId) {
  const row = await db.prepare(
    `SELECT id, expense_title, amount, category, expense_date
     FROM pending_expenses
     WHERE id = ? AND user_id = ?`
  ).bind(pendingId, userId).first();
  if (!row) return null;
  const result = await db.prepare("DELETE FROM pending_expenses WHERE id = ?").bind(pendingId).run();
  if (Number(result.meta?.changes || 0) === 0) return null;
  return row;
}

async function cleanupPendingExpenses(db) {
  try {
    const cutoff = `${formatDate(addDays(parseDate(kyivNow().date), -7))} 00:00:00`;
    await db.prepare("DELETE FROM pending_expenses WHERE created_at < ?").bind(cutoff).run();
  } catch (error) {
    console.log("[CRON_ERROR]", { action: "cleanup_pending_expenses", error: String(error) });
  }
}

async function handleBudgetInput(env, chatId, userId, text) {
  const amount = parseAmount(text);
  if (!amount) {
    await sendServiceMessage(env, chatId, userId, "Введи суму бюджету числом, наприклад 20000");
    return;
  }
  await setMonthlyBudget(env.DB, userId, amount);
  await clearState(env.DB, userId);
  await sendServiceMessage(env, chatId, userId, `💰 Бюджет на місяць встановлено: ${formatAmount(amount)} ${CURRENCY}`);
}

async function handleStatsPeriodInput(env, chatId, userId, text) {
  const range = parseStatsPeriodInput(text);
  if (!range) {
    await sendServiceMessage(env, chatId, userId, STATS_PERIOD_ERROR);
    return;
  }
  await showCustomStats(env, chatId, null, userId, range);
}

async function handleEditExpenseInput(env, chatId, userId, text, data) {
  const { date, items } = parseExpensesMessage(text);
  const parsed = items.length === 1 ? items[0] : null;
  if (!parsed?.title || !parsed?.amount) {
    await sendServiceMessage(env, chatId, userId, "Напиши назву і суму, наприклад: кава 100");
    return;
  }

  const category = await detectCategorySmart(env.DB, userId, parsed.title);
  const updated = await updateExpense(env.DB, userId, Number(data.expense_id), parsed.title, parsed.amount, category, date);
  await clearState(env.DB, userId);
  const resultText = updated
    ? `✅ Оновлено\n\n${capitalize(cleanExpenseTitle(parsed.title))} — ${formatAmount(parsed.amount)} ${CURRENCY} • ${formatCategory(category)}`
    : "Витрату не знайдено";
  await sendServiceMessage(env, chatId, userId, resultText);
}

// Розбирає повідомлення: дата («вчора», «1 липня»), кілька витрат через кому чи з нового рядка.
function parseExpensesMessage(text) {
  const { date, rest } = extractExpenseDate(String(text || ""));
  const segments = [];
  for (const line of rest.split(/\n+/)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const commaParts = trimmed.split(/[,;]+/).map((part) => part.trim()).filter(Boolean);
    if (commaParts.length > 1 && commaParts.every((part) => /\d/.test(part))) {
      segments.push(...commaParts);
    } else {
      segments.push(trimmed);
    }
  }
  return { date, items: segments.map(parseExpenseInput).filter(Boolean) };
}

function extractExpenseDate(text) {
  const today = parseDate(kyivNow().date);
  let value = ` ${text.trim()} `;

  const wordDates = [
    [/(^|\s)позавчора(?=\s|$)/i, -2],
    [/(^|\s)вчора(?=\s|$)/i, -1],
    [/(^|\s)сьогодні(?=\s|$)/i, 0]
  ];
  for (const [pattern, offset] of wordDates) {
    if (pattern.test(value)) {
      return {
        date: formatDate(addDays(today, offset)),
        rest: value.replace(pattern, " ").trim()
      };
    }
  }

  const monthPattern = new RegExp(`(^|\\s)(\\d{1,2})\\s+(${MONTHS_GENITIVE.join("|")})(?=\\s|$)`, "i");
  const match = value.match(monthPattern);
  if (match) {
    const day = Number(match[2]);
    const monthIndex = MONTHS_GENITIVE.findIndex((m) => m === match[3].toLowerCase());
    if (day >= 1 && day <= 31 && monthIndex >= 0) {
      let candidate = new Date(Date.UTC(today.getUTCFullYear(), monthIndex, day));
      if (candidate.getTime() > today.getTime()) {
        candidate = new Date(Date.UTC(today.getUTCFullYear() - 1, monthIndex, day));
      }
      return { date: formatDate(candidate), rest: value.replace(monthPattern, " ").trim() };
    }
  }

  return { date: null, rest: value.trim() };
}

const AMOUNT_PATTERN = /(\d+(?:[.,]\d+)?)\s?([кk](?![\p{L}\p{N}]))?/gu;

function parseExpenseInput(text) {
  let value = String(text || "").trim().replace(/\s+/g, " ");
  if (!value) return null;
  value = value.replace(/(^|\s|\d)(грн|гривень|гривні|гривня|uah)(?=\s|$|[.,!?])/gi, "$1").replace(/₴/g, " ").replace(/\s+/g, " ").trim();

  if (/^\d+(?:[.,]\d+)?\s?[кk]?$/i.test(value)) {
    return { title: null, amount: parseAmount(value) };
  }

  const matches = [...value.matchAll(AMOUNT_PATTERN)];
  if (!matches.length) return { title: cleanExpenseTitle(value), amount: null };

  const match = matches[matches.length - 1];
  let amount = Number(match[1].replace(",", "."));
  if (match[2]) amount *= 1000;
  amount = Math.round(amount * 100) / 100;

  const title = cleanExpenseTitle(
    (value.slice(0, match.index) + " " + value.slice(match.index + match[0].length)).replace(/\s+/g, " ").trim()
  );
  return { title, amount: amount > 0 ? amount : null };
}

function parseAmount(text) {
  let value = String(text || "").trim().toLowerCase();
  value = value.replace(/(грн|гривень|гривні|гривня|uah|₴)/g, "").trim();
  const match = value.match(/^(\d+(?:[.,]\d+)?)\s?([кk])?$/);
  if (!match) return null;
  let amount = Number(match[1].replace(",", "."));
  if (match[2]) amount *= 1000;
  amount = Math.round(amount * 100) / 100;
  return amount > 0 ? amount : null;
}

function cleanExpenseTitle(title) {
  const value = String(title || "").trim().replace(/\s+/g, " ");
  if (!value || isServiceTitle(value)) return "Без назви";
  return value;
}

function isServiceTitle(title) {
  const value = String(title || "").trim().toLowerCase();
  if (!value) return true;
  if (Object.keys(CATEGORY_LABELS).includes(value)) return true;
  if (Object.values(CATEGORY_LABELS).some((label) => stripEmoji(label).toLowerCase() === value)) return true;
  if (MONTHS.includes(value) || MONTHS_GENITIVE.includes(value)) return true;
  const monthPattern = [...MONTHS, ...MONTHS_GENITIVE].join("|");
  return (
    /^\d{4}-\d{2}(-\d{2})?$/.test(value) ||
    /^\d{1,2}[./-]\d{1,2}([./-]\d{2,4})?$/.test(value) ||
    new RegExp(`^(${monthPattern})\\s+\\d{4}$`).test(value) ||
    new RegExp(`^\\d{1,2}\\s+(${monthPattern})(\\s+.*)?$`).test(value)
  );
}

// Правило вирішення конфліктів: перемагає більша вага (бренд > фраза > корінь >
// нечіткий збіг), при рівній вазі — довший збіг, далі — порядок категорій.
function detectCategory(title) {
  const value = normalizeForMatch(title);
  if (!value) return "other";

  let best = null;
  const consider = (category, rank, length) => {
    if (!best || rank > best.rank || (rank === best.rank && length > best.length)) {
      best = { category, rank, length };
    }
  };

  for (const entry of PHRASE_ENTRIES) {
    if (value.includes(entry.text)) consider(entry.category, entry.rank, entry.text.length);
  }

  for (const token of value.split(" ")) {
    if (!token) continue;
    let matched = false;
    // Найдовший префікс токена, що є коренем у словнику.
    for (let length = token.length; length >= 2; length--) {
      const hit = ROOT_INDEX.get(token.slice(0, length));
      // exact-слова («газ», «бар») спрацьовують лише як ціле слово.
      if (!hit || (hit.exactOnly && length !== token.length)) continue;
      consider(hit.category, hit.rank, length);
      matched = true;
      break;
    }
    if (!matched && token.length > 5) {
      const fuzzy = findFuzzyRoot(token);
      if (fuzzy) consider(fuzzy.category, MATCH_RANK.fuzzy, fuzzy.length);
    }
  }

  if (best) return best.category;
  console.log("[UNKNOWN_CATEGORY]", title);
  return "other";
}

// Одруківки: шукаємо корінь на відстані Левенштейна 1, звіряючись лише з
// коренями схожої довжини, а не з усім словником.
function findFuzzyRoot(token) {
  // Корінь порівнюємо з ПРЕФІКСОМ токена тієї ж (±1) довжини: «продкти» має
  // збігтися з коренем «продукт» попри закінчення.
  const maxLength = Math.min(token.length + 1, 14);
  for (let length = maxLength; length >= 4; length--) {
    const bucket = ROOTS_BY_LENGTH.get(length);
    if (!bucket) continue;
    const candidates = [token.slice(0, length), token.slice(0, length - 1)];
    for (const root of bucket) {
      for (const candidate of candidates) {
        if (candidate.length < 4) continue;
        if (isWithinOneEdit(candidate, root)) {
          const hit = ROOT_INDEX.get(root);
          if (hit) return { category: hit.category, length: root.length };
        }
      }
    }
  }
  return null;
}

function isWithinOneEdit(a, b) {
  if (a === b) return true;
  const diff = a.length - b.length;
  if (diff > 1 || diff < -1) return false;
  // Перестановка сусідніх літер — найчастіша одруківка («шоколда»).
  if (diff === 0) {
    for (let k = 0; k < a.length - 1; k++) {
      if (a[k] !== b[k]) {
        return a[k] === b[k + 1] && a[k + 1] === b[k] && a.slice(k + 2) === b.slice(k + 2);
      }
    }
  }
  let i = 0;
  let j = 0;
  let edits = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      i++;
      j++;
      continue;
    }
    if (++edits > 1) return false;
    if (a.length > b.length) i++;
    else if (a.length < b.length) j++;
    else {
      i++;
      j++;
    }
  }
  if (i < a.length || j < b.length) edits++;
  return edits <= 1;
}

function normalizeTitle(title) {
  return String(title || "").toLowerCase().trim().replace(/\s+/g, " ");
}

// Спочатку перевіряє, чи користувач раніше вручну виправляв категорію для цієї назви.
async function detectCategorySmart(db, userId, title) {
  const norm = normalizeTitle(title);
  if (norm) {
    const row = await db.prepare(
      "SELECT category FROM category_overrides WHERE user_id = ? AND title_norm = ?"
    ).bind(userId, norm).first();
    if (row?.category && CATEGORY_LABELS[row.category]) return row.category;
  }
  return detectCategory(title);
}

async function saveCategoryOverride(db, userId, title, category) {
  const norm = normalizeTitle(title);
  if (!norm || norm === "без назви") return;
  await db.prepare(
    `INSERT INTO category_overrides (user_id, title_norm, category, updated_at)
     VALUES (?, ?, ?, ?)
     ON CONFLICT(user_id, title_norm) DO UPDATE SET
       category = excluded.category,
       updated_at = excluded.updated_at`
  ).bind(userId, norm, category, kyivNow().datetime).run();
  console.log("[DB]", { action: "save_category_override", user_id: userId, title_norm: norm, category });
}

function expenseCardText(expense, budgetLine) {
  const typeLabel = expense.expense_type === "emotional" ? "🔥 Емоційна" : "📌 Планова";
  const lines = [
    "✅ Зафіксовано",
    "",
    `${capitalize(expense.expense_title)} — ${formatAmount(expense.amount)} ${CURRENCY}`,
    `${typeLabel} • ${formatCategory(expense.category)} • 📅 ${formatShortDate(parseDate(expense.expense_date))}`
  ];
  if (budgetLine) lines.push("", budgetLine);
  return lines.join("\n");
}

function expenseCardKeyboard(expense) {
  const typeButton = expense.expense_type === "emotional"
    ? { text: "📌 Зробити плановою", callback_data: `exp_type:${expense.id}` }
    : { text: "🔥 Емоційна витрата", callback_data: `exp_type:${expense.id}` };
  return {
    inline_keyboard: [
      [typeButton],
      [{ text: "✏️ Змінити категорію", callback_data: `exp_cat:${expense.id}` }]
    ]
  };
}

function expenseCategoryPicker(expenseId) {
  const entries = Object.entries(CATEGORY_LABELS);
  const rows = [];
  for (let i = 0; i < entries.length; i += 2) {
    rows.push(entries.slice(i, i + 2).map(([key, label]) => ({
      text: label,
      callback_data: `exp_setcat:${expenseId}:${key}`
    })));
  }
  rows.push([{ text: "⬅️ Назад", callback_data: `exp_card:${expenseId}` }]);
  return { inline_keyboard: rows };
}

async function getMonthlyBudget(db, userId) {
  const row = await db.prepare("SELECT monthly_budget FROM settings WHERE user_id = ?").bind(userId).first();
  const budget = Number(row?.monthly_budget || 0);
  return budget > 0 ? budget : null;
}

async function setMonthlyBudget(db, userId, amount) {
  await db.prepare(
    `INSERT INTO settings (user_id, timezone, currency, monthly_budget)
     VALUES (?, 'Europe/Kyiv', 'грн', ?)
     ON CONFLICT(user_id) DO UPDATE SET monthly_budget = excluded.monthly_budget`
  ).bind(userId, amount).run();
  console.log("[DB]", { action: "set_budget", user_id: userId, monthly_budget: amount });
}

async function getMonthSpent(db, userId, ym) {
  const row = await db.prepare(
    `SELECT COALESCE(SUM(amount), 0) AS total
     FROM expenses
     WHERE user_id = ? AND substr(expense_date, 1, 7) = ?`
  ).bind(userId, ym).first();
  return Number(row?.total || 0);
}

function progressBar(percent) {
  const filled = Math.max(0, Math.min(10, Math.round(percent / 10)));
  return "▓".repeat(filled) + "░".repeat(10 - filled);
}

// Рядок для картки витрати/статистики: скільки бюджету використано (тільки поточний місяць).
async function budgetWarning(db, userId, expenseDate) {
  const currentYm = kyivNow().date.slice(0, 7);
  if (expenseDate && String(expenseDate).slice(0, 7) !== currentYm) return null;
  const budget = await getMonthlyBudget(db, userId);
  if (!budget) return null;
  const spent = await getMonthSpent(db, userId, currentYm);
  const percent = Math.round((spent / budget) * 100);
  let line = `💰 Бюджет: використано ${percent}% (${formatAmount(spent)} з ${formatAmount(budget)} ${CURRENCY})`;
  if (percent >= 100) line += "\n🚨 Бюджет на місяць вичерпано!";
  else if (percent >= 80) line += "\n⚠️ Уже близько до ліміту!";
  return line;
}

async function sendBudgetView(env, chatId, userId) {
  const currentYm = kyivNow().date.slice(0, 7);
  const monthName = MONTHS[Number(currentYm.slice(5, 7)) - 1];
  const budget = await getMonthlyBudget(env.DB, userId);
  const spent = await getMonthSpent(env.DB, userId, currentYm);

  const lines = ["💰 Бюджет на місяць", ""];
  const buttons = [];
  if (budget) {
    const percent = Math.round((spent / budget) * 100);
    lines.push(
      `Ліміт: ${formatAmount(budget)} ${CURRENCY}`,
      `Витрачено у ${MONTHS_GENITIVE[Number(currentYm.slice(5, 7)) - 1]}: ${formatAmount(spent)} ${CURRENCY} (${percent}%)`,
      progressBar(percent)
    );
    if (percent >= 100) lines.push("", "🚨 Бюджет вичерпано!");
    else if (percent >= 80) lines.push("", "⚠️ Близько до ліміту!");
    else lines.push("", `Залишилось: ${formatAmount(Math.max(0, budget - spent))} ${CURRENCY}`);
    buttons.push([{ text: "✏️ Змінити ліміт", callback_data: "budget_set" }]);
    buttons.push([{ text: "🗑 Прибрати бюджет", callback_data: "budget_clear" }]);
  } else {
    lines.push(
      "Бюджет ще не встановлено.",
      "",
      `Витрачено у ${MONTHS_GENITIVE[Number(currentYm.slice(5, 7)) - 1]}: ${formatAmount(spent)} ${CURRENCY}`,
      "",
      "Встанови ліміт — і я попереджу, коли витрати наблизяться до нього."
    );
    buttons.push([{ text: "💰 Встановити бюджет", callback_data: "budget_set" }]);
  }
  console.log("[BUDGET]", { user_id: userId, month: monthName, spent, budget });
  await sendServiceMessage(env, chatId, userId, lines.join("\n"), { inline_keyboard: buttons });
}

async function getActiveUsers(db) {
  const rows = await db.prepare(
    `SELECT user_id, chat_id, access_until, status
     FROM users
     WHERE status != 'blocked' AND chat_id IS NOT NULL AND chat_id != ''`
  ).all();
  return (rows.results || []).filter((user) => hasActiveAccess(user));
}

async function sendWeeklyReports(env) {
  const users = await getActiveUsers(env.DB);
  const range = getPeriodRange("week");
  for (const user of users) {
    try {
      const report = await buildPeriodReport(env.DB, user.user_id, range, "📬 Твій тижневий звіт");
      if (!report) continue;
      // Якір-авторемонт: звіт не видаляється, тож раз на тиждень відновлює клавіатуру.
      await sendMessage(env, user.chat_id, report, MAIN_KEYBOARD, true);
    } catch (error) {
      console.log("[CRON_ERROR]", { user_id: user.user_id, error: String(error) });
    }
  }
}

async function sendMonthlyReports(env) {
  const today = parseDate(kyivNow().date);
  const prev = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth() - 1, 1));
  const prevYm = `${prev.getUTCFullYear()}-${String(prev.getUTCMonth() + 1).padStart(2, "0")}`;
  const range = getMonthRange(prevYm);
  const users = await getActiveUsers(env.DB);
  for (const user of users) {
    try {
      const report = await buildPeriodReport(env.DB, user.user_id, range, "📬 Звіт за місяць");
      if (!report) continue;
      const categories = await getCategoryTotals(env.DB, user.user_id, range);
      await sendMessage(env, user.chat_id, report, categoryDetailsKeyboard(categories, `month:${prevYm}`), true);
    } catch (error) {
      console.log("[CRON_ERROR]", { user_id: user.user_id, error: String(error) });
    }
  }
}

async function getCategoryTotals(db, userId, range) {
  const rows = await db.prepare(
    `SELECT category, SUM(amount) AS total
     FROM expenses
     WHERE user_id = ? AND expense_date >= ? AND expense_date < ?
     GROUP BY category
     ORDER BY total DESC`
  ).bind(userId, range.from, range.to).all();
  return rows.results || [];
}

async function buildPeriodReport(db, userId, range, title) {
  const categories = await getCategoryTotals(db, userId, range);
  if (!categories.length) return null;

  const summary = await db.prepare(
    `SELECT
       COALESCE(SUM(amount), 0) AS total,
       COALESCE(SUM(CASE WHEN expense_type = 'emotional' THEN amount ELSE 0 END), 0) AS emotional
     FROM expenses
     WHERE user_id = ? AND expense_date >= ? AND expense_date < ?`
  ).bind(userId, range.from, range.to).first();

  const total = Number(summary?.total || 0);
  const emotional = Number(summary?.emotional || 0);
  const emotionalShare = total > 0 ? Math.round((emotional / total) * 100) : 0;

  const lines = [
    `${title} • ${range.label}`,
    "",
    `💸 Всього: ${formatAmount(total)} ${CURRENCY}`,
    "",
    "📁 По категоріях:"
  ];
  for (const row of categories) {
    const share = total > 0 ? Math.round((Number(row.total) / total) * 100) : 0;
    lines.push(`• ${formatCategory(row.category)} — ${formatAmount(row.total)} ${CURRENCY} (${share}%)`);
  }
  lines.push("", `🔥 Емоційні: ${formatAmount(emotional)} ${CURRENCY} (${emotionalShare}%)`);
  if (emotionalShare > 30) lines.push("⚠️ Емоційні витрати перевищують 30%!");

  const budget = await budgetWarning(db, userId, range.from);
  if (budget) lines.push("", budget);
  return lines.join("\n");
}

async function sendAccessReminders(env) {
  const rows = await env.DB.prepare(
    `SELECT user_id, chat_id, access_until
     FROM users
     WHERE status != 'blocked' AND access_until IS NOT NULL AND chat_id IS NOT NULL AND chat_id != ''`
  ).all();
  const today = parseDate(kyivNow().date);
  for (const user of rows.results || []) {
    try {
      const end = parseDate(String(user.access_until).slice(0, 10));
      const daysLeft = Math.round((end.getTime() - today.getTime()) / 86400000);
      if (daysLeft !== 3 && daysLeft !== 1) continue;
      const when = daysLeft === 1 ? "завтра" : `${formatHumanDate(user.access_until)}`;
      await sendMessage(
        env, user.chat_id,
        `⏳ Твій доступ закінчується ${when}.\n\nПродовж зараз, щоб не втратити статистику і звіти 👇`,
        paymentKeyboard()
      );
      console.log("[CRON]", { action: "access_reminder", user_id: user.user_id, days_left: daysLeft });
    } catch (error) {
      console.log("[CRON_ERROR]", { user_id: user.user_id, error: String(error) });
    }
  }
}

async function insertExpense(db, expense) {
  const now = kyivNow();
  const title = cleanExpenseTitle(expense.expense_title);
  const category = expense.category || detectCategory(title);
  const expenseDate = expense.expense_date || now.date;
  console.log("[DB]", {
    action: "save_expense",
    user_id: expense.user_id,
    raw_text: expense.expense_title,
    expense_title: title,
    amount: expense.amount,
    category,
    expense_type: expense.expense_type,
    expense_date: expenseDate
  });
  const result = await db.prepare(
    `INSERT INTO expenses
     (user_id, chat_id, expense_title, amount, category, expense_type, created_at, expense_date)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
  ).bind(
    expense.user_id,
    expense.chat_id,
    title,
    Number(expense.amount),
    category,
    expense.expense_type,
    now.datetime,
    expenseDate
  ).run();
  return Number(result.meta?.last_row_id || 0);
}

async function getExpenseDates(db, userId, limit = 10) {
  const rows = await db.prepare(
    `SELECT expense_date, COUNT(*) AS cnt, SUM(amount) AS total
     FROM expenses
     WHERE user_id = ?
     GROUP BY expense_date
     ORDER BY expense_date DESC
     LIMIT ?`
  ).bind(userId, limit).all();
  return rows.results || [];
}

async function getExpensesByDate(db, userId, date) {
  const rows = await db.prepare(
    `SELECT id, expense_title, amount, category, expense_type, expense_date
     FROM expenses
     WHERE user_id = ? AND expense_date = ?
     ORDER BY id DESC
     LIMIT 30`
  ).bind(userId, date).all();
  return rows.results || [];
}

async function sendManageDates(env, chatId, userId, mode) {
  const dates = await getExpenseDates(env.DB, userId);
  if (!dates.length) {
    await sendServiceMessage(env, chatId, userId, "Витрат поки немає");
    return;
  }
  const title = mode === "edit" ? "✏️ Редагування" : "🗑 Видалення";
  await sendServiceMessage(env, chatId, userId, `${title}\n\nОбери день:`, manageDatesKeyboard(dates, mode));
}

async function showManageDates(env, chatId, messageId, userId, mode) {
  const dates = await getExpenseDates(env.DB, userId);
  if (!dates.length) {
    await editMessage(env, chatId, messageId, "Витрат поки немає");
    return;
  }
  const title = mode === "edit" ? "✏️ Редагування" : "🗑 Видалення";
  await editMessage(env, chatId, messageId, `${title}\n\nОбери день:`, manageDatesKeyboard(dates, mode));
}

async function showManageDay(env, chatId, messageId, userId, mode, date) {
  const expenses = await getExpensesByDate(env.DB, userId, date);
  if (!expenses.length) {
    await showManageDates(env, chatId, messageId, userId, mode);
    return;
  }
  const action = mode === "edit" ? "Обери витрату для редагування:" : "Обери витрату для видалення:";
  const text = [
    `📅 ${formatShortDate(parseDate(date))}`,
    "",
    action,
    "",
    ...expenses.map((expense, index) =>
      `${index + 1}. ${capitalize(expense.expense_title)} — ${formatAmount(expense.amount)} ${CURRENCY}`
    )
  ].join("\n");
  await editMessage(env, chatId, messageId, text, manageDayKeyboard(expenses, mode));
}

function manageDatesKeyboard(dates, mode) {
  const buttons = dates.map((row) => [{
    text: `${formatShortDate(parseDate(row.expense_date))} • ${formatAmount(row.total)} ${CURRENCY} • ${pluralExpenses(row.cnt)}`,
    callback_data: `manage_day:${mode}:${row.expense_date}`
  }]);
  return { inline_keyboard: buttons };
}

function manageDayKeyboard(expenses, mode) {
  const prefix = mode === "edit" ? "manage_edit" : "manage_delete";
  const icon = mode === "edit" ? "✏️" : "🗑";
  const rows = [];
  for (let i = 0; i < expenses.length; i += 5) {
    rows.push(expenses.slice(i, i + 5).map((expense, j) => ({
      text: `${icon} ${i + j + 1}`,
      callback_data: `${prefix}:${expense.id}`
    })));
  }
  rows.push([{ text: "⬅️ Назад", callback_data: `manage_dates:${mode}` }]);
  return { inline_keyboard: rows };
}

function pluralExpenses(count) {
  const n = Number(count);
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return `${n} витрата`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return `${n} витрати`;
  return `${n} витрат`;
}

async function getExpenseById(db, userId, expenseId) {
  return db.prepare(
    `SELECT id, expense_title, amount, category, expense_type, expense_date
     FROM expenses
     WHERE user_id = ? AND id = ?`
  ).bind(userId, expenseId).first();
}

async function updateExpense(db, userId, expenseId, title, amount, category, date) {
  const cleanTitle = cleanExpenseTitle(title);
  const newCategory = category || detectCategory(cleanTitle);
  const result = date
    ? await db.prepare(
        `UPDATE expenses
         SET expense_title = ?, amount = ?, category = ?, expense_date = ?
         WHERE user_id = ? AND id = ?`
      ).bind(cleanTitle, Number(amount), newCategory, date, userId, expenseId).run()
    : await db.prepare(
        `UPDATE expenses
         SET expense_title = ?, amount = ?, category = ?
         WHERE user_id = ? AND id = ?`
      ).bind(cleanTitle, Number(amount), newCategory, userId, expenseId).run();
  console.log("[DB]", {
    action: "update_expense",
    user_id: userId,
    expense_id: expenseId,
    expense_title: cleanTitle,
    amount: Number(amount)
  });
  return Number(result.meta?.changes || 0) > 0;
}

async function deleteExpense(db, userId, expenseId) {
  const result = await db.prepare(
    `DELETE FROM expenses
     WHERE user_id = ? AND id = ?`
  ).bind(userId, expenseId).run();
  console.log("[DB]", { action: "delete_expense", user_id: userId, expense_id: expenseId });
  return Number(result.meta?.changes || 0) > 0;
}

async function showCustomStats(env, chatId, messageId, userId, range) {
  const rows = await env.DB.prepare(
    `SELECT category, SUM(amount) AS total
     FROM expenses
     WHERE user_id = ? AND expense_date >= ? AND expense_date <= ?
     GROUP BY category
     ORDER BY total DESC`
  ).bind(userId, range.from, range.to).all();

  const summary = await env.DB.prepare(
    `SELECT
       COALESCE(SUM(amount), 0) AS total,
       COALESCE(SUM(CASE WHEN expense_type = 'emotional' THEN amount ELSE 0 END), 0) AS emotional,
       COUNT(*) AS rows_count
     FROM expenses
     WHERE user_id = ? AND expense_date >= ? AND expense_date <= ?`
  ).bind(userId, range.from, range.to).first();

  console.log("[DB]", {
    action: "get_custom_stats",
    user_id: userId,
    date_from: range.from,
    date_to: range.to,
    rows_count: summary?.rows_count || 0
  });

  const categories = rows.results || [];
  const text = formatCustomStatsMessage(range.label, Number(summary?.total || 0), Number(summary?.emotional || 0), categories);
  const replyMarkup = categories.length ? customCategoryDetailsKeyboard(categories) : undefined;
  await saveLastStatsRange(env.DB, userId, range);

  if (messageId) {
    await editMessage(env, chatId, messageId, text, replyMarkup || { inline_keyboard: [] });
    return;
  }
  await sendServiceMessage(env, chatId, userId, text, replyMarkup);
}

async function showStats(env, chatId, messageId, userId, range, scope) {
  const rows = await env.DB.prepare(
    `SELECT category, SUM(amount) AS total
     FROM expenses
     WHERE user_id = ? AND expense_date >= ? AND expense_date < ?
     GROUP BY category
     ORDER BY total DESC`
  ).bind(userId, range.from, range.to).all();

  const summary = await env.DB.prepare(
    `SELECT
       COALESCE(SUM(amount), 0) AS total,
       COALESCE(SUM(CASE WHEN expense_type = 'emotional' THEN amount ELSE 0 END), 0) AS emotional,
       COUNT(*) AS rows_count
     FROM expenses
     WHERE user_id = ? AND expense_date >= ? AND expense_date < ?`
  ).bind(userId, range.from, range.to).first();

  console.log("[DB]", {
    action: "get_stats",
    user_id: userId,
    period: scope,
    date_from: range.from,
    date_to: range.to,
    rows_count: summary?.rows_count || 0
  });

  const categories = rows.results || [];
  let text = formatStatsMessage(range.label, Number(summary?.total || 0), Number(summary?.emotional || 0), categories);

  const currentYm = kyivNow().date.slice(0, 7);
  if (scope === `month:${currentYm}` && categories.length) {
    const budget = await budgetWarning(env.DB, userId, range.from);
    if (budget) text += `\n\n${budget}`;
  }
  if (categories.length) {
    text += "\n\nНатисни категорію, щоб побачити деталі 👇";
  }

  await editMessage(env, chatId, messageId, text, categoryDetailsKeyboard(categories, scope));
}

async function showCategoryDetails(env, chatId, messageId, userId, detail) {
  const range = detailToRange(detail);
  const rows = await env.DB.prepare(
    `SELECT expense_title, SUM(amount) AS total, COUNT(*) AS cnt
     FROM expenses
     WHERE user_id = ? AND category = ? AND expense_date >= ? AND expense_date < ?
     GROUP BY expense_title
     ORDER BY total DESC`
  ).bind(userId, detail.category, range.from, range.to).all();

  const items = (rows.results || []).map((row) => ({
    title: cleanExpenseTitle(row.expense_title),
    total: Number(row.total || 0),
    cnt: Number(row.cnt || 0)
  }));
  const total = items.reduce((sum, item) => sum + item.total, 0);

  console.log("[DB]", {
    action: "category_details",
    user_id: userId,
    category: detail.category,
    period: detail.scope,
    rows_count: items.length
  });

  const backData = detail.scope === "month" ? `stats_month:${detail.month}` : `stats:${detail.scope}`;
  await editMessage(env, chatId, messageId, formatCategoryDetails(detail.category, range.label, total, items), {
    inline_keyboard: [[{ text: "⬅️ Назад", callback_data: backData }]]
  });
}

async function showCustomCategoryDetails(env, chatId, messageId, userId, category, range) {
  const rows = await env.DB.prepare(
    `SELECT expense_title, amount
     FROM expenses
     WHERE user_id = ? AND category = ? AND expense_date >= ? AND expense_date <= ?
     ORDER BY expense_date DESC, id DESC`
  ).bind(userId, category, range.from, range.to).all();

  const items = (rows.results || []).map((row) => ({
    title: cleanExpenseTitle(row.expense_title),
    amount: Number(row.amount || 0)
  }));
  const total = items.reduce((sum, item) => sum + item.amount, 0);

  console.log("[DB]", {
    action: "custom_category_details",
    user_id: userId,
    category,
    date_from: range.from,
    date_to: range.to,
    rows_count: items.length
  });

  await saveLastStatsRange(env.DB, userId, range);
  await editMessage(env, chatId, messageId, formatCustomCategoryDetails(category, total, items), {
    inline_keyboard: [[{ text: "⬅️ Назад", callback_data: "stats_custom_back" }]]
  });
}

function formatStatsMessage(label, total, emotional, categories) {
  const lines = [`📊 ${label}`, ""];
  if (!categories.length) {
    lines.push("За цей період витрат немає.");
    return lines.join("\n");
  }
  lines.push(`💸 Всього: ${formatAmount(total)} ${CURRENCY}`, "", "📁 По категоріях:");
  for (const row of categories) {
    const share = total > 0 ? Math.round((Number(row.total) / total) * 100) : 0;
    lines.push(`• ${formatCategory(row.category)} — ${formatAmount(row.total)} ${CURRENCY} (${share}%)`);
  }
  const emotionalShare = total > 0 ? Math.round((emotional / total) * 100) : 0;
  lines.push("", `🔥 Емоційні: ${formatAmount(emotional)} ${CURRENCY} (${emotionalShare}%)`);
  if (emotionalShare > 30) {
    lines.push("⚠️ Емоційні витрати перевищують 30% — звернути увагу!");
  }
  return lines.join("\n");
}

function formatCustomStatsMessage(label, total, emotional, categories) {
  const lines = [`📊 Період ${label}`, "", "💸 Всього:", `${formatAmount(total)} ${CURRENCY}`, ""];
  if (!categories.length) {
    lines.push("Емоційні:", `${formatAmount(emotional)} ${CURRENCY}`);
    return lines.join("\n");
  }

  lines.push("📁 Категорії:");
  for (const row of categories) {
    const categoryTotal = Number(row.total || 0);
    const share = total > 0 ? Math.round((categoryTotal / total) * 100) : 0;
    lines.push(`• ${formatCategory(row.category)} — ${formatAmount(categoryTotal)} ${CURRENCY} • ${share}%`);
  }

  const emotionalShare = total > 0 ? Math.round((emotional / total) * 100) : 0;
  lines.push("", "Емоційні:", `${formatAmount(emotional)} ${CURRENCY} • ${emotionalShare}%`);
  return lines.join("\n");
}

function formatCategoryDetails(category, periodLabel, total, items) {
  const lines = [
    `${formatCategory(category)} • ${periodLabel}`,
    "",
    `💰 Разом: ${formatAmount(total)} ${CURRENCY}`,
    ""
  ];
  if (!items.length) {
    lines.push("Даних немає");
    return lines.join("\n");
  }
  for (const item of items.slice(0, 25)) {
    const suffix = item.cnt > 1 ? ` (${item.cnt}×)` : "";
    lines.push(`• ${capitalize(item.title)} — ${formatAmount(item.total)} ${CURRENCY}${suffix}`);
  }
  if (items.length > 25) {
    lines.push(`… та ще ${items.length - 25}`);
  }
  return lines.join("\n");
}

function formatCustomCategoryDetails(category, total, items) {
  const lines = [
    formatCategory(category),
    "",
    `💰 Разом: ${formatAmount(total)} ${CURRENCY}`,
    ""
  ];
  if (!items.length) {
    lines.push("Даних немає");
    return lines.join("\n");
  }
  for (const item of items.slice(0, 30)) {
    lines.push(`• ${capitalize(item.title)} — ${formatAmount(item.amount)} ${CURRENCY}`);
  }
  if (items.length > 30) {
    lines.push(`… та ще ${items.length - 30}`);
  }
  return lines.join("\n");
}

function getPeriodRange(period) {
  const now = kyivNow();
  const today = parseDate(now.date);
  if (period === "today") return { label: `Сьогодні ${formatShortDate(today)}`, from: formatDate(today), to: formatDate(addDays(today, 1)) };
  if (period === "yesterday") {
    const y = addDays(today, -1);
    return { label: `Вчора ${formatShortDate(y)}`, from: formatDate(y), to: formatDate(today) };
  }
  if (period === "week") {
    const start = startOfWeek(today);
    const end = addDays(start, 7);
    return { label: `Тиждень ${formatShortDate(start)}–${formatShortDate(addDays(end, -1))}`, from: formatDate(start), to: formatDate(end) };
  }
  if (period === "year") {
    const start = new Date(Date.UTC(today.getUTCFullYear(), 0, 1));
    const end = new Date(Date.UTC(today.getUTCFullYear() + 1, 0, 1));
    return { label: `Рік ${today.getUTCFullYear()}`, from: formatDate(start), to: formatDate(end) };
  }
  return getMonthRange(`${today.getUTCFullYear()}-${String(today.getUTCMonth() + 1).padStart(2, "0")}`);
}

function getMonthRange(monthValue) {
  const [year, month] = monthValue.split("-").map(Number);
  const start = new Date(Date.UTC(year, month - 1, 1));
  const end = new Date(Date.UTC(year, month, 1));
  return {
    label: `Місяць ${MONTHS[month - 1]} ${year}`,
    from: formatDate(start),
    to: formatDate(end)
  };
}

function parseStatsPeriodInput(text) {
  const value = String(text || "")
    .trim()
    .replace(/[–—]/g, "-")
    .replace(/\s+/g, "");
  if (!value) return null;

  const parts = value.split("-");
  if (parts.length > 2 || parts.some((part) => !part)) return null;

  const currentYear = parseDate(kyivNow().date).getUTCFullYear();
  const from = parseStatsDatePart(parts[0], currentYear);
  const to = parseStatsDatePart(parts[1] || parts[0], currentYear);
  if (!from || !to || from.getTime() > to.getTime()) return null;

  return {
    label: `${formatShortDate(from)}–${formatShortDate(to)}`,
    from: formatDate(from),
    to: formatDate(to)
  };
}

function parseStatsDatePart(value, fallbackYear) {
  const match = /^(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?$/.exec(value);
  if (!match) return null;

  const day = Number(match[1]);
  const month = Number(match[2]);
  const year = match[3] ? Number(match[3]) : fallbackYear;
  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    return null;
  }
  return date;
}

function detailToRange(detail) {
  if (detail.scope === "month") return getMonthRange(detail.month);
  return getPeriodRange(detail.scope);
}

function parseDetailCallback(data) {
  const parts = data.split(":");
  if (parts[1] === "month") {
    return { scope: "month", month: parts[2], category: parts[3] };
  }
  return { scope: parts[1], category: parts[2] };
}

async function monthKeyboard(db, userId) {
  const rows = await db.prepare(
    `SELECT DISTINCT substr(expense_date, 1, 7) AS month
     FROM expenses
     WHERE user_id = ?
     ORDER BY month DESC
     LIMIT 12`
  ).bind(userId).all();
  const buttons = (rows.results || []).map((row) => {
    const [year, month] = row.month.split("-").map(Number);
    return [{ text: `${MONTHS[month - 1]} ${year}`, callback_data: `stats_month:${row.month}` }];
  });
  buttons.push([{ text: "⬅️ Назад", callback_data: "stats_back" }]);
  return { inline_keyboard: buttons };
}

function statsKeyboard() {
  return {
    inline_keyboard: [
      [{ text: "Сьогодні", callback_data: "stats:today" }, { text: "Вчора", callback_data: "stats:yesterday" }],
      [{ text: "Тиждень", callback_data: "stats:week" }, { text: "Місяць", callback_data: "stats:month" }],
      [{ text: "Рік", callback_data: "stats:year" }],
      [{ text: "📅 Обрати період", callback_data: "stats:custom" }],
      [{ text: "⬅️ Назад", callback_data: "stats_main_back" }]
    ]
  };
}

function categoryDetailsKeyboard(categories, scope) {
  const buttons = categories.map((row) => {
    const data = scope.startsWith("month:")
      ? `stats_detail:month:${scope.slice(6)}:${row.category}`
      : `stats_detail:${scope}:${row.category}`;
    return { text: formatCategory(row.category), callback_data: data };
  });
  const rows = [];
  for (let i = 0; i < buttons.length; i += 2) {
    rows.push(buttons.slice(i, i + 2));
  }
  rows.push([{ text: "⬅️ Назад", callback_data: "stats_back" }]);
  return { inline_keyboard: rows };
}

function customCategoryDetailsKeyboard(categories) {
  const buttons = categories.map((row) => ({
    text: `Детальніше: ${formatCategory(row.category)}`,
    callback_data: `stats_detail_custom:${row.category}`
  }));
  const rows = [];
  for (let i = 0; i < buttons.length; i += 2) {
    rows.push(buttons.slice(i, i + 2));
  }
  rows.push([{ text: "⬅️ Назад", callback_data: "stats_back" }]);
  return { inline_keyboard: rows };
}

function addExpenseHelpKeyboard(showExamples = false) {
  const rows = [[{ text: "⚡ Швидкий вибір категорії", callback_data: "add_quick" }]];
  if (showExamples) rows.push([{ text: "❓ Приклади", callback_data: "add_examples" }]);
  return { inline_keyboard: rows };
}

function examplesKeyboard() {
  return { inline_keyboard: [[{ text: "❓ Приклади", callback_data: "add_examples" }]] };
}

async function userHasExpenses(db, userId) {
  const row = await db.prepare("SELECT 1 AS one FROM expenses WHERE user_id = ? LIMIT 1").bind(userId).first();
  return Boolean(row);
}

function quickCategoryKeyboard() {
  return {
    inline_keyboard: [
      [{ text: "🍔 Їжа", callback_data: "quick_cat:food" }, { text: "🚕 Транспорт", callback_data: "quick_cat:transport" }],
      [{ text: "🛍 Покупки", callback_data: "quick_cat:shopping" }, { text: "🏠 Дім", callback_data: "quick_cat:home" }],
      [{ text: "💊 Здоров’я", callback_data: "quick_cat:health" }, { text: "👶 Діти", callback_data: "quick_cat:kids" }],
      [{ text: "📚 Навчання", callback_data: "quick_cat:education" }, { text: "🎮 Розваги", callback_data: "quick_cat:fun" }],
      [{ text: "⬅️ Назад", callback_data: "quick_categories_back" }]
    ]
  };
}

function quickSubcategoryKeyboard(category) {
  const items = SUBCATEGORIES[category] || [];
  const rows = [];
  for (let i = 0; i < items.length; i += 2) {
    rows.push(items.slice(i, i + 2).map(([key, label]) => ({ text: label, callback_data: `quick_sub:${category}:${key}` })));
  }
  rows.push([{ text: "⬅️ Назад", callback_data: "add_quick" }]);
  return { inline_keyboard: rows };
}

function paymentKeyboard() {
  const rows = TARIFFS.map((tariff) => [
    { text: `${tariff.price} грн — ${tariff.label}`, callback_data: `buy_${tariff.days}` }
  ]);
  rows.push([{ text: "✅ Я оплатив", callback_data: "paid" }]);
  return { inline_keyboard: rows };
}

function paidKeyboard(days) {
  return { inline_keyboard: [[{ text: "✅ Я оплатив", callback_data: `paid_${days}` }]] };
}

function manageExpensesText() {
  return "Що хочеш зробити?";
}

function manageExpensesKeyboard() {
  return {
    inline_keyboard: [
      [{ text: "✏️ Редагувати витрату", callback_data: "manage_dates:edit" }],
      [{ text: "🗑 Видалити витрату", callback_data: "manage_dates:delete" }]
    ]
  };
}

function adminKeyboard() {
  return {
    inline_keyboard: [
      [{ text: "👥 Користувачі", callback_data: "admin:users" }],
      [{ text: "💳 Оплати", callback_data: "admin:payments" }],
      [{ text: "⏳ Доступи", callback_data: "admin:access" }],
      [{ text: "🚫 Заблоковані", callback_data: "admin:blocked" }]
    ]
  };
}

async function ensureAccess(env, userId, chatId, callbackData = "") {
  if (isAdmin(env, userId)) return true;
  const user = await getUser(env.DB, userId);
  if (user?.status === "blocked") {
    await sendMessage(env, chatId, "Доступ обмежено", undefined, true);
    return false;
  }
  if (callbackData.startsWith("buy_") || callbackData.startsWith("paid")) return true;
  if (hasActiveAccess(user)) return true;
  if (user?.access_until) {
    await env.DB.prepare("UPDATE users SET status = 'expired' WHERE user_id = ? AND status != 'blocked'").bind(userId).run();
  }
  await sendMessage(env, chatId, await paywallText(env, user), paymentKeyboard(), true);
  return false;
}

function isAdmin(env, userId) {
  return parseIds(env.ADMIN_USER_IDS).includes(String(userId));
}

function hasActiveAccess(user) {
  if (!user?.access_until) return false;
  return new Date(user.access_until.replace(" ", "T")).getTime() > Date.now();
}

// Оплата приймається лише на банку — тільки її поповнення емітить mono-webhook
// (приват і mono-картку не показуємо).
function jarPayLine(env) {
  return env.MONO_JAR_LINK ? `Банка: ${env.MONO_JAR_LINK}` : "Банка: (посилання не задано)";
}

// Єдиний блок тарифів — використовується і в paywall, і в «Мій доступ»,
// щоб не було двох різних версій тексту.
function tariffBlock(env, pending) {
  const payTarget = jarPayLine(env);
  const lines = [
    "💳 Тарифи:",
    ...TARIFFS.map((tariff) => `${tariff.price} грн — ${tariff.label}`),
    "",
    "Що входить:",
    "• необмежені витрати",
    "• статистика і бюджет",
    "• тижневі та місячні звіти",
    "",
    "Як платити:",
    payTarget
  ];
  if (pending?.code) {
    lines.push(
      "",
      `❗ Твій код: ${pending.code}`,
      `Сума: ${Number(pending.amount)} грн (${Number(pending.tariff_days)} днів)`,
      "Вкажи код у коментарі до переказу."
    );
  } else {
    lines.push("", "Обери тариф нижче — я дам код платежу, який треба вказати в коментарі до переказу.");
  }
  return lines.join("\n");
}

async function paywallText(env, user) {
  const pending = await getPendingPayment(env.DB, String(user?.user_id || ""));
  const expired = user?.access_until && !hasActiveAccess(user);
  const intro = expired
    ? "Доступ закінчився ⏳\n\nЩоб знову бачити статистику витрат, продовжи доступ 👇"
    : "Доступ до бота платний 👇";
  return `${intro}\n\n${tariffBlock(env, pending)}`;
}

function accessDaysLeft(user) {
  if (!user?.access_until) return 0;
  const end = parseDate(String(user.access_until).slice(0, 10));
  const today = parseDate(kyivNow().date);
  return Math.max(0, Math.round((end.getTime() - today.getTime()) / 86400000));
}

function tariffLabel(tariff) {
  if (tariff === "trial") return "пробний";
  const match = /^(\d+)_days$/.exec(String(tariff || ""));
  if (match) {
    const days = Number(match[1]);
    return TARIFF_BY_DAYS.get(days)?.label || `${days} днів`;
  }
  return tariff || "—";
}

// Екран «Мій доступ»: службове повідомлення, вигляд залежить від статусу юзера.
async function sendAccessView(env, chatId, userId) {
  const user = await getUser(env.DB, userId);
  const pending = await getPendingPayment(env.DB, userId);

  if (hasActiveAccess(user) && user?.status === "trial") {
    const text = [
      "🎁 Безкоштовний тиждень",
      "",
      `Залишилось: ${accessDaysLeft(user)} дн`,
      `Діє до: ${formatHumanDate(user.access_until)}`,
      "",
      tariffBlock(env, pending)
    ].join("\n");
    await sendServiceMessage(env, chatId, userId, text, paymentKeyboard());
    return;
  }

  if (hasActiveAccess(user)) {
    const text = [
      "💳 Доступ активний ✅",
      "",
      `Діє до: ${formatHumanDate(user.access_until)}`,
      `Залишилось: ${accessDaysLeft(user)} дн`,
      `Тариф: ${tariffLabel(user.tariff)}`
    ].join("\n");
    await sendServiceMessage(env, chatId, userId, text, {
      inline_keyboard: [[{ text: "💳 Продовжити доступ", callback_data: "access_extend" }]]
    });
    return;
  }

  const intro = user?.access_until ? "Доступ закінчився ⏳" : "Доступ ще не активний";
  await sendServiceMessage(env, chatId, userId, `${intro}\n\n${tariffBlock(env, pending)}`, paymentKeyboard());
}

function paymentText(env, tariff, code) {
  const lines = [
    "Для оплати:",
    "",
    jarPayLine(env),
    "",
    `Тариф: ${tariff.label} — ${tariff.price} грн`
  ];
  if (code) {
    lines.push("", `❗ Вкажи код ${code} у коментарі до переказу —`, "так я впізнаю саме твою оплату.");
  }
  lines.push("", "Після оплати натисни «✅ Я оплатив»");
  return lines.join("\n");
}

// Продовжує доступ юзеру на days днів від поточного кінця (або від сьогодні).
async function grantAccess(env, targetUserId, days, adminId) {
  const targetUser = await getUser(env.DB, targetUserId);
  const currentEnd = targetUser?.access_until && hasActiveAccess(targetUser)
    ? parseDate(String(targetUser.access_until).slice(0, 10))
    : parseDate(kyivNow().date);
  const until = addDays(currentEnd, days);
  const accessUntil = `${formatDate(until)} 23:59:59`;
  await env.DB.prepare(
    "UPDATE users SET access_until = ?, tariff = ?, status = 'active' WHERE user_id = ?"
  ).bind(accessUntil, `${days}_days`, targetUserId).run();
  console.log("[PAYMENT]", { user_id: targetUserId, tariff_days: days, status: "paid", admin_id: adminId });
  return accessUntil;
}

async function handleAdminPaymentAction(env, callback, data) {
  const adminId = String(callback.from?.id || "");
  if (!isAdmin(env, adminId)) return;
  const adminChatId = String(callback.message?.chat?.id || "");
  const adminMsgId = callback.message?.message_id;

  // Новий формат: дія по конкретному payments.id.
  if (data.startsWith("paycfm_") || data.startsWith("payrej_")) {
    const paymentId = Number(data.split("_")[1]);
    const payment = await env.DB.prepare(
      "SELECT id, user_id, amount, tariff_days, status FROM payments WHERE id = ?"
    ).bind(paymentId).first();
    if (!payment) {
      await editMessage(env, adminChatId, adminMsgId, "Заявку не знайдено");
      return;
    }
    const targetUserId = String(payment.user_id);
    if (payment.status !== "pending") {
      // Захист від подвійного тапу: заявку вже підтвердили/відхилили.
      await editMessage(env, adminChatId, adminMsgId, `Заявку вже оброблено (${payment.status})`);
      return;
    }
    if (data.startsWith("payrej_")) {
      await env.DB.prepare("UPDATE payments SET status = 'rejected', comment = ? WHERE id = ?")
        .bind(`admin ${adminId}`, paymentId).run();
      console.log("[PAYMENT]", { payment_id: paymentId, user_id: targetUserId, status: "rejected" });
      await sendMessage(env, targetUserId, "Не знайшов оплату 😔\nПеревір ще раз або напиши мені", paymentKeyboard(), true);
      await editMessage(env, adminChatId, adminMsgId, `❌ Відхилено (user ${targetUserId})`);
      return;
    }
    // Confirm фіксує саме той тариф і суму, що в заявці.
    const days = Number(payment.tariff_days);
    const accessUntil = await grantAccess(env, targetUserId, days, adminId);
    await env.DB.prepare("UPDATE payments SET status = 'paid', paid_at = ?, comment = ? WHERE id = ?")
      .bind(kyivNow().datetime, `admin ${adminId}`, paymentId).run();
    await sendMessage(env, targetUserId, `Доступ відкрито 🚀\n\nДо: ${formatHumanDate(accessUntil)}`, MAIN_KEYBOARD, true);
    await editMessage(env, adminChatId, adminMsgId, `✅ Підтверджено ${days} дн / ${Number(payment.amount)} грн (user ${targetUserId})`);
    return;
  }

  // Старий формат (fallback для повідомлень, надісланих до цього оновлення).
  const parts = data.split("_");
  if (parts[0] === "reject") {
    const targetUserId = parts[1];
    await env.DB.prepare(
      "UPDATE payments SET status = 'rejected', comment = ? WHERE user_id = ? AND status = 'pending'"
    ).bind("admin rejected", targetUserId).run();
    console.log("[PAYMENT]", { user_id: targetUserId, status: "rejected" });
    await sendMessage(env, targetUserId, "Не знайшов оплату 😔\nПеревір ще раз або напиши мені", paymentKeyboard(), true);
    return;
  }

  const days = Number(parts[1]);
  const targetUserId = parts[2];
  const accessUntil = await grantAccess(env, targetUserId, days, adminId);
  await env.DB.prepare(
    "UPDATE payments SET status = 'paid', paid_at = ?, comment = ? WHERE user_id = ? AND status = 'pending'"
  ).bind(kyivNow().datetime, `admin ${adminId}`, targetUserId).run();
  await sendMessage(env, targetUserId, `Доступ відкрито 🚀\n\nДо: ${formatHumanDate(accessUntil)}`, MAIN_KEYBOARD, true);
}

async function getPendingPayment(db, userId) {
  return db.prepare(
    "SELECT id, amount, tariff_days, code FROM payments WHERE user_id = ? AND status = 'pending' ORDER BY id DESC LIMIT 1"
  ).bind(userId).first();
}

// Алфавіт коду платежу без схожих символів (0/O, 1/I/L).
const PAYMENT_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";

function generatePaymentCode() {
  const bytes = crypto.getRandomValues(new Uint8Array(4));
  let code = "";
  for (let i = 0; i < 4; i++) {
    code += PAYMENT_CODE_ALPHABET[bytes[i] % PAYMENT_CODE_ALPHABET.length];
  }
  return `DG-${code}`;
}

// Код, унікальний серед активних (pending) заявок — щоб матчинг по коду був однозначний.
async function generateUniquePaymentCode(db) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const code = generatePaymentCode();
    const clash = await db.prepare(
      "SELECT 1 AS one FROM payments WHERE code = ? AND status = 'pending' LIMIT 1"
    ).bind(code).first();
    if (!clash) return code;
  }
  return generatePaymentCode();
}

async function createPayment(db, userId, amount, tariffDays, status) {
  const code = await generateUniquePaymentCode(db);
  await db.prepare(
    "INSERT INTO payments (user_id, amount, tariff_days, status, created_at, comment, code) VALUES (?, ?, ?, ?, ?, ?, ?)"
  ).bind(userId, amount, tariffDays, status, kyivNow().datetime, null, code).run();
  console.log("[PAYMENT]", { user_id: userId, tariff_days: tariffDays, amount, status, code });
  return code;
}

// Одна активна заявка на юзера: той самий тариф — нічого не робимо; інший —
// стару pending архівуємо як 'superseded' і створюємо нову.
async function ensurePendingPayment(db, userId, amount, tariffDays) {
  const existing = await db.prepare(
    "SELECT id, tariff_days, code FROM payments WHERE user_id = ? AND status = 'pending' ORDER BY id DESC LIMIT 1"
  ).bind(userId).first();
  if (existing && Number(existing.tariff_days) === tariffDays) return existing.code;
  if (existing) {
    await db.prepare("UPDATE payments SET status = 'superseded' WHERE user_id = ? AND status = 'pending'")
      .bind(userId).run();
  }
  return createPayment(db, userId, amount, tariffDays, "pending");
}

async function notifyAdmins(env, userId, username, payment) {
  const admins = parseIds(env.ADMIN_USER_IDS);
  const days = Number(payment.tariff_days);
  const amount = Number(payment.amount);
  for (const adminId of admins) {
    await sendMessage(env, adminId, [
      "Новий запит на доступ 💰",
      "",
      `user_id: ${userId}`,
      `username: ${username ? `@${username}` : "—"}`,
      `тариф: ${days} днів`,
      `сума: ${amount} грн`,
      `код: ${payment.code || "—"}`
    ].join("\n"), {
      inline_keyboard: [
        [{ text: `✅ Підтвердити (${days} дн / ${amount} грн)`, callback_data: `paycfm_${payment.id}` }],
        [{ text: "❌ Відхилити", callback_data: `payrej_${payment.id}` }]
      ]
    }, true);
  }
}

async function upsertUser(db, userId, chatId, telegramUser = {}, env = {}) {
  const now = kyivNow().datetime;
  const trialDays = Number(env.TRIAL_DAYS || 0);
  const trialAccessUntil = trialDays > 0 ? `${formatDate(addDays(parseDate(kyivNow().date), trialDays))} 23:59:59` : null;
  const status = trialDays > 0 ? "trial" : "active";

  await db.prepare(
    `INSERT INTO users (user_id, chat_id, username, first_name, last_name, created_at, access_until, tariff, status)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(user_id) DO UPDATE SET
       chat_id = excluded.chat_id,
       username = excluded.username,
       first_name = excluded.first_name,
       last_name = excluded.last_name`
  ).bind(
    userId,
    chatId,
    telegramUser.username || null,
    telegramUser.first_name || null,
    telegramUser.last_name || null,
    now,
    trialAccessUntil,
    trialDays > 0 ? "trial" : null,
    status
  ).run();

  await db.prepare(
    `INSERT INTO settings (user_id, timezone, currency)
     VALUES (?, 'Europe/Kyiv', 'грн')
     ON CONFLICT(user_id) DO NOTHING`
  ).bind(userId).run();

  return getUser(db, userId);
}

async function getUser(db, userId) {
  return db.prepare("SELECT * FROM users WHERE user_id = ?").bind(userId).first();
}

async function setState(db, userId, state, data) {
  await db.prepare(
    `INSERT INTO bot_state (user_id, state, data_json, updated_at)
     VALUES (?, ?, ?, ?)
     ON CONFLICT(user_id) DO UPDATE SET
       state = excluded.state,
       data_json = excluded.data_json,
       updated_at = excluded.updated_at`
  ).bind(userId, state, JSON.stringify(data || {}), kyivNow().datetime).run();
}

async function getState(db, userId) {
  const row = await db.prepare("SELECT state, data_json FROM bot_state WHERE user_id = ?").bind(userId).first();
  if (!row) return null;
  return { state: row.state, data: JSON.parse(row.data_json || "{}") };
}

async function clearState(db, userId) {
  await db.prepare("DELETE FROM bot_state WHERE user_id = ?").bind(userId).run();
}

async function saveLastStatsRange(db, userId, range) {
  await setState(db, userId, "idle", {
    last_stats_range: {
      date_from: range.from,
      date_to: range.to,
      label: range.label
    }
  });
}

async function getLastStatsRange(db, userId) {
  const state = await getState(db, userId);
  const stored = state?.data?.last_stats_range;
  if (!stored || !isIsoDate(stored.date_from) || !isIsoDate(stored.date_to) || !stored.label) {
    return null;
  }
  return {
    from: stored.date_from,
    to: stored.date_to,
    label: stored.label
  };
}

async function sendMessage(env, chatId, text, replyMarkup, silent = false) {
  return telegram(env, "sendMessage", {
    chat_id: chatId,
    text,
    reply_markup: replyMarkup,
    disable_notification: silent
  });
}

async function deleteMessage(env, chatId, messageId) {
  if (!messageId) return;
  return telegram(env, "deleteMessage", { chat_id: chatId, message_id: messageId });
}

// Службове повідомлення (меню/промпт/помилка) у юзера завжди одне: перед новим
// видаляємо попереднє. Картки витрат не трекаються — вони історія.
async function sendServiceMessage(env, chatId, userId, text, replyMarkup) {
  await deleteServiceMessage(env, userId);
  const sent = await sendMessage(env, chatId, text, replyMarkup, true);
  const messageId = Number(sent?.result?.message_id || 0);
  if (!messageId) return;
  try {
    await env.DB.prepare(
      `INSERT INTO service_messages (user_id, chat_id, message_id, updated_at)
       VALUES (?, ?, ?, ?)
       ON CONFLICT(user_id) DO UPDATE SET
         chat_id = excluded.chat_id,
         message_id = excluded.message_id,
         updated_at = excluded.updated_at`
    ).bind(userId, chatId, messageId, kyivNow().datetime).run();
  } catch (error) {
    // Без таблиці (міграцію не застосовано) поводимось як звичайний sendMessage.
    console.log("[SERVICE_MSG_ERROR]", { action: "save", error: String(error) });
  }
}

async function deleteServiceMessage(env, userId) {
  let row;
  try {
    row = await env.DB.prepare(
      "SELECT chat_id, message_id FROM service_messages WHERE user_id = ?"
    ).bind(userId).first();
  } catch (error) {
    console.log("[SERVICE_MSG_ERROR]", { action: "load", error: String(error) });
    return;
  }
  if (!row) return;
  await env.DB.prepare("DELETE FROM service_messages WHERE user_id = ?").bind(userId).run();
  // Помилка видалення не критична — юзер міг видалити повідомлення сам.
  await deleteMessage(env, row.chat_id, row.message_id);
}

// Коли трековане повідомлення видалили напряму (напр. закриття статистики) —
// просто забуваємо його id, без повторного deleteMessage.
async function forgetServiceMessage(db, userId, messageId) {
  try {
    await db.prepare("DELETE FROM service_messages WHERE user_id = ? AND message_id = ?")
      .bind(userId, messageId).run();
  } catch (error) {
    console.log("[SERVICE_MSG_ERROR]", { action: "forget", error: String(error) });
  }
}

async function editMessage(env, chatId, messageId, text, replyMarkup) {
  if (!messageId) return sendMessage(env, chatId, text, replyMarkup, true);
  return telegram(env, "editMessageText", {
    chat_id: chatId,
    message_id: messageId,
    text,
    reply_markup: replyMarkup
  });
}

async function answerCallback(env, callbackQueryId) {
  return telegram(env, "answerCallbackQuery", { callback_query_id: callbackQueryId });
}

// Повертає розпарсену відповідь Bot API (null при помилці) — так sendServiceMessage
// дістає message_id надісланого повідомлення; сирий Response ніхто не використовує.
async function telegram(env, method, payload) {
  const response = await fetch(`${TELEGRAM_API}${env.BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    console.log("[TELEGRAM_ERROR]", method, response.status, await response.text());
    return null;
  }
  return response.json().catch(() => null);
}

function startText(user) {
  const lines = [
    "Вітаю! 👋",
    "",
    "Тепер витрати будуть під контролем.",
    "",
    "Ти побачиш, куди йдуть гроші: за тиждень, місяць і рік — загалом та по категоріях.",
    "",
    "Окремо покажу емоційні витрати та чи не перевищують вони 30% від усіх витрат."
  ];
  // Подарунок бачить лише свіжий триал-юзер з активним доступом,
  // не платні й не прострочені.
  if (user?.status === "trial" && hasActiveAccess(user)) {
    lines.push(
      "",
      `🎁 Тобі відкрито безкоштовний тиждень — до ${formatHumanDate(user.access_until)}.`,
      "Все працює без обмежень, картку прив'язувати не треба."
    );
  }
  lines.push(
    "",
    "Щоб почати, натисни «➕ Додати витрату».",
    "",
    "Залишок днів і деталі доступу — у розділі «💳 Мій доступ»."
  );
  return lines.join("\n");
}

function stripEmoji(text) {
  return String(text || "").replace(/^[^\p{L}\p{N}]+/u, "").trim();
}

function capitalize(text) {
  const value = String(text || "").trim();
  return value ? value[0].toUpperCase() + value.slice(1) : value;
}

function formatCategory(category) {
  return CATEGORY_LABELS[category] || CATEGORY_LABELS.other;
}

function formatAmount(value) {
  return Number(value || 0).toLocaleString("uk-UA").replace(/\u00A0/g, " ");
}

function kyivNow() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Kyiv",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  }).formatToParts(new Date());
  const part = (type) => parts.find((item) => item.type === type)?.value;
  const date = `${part("year")}-${part("month")}-${part("day")}`;
  return { date, datetime: `${date} ${part("hour")}:${part("minute")}:${part("second")}` };
}

function parseDate(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

function formatDate(date) {
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(date.getUTCDate()).padStart(2, "0")}`;
}

function isIsoDate(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(String(value || ""));
}

function formatShortDate(date) {
  return `${String(date.getUTCDate()).padStart(2, "0")}.${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
}

function formatHumanDate(value) {
  const date = parseDate(String(value).slice(0, 10));
  return `${String(date.getUTCDate()).padStart(2, "0")} ${MONTHS_GENITIVE[date.getUTCMonth()]} ${date.getUTCFullYear()}`;
}

function addDays(date, days) {
  const copy = new Date(date.getTime());
  copy.setUTCDate(copy.getUTCDate() + days);
  return copy;
}

function startOfWeek(date) {
  const day = date.getUTCDay() || 7;
  return addDays(date, 1 - day);
}

function parseIds(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json" }
  });
}
