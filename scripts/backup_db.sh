#!/usr/bin/env bash
# Щоденний бекап Postgres для Gestia Home (gzip + ротація 14 днів).
# Запуск на хості (не всередині контейнера web).
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/gestia}"
KEEP_DAYS="${KEEP_DAYS:-14}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${BACKUP_DIR}/gestia_${STAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"
cd "${PROJECT_DIR}"

docker compose -f "${COMPOSE_FILE}" exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl' \
  | gzip -c > "${OUT}"

chmod 600 "${OUT}"

find "${BACKUP_DIR}" -type f -name 'gestia_*.sql.gz' -mtime "+${KEEP_DAYS}" -delete

echo "OK: ${OUT}"
