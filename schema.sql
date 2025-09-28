-- schema.sql
DROP TABLE IF EXISTS weights;
DROP TABLE IF EXISTS meals;

CREATE TABLE weights (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  weight REAL NOT NULL
);

CREATE TABLE meals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  time_slot TEXT NOT NULL,
  content TEXT NOT NULL,
  ingredients TEXT,
  image_path TEXT
);

DROP TABLE IF EXISTS training_sessions;
DROP TABLE IF EXISTS training_sets;

CREATE TABLE training_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    part TEXT NOT NULL,
    event TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE training_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL, /* どのセッションに属するかを示すID */
    set_number INTEGER NOT NULL,   /* セット番号 */
    weight REAL NOT NULL,          /* 負荷(kg) */
    reps INTEGER NOT NULL,           /* Rep数 */
    FOREIGN KEY (session_id) REFERENCES training_sessions (id)
);