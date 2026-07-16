CREATE TABLE IF NOT EXISTS pending_expenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  chat_id TEXT NOT NULL,
  expense_title TEXT NOT NULL,
  amount REAL NOT NULL,
  category TEXT NOT NULL,
  expense_date TEXT,
  created_at TEXT NOT NULL
);
