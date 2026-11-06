#!/bin/bash
set -euo pipefail

name=shirube-restore-drill
course_tables=(course_sections syllabi syllabus_codes syllabus_chunks embeddings)

log() {
	echo "$(date '+%F %T') $*"
}

production() {
	docker compose -f compose.prod.yaml exec -T db psql -U shirube -d shirube -tAc "$1"
}

drill() {
	docker exec "$name" psql -h 127.0.0.1 -U shirube -d shirube -tAc "$1"
}

remove_drill() {
	docker rm -f "$name" > /dev/null 2>&1 || true
}

main() {
	cd "$(dirname "$(readlink -f "$0")")"
	local dump
	dump=$(find "$HOME/backups" -name 'shirube-*.dump' | sort | tail -n 1)
	[ -n "$dump" ] || {
		log "バックアップが無い"
		exit 1
	}
	trap remove_drill EXIT
	remove_drill

	local started
	started=$(date +%s)
	docker run -d --name "$name" --network none \
		-e POSTGRES_USER=shirube -e POSTGRES_PASSWORD=drill -e POSTGRES_DB=shirube \
		pgvector/pgvector:pg16 > /dev/null
	until drill "select 1" > /dev/null 2>&1; do
		sleep 1
	done
	docker exec -i "$name" pg_restore -h 127.0.0.1 -U shirube -d shirube --no-owner --exit-on-error < "$dump"
	local restored_from
	restored_from=$(drill "select version_num from alembic_version")
	local migration
	if ! migration=$(docker run --rm --network "container:$name" \
		-e DATABASE_URL=postgresql+psycopg://shirube:drill@127.0.0.1:5432/shirube \
		shirube-prod-backend:latest uv run --no-sync alembic upgrade head 2>&1); then
		log "戻したものにマイグレーションを流せなかった"
		echo "$migration"
		exit 1
	fi
	local seconds=$(($(date +%s) - started))

	local failures=0 table expected actual schema
	expected=$(production "select version_num from alembic_version")
	schema=$(drill "select version_num from alembic_version")
	if [ "$expected" != "$schema" ]; then
		log "スキーマの版が違う: 本番 $expected、戻したもの $schema"
		failures=$((failures + 1))
	fi
	for table in "${course_tables[@]}"; do
		expected=$(production "select count(*) from $table")
		actual=$(drill "select count(*) from $table")
		if [ "$expected" != "$actual" ]; then
			log "$table の行の数が違う: 本番 $expected、戻したもの $actual"
			failures=$((failures + 1))
		fi
	done
	local people plans
	people=$(drill "select count(*) from users")
	plans=$(drill "select count(*) from plans")

	if [ "$failures" -gt 0 ]; then
		log "$(basename "$dump") の戻しの演習で $failures か所が合わなかった"
		exit 1
	fi
	log "$(basename "$dump") を ${seconds} 秒で戻した(スキーマ $restored_from から $schema へ、科目の表は本番と同じ、利用者 $people 人、道標 $plans 件)"
}

main "$@"
