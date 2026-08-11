#!/bin/sh
set -e
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"
mkdir -p "$BACKUP_DIR"
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-lead}" "${POSTGRES_DB:-lead}" > "$FILE"
echo "Backup saved to $FILE"