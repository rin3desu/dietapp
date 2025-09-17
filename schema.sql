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