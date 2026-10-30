# 0077. frontend は自分の URL を AUTH_URL で Auth.js に渡す

- ステータス: 承認
- 日付: 2026-10-31

## 文脈

- 本番を出したところ、Google のログインが `redirect_uri_mismatch` で失敗し、`https://localhost:3000/login?error=Configuration` に飛ばされた
- Next はリクエストの URL を、待ち受けの `localhost:3000` で組む。ログインを始めるサーバーアクションでは、Auth.js が転送のヘッダー(Caddy が付ける `X-Forwarded-Host` と `X-Forwarded-Proto`)から `https://shirube.duckdns.org` を組むので Google の画面までは進むが、戻り先の Route Handler ではリクエストの URL から `https://localhost:3000` を組み、Google にコードを引き換えに行って断られていた。`/api/auth/providers` の `callbackUrl` でも同じずれが見える
- 開発用のサーバー(`next dev`)も、届いた名前やポートを見ずに待ち受けの名前とポートで組む(`Host: localhost:3001` でも `Host: 192.168.0.5:3001` でも、戻り先は待ち受けの `localhost:3007` だった)。開発用の compose は、`FRONTEND_PORT` を変えるとブラウザのポートとコンテナの中の 3000 がずれる。LAN の IP で開いたときのログインは、もともと `localhost` に戻される
- ADR 0039 は、送り元の確かめで `Origin` を `AUTH_URL` と照らす案を、自分の URL を設定しなくてよいことを理由の 1 つにして採らず、`Sec-Fetch-Site` と、無ければ `Origin` と `X-Forwarded-Host` を照らす形にした

## 検討した選択肢

- `AUTH_URL` に自分の URL を渡す(Auth.js の決まった直し方)
- Next にリクエストの URL を転送のヘッダーから組ませる(Next にその設定が無く、自前の処理が要る)

## 決定

- 本番の compose で、frontend に `SITE_URL` と同じ `https://${SITE_DOMAIN}` を `AUTH_URL` として渡す。3 か所(ビルドの SITE_URL、動かすときの SITE_URL と AUTH_URL)は YAML のアンカーで 1 つの値にする。`AUTH_URL` があれば Auth.js が転送のヘッダーを信じる設定(`trustHost`)を自分で有効にするので、`AUTH_TRUST_HOST` は外す
- 開発用の compose では、`AUTH_URL` に `http://localhost:${FRONTEND_PORT}` を渡す(手元の `AUTH_URL` があればそれを使い、127.0.0.1 やトンネルの URL で開くときに替えられる)。`SITE_URL` とは切り離し、OG や sitemap の確かめのために `SITE_URL` を本番に替えても、ログインは手元のままにする
- e2e も、本番と同じに `AUTH_URL` で動かす
- CI の production の job は、`SITE_DOMAIN` を Next の待ち受けと違う名前の `shirube.localhost`(Caddy が内部の証明書を出す)にし、`/api/auth/providers` の `callbackUrl` が `https://shirube.localhost/api/auth/callback/google` かを確かめる。名前とポートのどちらを取り違えても落ちる
- ADR 0039 の送り元の確かめは変えない。本番の Caddy は `SITE_DOMAIN` の 1 つの名前だけを受け、`X-Forwarded-Host` をその名前で付けるので、送り元の確かめが見るホストと `AUTH_URL` のホストは食い違わない。ほとんどのブラウザは `Sec-Fetch-Site` を送り、こちらはホストを見ない

## 理由

- Auth.js が戻り先とクッキーの名前を 1 つの URL から決めるようになり、プロキシやポートの違いに左右されない
- CI の試しの構成でも、`AUTH_URL` が無いと戻り先が `https://localhost:3000` になるので、同じ不具合を本番の前に見つけられる

## 受け入れたトレードオフ

- 自分の URL を `SITE_DOMAIN` から決めるので、独自のドメインに移るときは `.env` の `SITE_DOMAIN` を替えてビルドし直す(ADR 0075 のとおり)。替え忘れると、ログインの戻り先も古い名前になる
- 送り元の確かめ(転送のヘッダー)と Auth.js(`AUTH_URL`)が、自分の名前を別のところから得る。今は Caddy が 1 つの名前だけを受けるので食い違わない

## 再検討する条件

- 1 つのサーバーで複数の名前を受けるか、Caddy の前にほかのプロキシを置くとき(送り元の確かめも `AUTH_URL` と照らすかを決める)
