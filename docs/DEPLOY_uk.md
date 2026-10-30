# Деплой Gestia Home (Ubuntu 24.04 + Docker)

Покрокова інструкція для власника. **Ніколи не публікуйте** `SECRET_KEY`, паролі БД і шлях адмінки.

На сервері використовуйте **лише** `docker-compose.prod.yml` (`docker compose -f docker-compose.prod.yml …`). Файл `docker-compose.yml` — лише для локальної розробки; на прод його не запускайте.

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

- `SECRET_KEY` — згенерований рядок (**обовʼязково** в проді)
- `ADMIN_URL` — **власний** секретний шлях (не `admin/`), зі слешем наприкінці
- `IP_HASH_SALT` — випадковий рядок (**обовʼязково** в проді)
- `POSTGRES_PASSWORD` і відповідний пароль у `DATABASE_URL`
- `DEBUG=0`
- `SECURE_SSL_REDIRECT=0` на **першому HTTP-only** запуску (до certbot). Інакше Django редиректить на неіснуючий HTTPS
- `SECURE_HSTS_SECONDS=31536000` (після того як HTTPS стабільно працює; можна змінити через env)

Без `SECRET_KEY` / `IP_HASH_SALT` / `ADMIN_URL` при `DEBUG=0` застосунок **не стартує**.

## 4. Запуск (HTTP-only, до SSL)

```bash
# у .env: SECURE_SSL_REDIRECT=0
docker compose -f docker-compose.prod.yml up -d --build
```

Створіть суперкористувача:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

Адмінка буде за адресою `https://gestia-home.com/<ваш-ADMIN_URL>` (після SSL).
Після 5 невдалих спроб входу акаунт/IP блокується на 1 годину (django-axes).

## 5. HTTPS (certbot, webroot) + редірект 80→443

Переконайтесь, що HTTP відкритий і DNS вказує на сервер. Видайте сертифікат через контейнер certbot (webroot `/var/www/certbot`), наприклад:

```bash
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d gestia-home.com -d www.gestia-home.com \
  --email YOUR@EMAIL --agree-tos --no-eff-email
```

Потім у `nginx/conf.d/gestia.conf`:

1. Розкоментуйте блок `listen 443 ssl http2` (SSL-шаблон уже з security headers, CSP, HSTS, `limit_req` на `/subscribe/`).
2. У блоці `listen 80` розкоментуйте `return 301 https://$host$request_uri;` і **приберіть** (закоментуйте) proxy-локації `/` та `/subscribe/`, залишивши лише `/.well-known/acme-challenge/`.
3. Перезавантажте nginx:

```bash
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

Після успішного SSL у `.env` встановіть `SECURE_SSL_REDIRECT=1` і перезапустіть web:

```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate web
```

Перевірка: `curl -I http://gestia-home.com/` має дати `301` на HTTPS; на 443 — заголовки CSP / HSTS / `nosniff`.

## 6. HSTS

У проді Django за замовчуванням ставить `SECURE_HSTS_SECONDS=31536000` (можна перевизначити env). Nginx на 443 також віддає HSTS. Не вмикайте HSTS, доки HTTPS не працює стабільно для обох імен хоста.

## 7. Бекап Postgres

Скрипт: `scripts/backup_db.sh` — `pg_dump` через `docker compose exec db`, gzip у `/var/backups/gestia/`, ротація **14 днів**.

Один раз на сервері:

```bash
sudo mkdir -p /var/backups/gestia
sudo chown "$USER" /var/backups/gestia
chmod +x scripts/backup_db.sh
./scripts/backup_db.sh
```

Cron (щодня о 03:15, з каталогу проєкту):

```cron
15 3 * * * cd /path/to/gestia && ./scripts/backup_db.sh >> /var/log/gestia-backup.log 2>&1
```

**Обовʼязково** копіюйте бекапи **поза сервер** (не лише `/var/backups/gestia/` на тому ж дроплеті): наприклад DO Spaces / rclone, або `rsync` на іншу машину. Без offsite втрата диска = втрата даних.

### Відновлення з бекапу

```bash
gunzip -c /var/backups/gestia/gestia_YYYYMMDD_HHMMSS.sql.gz \
  | docker compose -f docker-compose.prod.yml exec -T db \
    sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Перед restore зупиніть `web` або переконайтесь, що немає активних записів у БД. Після відновлення: `docker compose -f docker-compose.prod.yml restart web`.

## 8. Оновлення

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Міграції та `createcachetable` виконуються автоматично в entrypoint.
