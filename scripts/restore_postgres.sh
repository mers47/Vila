#!/bin/sh
set -e
if [ -z "$1" ]; then
  echo "Usage: $0 <backup-file.sql>"
  exit 1
fi
docker compose exec -T postgres psql -U "${POSTGRES_USER:-lead}" -d "${POSTGRES_DB:-lead}" < "$1"
echo "Restore complete from $1"