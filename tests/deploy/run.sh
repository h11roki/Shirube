#!/bin/bash
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
deploy_script="$here/../../deploy.sh"
export PATH="$here/shims:$PATH"
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
failures=0

check() {
	if eval "$2"; then echo "  ok: $1"; else echo "  NG: $1"; failures=$((failures + 1)); fi
}

setup() {
	HOME=$(mktemp -d)
	export HOME
	git init -q --bare -b main "$HOME/origin.git"
	git clone -q "$HOME/origin.git" "$HOME/work" 2> /dev/null
	cd "$HOME/work" || exit 1
	mkdir -p backend/migrations frontend
	cp "$deploy_script" deploy.sh
	echo v1 > Caddyfile
	echo m1 > backend/migrations/0001.py
	echo api1 > backend/app.py
	echo page1 > frontend/page.tsx
	git add -A && git commit -qm one && git push -q origin main
	git clone -q "$HOME/origin.git" "$HOME/Shirube" 2> /dev/null
	echo "SITE_DOMAIN=shirube.example" > "$HOME/Shirube/.env"
	old=$(git rev-parse HEAD)
	printf 'shirube-prod-backend:latest id-local\nshirube-prod-frontend:latest id-local\n' > "$HOME/images"
	: > "$HOME/published"
	: > "$HOME/calls"
}

push_change() {
	cd "$HOME/work" || exit 1
	echo "$2" > "$1"
	git add -A && git commit -qm change && git push -q origin main
	new=$(git rev-parse HEAD)
	echo "$new" >> "$HOME/published"
	cd "$HOME/Shirube" || exit 1
}

deploy() {
	"$HOME/Shirube/deploy.sh" >> "$HOME/log" 2>&1
	status=$?
}

exited() { [ "$status" = "$1" ]; }
latest() { awk -v name="shirube-prod-$1:latest" '$1 == name { print $2 }' "$HOME/images"; }
head_is() { [ "$(git -C "$HOME/Shirube" rev-parse HEAD)" = "$1" ]; }
deployed_is() { [ "$(cat "$HOME/deploy.version")" = "$1" ]; }

echo "A 初回: backend だけ変わった版を入れ替える"
setup; push_change backend/app.py api2; deploy
check "終了 0" 'exited 0'
check "HEAD と deploy.version が新しい版" 'head_is $new && deployed_is $new'
check "backend は取ったイメージ" '[ "$(latest backend)" = id-$new ]'
check "変わっていない frontend は取らずに前のイメージを使う" '[ "$(latest frontend)" = id-local ] && ! grep -q "pull --quiet ghcr.io/h11roki/shirube-frontend" $HOME/calls'
check "前の版の札を残す" 'grep -q "shirube-prod-backend:$old id-local" $HOME/images'
check "GHCR の名前は外す" '! grep -q ghcr.io $HOME/images'
check "backend と worker を止めない" '! grep -q "compose -f compose.prod.yaml stop" $HOME/calls'
check "caddy を作り直さない" '! grep -q force-recreate $HOME/calls'
check "入れ替えたと書く" 'grep -q "に入れ替えた" $HOME/log'
deploy
check "2 回目は何もしない" 'exited 0 && [ $(grep -c "入れ替える" $HOME/log) = 1 ]'

echo "B イメージがまだ無い"
setup; push_change backend/app.py api2; : > "$HOME/published"; deploy
check "終了 0 で何も書かない" 'exited 0 && [ ! -s $HOME/log ] && head_is $old'

echo "C GHCR に断られる"
setup; push_change backend/app.py api2; MANIFEST=denied deploy
check "終了 1 で理由を書く" 'exited 1 && grep -q "確かめられなかった" $HOME/log && head_is $old'

echo "D 起動しないので戻す(マイグレーション無し)"
setup; push_change backend/app.py api2; UP_FAIL=1 deploy
check "終了 1" 'exited 1'
check "HEAD とイメージを前の版に戻す" 'head_is $old && [ "$(latest backend)" = id-local ] && deployed_is $old'
check "失敗した版を覚える" '[ "$(cat $HOME/deploy.failed)" = $new ]'
check "失敗した版のイメージを消す" '! grep -q "shirube-prod-backend:$new" $HOME/images'
check "戻したと書く" 'grep -q "に戻した" $HOME/log'
: > "$HOME/log"; deploy
check "同じ版は試さない" 'exited 0 && [ ! -s $HOME/log ]'
push_change backend/app.py api3; deploy
check "次の版は入れ替える" 'exited 0 && deployed_is $new && [ ! -e $HOME/deploy.failed ]'

echo "E マイグレーションに失敗して戻す"
setup; push_change backend/migrations/0002.py m2; MIGRATE_FAIL=1 deploy
check "終了 1 で HEAD とイメージを戻す" 'exited 1 && head_is $old && [ "$(latest backend)" = id-local ]'
check "backend と worker を止めた" 'grep -q "compose -f compose.prod.yaml stop backend worker" $HOME/calls'

echo "F マイグレーションを流した版が応えないときは戻さず、消すまで止める"
setup; push_change backend/migrations/0002.py m2; failed_version=$new; UP_FAIL=1 deploy
check "終了 1 で HEAD は新しい版のまま" 'exited 1 && head_is $new && deployed_is $old'
check "止めたと書く" 'grep -q "入れ替えを止める" $HOME/log && [ "$(cat $HOME/deploy.held)" = $new ]'
push_change backend/app.py fix; deploy
check "止めているあいだは次の版も入れ替えない" "exited 0 && head_is $failed_version"
rm "$HOME/deploy.held"; deploy
check "消すと main の先頭を入れ替える" 'exited 0 && deployed_is $new && [ "$(latest backend)" = id-$new ]'

echo "G Caddyfile が変わった版は caddy を作り直す"
setup; push_change Caddyfile v2; deploy
check "終了 0 で caddy を作り直し、イメージは取らない" 'exited 0 && grep -q "force-recreate caddy" $HOME/calls && ! grep -q "docker pull" $HOME/calls'

echo "H frontend に入った URL がサーバーの設定と違う"
setup; push_change frontend/page.tsx page2; ROBOTS_SITE=other.example deploy
check "終了 1 で戻す" 'exited 1 && head_is $old && [ "$(latest frontend)" = id-local ]'

echo "I 途中で止まった版を次に試し直す"
setup; push_change backend/app.py api2
git -C "$HOME/Shirube" merge -q --ff-only origin/main
printf 'shirube-prod-backend:latest id-%s\nshirube-prod-frontend:latest id-local\nshirube-prod-backend:%s id-local\nshirube-prod-frontend:%s id-local\n' "$new" "$old" "$old" > "$HOME/images"
echo "$old" > "$HOME/deploy.version"; deploy
check "前の版の札を新しいイメージで上書きしない" 'grep -q "shirube-prod-backend:$old id-local" $HOME/images'
check "入れ替える" 'exited 0 && deployed_is $new'

echo "J トップが応えないので戻す"
setup; push_change backend/app.py api2; CURL_FAIL=1 deploy
check "終了 1 で戻す" 'exited 1 && head_is $old && [ "$(latest backend)" = id-local ]'

echo
echo "failures: $failures"
[ "$failures" = 0 ]
