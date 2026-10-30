# Gestia Home — coming soon

Django-проєкт «скоро» для Gestia Home: відео-фон, форма підписки на e-mail, Unfold-адмінка. Візуал сторінки збережено піксель-в-піксель зі статичної версії.

## Стек

- Django 5.2 LTS, django-unfold, gunicorn, whitenoise
- SQLite локально; PostgreSQL у Docker / прод
- Python 3.12

## Локальний запуск (venv + SQLite)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DEBUG=1
export ADMIN_URL=admin-local/
python manage.py migrate
python manage.py runserver
```

Відкрийте http://127.0.0.1:8000/  
Адмінка: http://127.0.0.1:8000/admin-local/

Тести:

```bash
python manage.py test
```

## Docker (dev)

```bash
cp .env.example .env
# заповніть SECRET_KEY, ADMIN_URL, DEBUG=1 тощо
docker compose up --build
```

## Прод

Див. [docs/DEPLOY_uk.md](docs/DEPLOY_uk.md).

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## Структура

```
config/           # settings, urls, wsgi
subscribers/      # модель, /subscribe/, адмінка, тести
templates/        # index.html
static/           # styles.css, script.js, assets/
nginx/            # prod reverse proxy
docs/DEPLOY_uk.md
```

## Підписка

`POST /subscribe/` (JSON або form) — CSRF, honeypot `website`, rate limit 5 / 10 хв на IP.
