#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn flower_shop.wsgi:application \
  --bind "0.0.0.0:${PORT:-8080}" \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-60}"
