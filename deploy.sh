#!/bin/bash
set -eEuo pipefail

registry=ghcr.io/h11roki
services=(backend frontend)
deployed_file="$HOME/deploy.version"
failed_file="$HOME/deploy.failed"
held_file="$HOME/deploy.held"

log() {
	echo "$(date '+%F %T') $*"
}

compose() {
	docker compose -f compose.prod.yaml "$@"
}

published() {
	local service output
	for service in "${services[@]}"; do
		if ! output=$(docker manifest inspect "$registry/shirube-$service:$1" 2>&1 > /dev/null); then
			case "$output" in
				*"no such manifest"* | *"manifest unknown"*) return 1 ;;
			esac
			log "GHCR の $service のイメージを確かめられなかった: $output"
			exit 1
		fi
	done
}

prepare_images() {
	local service
	for service in "${services[@]}"; do
		docker image inspect "shirube-prod-$service:$deployed" > /dev/null 2>&1 ||
			docker tag "shirube-prod-$service:latest" "shirube-prod-$service:$deployed"
		if git diff --quiet "$deployed" "$target" -- "$service" .github/workflows/ci.yml; then
			docker tag "shirube-prod-$service:$deployed" "shirube-prod-$service:$target"
		else
			docker pull --quiet "$registry/shirube-$service:$target" > /dev/null
			docker tag "$registry/shirube-$service:$target" "shirube-prod-$service:$target"
			docker rmi "$registry/shirube-$service:$target" > /dev/null
		fi
	done
}

switch_to() {
	local service
	for service in "${services[@]}"; do
		docker tag "shirube-prod-$service:$1" "shirube-prod-$service:latest"
	done
	echo "APP_VERSION=$1" > .env.version
}

keep_images() {
	local service tag
	for service in "${services[@]}"; do
		docker images "shirube-prod-$service" --format '{{.Tag}}' | grep -E '^[0-9a-f]{40}$' |
			while read -r tag; do
				case " $* " in
					*" $tag "*) ;;
					*) docker rmi "shirube-prod-$service:$tag" > /dev/null ;;
				esac
			done
	done
	docker image prune -f > /dev/null
}

bring_up() {
	compose up -d --no-build --wait --wait-timeout 180 || return 1
	if ! git diff --quiet "$1" "$2" -- Caddyfile; then
		compose up -d --no-build --no-deps --force-recreate caddy || return 1
	fi
}

answering() {
	local site resolve health
	site=$(compose config caddy | sed -n 's/^ *SITE_DOMAIN: *//p')
	resolve=(--resolve "$site:443:127.0.0.1")
	curl "${resolve[@]}" -fsS --retry 10 --retry-all-errors --retry-delay 3 -o /dev/null "https://$site/" &&
		test "$(curl "${resolve[@]}" -sS -o /dev/null -w '%{http_code}' "https://$site/api/plans")" = 401 &&
		curl "${resolve[@]}" -fsS "https://$site/robots.txt" | grep -qF "Sitemap: https://$site/sitemap.xml" &&
		health=$(curl "${resolve[@]}" -fsS --retry 10 --retry-all-errors --retry-delay 3 "https://$site/api/health") &&
		[[ "$health" == *"\"version\":\"$target\""* && "$health" == *'"database":"ok"'* ]]
}

fail() {
	echo "$target" > "$failed_file"
	log "$1"
	exit 1
}

roll_back() {
	echo "$target" > "$failed_file"
	git reset --keep --quiet "$deployed"
	switch_to "$deployed"
	bring_up "$target" "$deployed" || log "$deployed も応えない"
	keep_images "$deployed" || log "古いイメージを消せなかった"
	fail "$1"
}

main() {
	cd "$(dirname "$0")"
	exec 9> "$HOME/deploy.lock"
	flock -n 9 || exit 0
	[ -e "$held_file" ] && exit 0

	[ -e "$deployed_file" ] || git rev-parse HEAD > "$deployed_file"
	deployed=$(cat "$deployed_file")
	if ! git fetch --quiet origin main 2> /dev/null; then
		log "origin の main を取れなかった"
		exit 1
	fi
	target=$(git rev-parse origin/main)
	[ "$deployed" = "$target" ] && exit 0
	[ "$(cat "$failed_file" 2> /dev/null)" = "$target" ] && exit 0
	published "$target" || exit 0

	log "$deployed から $target に入れ替える"
	trap 'log "$target の入れ替えが途中で止まった(終了コード $?)"' ERR
	prepare_images
	git merge --ff-only --quiet "$target" || fail "git を $target に進められなかった"
	if [ -z "${DEPLOY_RESTARTED:-}" ] && ! git diff --quiet "$deployed" "$target" -- deploy.sh; then
		log "deploy.sh が変わったので、新しい deploy.sh で初めからやり直す"
		DEPLOY_RESTARTED=1 exec "$0"
	fi
	switch_to "$target"

	local migrated=false
	if ! git diff --quiet "$deployed" "$target" -- backend/migrations; then
		migrated=true
		compose stop backend worker
		compose run --rm backend uv run --no-sync alembic upgrade head ||
			roll_back "マイグレーションに失敗したので $deployed に戻した"
	fi

	if bring_up "$deployed" "$target" && answering; then
		echo "$target" > "$deployed_file"
		rm -f "$failed_file"
		log "$target に入れ替えた"
		keep_images "$target" "$deployed" || log "古いイメージを消せなかった"
		return
	fi
	if "$migrated"; then
		echo "$target" > "$held_file"
		log "$target が応えない。マイグレーションを流したので戻さず、$held_file を消すまで入れ替えを止める"
		exit 1
	fi
	roll_back "$target が応えないので $deployed に戻した"
}

main "$@"
