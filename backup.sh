#!/bin/sh
set -eu
cd "$(dirname "$0")"
backups="$HOME/backups"
mkdir -p "$backups"
file="$backups/shirube-$(date +%F).dump"
docker compose -f compose.prod.yaml exec -T db pg_dump -U shirube -Fc shirube > "$file.partial"
mv "$file.partial" "$file"
find "$backups" -name 'shirube-*.dump' -mtime +6 -delete
echo "$(date '+%F %T') $file"
