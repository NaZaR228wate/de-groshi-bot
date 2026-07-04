ALTER TABLE settings ADD COLUMN monthly_budget REAL;

CREATE TABLE IF NOT EXISTS category_overrides (
  user_id TEXT NOT NULL,
  title_norm TEXT NOT NULL,
  category TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (user_id, title_norm)
);
