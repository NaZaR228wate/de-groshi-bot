CREATE TABLE IF NOT EXISTS service_messages (
  user_id TEXT PRIMARY KEY,
  chat_id TEXT NOT NULL,
  message_id INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);
