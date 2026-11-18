#!/usr/bin/env bash
set -euo pipefail
python manage.py migrate
exec gunicorn app:app --bind "0.0.0.0:${PORT:-10000}" --workers 2 --threads 2 --timeout 75
