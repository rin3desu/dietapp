"""Read-only diagnostics of the app's existing persistent disk; no record contents."""
import json
import sqlite3
from pathlib import Path


def inspect_storage(logger, root=None):
    root = Path(root or '/var/data')
    candidates = []
    for directory in [root, root / 'instance', root / 'stoiq']:
        if directory.is_dir():
            for pattern in ['*.db', '*.sqlite', '*.sqlite3']:
                candidates.extend(directory.glob(pattern))
    report = []
    for path in sorted(set(candidates))[:20]:
        if not path.is_file():
            continue
        connection = None
        try:
            connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
            tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            counts = {}
            for table in ['users', 'gyms', 'machines', 'weights', 'meals', 'training_sessions']:
                if table in tables:
                    counts[table] = connection.execute('SELECT COUNT(*) FROM "' + table + '"').fetchone()[0]
            columns = [r[1] for r in connection.execute('PRAGMA table_info(users)')]
            report.append(dict(path=str(path), bytes=path.stat().st_size, counts=counts, compatible_users={'id','username','password_hash'}.issubset(columns)))
        except (sqlite3.DatabaseError, OSError):
            report.append(dict(path=str(path), readable=False))
        finally:
            if connection:
                connection.close()
    logger.warning('STOIQ storage metadata (no record contents): %s', json.dumps(report))
    return report
