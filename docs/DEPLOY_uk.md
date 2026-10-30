# Деплой Gestia Home (Ubuntu 24.04 + Docker)

Покрокова інструкція для власника. **Ніколи не публікуйте** `SECRET_KEY`, паролі БД і шлях адмінки.

## 1. Сервер

1. Створіть Droplet у DigitalOcean: Ubuntu 24.04, мінімум 1 GB RAM.
2. Запишіть публічну IP-адресу.
3. Увійдіть по SSH і встановіть Docker (офіційний спосіб Docker для Ubuntu) + плагін Compose.

## 2. DNS (nic.ua)

Створіть A-записи:

- `@` → IP дроплета
- `www` → IP дроплета

Дочекайтесь поширення DNS (хвилини–години).

## 3. Код і змінні оточення

```bash
git clone <URL_ВАШОГО_РЕПО> gestia
cd gestia
cp .env.example .env
```

Згенеруйте секретний ключ:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

У `.env` заповніть:

- `SECRET_KEY` — згенерований рядок
- `ADMIN_URL` — **власний** секретний шлях (не `admin/`), зі слешем наприкінці
- `IP_HASH_SALT` — випадковий рядок
- `POSTGRES_PASSWORD` і відповідний пароль у `DATABASE_URL`
- `DEBUG=0`

## 4. Запуск

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Створіть суперкористувача:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

Адмінка буде за адресою `https://gestia-home.com/<ваш-ADMIN_URL>` (після SSL).

## 5. HTTPS (certbot, webroot)

Переконайтесь, що HTTP відкритий і DNS вказує на сервер. Видайте сертифікат через контейнер certbot (webroot `/var/www/certbot`), наприклад для `gestia-home.com` і `www.gestia-home.com`.

Потім у `nginx/conf.d/gestia.conf`:

1. Розкоментуйте блок `listen 443 ssl`.
2. Додайте редірект з порту 80 на HTTPS (залишивши `/.well-known/acme-challenge/`).
3. Перезавантажте nginx:

```bash
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## 6. HSTS

Після того як SSL стабільно працює, у `.env` підніміть:

```
SECURE_HSTS_SECONDS=31536000
```

і перезапустіть `web`.

## 7. Оновлення

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Міграції виконуються автоматично в entrypoint.
