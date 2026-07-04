Telegram bot "De groshi?"

There are two run modes.

## Local Python bot

```powershell
python -m pip install -r requirements.txt
python bot.py
```

This mode uses aiogram polling and local SQLite.

## Cloudflare Workers + D1 bot

```powershell
npm install
npm run check
npm run deploy
```

This mode uses:

- Telegram webhook
- Cloudflare Worker
- Cloudflare D1

No polling.

No local SQLite.

Deploy guide:

```text
docs/cloudflare-workers.md
```
