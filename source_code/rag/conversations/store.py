import json
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT 'New chat',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    citations TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
"""

DEFAULT_TITLE = "New chat"
TITLE_LENGTH = 80


def _now():
    return datetime.now(timezone.utc).isoformat()


class ConversationStore:
    def __init__(self, path):
        self._path = str(path)
        with self._connect() as db:
            db.executescript(SCHEMA)

    def _connect(self):
        db = sqlite3.connect(self._path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def create(self):
        now = _now()
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO conversations (title, created_at, updated_at) VALUES (?, ?, ?)",
                (DEFAULT_TITLE, now, now),
            )
            return self.get(cursor.lastrowid, db)

    def list(self):
        with self._connect() as db:
            rows = db.execute("SELECT * FROM conversations ORDER BY updated_at DESC, id DESC").fetchall()
            return [dict(row) for row in rows]

    def get(self, conversation_id, db=None):
        if db is None:
            with self._connect() as db:
                return self.get(conversation_id, db)
        row = db.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        if row is None:
            return None
        messages = db.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id", (conversation_id,)
        ).fetchall()
        return {**dict(row), "messages": [self._message(message) for message in messages]}

    def delete(self, conversation_id):
        with self._connect() as db:
            return db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,)).rowcount > 0

    def add_message(self, conversation_id, role, content, citations=()):
        now = _now()
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO messages (conversation_id, role, content, citations, created_at) VALUES (?, ?, ?, ?, ?)",
                (conversation_id, role, content, json.dumps(list(citations)), now),
            )
            if role == "user":
                db.execute(
                    "UPDATE conversations SET title = ? WHERE id = ? AND title = ?",
                    (content[:TITLE_LENGTH], conversation_id, DEFAULT_TITLE),
                )
            db.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
            row = db.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return self._message(row)

    @staticmethod
    def _message(row):
        message = dict(row)
        message["citations"] = json.loads(message["citations"])
        return message
