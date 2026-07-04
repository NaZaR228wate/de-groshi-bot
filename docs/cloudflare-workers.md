# Cloudflare Workers + D1 deploy

Нова Worker-версія бота знаходиться в `src/index.js`.

Архітектура:

```text
Telegram Bot API -> webhook -> Cloudflare Worker -> Cloudflare D1
```

Python `bot.py` не використовується для Cloudflare-деплою.

## Multi-user модель

Бот працює для багатьох користувачів.

Немає `ALLOWED_USER_IDS`.

Кожен користувач ідентифікується через Telegram `user_id`.

Усі основні таблиці мають `user_id`:

- `users`
- `expenses`
- `payments`
- `settings`
- `bot_state`

Статистика, деталізація, платежі й доступ завжди фільтруються по `user_id`.

## Secrets

Задати через Cloudflare:

```powershell
npx wrangler secret put BOT_TOKEN
npx wrangler secret put WEBHOOK_SECRET
npx wrangler secret put ADMIN_USER_IDS
npx wrangler secret put MONO_CARD
npx wrangler secret put PRIVAT_CARD
```

`ADMIN_USER_IDS` — список Telegram user_id адмінів через кому:

```text
123456789,987654321
```

Опційно:

```powershell
npx wrangler secret put TRIAL_DAYS
```

Якщо `TRIAL_DAYS` не заданий або `0`, новий користувач бачить paywall.

## D1

Створити базу:

```powershell
npx wrangler d1 create de-groshi-db
```

Вставити `database_id` у `wrangler.toml`.

Застосувати міграції:

```powershell
npx wrangler d1 migrations apply de-groshi-db --remote
```

## Deploy

```powershell
npm install
npm run check
npm run deploy
```

## Telegram webhook

Після деплою:

```powershell
$BOT_TOKEN="..."
$WORKER_URL="https://de-groshi-bot.<account>.workers.dev/webhook"
$WEBHOOK_SECRET="..."

Invoke-RestMethod "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" `
  -Method Post `
  -ContentType "application/json" `
  -Body (@{
    url = $WORKER_URL
    secret_token = $WEBHOOK_SECRET
    allowed_updates = @("message", "callback_query")
  } | ConvertTo-Json)
```

## Admin

Команда:

```text
/admin
```

Доступна тільки користувачам з `ADMIN_USER_IDS`.

Адмін бачить:

- користувачів
- оплати
- доступи
- заблокованих

Ручні команди:

```text
/grant user_id 7
/grant user_id 30
/block user_id
/unblock user_id
```

## Локальний запуск

Скопіювати `.dev.vars.example` у `.dev.vars` і заповнити.

```powershell
npm run d1:migrate:local
npm run dev
```

Для локального webhook потрібен публічний tunnel.

## Важливо про витрати

У загальному звіті групування йде по `category`.

У деталізації показується тільки `expense_title`.

Дата, місяць або період не використовуються як назва витрати.
