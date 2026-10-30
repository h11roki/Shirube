#!/bin/sh
set -eu
umask 077
cd "$(dirname "$0")"
backups="$HOME/backups"
mkdir -p "$backups"
exec 9>"$backups/backup.lock"
if ! flock -n 9; then
	echo "$(date '+%F %T') 前のバックアップがまだ動いている" >&2
	exit 1
fi
find "$backups" -name 'shirube-*.dump*' -mmin +10080 -delete
file="$backups/shirube-$(date +%F).dump"
docker compose -f compose.prod.yaml exec -T db pg_dump -U shirube -Fc shirube > "$file.partial"
mv "$file.partial" "$file"
ls -1t "$backups"/shirube-*.dump | tail -n +8 | xargs -r rm -f
echo "$(date '+%F %T') $file"
