"""Database schema definitions for ZenFlow.

This module contains all SQL CREATE TABLE and CREATE INDEX statements
as string constants for initializing the SQLite database.
"""

# Enable foreign key constraints
PRAGMA_FOREIGN_KEYS: str = "PRAGMA foreign_keys = ON;"

# Table schemas
CREATE_USERS_TABLE: str = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_TASKS_TABLE: str = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT NOT NULL CHECK(priority IN ('LOW', 'MEDIUM', 'HIGH')),
    status TEXT DEFAULT 'TODO' CHECK(status IN ('TODO', 'IN_PROGRESS', 'DONE')),
    due_date TIMESTAMP,
    completed_at TIMESTAMP,
    xp_reward INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

CREATE_HABITS_TABLE: str = """
CREATE TABLE IF NOT EXISTS habits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    frequency TEXT NOT NULL CHECK(frequency IN ('DAILY', 'WEEKLY')),
    streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_completed TIMESTAMP,
    target_days INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

CREATE_HABIT_LOGS_TABLE: str = """
CREATE TABLE IF NOT EXISTS habit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id INTEGER NOT NULL,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (habit_id) REFERENCES habits(id)
);
"""

CREATE_ACHIEVEMENTS_TABLE: str = """
CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    achievement_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    xp_earned INTEGER NOT NULL,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, achievement_type)
);
"""

CREATE_FOCUS_SESSIONS_TABLE: str = """
CREATE TABLE IF NOT EXISTS focus_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    duration_minutes INTEGER DEFAULT 25,
    completed BOOLEAN DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

CREATE_DAILY_STATS_TABLE: str = """
CREATE TABLE IF NOT EXISTS daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date DATE UNIQUE NOT NULL,
    tasks_completed INTEGER DEFAULT 0,
    xp_earned INTEGER DEFAULT 0,
    focus_minutes INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

# Indexes for query optimization
CREATE_INDEX_TASKS_USER_STATUS: str = """
CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks(user_id, status);
"""

CREATE_INDEX_TASKS_DUE_DATE: str = """
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
"""

CREATE_INDEX_HABITS_USER: str = """
CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id);
"""

CREATE_INDEX_HABIT_LOGS_HABIT: str = """
CREATE INDEX IF NOT EXISTS idx_habit_logs_habit ON habit_logs(habit_id);
"""

CREATE_INDEX_ACHIEVEMENTS_USER: str = """
CREATE INDEX IF NOT EXISTS idx_achievements_user ON achievements(user_id);
"""

CREATE_INDEX_FOCUS_SESSIONS_USER: str = """
CREATE INDEX IF NOT EXISTS idx_focus_sessions_user ON focus_sessions(user_id);
"""

CREATE_INDEX_DAILY_STATS_USER_DATE: str = """
CREATE INDEX IF NOT EXISTS idx_daily_stats_user_date ON daily_stats(user_id, date);
"""

# All table creation statements in order
ALL_TABLES: list[str] = [
    CREATE_USERS_TABLE,
    CREATE_TASKS_TABLE,
    CREATE_HABITS_TABLE,
    CREATE_HABIT_LOGS_TABLE,
    CREATE_ACHIEVEMENTS_TABLE,
    CREATE_FOCUS_SESSIONS_TABLE,
    CREATE_DAILY_STATS_TABLE,
]

# All index creation statements
ALL_INDEXES: list[str] = [
    CREATE_INDEX_TASKS_USER_STATUS,
    CREATE_INDEX_TASKS_DUE_DATE,
    CREATE_INDEX_HABITS_USER,
    CREATE_INDEX_HABIT_LOGS_HABIT,
    CREATE_INDEX_ACHIEVEMENTS_USER,
    CREATE_INDEX_FOCUS_SESSIONS_USER,
    CREATE_INDEX_DAILY_STATS_USER_DATE,
]
