# Gestia Home (заглушка): security-аудит перед запуском
- Дата: 30.10.2026, 17:20 (Київ, UTC+2)
- Репо: MacBook Air ~/Sites/Gestia/Gestia-zahlushka, HEAD 2bbd7b9c49072785d78a4514af614e5e1b0c5dad (лише статика)
- Django-бекенд НЕ закомічений: перевірено робоче дерево (у процесі, файли ще дописувались під час аудиту)
- Режим: find&report, лише читання. pip-audit і check --deploy у тимчасовому venv /tmp (видалено)

## Вердикт: FAIL (3 × P1)

| ID | P | Де | Проблема | Рекомендація | Хто |
|---|---|---|---|---|---|
| GH-SEC-01 | P1 | requirements.txt:1,7 | Django==5.2.7: 13 PYSEC (до 5.2.17); python-dotenv 1.1.1 (PYSEC-2026-2270) | Django>=5.2.17,<6; python-dotenv>=1.2.2 | Cursor Coder |
| GH-SEC-02 | P1 | subscribers/views.py:30-34 + nginx/conf.d/gestia.conf:23 | IP береться з першого X-Forwarded-For, а nginx робить $proxy_add_x_forwarded_for, тож клієнт підставляє будь-який IP і обходить rate limit | nginx: `proxy_set_header X-Forwarded-For $remote_addr;` (або X-Real-IP). Django: брати останній IP / X-Real-IP | Cursor Coder + Deploy Ops |
| GH-SEC-03 | P1 | config/settings.py:14, :38 | SECRET_KEY має insecure default, IP_HASH_SALT теж. Без env прод стартує з відомим ключем (не fail-closed) | Якщо не DEBUG і змінної немає, кидати ImproperlyConfigured | Cursor Coder |
| GH-SEC-04 | P2 | settings.py:130-135; gestia.conf (немає limit_req) | Rate limit у LocMemCache окремий для кожного з 3 gunicorn-воркерів і скидається при рестарті; у nginx немає limit_req; глобального ліміту немає, тож масовий спам заллє БД валідними фейковими email | nginx `limit_req_zone $binary_remote_addr zone=sub:10m rate=5r/m;` на /subscribe/ (burst=5 nodelay); кеш у БД/Redis | Deploy Ops + Cursor Coder |
| GH-SEC-05 | P2 | gestia.conf (весь) | Немає server_tokens off, security headers і CSP; SSL-блок закоментований | Див. CSP нижче | Deploy Ops |
| GH-SEC-06 | P2 | settings.py:151 | SECURE_HSTS_SECONDS за замовчуванням 0 | Після SSL поставити 31536000 в env | Deploy Ops |
| GH-SEC-07 | P2 | репо (немає скрипта) | Немає бекапу Postgres: ні скрипта, ні cron, ні ротації, ні копії поза сервером | pg_dump-cron + ротація 14 днів + DO Spaces/offsite; описати в docs/DEPLOY_uk.md | Deploy Ops |
| GH-SEC-08 | P2 | templates/index.html:70-96 | Біля форми немає тексту згоди і посилання на політику; ретенцію не визначено; зберігається user_agent (PII) | Рядок згоди + /privacy, строк зберігання, не зберігати UA без потреби | Cursor Coder |
| GH-SEC-09 | P2 | settings.py:50-59 | Адмінка без lockout (немає django-axes) | django-axes (5 спроб, 1 год) | Cursor Coder |
| GH-SEC-10 | P3 | views.py:73-90 | Немає time-trap. Довжина email явно не обмежена: адреса >254 символів пройде валідатор і на Postgres дасть DataError і 500 | Перевірка len<=254; приховане поле з timestamp, мінімум 2 с | Cursor Coder |
| GH-SEC-11 | P3 | settings.py:153 | check --deploy: W021 (HSTS_PRELOAD=False) | Свідомо, можна лишити | — |

## CSP для Deploy Ops (nginx, server 443)
```
server_tokens off;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; media-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'" always;
add_header X-Content-Type-Options nosniff always;
add_header Referrer-Policy same-origin always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
location ~ /\.(?!well-known) { deny all; }
```
(Відео віддається з /static/assets/video/ (self), шрифти з Google Fonts. Скрипт static/script.js, inline-скрипти не знайдено; перед вмиканням CSP перевірити inline style у шаблоні.)

## Що зробити до запуску
1. Оновити Django до >=5.2.17 і python-dotenv до >=1.2.2 (GH-SEC-01).
2. Виправити визначення IP у nginx і views (GH-SEC-02).
3. Fail-closed для SECRET_KEY і IP_HASH_SALT (GH-SEC-03).
4. limit_req у nginx + спільний кеш (GH-SEC-04).
5. Увімкнути SSL-блок, редирект 80→443, HSTS, заголовки і CSP (GH-SEC-05/06).
6. Налаштувати бекап Postgres з offsite-копією (GH-SEC-07).
7. Додати текст згоди, політику і ретенцію (GH-SEC-08).
8. Закомітити бекенд і пройти повторний аудит по фінальному sha.

## Перевірено, працює правильно
- CSRF: csrf_exempt немає, {% csrf_token %} у index.html:71, X-CSRFToken у script.js:97, ensure_csrf_cookie views.py:25.
- Honeypot `website` (views.py:70), відповідь однакова, без витоку (дубль/бот → той самий success). Відправки листів немає, отже header injection не загрожує.
- Дедуп: unique + UniqueConstraint(Lower(email)) у models.py:17-22, lower() при збереженні.
- DEBUG за замовчуванням False (settings.py:16); ALLOWED_HOSTS ≠ * ; CSRF_TRUSTED_ORIGINS задано; SECURE_SSL_REDIRECT, cookie Secure, SECURE_PROXY_SSL_HEADER, X_FRAME_OPTIONS=DENY, nosniff.
- ADMIN_URL з env: так, ≠ admin/: так (fail-closed у проді, settings.py:40-48). У robots і sitemap адмінку не згадано.
- client_max_body_size 128k (gestia.conf:9).
- docker-compose.prod.yml: порт 5432 не публікується; POSTGRES_PASSWORD береться з env з `:?`, тобто без дефолту (рядок 8).
- .env у .gitignore; .env.example містить лише назви змінних: SECRET_KEY, DEBUG, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, DATABASE_URL, ADMIN_URL, SITE_URL, IP_HASH_SALT, SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS, POSTGRES_DB/USER/PASSWORD. В історії git секретів не знайдено.
- check --deploy з фейковими env: лише W021.
- Експорт CSV лише через admin action (потрібен вхід в адмінку).

## Не перевірено
- Прод-домен: не живий. gestia-home.com стоїть на паркуванні nic.ua (HTTP 500, Server: Pingora; HTTPS не відповідає; сертифікат *.nic.ua). Тому SSL, 80→443, HSTS і реальні заголовки не перевірені.
- Сервер, реальний .env, superuser і ролі (клієнт = is_staff + група) не перевіряв: SSH не надано, БД не читав.
- Фінальний Dockerfile, docs/DEPLOY_uk.md і gestia.conf ще дописувались, перевірено зріз на ~17:20.
- Значення в .env.example на плейсхолдерність не перевірялись (лише назви змінних).
