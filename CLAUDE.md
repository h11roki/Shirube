# shirube

なりたい職業と回生から、卒業までの学期ごとの時間割(道標)を組む Web アプリ。対象は立命館大学 理工学部 電子情報工学科から始め、他学部・他大学へ広げる。設計判断は `docs/adr/`、コードの規約は README の「開発ルール」にある。

## コマンド

backend(`backend/` で実行)

- `uv sync`(dev と scraper の両グループが入る。Web 用イメージは `--no-default-groups` で本体の依存だけ)
- `uv run playwright install chromium`(取り込みや fixture 生成で Playwright を使うとき)
- `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest`(CI と同じ。DB の結合テストは `DATABASE_URL` があるときだけ走り、そのデータベース名に `_test` を付けた別のデータベースを作って使うので、手元の実データには触れない。手元では `docker compose up -d db` のあと `DATABASE_URL=postgresql+psycopg://shirube:shirube@localhost:5432/shirube` を付ける)
- `DATABASE_URL=... uv run alembic upgrade head` でマイグレーション。モデルを変えたら `DATABASE_URL=... uv run alembic revision --autogenerate --rev-id <次の4桁> -m "<内容>"` で `migrations/versions/<4桁>_<内容>.py` を生成する(テンプレートと ruff の hook で整形済みになる。拡張機能の作成など autogenerate が拾わない操作は手で足す)
- `DATABASE_URL=... uv run python -m app.presentation.cli.ingest timetable data/curriculum/<時間割表>.pdf ...` でその年度の時間割表を全てまとめて、`... ingest syllabi` で保存済みシラバスを全て、それぞれ年度単位で DB に入れ替える(ADR 0014)。片方だけ取り直せる
- `DATABASE_URL=... OPENAI_API_KEY=... uv run python -m app.presentation.cli.embed` で、その年度のシラバスをチャンクにして埋め込む(ADR 0015)。`ingest syllabi` の後に実行する。埋め込み済みの本文は API を呼ばずに再利用する。`--prune` で今のモデル以外と使われなくなった埋め込みを消す(全ての年度を embed し直した後に使う)
- `uv run python -m app.presentation.cli.timetable data/curriculum/<時間割表>.pdf > data/curriculum/timetable.jsonl` で時間割表を JSON Lines に変換
- `uv run python -m app.presentation.cli.fetch_syllabus listings` で理工学部の検索結果(学期×曜日×時限)を `data/raw/ritsumeikan/<年度>/listings/` に保存。`... details --codes-from data/curriculum/timetable.jsonl` で授業コードごとの詳細ページを `details/<主コード>.html` に保存(合併科目は別名のコードでも主コードのページに当たる、ADR 0013)。どちらも保存済みは飛ばすので中断後に再実行できる
- `uv run python -m app.presentation.cli.syllabus 32494` で保存済みの詳細ページを解析して JSON 表示。引数なしで保存済み全件の解析検査

frontend(`frontend/` で実行)

- `pnpm install`
- `pnpm lint && pnpm typecheck && pnpm format:check`(CI と同じ)

全体

- `docker compose up` で db(pgvector、5432)/ backend(8000)/ frontend(3000)。ポートが塞がっていれば `FRONTEND_PORT=3001` のように変える

## 構成と依存の向き

`backend/app` は4層。依存は presentation → application → domain の一方向で、infrastructure は application のポート(Protocol)を実装する。

- domain: エンティティ(CourseSection, Audience, TimeSlot, Plan, SemesterPlan)と純粋ロジック(時間割生成)。標準ライブラリ以外を import しない
- application: ユースケース(CreatePlan, IngestTimetable, IngestSyllabi, FetchSyllabus)とポート(`ports.py`)。ポートは差し替え先が実在するものだけ(時間割表の取得元、シラバスの取得元、LLM、埋め込み、科目リポジトリ、Plan リポジトリ)
- infrastructure: `db/`(SQLAlchemy, Alembic)、`llm/`(OpenAI, LangChain)、`curriculum/<university>/`(時間割表の解析)、`scrapers/<university>/`(シラバスの取得と解析)、`auth/`
- presentation: `api/`(FastAPI ルータ、接頭辞 `/api/v1`)、`schemas/`(Pydantic DTO)、`cli/`

`main.py` と `presentation/cli/` は合成ルートで、infrastructure の実装を組み立てて application のポートの型として渡す。それ以外の presentation のコードは infrastructure を import しない。

frontend は API を呼んで表示するだけで、業務ロジックを置かない。バックエンドは Next.js の Route Handler 経由で呼ぶ。

## 決まっていること(詳細は ADR)

- pgvector、セクション単位のチャンク、text-embedding-3-small(モデル名と次元数は設定値)
- 時間割は学期ごとの貪欲法。前提科目は制約にせず表示だけ
- 当年度のシラバスを翌年度以降の代理とみなす
- 認証は Auth.js の Google ログイン。バックエンドは JWT を検証し、認可はバックエンドで行う
- 本番は EC2 1台 + compose。設定は環境変数、アプリはステートレス

## データの取り扱い

- シラバス(https://syllabus.ritsumei.ac.jp/syllabus/s)は Salesforce 製で JavaScript 描画。取得は Playwright、解析は BeautifulSoup。取得と解析を分け、取得した HTML は `backend/data/raw/` に保存して再取得しない(`backend/data/` は git 管理外)
- 1リクエスト 2〜3 秒以上、単一スレッド、連絡先入りの User-Agent。教員の連絡先は保存しない
- 画面に出すシラバス本文は短い引用にとどめ、原ページへリンクする
- テスト用の実ページは `backend/tests/fixtures/html/` に置く

## 進め方

- フェーズ順: 2 データ取得の検証、3 取り込み、4 検索、5 LLM パイプライン、6 道標生成、7 認証、8 フロント、9 本番化、10 汎用化。フェーズ1(起票)は完了
- 新しい設計判断は先に ADR を書き、`docs/adr/README.md` の一覧を更新する
- Python 3.13、mypy strict。TypeScript strict。コメントは書かず、経緯はコミットメッセージに書く
