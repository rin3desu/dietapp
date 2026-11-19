-- Additive migration only. Never run the legacy destructive schema.sql in production.
CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS weights (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), date TEXT NOT NULL, weight REAL NOT NULL);
CREATE TABLE IF NOT EXISTS meals (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), date TEXT NOT NULL, time_slot TEXT NOT NULL, content TEXT NOT NULL, ingredients TEXT, image_path TEXT);
CREATE TABLE IF NOT EXISTS training_sessions (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), date TEXT NOT NULL, part TEXT NOT NULL, event TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS training_sets (id SERIAL PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES training_sessions(id), set_number INTEGER, weight REAL NOT NULL, reps INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS gyms (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), name TEXT NOT NULL, latitude REAL, longitude REAL, address TEXT);
CREATE TABLE IF NOT EXISTS machines (id SERIAL PRIMARY KEY, gym_id INTEGER NOT NULL REFERENCES gyms(id), name TEXT NOT NULL, target_muscle TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS custom_exercises (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), muscle_group TEXT NOT NULL, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stoiq_recipes (id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), payload TEXT NOT NULL, published INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS stoiq_recipe_owner ON stoiq_recipes(user_id, created_at);
CREATE TABLE IF NOT EXISTS stoiq_ai_usage (user_id INTEGER NOT NULL REFERENCES users(id), day TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(user_id, day));
CREATE TABLE IF NOT EXISTS growth_challenges (id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), start_date TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(user_id, id));
CREATE INDEX IF NOT EXISTS growth_challenge_owner ON growth_challenges(user_id, created_at);
CREATE TABLE IF NOT EXISTS growth_habits (id TEXT PRIMARY KEY, challenge_id TEXT NOT NULL REFERENCES growth_challenges(id), name TEXT NOT NULL, category_id INTEGER NOT NULL, frequency TEXT NOT NULL, weekdays TEXT NOT NULL, target TEXT NOT NULL, memo TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT);
CREATE TABLE IF NOT EXISTS growth_habit_logs (habit_id TEXT NOT NULL REFERENCES growth_habits(id), date TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0, memo TEXT NOT NULL DEFAULT '', PRIMARY KEY(habit_id, date));
CREATE TABLE IF NOT EXISTS growth_reflections (id TEXT PRIMARY KEY, challenge_id TEXT NOT NULL REFERENCES growth_challenges(id), date TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(challenge_id, date));
CREATE TABLE IF NOT EXISTS growth_assessments (challenge_id TEXT NOT NULL REFERENCES growth_challenges(id), category_id INTEGER NOT NULL, date TEXT NOT NULL, score INTEGER NOT NULL, target_score INTEGER NOT NULL, action_goal TEXT NOT NULL DEFAULT '', reflection TEXT NOT NULL DEFAULT '', PRIMARY KEY(challenge_id, category_id, date));
CREATE TABLE IF NOT EXISTS growth_reviews (id TEXT PRIMARY KEY, challenge_id TEXT NOT NULL REFERENCES growth_challenges(id), week_start TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(challenge_id, week_start));
CREATE TABLE IF NOT EXISTS growth_measurements (id TEXT PRIMARY KEY, challenge_id TEXT NOT NULL REFERENCES growth_challenges(id), date TEXT NOT NULL, weight REAL, waist REAL, UNIQUE(challenge_id, date));
CREATE TABLE IF NOT EXISTS growth_workouts (id TEXT PRIMARY KEY, challenge_id TEXT NOT NULL REFERENCES growth_challenges(id), date TEXT NOT NULL, payload TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS growth_emotions (id TEXT PRIMARY KEY, challenge_id TEXT NOT NULL REFERENCES growth_challenges(id), date TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS growth_profiles (user_id INTEGER PRIMARY KEY REFERENCES users(id), payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stoiq_recipe_photos (recipe_id TEXT PRIMARY KEY REFERENCES stoiq_recipes(id), image_base64 TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ideal_goals (id TEXT PRIMARY KEY, user_id INTEGER UNIQUE NOT NULL REFERENCES users(id), title TEXT NOT NULL, vision TEXT NOT NULL, why TEXT NOT NULL DEFAULT '', target_date TEXT, person_name TEXT NOT NULL DEFAULT '', person_kind TEXT NOT NULL DEFAULT 'real', person_context TEXT NOT NULL DEFAULT '', admiration TEXT NOT NULL DEFAULT '', analysis TEXT, revision TEXT, image_base64 TEXT, image_prompt TEXT, image_revision TEXT, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ideal_ai_usage (user_id INTEGER NOT NULL REFERENCES users(id), day TEXT NOT NULL, kind TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(user_id,day,kind));
CREATE TABLE IF NOT EXISTS ideal_habit_links (ideal_id TEXT NOT NULL REFERENCES ideal_goals(id), revision TEXT NOT NULL, habit_index INTEGER NOT NULL, habit_id TEXT NOT NULL, PRIMARY KEY(ideal_id,revision,habit_index));
