#!/usr/bin/env bash
set -euo pipefail

backend_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$backend_dir"

if [[ ! -f .env.oracle ]]; then
  echo ".env.oracle is missing" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env.oracle
set +a

backup_dir="${1:-$backend_dir/backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_dir"

docker compose --env-file .env.oracle -f docker-compose.oracle.yml exec -T db \
  pg_dump --format=custom --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  > "$backup_dir/postgres-$timestamp.dump"

tar -czf "$backup_dir/files-$timestamp.tar.gz" chroma_db static

echo "Backup created in $backup_dir"
