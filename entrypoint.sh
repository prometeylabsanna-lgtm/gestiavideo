#!/bin/sh
set -e
python manage.py migrate --noinput
python manage.py createcachetable
exec gunicorn config.wsgi:application -w 3 -b 0.0.0.0:8000
