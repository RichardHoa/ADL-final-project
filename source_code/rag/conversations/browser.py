import sqlite3
from contextlib import closing
from pathlib import Path


class DatabaseBrowser:
    """Read-only view of every user table in a SQLite database."""

    def __init__(self, path):
        self._path = str(path)

    def _connect(self):
        return closing(sqlite3.connect(f"{Path(self._path).resolve().as_uri()}?mode=ro", uri=True))

    def _table_names(self, db):
        rows = db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid"
        ).fetchall()
        return [row[0] for row in rows]

    def tables(self):
        with self._connect() as db:
            return [
                {"name": name, "rows": db.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]}
                for name in self._table_names(db)
            ]

    def rows(self, table, page=1, per_page=50):
        with self._connect() as db:
            if table not in self._table_names(db):
                return None
            total = db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            cursor = db.execute(f'SELECT * FROM "{table}" ORDER BY rowid LIMIT ? OFFSET ?', (per_page, (page - 1) * per_page))
            columns = [column[0] for column in cursor.description]
            return {"columns": columns, "rows": [list(row) for row in cursor.fetchall()], "total": total, "page": page, "per_page": per_page}
