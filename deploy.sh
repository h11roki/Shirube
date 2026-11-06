#!/bin/bash
set -euo pipefail

registry=ghcr.io/h11roki
services=(backend frontend)
failed_file="$HOME/deploy.failed"

log() {
	echo "$(date '+%F %T') $*"
}

compose() {
	docker compose -f compose.prod.yaml "$@"
}

published() {
	local service
	for service in "${services[@]}"; do
		docker manifest inspect "$registry/shirube-$service:$1" > /dev/null 2>&1 || return 1
	done
}

serving() {
	local site resolve
	site=$(sed -n 's/^SITE_DOMAIN=//p' .env)
	resolve=(--resolve "$site:443:127.0.0.1")
	compose up -d --no-build --wait --wait-timeout 180 &&
		curl "${resolve[@]}" -fsS --retry 10 --retry-all-errors --retry-delay 3 -o /dev/null "https://$site/" &&
		test "$(curl "${resolve[@]}" -sS -o /dev/null -w '%{http_code}' "https://$site/api/plans")" = 401
}

give_up() {
	echo "$target" > "$failed_file"
	log "$1"
	exit 1
}

roll_back() {
	local service
	git reset --hard --quiet "$current"
	for service in "${services[@]}"; do
		docker tag "shirube-prod-$service:previous" "shirube-prod-$service:latest"
	done
	compose up -d --no-build
	give_up "$1"
}

main() {
	cd "$(dirname "$0")"
	exec 9> "$HOME/deploy.lock"
	flock -n 9 || exit 0

	git fetch --quiet origin main
	current=$(git rev-parse HEAD)
	target=$(git rev-parse origin/main)
	[ "$current" = "$target" ] && exit 0
	[ "$(cat "$failed_file" 2> /dev/null)" = "$target" ] && exit 0
	published "$target" || exit 0

	log "$current から $target に入れ替える"
	local service
	for service in "${services[@]}"; do
		docker pull --quiet "$registry/shirube-$service:$target" > /dev/null
	done
	git merge --ff-only --quiet "$target" || give_up "git を $target に進められなかった"
	for service in "${services[@]}"; do
		docker tag "shirube-prod-$service:latest" "shirube-prod-$service:previous"
		docker tag "$registry/shirube-$service:$target" "shirube-prod-$service:latest"
		docker rmi "$registry/shirube-$service:$target" > /dev/null
	done

	local migrated=false
	if ! git diff --quiet "$current" "$target" -- backend/migrations; then
		migrated=true
		compose stop backend worker
		compose run --rm backend uv run --no-sync alembic upgrade head ||
			roll_back "マイグレーションに失敗したので $current に戻した"
	fi

	if serving; then
		rm -f "$failed_file"
		docker image prune -f > /dev/null
		log "$target に入れ替えた"
		return
	fi
	if "$migrated"; then
		give_up "$target が応えない。マイグレーションを流したので戻さずに止めた"
	fi
	roll_back "$target が応えないので $current に戻した"
}

main "$@"
