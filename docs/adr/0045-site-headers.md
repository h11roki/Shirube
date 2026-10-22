# 0045. セキュリティヘッダーは nonce 無しの CSP とほかのヘッダーを next.config で付け、検索はトップと規約・ポリシーだけに許し、共有のカードは行先表示の静的な画像にする

- ステータス: 承認
- 日付: 2026-10-22

## 文脈

本番の前の点検(テーマ D、画面の壊れにくさ)で、セキュリティヘッダーが何も付いておらず(`next.config.ts` に headers が無い)、favicon、OG 画像、manifest、robots.txt、sitemap がどれも 404 だった。公開は誰でも Google でログインして使える形(ADR 0038)で、道標の画面はログインが要る。本番の前段のプロキシ(TLS、HSTS)は本番化(ADR 0009 の見直し)で決める。

## 検討した選択肢

セキュリティヘッダー(特に CSP)

1. nonce 無しの CSP とほかのヘッダーを `next.config.ts` の headers で付ける。script は self と unsafe-inline(Next がインラインの script を出すため)、外部の script・接続・frame は禁止、frame-ancestors none、object none、base-uri self。今の作り(cacheComponents の静的な部分)を変えずに済むが、インラインの script を許したままなので XSS への守りは弱い
2. nonce 付きの厳しい CSP。middleware で nonce を作りインラインの script を nonce で限る。XSS に強いが、Next が nonce を使うには全ページを動的に描く必要があり、cacheComponents の静的な部分を手放す
3. CSP 以外のヘッダーだけ今回付け、CSP はプロキシを置く本番化で決める

OG 画像(共有したときのカード)

1. 行先表示の板の見た目の静的な PNG(1200×630)を `app/opengraph-image.png` に置く。決まった絵なので確かめやすく、ビルドにフォントの読み込みが要らない
2. `next/og` の `ImageResponse` で描く。ページごとに変えられるが、日本語フォントをビルドで読み込む必要があり重い
3. 画像は置かず title と description だけ

検索エンジン(robots.txt)

1. トップと規約・ポリシーだけ許す。`/api` と `/plans` と `/login` は拒否し、sitemap はその 3 ページを載せる
2. 全て許す(ログインが要る画面もクロールされ、無駄な要求が増える)
3. 全て拒否(検索から見つからない)

## 決定

高橋さんが選んだ。ヘッダーは 1、OG 画像は 1、検索は 1。

- `src/lib/security-headers.ts` がヘッダーの列を作り(純粋な関数で Vitest が確かめる)、`next.config.ts` の `headers` が全ての経路に付ける。CSP は `default-src 'self'`、`script-src 'self' 'unsafe-inline'`(開発中だけ `'unsafe-eval'`)、`style-src 'self' 'unsafe-inline'`(style 属性のため)、`img-src 'self' data: blob:`、`font-src 'self'`(next/font が自前で配る)、`connect-src 'self'`(開発用サーバーの WebSocket も同じオリジンなので `ws:` は要らない)、`frame-ancestors 'none'`、`object-src 'none'`、`base-uri 'self'`。`form-action` は付けない。Auth.js のログインはフォームの送信のあと Google へ 303 で移り、JavaScript が効かないときは素のフォームの送信になって Chrome が移った先にも form-action を当てるので、Google から大学などの SSO の IdP へさらに移る経路を止めてしまう。ほかに `X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`Referrer-Policy: strict-origin-when-cross-origin`、`Permissions-Policy: camera=(), microphone=(), geolocation=()`。HSTS と COOP は TLS を終える前段のプロキシで本番化のときに付ける
- `app/robots.ts` は `/api/`、`/plans`、`/login` を拒否して残りを許し、`app/sitemap.ts` はトップ、利用規約、プライバシーポリシーを載せる。本番の URL は環境変数 `SITE_URL`(無いか空なら `http://localhost:3000`。http か https のパスを含まないオリジンで、違えばビルドが分かる文で止まる)で、`metadataBase`(OG 画像の絶対 URL)と robots と sitemap に使う。これらはビルドで静的に作られるので、`SITE_URL` はビルドのときに渡す
- `app/opengraph-image.png`(1200×630)は、行先表示の板に「なりたい職業 行」と、アプリの名前と一言を描いた静的な画像で、`opengraph-image.alt.txt` が代替の文。`app/icon.svg`(道標の絵、favicon。絵の元はこの 1 つ)、`app/favicon.ico`(link を読まずに `/favicon.ico` を取りに来る相手のため)、`app/apple-icon.png`(180×180)、`public/icon-192.png` と `public/icon-512.png`(ホーム画面に置くとき)も置き、`app/manifest.ts` が名前と色とアイコンを出す。manifest の色は既定の明るい見た目の紙の色(暗い見た目は画面の中の切り替えで、manifest からは分からない)。PNG と ICO は `frontend/brand/make.py` が `frontend/brand/` の HTML を Playwright で開き、フォントの読み込み(`document.fonts.ready`)を待って撮る(作り方は CLAUDE.md)。OG の title と description はページごとの title から Next が引き継ぐ

## 理由

- nonce 付きの CSP は守りが強いが、全ページを動的に描くことになり、しるべ線の画面の静的な部分(ADR 0030)を手放す。インラインの script を許す CSP でも、外部の script の読み込み、ほかのサイトからの frame 埋め込み、object、base の差し替えは止められる(フォームの送り先は、ログインの経路のため止めない)
- 静的な OG 画像は作り方が単純で、ページごとに変える要望は今は無い
- 道標の画面はログインが要るので、クロールさせても意味が無い

## 受け入れたトレードオフ

- インラインの script を許すので、XSS が起きたときの CSP の守りは弱い。入力は backend が検査し(ADR 0026)、画面に出す文は React がエスケープする。`form-action` も付けないので、注入されたフォームの送り先は CSP では止まらない
- OG 画像の作り直しは Google Fonts への接続が要る(フォントは同梱しない)
- OG 画像はページごとに同じ。道標ごとの画像を出すなら `ImageResponse` に替える
- `SITE_URL` はビルドのときに決まるので、本番のイメージを作る CI に渡す必要がある。渡し忘れると sitemap と OG 画像の URL が localhost になる(本番化の手順に入れる)

## 再検討する条件

- Next が静的な描画のまま nonce を使えるようになったとき(厳しい CSP に替える)
- 道標を共有する機能を作り、道標ごとの OG 画像が欲しくなったとき
- 本番化でプロキシの側に CSP をまとめたくなったとき
