import sqlite3
import json
from datetime import datetime
from config import config

DB_PATH = config.DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    )
    ''')

    # Groups Table (Optional, for tracking groups)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS groups (
        chat_id INTEGER PRIMARY KEY,
        title TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # User Stats Table (for chat counts per group)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_stats (
        user_id INTEGER,
        chat_id INTEGER,
        chat_count INTEGER DEFAULT 0,
        last_chat_at TIMESTAMP,
        PRIMARY KEY (user_id, chat_id),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    ''')

    # Attendance Table (per group)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        chat_id INTEGER,
        date TEXT, -- YYYY-MM-DD format
        time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        UNIQUE(user_id, chat_id, date)
    )
    ''')

    # Admin Settings Table (per group)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_settings (
        chat_id INTEGER,
        key TEXT,
        value TEXT,
        PRIMARY KEY (chat_id, key)
    )
    ''')

    # Banned Words Table (per group)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS banned_words (
        chat_id INTEGER,
        word TEXT,
        PRIMARY KEY (chat_id, word)
    )
    ''')

    # Scheduled Messages Table (per group)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scheduled_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        message TEXT,
        schedule_time TEXT, -- HH:MM format or specific cron expression
        repeat_type TEXT, -- 'daily', 'weekly', 'none'
        is_active BOOLEAN DEFAULT 1
    )
    ''')

    conn.commit()
    conn.close()

# Initialize DB when module is imported
init_db()

# --- CRUD Helpers ---

# User
def add_or_update_user(user_id, username, first_name, last_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO users (user_id, username, first_name, last_name, is_active)
    VALUES (?, ?, ?, ?, 1)
    ON CONFLICT(user_id) DO UPDATE SET
        username=excluded.username,
        first_name=excluded.first_name,
        last_name=excluded.last_name,
        is_active=1
    ''', (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# Group
def add_or_update_group(chat_id, title):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO groups (chat_id, title)
    VALUES (?, ?)
    ON CONFLICT(chat_id) DO UPDATE SET
        title=excluded.title
    ''', (chat_id, title))
    conn.commit()
    conn.close()

def get_all_groups():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM groups')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# User Stats
def increment_chat_count(user_id, chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
    INSERT INTO user_stats (user_id, chat_id, chat_count, last_chat_at)
    VALUES (?, ?, 1, ?)
    ON CONFLICT(user_id, chat_id) DO UPDATE SET
        chat_count = chat_count + 1,
        last_chat_at = excluded.last_chat_at
    ''', (user_id, chat_id, now))
    conn.commit()
    conn.close()

def get_user_stats(user_id, chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user_stats WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {"user_id": user_id, "chat_id": chat_id, "chat_count": 0, "last_chat_at": None}

def get_top_chatters(chat_id, limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT u.user_id, u.username, u.first_name, s.chat_count 
    FROM user_stats s
    JOIN users u ON s.user_id = u.user_id
    WHERE s.chat_id = ?
    ORDER BY s.chat_count DESC
    LIMIT ?
    ''', (chat_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def reset_all_user_stats(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_stats WHERE chat_id = ?', (chat_id,))
    conn.commit()
    conn.close()

# Attendance
def record_attendance(user_id, chat_id):
    date_str = datetime.now().strftime('%Y-%m-%d')
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO attendance (user_id, chat_id, date)
        VALUES (?, ?, ?)
        ''', (user_id, chat_id, date_str))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False # Already attended today
    conn.close()
    return success

def get_attendance_count(user_id, chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM attendance WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    row = cursor.fetchone()
    conn.close()
    return row['count'] if row else 0

def get_top_attendance(chat_id, limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT u.user_id, u.username, u.first_name, COUNT(a.id) as attend_count
    FROM attendance a
    JOIN users u ON a.user_id = u.user_id
    WHERE a.chat_id = ?
    GROUP BY a.user_id
    ORDER BY attend_count DESC
    LIMIT ?
    ''', (chat_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def reset_all_attendance(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM attendance WHERE chat_id = ?', (chat_id,))
    conn.commit()
    conn.close()

# Admin Settings
def get_setting(chat_id, key, default=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM admin_settings WHERE chat_id = ? AND key = ?', (chat_id, key))
    row = cursor.fetchone()
    conn.close()
    if row:
        try:
            return json.loads(row['value'])
        except json.JSONDecodeError:
            return row['value']
    return default

def set_setting(chat_id, key, value):
    val_str = json.dumps(value) if isinstance(value, (dict, list, bool, int)) else str(value)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO admin_settings (chat_id, key, value)
    VALUES (?, ?, ?)
    ON CONFLICT(chat_id, key) DO UPDATE SET value=excluded.value
    ''', (chat_id, key, val_str))
    conn.commit()
    conn.close()

# Banned Words
def add_banned_word(chat_id, word):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO banned_words (chat_id, word) VALUES (?, ?)', (chat_id, word))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def remove_banned_word(chat_id, word):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM banned_words WHERE chat_id = ? AND word = ?', (chat_id, word))
    changes = cursor.rowcount
    conn.commit()
    conn.close()
    return changes > 0

def get_banned_words(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT word FROM banned_words WHERE chat_id = ?', (chat_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row['word'] for row in rows]

# Scheduled Messages
def add_scheduled_message(chat_id, message, schedule_time, repeat_type):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO scheduled_messages (chat_id, message, schedule_time, repeat_type)
    VALUES (?, ?, ?, ?)
    ''', (chat_id, message, schedule_time, repeat_type))
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return msg_id

def get_scheduled_messages(chat_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if chat_id is not None:
        cursor.execute('SELECT * FROM scheduled_messages WHERE chat_id = ? AND is_active = 1', (chat_id,))
    else:
        cursor.execute('SELECT * FROM scheduled_messages WHERE is_active = 1')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_scheduled_message(chat_id, msg_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM scheduled_messages WHERE chat_id = ? AND id = ?', (chat_id, msg_id))
    changes = cursor.rowcount
    conn.commit()
    conn.close()
    return changes > 0
