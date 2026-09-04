CREATE TABLE IF NOT EXISTS mono_processed (
  tx_id TEXT PRIMARY KEY,
  processed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mono_poll (
  id INTEGER PRIMARY KEY,
  last_pull_at INTEGER
);
