import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot_data.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER DEFAULT 1,
            file_id TEXT,
            file_name TEXT,
            file_type TEXT,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS file_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER DEFAULT 1,
            short_code TEXT UNIQUE,
            file_id TEXT,
            file_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS custom_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER DEFAULT 1,
            command TEXT,
            response_text TEXT,
            UNIQUE(bot_id, command)
        );

        CREATE TABLE IF NOT EXISTS custom_buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER DEFAULT 1,
            button_text TEXT,
            action_type TEXT,
            action_value TEXT,
            menu_type TEXT DEFAULT 'keyboard'
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            bot_id INTEGER DEFAULT 1,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS force_join (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER DEFAULT 1,
            channel_name TEXT,
            channel_username TEXT,
            custom_message TEXT,
            enabled INTEGER DEFAULT 1,
            UNIQUE(bot_id, channel_username)
        );

        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY,
            bot_id INTEGER DEFAULT 1,
            first_name TEXT,
            ban_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- جداول اختصاصی انواع ربات
        CREATE TABLE IF NOT EXISTS anon_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER DEFAULT 1,
            owner_chat_id INTEGER,
            sender_chat_id INTEGER,
            message_text TEXT,
            reply_text TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS broadcast_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER DEFAULT 1,
            message_text TEXT,
            scheduled_time TEXT,
            timezone TEXT,
            sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    conn.close()