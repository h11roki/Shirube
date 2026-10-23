# shirube

なりたい職業から、卒業までの履修の道標を描く。

大学のシラバスをもとに、入力した職業に必要なスキルを満たす授業を選び、取るべき理由を添えて、曜日・時限が重ならない学期ごとの時間割を自動で組む Web アプリ。最初の対象は立命館大学 理工学部 電子情報工学科。他学部・他大学へ広げる前提で設計している。

## できること

- 職業と回生を入力すると、その職業に必要なスキルを提示する
- シラバスから関連する授業を選び、授業ごとに取るべき理由を添える
- 卒業までの残り学期ごとに、曜日・時限が重ならない時間割を組む
- Google ログインで自分の道標を保存し、後から見返す

## 構成

```mermaid
flowchart LR
  U[ブラウザ] --> F[Next.js]
  F -->|Route Handler| B[FastAPI]
  B -->|待ちで保存| P[(PostgreSQL + pgvector)]
  W[worker] -->|取って作る| P
  W --> O[OpenAI API]
  C[取り込み CLI<br/>Playwright] --> S[大学のシラバス]
  C --> P
```

| 領域 | 技術 |
|---|---|
| フロント | Next.js (App Router, TypeScript), Auth.js, pnpm, Vitest |
| バックエンド | Python, FastAPI, SQLAlchemy, Alembic, LangChain |
| DB | PostgreSQL + pgvector |
| LLM / 埋め込み | OpenAI API |
| 取り込み | Playwright, BeautifulSoup |
| 開発環境 | Docker Compose |
| CI | GitHub Actions |
| 本番 | AWS EC2 |

## 起動

```sh
docker compose up
```

- フロント: http://localhost:3000
- バックエンド: http://localhost:8000 (OpenAPI: http://localhost:8000/docs)

ポートが使用中のときは `FRONTEND_PORT` / `BACKEND_PORT` / `DB_PORT` で手元側のポートを変えられる。道標は API が「待ち」で受け付け、worker(`python -m app.presentation.worker`)が 1 件ずつ取って作る(ADR 0029)。画面は道標ができるまで GET を繰り返す。worker と backend は起動に `OPENAI_API_KEY` が要る(無ければログに理由が出て止まる)。道標の API はフロントの Route Handler が作る JWT で利用者を確かめる(ADR 0027)ので、起動に `AUTH_JWT_SECRET`(32 文字以上の乱数。`openssl rand -hex 32` で一度だけ作った値を書く)も要る。backend は外に公開せずフロントからだけ呼ぶので、ポートは手元(127.0.0.1)だけに開ける。`docker compose up` は手元の環境変数の `OPENAI_API_KEY` と `AUTH_JWT_SECRET` を backend に、`OPENAI_API_KEY` を worker に渡す。シラバスの埋め込み(`embed` コマンド)と検索の評価(`evaluate` コマンド)は手元で実行し、同じく `OPENAI_API_KEY` を環境変数で渡す。リポジトリ直下の `.envrc`(direnv、git 管理外)に `export OPENAI_API_KEY=...` と `export AUTH_JWT_SECRET=...`(`openssl rand -hex 32` で一度だけ作った値)を書き、`direnv allow` で有効にする。direnv は一番近い `.envrc` だけを読む。親ディレクトリの `.envrc` で渡している変数があるなら、先頭に `source_up` を書かないとリポジトリの中ではそれが消える。

ログインは Google で行う(Auth.js、ADR 0028)。Google Cloud のコンソールで OAuth クライアント(種類はウェブ アプリケーション)を作り、承認済みのリダイレクト URI に `http://localhost:3000/api/auth/callback/google` を足す(`FRONTEND_PORT` を変えたらそのポートにする)。`.envrc` に、そのクライアントの ID とシークレットを `AUTH_GOOGLE_ID` と `AUTH_GOOGLE_SECRET` として、ログインのクッキーを暗号化する鍵を `AUTH_SECRET`(`openssl rand -hex 32` で一度だけ作った値)として書く。`docker compose up` はこの 3 つと `AUTH_JWT_SECRET` を frontend に渡す。frontend が作った JWT を backend が確かめるので、`AUTH_JWT_SECRET` は両方に同じ値を渡す。

DB のスキーマは Alembic で管理する。初回と、`backend/migrations/versions/` が増えたときに適用する。

```sh
docker compose exec backend uv run --no-sync alembic upgrade head
```

科目データは、時間割表の PDF と保存済みのシラバス(`backend/data/`、git 管理外)から取り込む。手順は `CLAUDE.md` のコマンド一覧にある。

## 設計

ビジネスロジックは全てバックエンドに置き、フロントは API を呼んで表示するだけにする。バックエンドは domain / application / infrastructure / presentation の4層で、依存は presentation → application → domain の一方向。大学ごとのシラバス取得元は infrastructure の実装を足すだけで増やせる。

設計上の判断は [ADR](docs/adr/README.md) に記録している。

前提: 将来の学期のシラバスは存在しないため、当年度のシラバスを翌年度以降の代理として道標を組む。

## 推薦の評価

推薦は 3 段で動く。

```mermaid
flowchart LR
  J[職業名] -->|gpt-5.4-mini| R[読み取り<br/>解釈とスキル]
  R -->|text-embedding-3-small<br/>pgvector| S[シラバスの節を検索<br/>上位 30 科目]
  S -->|gpt-5.4-nano| C[中心と土台を<br/>理由つきで選ぶ]
  C --> T[学期ごとの<br/>時間割に並べる]
```

評価データは電子情報工学科の 10 職業。3 つの立場の LLM(Claude)が職業と科目の組ごとに中心・土台・関係なしの票を入れ、その多数決で科目を期待・土台・少数・関係なしに分けた(ADR 0017、0023)。期待する科目は計 33。`experiment run` が 10 職業に推薦を本番と同じ道で決めた回数だけ流し、精度、揺れ、費用、時間を `backend/eval/runs/` の JSON に残す。`experiment compare` は 2 つの結果の差が揺れより大きいかを示す(ADR 0048)。

基準(2026-10-23、commit 7c4feb5、10 職業 × 3 回の平均 ± 標本標準偏差。`backend/eval/runs/20261023-104015-baseline.json` と `20261023-104147-baseline-handwritten.json`)

| 指標 | 通し(本番と同じ) | 読み取りを手書きのスキルに固定 |
|---|---|---|
| 検索の再現率 @10 / @20 | 84% ± 6 / 96% ± 2 | 93% ± 0 / 100% ± 0 |
| 選び直しに渡した候補(30 件)の再現率 | 100% | 100% |
| 中心(柱)の適合率 | 50% ± 5 | 54% ± 2 |
| 期待する科目を中心に選んだ割合 | 76% ± 0 | 81% ± 5 |
| 選んだ科目のうち関係なし | 23% ± 2 | 14% ± 1 |
| 同じ職業の回どうしの選んだ科目の重なり(Jaccard) | 0.45 | 0.65 |
| 1 回の推薦の費用 / 時間 | 0.81 円 / 8.0 秒 | 0.36 円 / 5.6 秒 |

検索は期待する科目を全て候補に入れていて、誤りと揺れは選び直しの段で起きる。LLM の職業の読み取りの揺れがそれを広げている(関係なし 14% → 23%、重なり 0.65 → 0.45)。精度を上げる手は、この基準と `experiment compare` で比べて選ぶ。

改善: 選び直しを 3 回並べて呼び、過半数が選んだ科目だけを残す(ADR 0049、`SELECTION_VOTES=3`。2026-10-23、commit d1e8dce、`backend/eval/runs/20261023-125956-votes-3.json`)

| 指標 | 基準(通し) | 多数決 3 回 | 差 |
|---|---|---|---|
| 中心(柱)の適合率 | 50% ± 5 | 55% ± 3 | +5 ポイント(揺れの範囲) |
| 期待する科目を中心に選んだ割合 | 76% ± 0 | 74% ± 8 | -2 ポイント(揺れの範囲) |
| 選んだ科目のうち関係なし | 23% ± 2 | 10% ± 1 | -14 ポイント(揺れより大きい) |
| 1 職業に選んだ中心 / 土台 | 5.0 / 5.2 | 4.4 / 3.9 | 1 回だけ選ばれる科目が落ちる |
| 同じ職業の回どうしの重なり(選んだ科目 / 中心) | 0.45 / 0.54 | 0.59 / 0.64 | +0.14 / +0.11 |
| 1 回の推薦の費用 / 時間 | 0.81 円 / 8.0 秒 | 1.57 円 / 9.0 秒 | 費用は約 1.9 倍、時間は並べて呼ぶので 1 秒ほど |

関係なしは、読み取りを手書きのスキルに固定した基準(14%)より下がった。期待する科目を中心に選ぶ割合は保ったまま、関係の薄い科目を落として揺れを減らす、という効き方になる。多数決の決まりを直す前の作りで流した 1 回目(commit 29dfe4d、`20261023-121203-votes-3.json`)は、適合率 57%、期待する科目を中心に 81%、関係なし 14%、重なり 0.59 で、向きは同じだった。同じ設定でも実験ごとに数ポイント動くので、3 回での「揺れより大きい」は目安にとどまる。

## データの取り扱い

- シラバスは公開ページから、1リクエスト 2〜3 秒以上の間隔、単一スレッド、リポジトリの URL を入れた User-Agent で取得する。取得した HTML は保存し、解析のやり直しで再取得しない
- 画面に出すシラバス本文は短い引用にとどめ、原ページへリンクする
- 教員の連絡先は保存しない
- Google ログインで得たメールアドレスと名前は保存せず、Google の利用者の番号(sub)だけを保存する(ADR 0027)。その扱いは画面のプライバシーポリシー(`/privacy`)に書く(ADR 0042)

## 開発ルール

- コメントは原則書かない。経緯や日付はコミットメッセージに書く
- 1か所でしか使わない短い処理は関数に切り出さない
- 変更は小さな単位で行う
- 設計判断は実装より先に ADR に書く

## ライセンス

コードは [MIT License](LICENSE)。取り込んだシラバスと時間割表の内容(`backend/data/`、git 管理外)と画面に出す引用は、このライセンスの対象外(大学と担当教員のもの)。テストには実ページを置かず、科目名・教員名・本文が架空の合成のページ(`backend/tests/unit/syllabus_pages.py` がテストの中で組み立てる)と PDF(`backend/tests/fixtures/timetable/make_sample.py` が作る)を使う(ADR 0043)。
