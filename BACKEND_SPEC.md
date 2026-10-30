# Backend spec — turn this static page into a minimal Django project (deploy-ready, NOT deployed)

Keep the existing visuals PIXEL-IDENTICAL: index.html markup/classes, styles.css, assets/ must render exactly as now. Move them: index.html -> templates/index.html (use {% static %} for asset URLs), styles.css/script.js/assets -> static/ (keep relative structure: static/styles.css, static/script.js, static/assets/...). Do not alter CSS rules or asset files. Remove old root copies after moving (git mv).

Stack: Django 5.2 LTS, Python 3.12 image, django-unfold, gunicorn, whitenoise (CompressedManifestStaticFilesStorage), psycopg[binary], dj-database-url (or env parsing), python-dotenv optional. requirements.txt pinned.
Project: config/ (settings, urls, wsgi), app `subscribers`.
Settings from env: SECRET_KEY, DEBUG (default False), ALLOWED_HOSTS (default "gestia-home.com,www.gestia-home.com"), CSRF_TRUSTED_ORIGINS (default https://gestia-home.com,https://www.gestia-home.com), DATABASE_URL (default sqlite for local dev), ADMIN_URL (required non-default path, e.g. env; default only in DEBUG "admin-local/"), SITE_URL=https://gestia-home.com, IP_HASH_SALT.
LANGUAGE_CODE="uk", TIME_ZONE="Europe/Kyiv". Unfold admin with SITE_TITLE/SITE_HEADER "Gestia Home".
Prod security when not DEBUG: SECURE_PROXY_SSL_HEADER, SESSION/CSRF_COOKIE_SECURE, SECURE_SSL_REDIRECT from env (default True), SECURE_HSTS_SECONDS from env (default 0, docs say raise to 31536000 after SSL works), HSTS include subdomains, X_FRAME_OPTIONS DENY, SECURE_CONTENT_TYPE_NOSNIFF, REFERRER_POLICY. CSP-friendly: no inline scripts/styles in template (script.js external; pass CSRF via cookie or a data-attribute/meta tag).

Model Subscriber: email EmailField unique (store lowercased+stripped; UniqueConstraint on Lower(email)), created_at auto_now_add, source CharField default "coming-soon", lang CharField default "uk", ip_hash CharField blank (sha256(salt+ip)), user_agent short optional. verbose_name uk ("Підписник","Підписники").

View POST /subscribe/ (JSON or form-encoded, CSRF protected): fields email, website (honeypot, hidden off-screen input in the form, tabindex -1, autocomplete off, aria-hidden). Honeypot filled -> return 200 same success (don't save). Validate with Django EmailValidator -> 400 {"ok":false,"message":"Будь ласка, введіть коректний e-mail"}. Duplicate -> 200 same success. Success: {"ok":true,"message":"Дякуємо! Ми повідомимо тебе першою, щойно бокси стануть доступними."}. Rate limit via Django cache: max 5 requests / 10 min per ip_hash -> 429 {"ok":false,"message":"Забагато спроб. Спробуйте пізніше."}. Use X-Forwarded-For first IP if present (behind nginx).
script.js: FORM_ENDPOINT = "/subscribe/" (or from form action), send fetch with X-CSRFToken header (token from csrftoken cookie or hidden csrfmiddlewaretoken input via {% csrf_token %}); show server message; keep client validation.
Index view: ensure_csrf_cookie.

Admin (Unfold ModelAdmin): list_display email, created_at, source, lang; search email; list_filter created_at (date), source; readonly created_at, ip_hash; date_hierarchy created_at; show total count (subtitle or changelist message "Всього: N"); action "Експортувати в CSV" (UTF-8 with BOM, columns email,created_at,source,lang).

SEO: <link rel=canonical href="https://gestia-home.com/">, og:url, og:image absolute https://gestia-home.com/static/assets/img/og-image.jpg (use SITE_URL setting via context processor). /robots.txt (allow all, Disallow nothing for admin path — don't reveal it; Sitemap: https://gestia-home.com/sitemap.xml) and simple /sitemap.xml with /. /favicon.ico served (redirect or whitenoise root).

Docker: Dockerfile (python:3.12-slim, non-root, collectstatic at build, entrypoint runs migrate then gunicorn config.wsgi -w 3 -b 0.0.0.0:8000). docker-compose.yml (dev: web + db postgres:16, env from .env). docker-compose.prod.yml (web, db with volume, nginx:alpine with nginx/conf.d/gestia.conf for gestia-home.com + www, proxy to web, /.well-known/acme-challenge for certbot webroot volume, ssl server block template commented/ready, certbot service). client_max_body_size small, gzip.
.env.example with placeholders only (no real secrets). .gitignore: .env, venv, __pycache__, staticfiles, db.sqlite3, .DS_Store.

docs/DEPLOY_uk.md (Ukrainian, step-by-step for owner): create DO droplet (Ubuntu 24.04, Docker), DNS A records at nic.ua for @ and www -> droplet IP, clone repo, cp .env.example .env and fill (generate SECRET_KEY command, choose own secret ADMIN_URL), docker compose -f docker-compose.prod.yml up -d --build, createsuperuser, certbot issuance via webroot, enable SSL block, raise HSTS. NEVER write a concrete admin URL or secrets.
README.md update (Ukrainian): local run (venv + sqlite: pip install -r requirements.txt, DEBUG=1 ADMIN_URL=... python manage.py migrate/runserver; or docker compose up).

Tests (subscribers/tests.py, Django TestCase): page renders 200 with form & canonical; valid submit creates subscriber; duplicate (different case) -> 200 success, still 1 row; invalid email -> 400; honeypot -> 200, 0 rows; rate limit -> 429; admin CSV export action returns csv with email (superuser client). Tests must pass with sqlite (DATABASE_URL unset).

Do not commit. Do not deploy. Do not push. Do not touch ../Gestia.
