"""Compatible with the existing Render start command: python -m gunicorn app:app."""
import os

bind = '0.0.0.0:' + os.getenv('PORT', '10000')
workers = 2
threads = 2
timeout = 75


def on_starting(server):
    # Run once in the master before workers start. Existing records are retained.
    from app import app
    from stoic_db import migrate
    from psycopg2 import OperationalError
    try:
        migrate(app.config)
        app.config['DATABASE_READY'] = True
    except OperationalError:
        app.config['DATABASE_READY'] = False
        app.logger.warning('Database unavailable. Public editorial recipes remain available; private features require database recovery.')
        from storage_probe import inspect_storage
        inspect_storage(app.logger)
