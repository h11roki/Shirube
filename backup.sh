#!/bin/sh
set -eu
cd "$(dirname "$0")"
backups="$HOME/backups"
mkdir -p "$backups"
rm -f "$backups"/shirube-*.dump.partial
file="$backups/shirube-$(date +%F).dump"
docker compose -f compose.prod.yaml exec -T db pg_dump -U shirube -Fc shirube > "$file.partial"
mv "$file.partial" "$file"
ls -1t "$backups"/shirube-*.dump | tail -n +8 | xargs -r rm -f
echo "$(date '+%F %T') $file"
