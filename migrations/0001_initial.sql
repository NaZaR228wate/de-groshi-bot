CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT UNIQUE NOT NULL,
  chat_id TEXT NOT NULL,
  username TEXT,
  first_name TEXT,
  last_name TEXT,
  created_at TEXT NOT NULL,
  access_until TEXT,
  tariff TEXT,
  status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS expenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  chat_id TEXT NOT NULL,
  expense_title TEXT NOT NULL,
  amount INTEGER NOT NULL,
  category TEXT NOT NULL,
  expense_type TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expense_date TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_date
ON expenses (user_id, expense_date);

CREATE INDEX IF NOT EXISTS idx_expenses_user_category_date
ON expenses (user_id, category, expense_date);

CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  amount INTEGER NOT NULL,
  tariff_days INTEGER NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  paid_at TEXT,
  comment TEXT
);

CREATE TABLE IF NOT EXISTS settings (
  user_id TEXT PRIMARY KEY,
  timezone TEXT DEFAULT 'Europe/Kyiv',
  currency TEXT DEFAULT 'грн'
);

CREATE TABLE IF NOT EXISTS bot_state (
  user_id TEXT PRIMARY KEY,
  state TEXT NOT NULL,
  data_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
