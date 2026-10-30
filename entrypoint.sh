#!/bin/sh
set -e
python manage.py migrate --noinput
exec gunicorn config.wsgi:application -w 3 -b 0.0.0.0:8000
