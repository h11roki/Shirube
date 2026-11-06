# 0095. 本番の様子は health の API にまとめ、GitHub Actions の定期実行が 15 分ごとに外から確かめて、落ちたら GitHub のメールで知らせる

- ステータス: 承認
- 日付: 2026-11-07

## 文脈

- 本番が止まっても、OpenAI の残高が尽きても、知る手段がなかった。残高切れは、作った記録(ADR 0087)をサーバーの CLI で見て初めて分かる
- `/api/v1/health` はあったが、`{"status": "ok"}` を返すだけで、DB にも触れていない
- ADR 0094 の自動の入れ替えは、backend が 8000 番に繋がるかしか確かめておらず、マイグレーションを流した版で止まったとき(`~/deploy.held`)や、GHCR から取れないときに、誰も気づかない
- 高橋さんは、監視と知らせを GitHub Actions だけで行う案を選んだ(Sentry を足す案と比べて)。お金はかけず、新しいアカウントを作らず、外へ送るデータを増やさない(プライバシーポリシーを変えない)

## 検討した選択肢

1. GitHub Actions だけ: backend の health の API に、DB、待ちの滞り、残高切れ、動いている版をまとめ、Actions の定期実行が外からトップ、API、health、証明書の期限、main との追いつきを確かめる。落ちたら Actions の失敗のメールで知る
2. 1 に加えて Sentry: 例外を Sentry に送り、スタックトレースで追う。アカウントを作り、例外の中身を外(米国)へ送るので、ポリシーと ADR を直す

## 決定

高橋さんが 1 を選んだ。

- `GET /api/v1/health`(ログイン不要)は、`status`(ok / degraded / down)、`version`(動いている commit)、`database`(ok / down)、`queue`(ok / stalled / unknown)、`openai`(ok / out_of_credit / unknown)を返す
  - database: 待ちの道標と作った記録を読めれば ok。読めなければ down で、HTTP は 503(ほかは unknown)
  - queue: 待ちの道標のうち一番古いものが `PLAN_STALL_MINUTES`(既定 20 分)より長く待っていれば stalled(worker が止まっている)
  - openai: 直近 1 日の最後に作り終えた道標が、残高切れ(`insufficient_quota`)で失敗していれば out_of_credit。残高を足して次に成功すれば ok に戻る
  - status: database が down なら down、queue か openai に問題があれば degraded、ほかは ok。degraded でも HTTP は 200(サービスは応えている)
  - version: `deploy.sh` がサーバーのリポジトリ直下の `.env.version`(`APP_VERSION=<commit>`、git の管理外)に書き、compose が backend にだけ渡す。無ければ `unknown`。worker には渡さないので、版が替わっても worker は作り直さない
- Caddy が `/api/health` を backend の `/api/v1/health` に直接渡す(frontend を通さない)
- `deploy.sh` は、入れ替えたあとに Caddy を通して health を読み、`version` が入れ替えた版で、`database` が ok かも確かめる。ADR 0094 で見送った、backend が DB を読めるかの確かめになる。queue と openai は入れ替えとは関係が無いので、見ない
- `.github/workflows/monitor.yml` を 15 分ごと(`7,22,37,52 * * * *`)と手で流す。トップが 200、ログインなしの API が 401、health の `status` が ok、証明書の残りが 14 日以上、本番の版が main の先頭と同じか、main の先頭の commit から 45 分以内か、を確かめる。どれかが通らなければ job が落ち、GitHub が定期実行の失敗をメールで知らせる(cron を最後に書き換えた人に届く)
- CI の production の job も、health が ok で `database` が ok、`version` が unknown(`.env.version` が無い)かを確かめる

## 理由

- お金も新しいアカウントも要らず、知らせは GitHub のメールで届く。監視の定義がリポジトリにあり、レビューと履歴に乗る
- 外へ送るのは公開しているページと health の結果だけで、利用者の情報は含まない
- 本番が main から遅れたままなのを外から見れば、CI の失敗、GHCR から取れない、`deploy.held`、cron の止まりを 1 つの確かめで拾える
- health の API を backend に置けば、`deploy.sh` と外の監視とが同じ物差しを使う

## 受け入れたトレードオフ

- 例外のスタックトレースは集めない。原因はサーバーの `docker compose logs` と、作った記録の失敗の種類(ADR 0087)で追う
- 知らせは最短でも 15 分、GitHub の定期実行の混み具合でさらに遅れる。公開リポジトリの定期実行は、リポジトリに 60 日動きが無いと止まる
- health は誰でも読める。DB に届くか、待ちが滞っているか、残高が切れているか、動いている commit は外から分かる(コードは公開しているので、秘密は無い)
- worker が止まっていても、待ちの道標が無ければ分からない。次に誰かが道標を頼んで 20 分経つと stalled になる
- 版を backend に渡すため、入れ替えのたびに backend を作り直す(数秒)。worker は作り直さない
- 残高切れは、残高が切れてから最初に道標を頼まれるまで分からない

## 再検討する条件

- 利用者が増え、15 分の遅れや、例外を後から追えないことが困るようになったとき(Sentry などを足す)
- 監視を GitHub の外(専用の外形監視)に移したくなったとき
