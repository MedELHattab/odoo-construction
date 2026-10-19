#!/usr/bin/env bash
# Backup the Odoo database and filestore into ./backups (run from project root).
# Usage: bash scripts/backup.sh   (keeps the 14 most recent backups)
set -euo pipefail
export MSYS_NO_PATHCONV=1  # stop Git Bash on Windows rewriting container paths
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a

mkdir -p backups
stamp=$(date +%Y%m%d-%H%M%S)

docker compose exec -T db pg_dump -U "$POSTGRES_USER" -Fc "$ODOO_DB" > "backups/${ODOO_DB}-${stamp}.dump"
docker compose exec -T odoo tar -C /var/lib/odoo -czf - . > "backups/filestore-${stamp}.tar.gz"

ls -1t backups/*.dump 2>/dev/null | tail -n +15 | xargs -r rm --
ls -1t backups/filestore-*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm --
echo "Backup written: backups/${ODOO_DB}-${stamp}.dump"
