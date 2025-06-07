import sqlite3
from datetime import datetime
from dataclasses import dataclass

@dataclass
class Contact:
    id: int
    name: str
    phone: str
    note: str = None
    telegram_user_id: int = None
    date_added: datetime = None

@dataclass
class Message:
    id: int
    contact_id: int
    message_id: int
    direction: str  # 'incoming' или 'outgoing'
    text: str
    media_type: str = 'text'  # 'text', 'photo', 'video', 'document', 'none'
    media_file_id: str = None
    timestamp: datetime = None

@dataclass
class Admin:
    id: int
    username: str
    telegram_user_id: int
    date_added: datetime = None

# SQL запросы для создания таблиц
CREATE_CONTACTS_TABLE = """
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    note TEXT,
    telegram_user_id BIGINT,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER,
    message_id BIGINT,
    direction TEXT CHECK(direction IN ('incoming', 'outgoing')),
    text TEXT,
    media_type TEXT DEFAULT 'text',
    media_file_id TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts (id)
);
"""

CREATE_ADMINS_TABLE = """
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    telegram_user_id BIGINT NOT NULL,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""" 