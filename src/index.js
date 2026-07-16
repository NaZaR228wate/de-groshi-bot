const TELEGRAM_API = "https://api.telegram.org/bot";
const CURRENCY = "грн";

const MAIN_KEYBOARD = {
  keyboard: [
    [{ text: "➕ Додати витрату" }],
    [{ text: "📊 Статистика" }, { text: "💰 Бюджет" }],
    [{ text: "✏️ Керувати витратами" }]
  ],
  resize_keyboard: true,
  input_field_placeholder: "Введи витрату або обери дію…"
};
const BACK_KEYBOARD = {
  keyboard: [[{ text: "⬅️ Назад" }]],
  resize_keyboard: true
};

const CRON_DAILY = "0 7 * * *";
const CRON_WEEKLY = "0 17 * * SUN";
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

// Порядок категорій важливий: перевірка йде зверху вниз,
// специфічніші категорії стоять вище (напр. "магазин" містить "газ").
const CATEGORY_KEYWORDS = {
  health: ["лік", "таблет", "аптек", "стоматолог", "аналіз", "клінік", "медиц", "медич", "зуб", "вітамін", "терапевт", "педіатр", "окуляр", "лінз", "масаж", "психолог", "щеплен"],
  transport: ["бензин", "бенз", "паливо", "заправ", "окко", "wog", "таксі", "uber", "uklon", "уклон", "bolt", "болт", "метро", "автобус", "маршрутк", "електричк", "потяг", "поїзд", "квиток", "сто", "шиномонтаж", "автомийк", "мийк", "парковк", "стоянк", "автоцивілк", "страховк", "транспорт"],
  kids: ["дит", "діти", "школ", "садок", "садоч", "кишеньков", "іграш", "англійськ", "гурток", "репетитор", "памперс", "підгузк", "шоколадк", "солодке"],
  food: ["кава", "чай", "піц", "продукт", "ресторан", "кафе", "їдальн", "суші", "шаурм", "бургер", "морозив", "макдон", "mcdonald", "kfc", "атб", "сільпо", "сильпо", "новус", "novus", "варус", "фора", "ашан", "їжа", "обід", "вечер", "сніданок", "напій", "напої", "хліб", "молок", "мясо", "м'ясо", "м’ясо", "овоч", "фрукт", "торт", "випічк", "бакалі"],
  shopping: ["одяг", "плаття", "сукн", "взутт", "кросівк", "куртк", "джинс", "футболк", "технік", "телевізор", "ноутбук", "навушник", "подарун", "квіти", "косметик", "парфум", "шампун", "магазин", "побутов", "хімі", "rozetka", "розетка", "aliexpress", "покупк", "канцеляр"],
  fun: ["кіно", "театр", "концерт", "ігри", "гейм", "playstation", "steam", "відпочинок", "музик", "бар", "клуб", "боулінг", "квест", "хобі", "книг", "спортзал", "абонемент", "басейн", "розваг", "пиво", "вино"],
  home: ["комунал", "оренд", "квартплат", "квартир", "будинок", "дім", "інтернет", "internet", "wifi", "вай-фай", "зв'язок", "зв’язок", "звязок", "мобільн", "телефон", "поповненн", "київстар", "kyivstar", "lifecell", "лайф", "vodafone", "водафон", "світло", "електро", "газ", "вода", "опаленн", "сміття", "домофон", "охорон", "меблі", "ремонт", "підписк", "netflix", "spotify", "youtube"]
};

const MONTHS = [
  "січень", "лютий", "березень", "квітень", "травень", "червень",
  "липень", "серпень", "вересень", "жовтень", "листопад", "грудень"
];

const MONTHS_GENITIVE = [
  "січня", "лютого", "березня", "квітня", "травня", "червня",
  "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"
];

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true });
    }
    if (request.method !== "POST" || url.pathname !== "/webhook") {
      return new Response("Not found", { status: 404 });
    }
    if (env.WEBHOOK_SECRET) {
      const token = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
      if (token !== env.WEBHOOK_SECRET) {
        return new Response("Forbidden", { status: 403 });
      }
    }

    const update = await request.json();
    await handleUpdate(update, env);
    return json({ ok: true });
  },

  async scheduled(controller, env) {
    console.log("[CRON]", { cron: controller.cron });
    if (controller.cron === CRON_WEEKLY) {
      await sendWeeklyReports(env);
      return;
    }
    await sendAccessReminders(env);
    if (kyivNow().date.slice(8, 10) === "01") {
      await sendMonthlyReports(env);
    }
  }
};

async function handleUpdate(update, env) {
  if (update.message) {
    await handleMessage(update.message, env);
    return;
  }
  if (update.callback_query) {
    await handleCallback(update.callback_query, env);
  }
}

async function handleMessage(message, env) {
  const userId = String(message.from?.id || "");
  const chatId = String(message.chat?.id || "");
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
      await sendMessage(env, chatId, startText(), MAIN_KEYBOARD);
    } else {
      await sendMessage(env, chatId, `${startText()}\n\n${paywallText(user?.access_until)}`, paymentKeyboard(), true);
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
    await ensurePendingPayment(env.DB, userId, 390, 30);
    await sendMessage(env, chatId, "Заявку на оплату передано на перевірку", paymentKeyboard(), true);
    await notifyAdmins(env, userId, username, 30);
    return;
  }

  if (!(await ensureAccess(env, userId, chatId))) return;

  if (text === "⬅️ Назад") {
    await clearState(env.DB, userId);
    await sendMessage(env, chatId, "Обери дію 👇", MAIN_KEYBOARD, true);
    return;
  }

  if (text === "➕ Додати витрату") {
    await clearState(env.DB, userId);
    await sendMessage(env, chatId, ADD_EXPENSE_HINT, addExpenseHelpKeyboard(), true);
    return;
  }

  if (text === "💰 Бюджет") {
    await clearState(env.DB, userId);
    await sendBudgetView(env, chatId, userId);
    return;
  }

  if (text === "📊 Статистика") {
    await clearState(env.DB, userId);
    await sendMessage(env, chatId, "Обери період статистики:", statsKeyboard(), true);
    return;
  }

  if (text === "📅 Обрати період") {
    await setState(env.DB, userId, WAITING_FOR_STATS_PERIOD, {});
    await sendMessage(env, chatId, STATS_PERIOD_PROMPT, statsPeriodInputKeyboard(), true);
    return;
  }

  if (text === "✏️ Керувати витратами") {
    await clearState(env.DB, userId);
    await sendMessage(env, chatId, manageExpensesText(), manageExpensesKeyboard(), true);
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
    await deleteMessage(env, chatId, messageId);
    await sendMessage(
      env, chatId,
      `✏️ Редагування\n\n${capitalize(expense.expense_title)} — ${formatAmount(expense.amount)} ${CURRENCY}\n\nНапиши нову назву і суму, наприклад:\n${expense.expense_title} ${expense.amount}`,
      BACK_KEYBOARD,
      true
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
    await deleteMessage(env, chatId, messageId);
    await sendMessage(env, chatId, STATS_PERIOD_PROMPT, statsPeriodInputKeyboard(), true);
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
    await sendMainMenu(env, chatId);
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
    await editMessage(env, chatId, messageId, ADD_EXPENSE_HINT, addExpenseHelpKeyboard());
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
    await deleteMessage(env, chatId, messageId);
    await sendMessage(env, chatId, `Введи суму 💸\n\n${capitalize(title)}`, BACK_KEYBOARD, true);
    return;
  }

  if (data === "type_choice:planned" || data === "type_choice:emotional") {
    const state = await getState(env.DB, userId);
    if (state?.state !== "pending_type") {
      await editMessage(env, chatId, messageId, "Це повідомлення застаріло. Напиши витрату ще раз 👇");
      return;
    }
    const expenseType = data.split(":")[1];
    const pending = state.data;
    const expenseId = await insertExpense(env.DB, {
      user_id: userId,
      chat_id: chatId,
      expense_title: pending.expense_title,
      amount: pending.amount,
      category: pending.category,
      expense_type: expenseType,
      expense_date: pending.date
    });
    await clearState(env.DB, userId);
    const expense = await getExpenseById(env.DB, userId, expenseId);
    const budget = await budgetWarning(env.DB, userId, expense.expense_date);
    await editMessage(env, chatId, messageId, expenseCardText(expense, budget), expenseCardKeyboard(expense));
    await sendMessage(env, chatId, "✍️ Введи наступну витрату", MAIN_KEYBOARD, true);
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
    await deleteMessage(env, chatId, messageId);
    await sendMessage(env, chatId, "💰 Напиши суму бюджету на місяць, наприклад 20000", BACK_KEYBOARD, true);
    return;
  }

  if (data === "budget_clear") {
    await setMonthlyBudget(env.DB, userId, null);
    await clearState(env.DB, userId);
    await editMessage(env, chatId, messageId, "Бюджет прибрано. Можеш встановити новий у меню «💰 Бюджет».");
    return;
  }

  if (data.startsWith("buy_")) {
    const days = Number(data.split("_")[1]);
    await ensurePendingPayment(env.DB, userId, days === 7 ? 290 : 390, days);
    await editMessage(env, chatId, messageId, paymentText(env, days), paidKeyboard(days));
    return;
  }

  if (data === "paid" || data.startsWith("paid_")) {
    const days = data.includes("_") ? Number(data.split("_")[1]) : 30;
    const amount = days === 7 ? 290 : 390;
    await ensurePendingPayment(env.DB, userId, amount, days);
    await editMessage(env, chatId, messageId, "Дякую 🙌\n\nПеревірю оплату і відкрию доступ протягом 1–5 хвилин.");
    await notifyAdmins(env, userId, callback.from?.username || "", days);
    return;
  }

  if (data.startsWith("confirm_") || data.startsWith("reject_")) {
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
    const days = Number(daysText || 30);
    if (![7, 30].includes(days)) {
      await sendMessage(env, chatId, "Дні мають бути 7 або 30", undefined, true);
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
    await sendMessage(env, chatId, ADD_EXPENSE_HINT, BACK_KEYBOARD, true);
    return;
  }

  if (items.length === 1) {
    const parsed = items[0];
    if (!parsed || (!parsed.title && !parsed.amount)) {
      await sendMessage(env, chatId, ADD_EXPENSE_HINT, BACK_KEYBOARD, true);
      return;
    }
    if (parsed.title && !parsed.amount) {
      const category = await detectCategorySmart(env.DB, userId, parsed.title);
      await setState(env.DB, userId, "waiting_amount", { expense_title: parsed.title, category, date });
      await sendMessage(env, chatId, `💸 Введи суму для «${capitalize(parsed.title)}»`, BACK_KEYBOARD, true);
      return;
    }
    if (!parsed.title) {
      await sendMessage(env, chatId, "Спочатку напиши назву витрати, наприклад: кава 80", BACK_KEYBOARD, true);
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
    await sendMessage(
      env, chatId,
      "У деяких витратах не бачу назву або суму. Напиши кожну як «назва сума», наприклад:\nкава 80, таксі 150",
      BACK_KEYBOARD, true
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
  await sendMessage(env, chatId, lines.join("\n"), MAIN_KEYBOARD, true);
}

async function handleAmountInput(env, chatId, userId, text, data) {
  const amount = parseAmount(text);
  if (!amount) {
    await sendMessage(env, chatId, "Введи тільки суму, наприклад 300 або 149.50", BACK_KEYBOARD, true);
    return;
  }
  await askExpenseType(env, chatId, userId, {
    expense_title: data.expense_title,
    amount,
    category: data.category,
    date: data.date
  });
}

// Показує картку витрати одразу з двома кнопками "Планова"/"Емоційна" —
// користувач обирає тип напряму, без проміжного стану "за замовчуванням планова".
async function askExpenseType(env, chatId, userId, data) {
  const category = data.category || await detectCategorySmart(env.DB, userId, data.expense_title);
  await setState(env.DB, userId, "pending_type", { ...data, category });
  const dateLabel = data.date ? ` • 📅 ${formatShortDate(parseDate(data.date))}` : "";
  const text = [
    `💸 ${capitalize(data.expense_title)} — ${formatAmount(data.amount)} ${CURRENCY}`,
    `${formatCategory(category)}${dateLabel}`,
    "",
    "Обери тип витрати:"
  ].join("\n");
  await sendMessage(env, chatId, text, {
    inline_keyboard: [[
      { text: "📌 Планова", callback_data: "type_choice:planned" },
      { text: "🔥 Емоційна", callback_data: "type_choice:emotional" }
    ]]
  }, true);
}

async function handleBudgetInput(env, chatId, userId, text) {
  const amount = parseAmount(text);
  if (!amount) {
    await sendMessage(env, chatId, "Введи суму бюджету числом, наприклад 20000", BACK_KEYBOARD, true);
    return;
  }
  await setMonthlyBudget(env.DB, userId, amount);
  await clearState(env.DB, userId);
  await sendMessage(env, chatId, `💰 Бюджет на місяць встановлено: ${formatAmount(amount)} ${CURRENCY}`, MAIN_KEYBOARD, true);
}

async function handleStatsPeriodInput(env, chatId, userId, text) {
  const range = parseStatsPeriodInput(text);
  if (!range) {
    await sendMessage(env, chatId, STATS_PERIOD_ERROR, statsPeriodInputKeyboard(), true);
    return;
  }
  await showCustomStats(env, chatId, null, userId, range);
}

async function handleEditExpenseInput(env, chatId, userId, text, data) {
  const { date, items } = parseExpensesMessage(text);
  const parsed = items.length === 1 ? items[0] : null;
  if (!parsed?.title || !parsed?.amount) {
    await sendMessage(env, chatId, "Напиши назву і суму, наприклад: кава 100", BACK_KEYBOARD, true);
    return;
  }

  const category = await detectCategorySmart(env.DB, userId, parsed.title);
  const updated = await updateExpense(env.DB, userId, Number(data.expense_id), parsed.title, parsed.amount, category, date);
  await clearState(env.DB, userId);
  const resultText = updated
    ? `✅ Оновлено\n\n${capitalize(cleanExpenseTitle(parsed.title))} — ${formatAmount(parsed.amount)} ${CURRENCY} • ${formatCategory(category)}`
    : "Витрату не знайдено";
  await sendMessage(env, chatId, resultText, MAIN_KEYBOARD, true);
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

function detectCategory(title) {
  const value = String(title || "").toLowerCase();
  for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
    if (keywords.some((keyword) => value.includes(keyword))) return category;
  }
  return "other";
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
  await sendMessage(env, chatId, lines.join("\n"), { inline_keyboard: buttons }, true);
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
      await sendMessage(env, user.chat_id, report, undefined, true);
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
    await sendMessage(env, chatId, "Витрат поки немає", MAIN_KEYBOARD, true);
    return;
  }
  const title = mode === "edit" ? "✏️ Редагування" : "🗑 Видалення";
  await sendMessage(env, chatId, `${title}\n\nОбери день:`, manageDatesKeyboard(dates, mode), true);
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
  await sendMessage(env, chatId, text, replyMarkup, true);
  await sendMainMenu(env, chatId);
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

function statsPeriodInputKeyboard() {
  return BACK_KEYBOARD;
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

function addExpenseHelpKeyboard() {
  return {
    inline_keyboard: [[{ text: "⚡ Швидкий вибір категорії", callback_data: "add_quick" }]]
  };
}

function quickCategoryKeyboard() {
  return {
    inline_keyboard: [
      [{ text: "🍔 Їжа", callback_data: "quick_cat:food" }, { text: "🚕 Транспорт", callback_data: "quick_cat:transport" }],
      [{ text: "🛍 Покупки", callback_data: "quick_cat:shopping" }, { text: "🏠 Дім", callback_data: "quick_cat:home" }],
      [{ text: "💊 Здоров’я", callback_data: "quick_cat:health" }, { text: "👶 Діти", callback_data: "quick_cat:kids" }],
      [{ text: "🎮 Розваги", callback_data: "quick_cat:fun" }],
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
  return {
    inline_keyboard: [
      [{ text: "💳 7 днів — 290 грн", callback_data: "buy_7" }],
      [{ text: "🔥 30 днів — 390 грн", callback_data: "buy_30" }],
      [{ text: "✅ Я оплатив", callback_data: "paid" }]
    ]
  };
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
  await sendMessage(env, chatId, paywallText(user?.access_until), paymentKeyboard(), true);
  return false;
}

function isAdmin(env, userId) {
  return parseIds(env.ADMIN_USER_IDS).includes(String(userId));
}

function hasActiveAccess(user) {
  if (!user?.access_until) return false;
  return new Date(user.access_until.replace(" ", "T")).getTime() > Date.now();
}

function paywallText(accessUntil) {
  if (accessUntil && !hasActiveAccess({ access_until: accessUntil })) {
    return "Доступ закінчився ⏳\n\nЩоб знову бачити статистику витрат,\nпродовжи доступ 👇";
  }
  return "Доступ до бота платний 👇\n\n7 днів — 290 грн\n🔥 30 днів — 390 грн\n\n30 днів вигідніше — різниця лише 100 грн.\n\nОбери варіант:";
}

function paymentText(env, days) {
  return [
    "Для оплати:",
    "",
    `mono: ${env.MONO_CARD || "не задано"}`,
    `privat: ${env.PRIVAT_CARD || "не задано"}`,
    "",
    `Тариф: ${days} днів`,
    "",
    "Після оплати натисни «✅ Я оплатив»"
  ].join("\n");
}

async function handleAdminPaymentAction(env, callback, data) {
  const adminId = String(callback.from?.id || "");
  if (!isAdmin(env, adminId)) return;

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
  const targetUser = await getUser(env.DB, targetUserId);
  const currentEnd = targetUser?.access_until && hasActiveAccess(targetUser)
    ? parseDate(String(targetUser.access_until).slice(0, 10))
    : parseDate(kyivNow().date);
  const until = addDays(currentEnd, days);
  const accessUntil = `${formatDate(until)} 23:59:59`;

  await env.DB.prepare(
    "UPDATE users SET access_until = ?, tariff = ?, status = 'active' WHERE user_id = ?"
  ).bind(accessUntil, `${days}_days`, targetUserId).run();
  await env.DB.prepare(
    "UPDATE payments SET status = 'paid', paid_at = ?, comment = ? WHERE user_id = ? AND status = 'pending'"
  ).bind(kyivNow().datetime, `admin ${adminId}`, targetUserId).run();

  console.log("[PAYMENT]", { user_id: targetUserId, tariff_days: days, amount: days === 7 ? 290 : 390, status: "paid" });
  await sendMessage(env, targetUserId, `Доступ відкрито 🚀\n\nДо: ${formatHumanDate(accessUntil)}`, MAIN_KEYBOARD, true);
}

async function createPayment(db, userId, amount, tariffDays, status) {
  await db.prepare(
    "INSERT INTO payments (user_id, amount, tariff_days, status, created_at, comment) VALUES (?, ?, ?, ?, ?, ?)"
  ).bind(userId, amount, tariffDays, status, kyivNow().datetime, null).run();
  console.log("[PAYMENT]", { user_id: userId, tariff_days: tariffDays, amount, status });
}

async function ensurePendingPayment(db, userId, amount, tariffDays) {
  const pending = await db.prepare(
    "SELECT id FROM payments WHERE user_id = ? AND tariff_days = ? AND status = 'pending' ORDER BY id DESC LIMIT 1"
  ).bind(userId, tariffDays).first();
  if (pending) return;
  await createPayment(db, userId, amount, tariffDays, "pending");
}

async function notifyAdmins(env, userId, username, tariff) {
  const admins = parseIds(env.ADMIN_USER_IDS);
  for (const adminId of admins) {
    await sendMessage(env, adminId, [
      "Новий запит на доступ 💰",
      "",
      `user_id: ${userId}`,
      `username: ${username ? `@${username}` : "—"}`,
      `тариф: ${tariff} днів`
    ].join("\n"), {
      inline_keyboard: [
        [{ text: "✅ 7 днів", callback_data: `confirm_7_${userId}` }],
        [{ text: "✅ 30 днів", callback_data: `confirm_30_${userId}` }],
        [{ text: "❌ Відхилити", callback_data: `reject_${userId}` }]
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

async function sendMainMenu(env, chatId) {
  return sendMessage(env, chatId, "Обери дію 👇", MAIN_KEYBOARD, true);
}

async function deleteMessage(env, chatId, messageId) {
  if (!messageId) return;
  return telegram(env, "deleteMessage", { chat_id: chatId, message_id: messageId });
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

async function telegram(env, method, payload) {
  const response = await fetch(`${TELEGRAM_API}${env.BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    console.log("[TELEGRAM_ERROR]", method, response.status, await response.text());
  }
  return response;
}

function startText() {
  return [
    "Вітаю! 👋",
    "",
    "Тепер витрати будуть під контролем.",
    "",
    "Ти побачиш, куди йдуть гроші: за тиждень, місяць і рік — загалом та по категоріях.",
    "",
    "Окремо покажу емоційні витрати та чи не перевищують вони 30% від усіх витрат.",
    "",
    "Щоб почати, натисни «➕ Додати витрату»."
  ].join("\n");
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
