# Database (SQLite) Overview

## Files
- Database file: `interview_prep.db` (created on first run)
- Initialization: `backend/app.py` → `init_db()`

## Schema
- `users`
  - `id` INTEGER PK AUTOINCREMENT
  - `name` TEXT NOT NULL
  - `email` TEXT UNIQUE NOT NULL
  - `password_hash` TEXT NOT NULL
  - `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

- `attempts`
  - `id` INTEGER PK AUTOINCREMENT
  - `user_id` INTEGER NOT NULL → FK `users.id`
  - `question_id` INTEGER NOT NULL
  - `correct` BOOLEAN NOT NULL
  - `user_answer` TEXT
  - `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

- `mock_sessions`
  - `id` INTEGER PK AUTOINCREMENT
  - `user_id` INTEGER NOT NULL → FK `users.id`
  - `start_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  - `end_time` TIMESTAMP NULL
  - `total_questions` INTEGER DEFAULT 0
  - `correct_answers` INTEGER DEFAULT 0

## Access Patterns
- Connection: `sqlite3.connect('interview_prep.db')`
- Cursor: `conn.cursor()`
- Always `conn.commit()` (for writes) and `conn.close()`

## Key Queries
- Total attempts by user: `SELECT COUNT(*) FROM attempts WHERE user_id = ?`
- Correct attempts: `SELECT COUNT(*) FROM attempts WHERE user_id = ? AND correct = 1`
- Weak topics: group incorrect attempts by `question_id`
- Recent mock sessions (non-empty): order by `start_time` desc, limit 5

## Data Considerations
- Guard divisions by zero (e.g., accuracy, score calculations)
- Use parameterized queries (`?`) to prevent SQL injection
- Consider indices on `attempts(user_id, correct)` if DB grows

## Future Enhancements
- Migrations via Alembic (if upgrading to SQLAlchemy)
- Replace raw sqlite3 with ORM models for maintainability
