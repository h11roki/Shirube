#!/bin/bash
set -euo pipefail

name=shirube-restore-drill
changing_tables="'alembic_version', 'users', 'plans', 'taken_courses', 'deleted_plans', 'plan_builds', 'remembered_recommendations'"
newest_backup_minutes=1380
ready_seconds=60
deploy_wait_seconds=1800

log() {
	echo "$(date '+%F %T') $*"
}

production() {
	docker compose -f compose.prod.yaml exec -T db psql -U shirube -d shirube -tAc "$1"
}

drill() {
	docker exec "$name" psql -h 127.0.0.1 -U shirube -d shirube -tAc "$1"
}

running_image() {
	docker inspect -f '{{.Image}}' "$(docker compose -f compose.prod.yaml ps -q "$1")"
}

remove_drill() {
	docker rm -f -v "$name" > /dev/null 2>&1 || true
}

main() {
	cd "$(dirname "$(readlink -f "$0")")"
	exec 9> "$HOME/deploy.lock"
	flock -w "$deploy_wait_seconds" 9 || {
		log "入れ替えが終わらないので演習しなかった"
		exit 1
	}
	local dump
	dump=$(find "$HOME/backups" -name 'shirube-*.dump' -mmin "-$newest_backup_minutes" | sort | tail -n 1)
	[ -n "$dump" ] || {
		log "23 時間より新しいバックアップが無い"
		exit 1
	}
	trap 'log "$(basename "$dump") の演習が途中で止まった(終了コード $?)"' ERR
	trap remove_drill EXIT
	remove_drill

	local started waited
	started=$(date +%s)
	docker run -d --name "$name" --network none --memory 512m \
		--tmpfs /var/lib/postgresql/data:size=256m \
		-e POSTGRES_USER=shirube -e POSTGRES_PASSWORD=drill -e POSTGRES_DB=shirube \
		"$(running_image db)" > /dev/null
	for ((waited = 0; ; waited++)); do
		drill "select 1" > /dev/null 2>&1 && break
		if [ "$waited" -ge "$ready_seconds" ] || [ "$(docker inspect -f '{{.State.Running}}' "$name")" != true ]; then
			log "演習の Postgres が起動しなかった"
			docker logs --tail 20 "$name"
			exit 1
		fi
		sleep 1
	done
	docker exec -i "$name" pg_restore -h 127.0.0.1 -U shirube -d shirube --no-owner --single-transaction < "$dump"
	local restored_from migration
	restored_from=$(drill "select version_num from alembic_version")
	if ! migration=$(docker run --rm --network "container:$name" \
		-e DATABASE_URL=postgresql+psycopg://shirube:drill@127.0.0.1:5432/shirube \
		"$(running_image backend)" uv run --no-sync alembic upgrade head 2>&1); then
		log "戻したものにマイグレーションを流せなかった"
		echo "$migration"
		exit 1
	fi
	local seconds=$(($(date +%s) - started))

	local expected schema tables counts expected_counts actual_counts
	expected=$(production "select version_num from alembic_version")
	schema=$(drill "select version_num from alembic_version")
	if [ "$expected" != "$schema" ]; then
		log "スキーマの版が違う: 本番 $expected、戻したもの $schema"
		exit 1
	fi
	tables=$(production "select tablename from pg_tables where schemaname = 'public' and tablename not in ($changing_tables) order by 1")
	counts=$(echo "$tables" | sed "s/.*/select '&', count(*) from &/" | paste -sd '|' - | sed 's/|/ union all /g')
	expected_counts=$(production "$counts order by 1")
	actual_counts=$(drill "$counts order by 1")
	if [ "$expected_counts" != "$actual_counts" ]; then
		log "表の行の数が違う: $(diff <(echo "$expected_counts") <(echo "$actual_counts") | grep '^[<>]' | paste -sd ' ' -)"
		exit 1
	fi
	local people plans
	people=$(drill "select count(*) from users")
	plans=$(drill "select count(*) from plans")
	log "$(basename "$dump") を ${seconds} 秒で戻した(スキーマ $restored_from から $schema へ、利用者の表を除く $(echo "$tables" | wc -l) 表は本番と同じ、利用者 $people 人、道標 $plans 件)"
}

main "$@"
