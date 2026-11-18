"""PostgreSQL in production, isolated SQLite files for local development/tests."""
import re
import sqlite3
from pathlib import Path
import psycopg2
import psycopg2.extras


class SQLiteCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, sql, params=()):
        sql = sql.replace('%s', '?')
        sql = re.sub(r"TO_CHAR\(date,\s*'YYYY-MM-DD'\)", "substr(date, 1, 10)", sql, flags=re.I)
        self.cursor.execute(sql, params)
        return self

    def fetchone(self):
        row = self.cursor.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        return [dict(row) for row in self.cursor.fetchall()]

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cursor.close()


class SQLiteConnection:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.raw = sqlite3.connect(path, timeout=10)
        self.raw.row_factory = sqlite3.Row
        self.raw.execute('PRAGMA foreign_keys=ON')

    def cursor(self):
        return SQLiteCursor(self.raw.cursor())

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.raw.close()


def connect(config):
    url = config.get('DATABASE_URL')
    if url:
        return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor, connect_timeout=10)
    return SQLiteConnection(config['SQLITE_PATH'])


def migrate(config):
    db = connect(config)
    try:
        sql = (Path(__file__).parent / 'migrations' / '001_stoiq.sql').read_text(encoding='utf-8')
        if isinstance(db, SQLiteConnection):
            sql = sql.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
        with db.cursor() as cursor:
            for statement in sql.split(';'):
                if statement.strip():
                    cursor.execute(statement)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
