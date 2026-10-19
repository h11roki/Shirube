# shirube

なりたい職業と回生から、卒業までの学期ごとの時間割(道標)を組む Web アプリ。対象は立命館大学 理工学部 電子情報工学科から始め、他学部・他大学へ広げる。設計判断は `docs/adr/`、コードの規約は README の「開発ルール」にある。

## コマンド

backend(`backend/` で実行)

- `uv sync`(dev と scraper の両グループが入る。Web 用イメージは `--no-default-groups` で本体の依存だけ)
- `uv run playwright install chromium`(取り込みや fixture 生成で Playwright を使うとき)
- `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest`(CI と同じ。DB の結合テストは `DATABASE_URL` があるときだけ走り、そのデータベース名に `_test` を付けた別のデータベースを作って使うので、手元の実データには触れない。手元では `docker compose up -d db` のあと `DATABASE_URL=postgresql+psycopg://shirube:shirube@localhost:5432/shirube` を付ける)
- `DATABASE_URL=... uv run alembic upgrade head` でマイグレーション。モデルを変えたら `DATABASE_URL=... uv run alembic revision --autogenerate --rev-id <次の4桁> -m "<内容>"` で `migrations/versions/<4桁>_<内容>.py` を生成する(テンプレートと ruff の hook で整形済みになる。拡張機能の作成など autogenerate が拾わない操作は手で足す)
- `DATABASE_URL=... uv run python -m app.presentation.cli.ingest timetable data/curriculum/<時間割表>.pdf ...` でその年度の時間割表を全てまとめて、`... ingest syllabi` で保存済みシラバスを全て、それぞれ年度単位で DB に入れ替える(ADR 0014)。片方だけ取り直せる
- `DATABASE_URL=... uv run python -m app.presentation.cli.embed`(`OPENAI_API_KEY` が要る)で、その年度のシラバスをチャンクにして埋め込む(ADR 0015)。`ingest syllabi` の後に実行する。埋め込み済みの本文は API を呼ばずに再利用する。`--prune` で今のモデル以外と使われなくなった埋め込みを消す(今のモデルで埋め込み終わっていない年度があれば断る)。embed を 2 つ同時に走らせない
- `DATABASE_URL=... uv run python -m app.presentation.cli.evaluate`(`OPENAI_API_KEY` が要る)で、`eval/occupations.json` の職業ごとに検索の再現率@10 と @20 を出す(ADR 0017)。`--skills llm` で手書きのスキルの代わりに LLM が職業名から出したスキルを使う(ADR 0018、モデルは `CHAT_MODEL`)。`embed` の後に実行する。チャンクの切り方、モデル、クエリを変えたら測り直す。期待する科目は手で書き換えず、`eval/judgments.json` の判定の多数決と高橋さんの決定から作る(テストが一致を確かめる)
- `DATABASE_URL=... uv run python -m app.presentation.cli.recommend 職業名`(`OPENAI_API_KEY` が要る)で、LLM が職業をスキルに直し(`CHAT_MODEL`)、検索の上位 30 件(`SELECTION_CANDIDATE_LIMIT`)から中心と土台の科目を理由つきで選ぶ(`SELECTION_MODEL`、ADR 0018、0023)。土台は前提にする中心の科目を 1 つ指し、中心に選ばれていなければ外して表示する。`--year`、`--department`(既定は情)、`--grades` で候補を絞る。土台は中心に選んだ授業の前提に限るので、低い回生だけに絞って候補に中心が無いと空になる。1 回に LLM を 2 回呼び、数円かかる
- `DATABASE_URL=... uv run python -m app.presentation.cli.evaluate_selection`(`OPENAI_API_KEY` が要る)で、評価データの職業ごとに選び直しの結果を判定の票(期待・土台・少数・関係なし)と比べる(ADR 0023)。中心につながらず外した土台と、その判定の内訳も出す。スキルは評価データの手書きのものを使う。選び手は土台の意味が判定者より狭く、迷ったときの決め方も違うので、中心と土台の内訳は判定と同じ物差しではない。判定の関係なしを誤りの目安に見る。1 回 10 職業で約 15 円(nano)。指示文や `SELECTION_MODEL` を変えたら測り直す
- `DATABASE_URL=... uv run python -m app.presentation.cli.plan create 職業名 --grade 3`(`OPENAI_API_KEY` が要る)で、道標を待ちで保存し、worker を待たずにその場で取って、推薦して始める学期から 4 回生の秋学期までの道標を作って表示する(ADR 0029)。失敗したら失敗の文を出して 1 で終わる。`--term`(spring / autumn、既定は今日の月から)、`--department`、`--year`、`--class 科目名=クラス記号`(学科で分かれたクラスの選択、繰り返せる。記号の無いクラスは `科目名=`)。1 学期の単位の上限は `SEMESTER_CREDIT_LIMIT`(既定 16)。`... plan show <id>` で保存した道標を状態つきで表示する。CLI で作った道標は sub が cli:local の利用者のもの(ADR 0027)
- `uv run python -m app.presentation.cli.timetable data/curriculum/<時間割表>.pdf > data/curriculum/timetable.jsonl` で時間割表を JSON Lines に変換
- `uv run python -m app.presentation.cli.fetch_syllabus listings` で理工学部の検索結果(学期×曜日×時限)を `data/raw/ritsumeikan/<年度>/listings/` に保存。`... details --codes-from data/curriculum/timetable.jsonl` で授業コードごとの詳細ページを `details/<主コード>.html` に保存(合併科目は別名のコードでも主コードのページに当たる、ADR 0013)。どちらも保存済みは飛ばすので中断後に再実行できる
- `uv run python -m app.presentation.cli.syllabus 32494` で保存済みの詳細ページを解析して JSON 表示。引数なしで保存済み全件の解析検査

frontend(`frontend/` で実行)

- `pnpm install`
- `pnpm lint && pnpm typecheck && pnpm test && pnpm format:check`(CI と同じ。テストは Vitest。CI は先に `pnpm gen:api` で型を作り直し、差があれば落ちる)
- API を変えたら、backend で `uv run python -m tests.openapi_document`(OpenAPI を `frontend/src/lib/api/openapi.json` に書き出す)、frontend で `pnpm gen:api`(`src/lib/api/schema.ts` を作る)を実行し、どちらもコミットする(ADR 0030)。backend のテストが OpenAPI の食い違いを見つける
- compose の外で動かすときは `BACKEND_URL=http://localhost:8000 direnv exec . pnpm dev`(ログインと転送に `AUTH_SECRET`、`AUTH_GOOGLE_ID`、`AUTH_GOOGLE_SECRET`、`AUTH_JWT_SECRET` が要る)

全体

- `docker compose up` で db(pgvector、5432)/ backend(8000)/ worker / frontend(3000)。ポートが塞がっていれば `FRONTEND_PORT=3001` のように変える。backend は起動に `OPENAI_API_KEY` と `AUTH_JWT_SECRET`(32 文字以上)が、worker は `OPENAI_API_KEY` が要り、frontend はログインに `AUTH_SECRET`、`AUTH_GOOGLE_ID`、`AUTH_GOOGLE_SECRET` と、backend と同じ `AUTH_JWT_SECRET` が要る。compose が手元の環境変数を渡す(リポジトリ直下の `.envrc` に書く)
- `DATABASE_URL=... uv run python -m app.presentation.worker`(`OPENAI_API_KEY` が要る)で、待ちの道標を古い順に 1 件ずつ取って作る(ADR 0029)。待ちが無ければ `WORKER_POLL_SECONDS`(既定 1)秒待ち、作成中のまま `PLAN_STALL_MINUTES`(既定 15)分を過ぎた道標を失敗にする。SIGTERM か Ctrl-C を受けたら作っている 1 件を終えて止まる(Ctrl-C をもう 1 回押すとすぐ止まる)。compose では worker のサービスが watchfiles の下で動かし、`app/` の Python を変えると読み直す。止める猶予は 1 件の最悪の所要時間に合わせて 11 分。CLI の `plan create` も始める前に止まった道標を失敗にする。15 分と 11 分は 1 件の最悪の所要時間(3 回の呼び出し × (2 回の試行 × `OPENAI_TIMEOUT_SECONDS` + `Retry-After` の 120 秒))から決めたので、`OPENAI_TIMEOUT_SECONDS` か `OPENAI_MAX_RETRIES` を変えたら `PLAN_STALL_MINUTES` と compose の猶予も見直す
- API: `POST /api/v1/plans`(本文は occupation、grade、department、省ける term と chosen_classes。選べないクラスと候補の無いときは 422、そうでなければ待ちで保存して 202 と Location を返す)と `GET /api/v1/plans/{id}`(status が pending / running / succeeded / failed、作成中なら今の段 stage(analyzing / searching / selecting / placing、ADR 0031)、完了なら result、失敗なら failure を返す。ADR 0029)。`GET /api/v1/plans` は自分の道標を新しい順に 50 件の要約で、`GET /api/v1/class-choices?department=&grade=&term=` は決めた始める学期と、残りの学期に学科で分かれたクラスのある科目と選べるクラスの記号を返す(画面はその学期を POST に送り返す。ADR 0030)。エラーはどれも `{"detail": 文}` で、OpenAPI にも ErrorOut として書く。この行の API はどれも `Authorization: Bearer <JWT>` が要り(HS256、鍵は `AUTH_JWT_SECRET`、iss は shirube-frontend、aud は shirube-backend、5 分まで、ADR 0027)、無ければ 401、他人の Plan は 404。年度は設定 `CURRICULUM_YEAR`(既定 2026)、OpenAI のタイムアウトは `OPENAI_TIMEOUT_SECONDS`(既定 45)、再試行は `OPENAI_MAX_RETRIES`(既定 1)。CLI の `--year` も省けば `CURRICULUM_YEAR`。5xx は決まった文だけを返し、中身はログに出す。OpenAPI は `/docs`
- `OPENAI_API_KEY` は README の「起動」のとおりリポジトリ直下の `.envrc` から読む。worktree にこのファイルは無いが、`.claude/worktrees/` の下なら direnv が親をたどって読む。セッションの環境変数に無いときは `direnv exec . <コマンド>` で読み込んで実行する。キーの値はコマンドにも出力にも書かない

## 構成と依存の向き

`backend/app` は4層。依存は presentation → application → domain の一方向で、infrastructure は application のポート(Protocol)を実装する。

- domain: エンティティ(CourseSection, Audience, TimeSlot, Syllabus, SyllabusChunk, OccupationProfile, Recommendation, Semester, Roadmap, SemesterPlan, ClassChoice, Plan, PlanResult, PlanSummary)と純粋ロジック(チャンクの組み立て、科目の順位付け、時間割生成)。標準ライブラリ以外を import しない
- application: ユースケース(RequestPlan, BuildPlans, GetPlan, ListPlans, ListClassChoices, IdentifyUser, IngestTimetable, IngestSyllabi, FetchSyllabus, EmbedSyllabi, SearchCourses, EvaluateSearch, RecommendCourses, EvaluateSelection)とポート(`ports.py`)。ポートは差し替え先が実在するものだけ(時間割表の取得元、シラバスの取得元、LLM、埋め込み、科目リポジトリ、チャンクの保存、チャンクの検索、Plan リポジトリ、JWT の検証、利用者リポジトリ)
- infrastructure: `db/`(SQLAlchemy, Alembic)、`llm/`(OpenAI, LangChain)、`curriculum/<university>/`(時間割表の解析)、`scrapers/<university>/`(シラバスの取得と解析)、`auth/`(JWT の検証、PyJWT)
- presentation: `api/`(FastAPI ルータ、接頭辞 `/api/v1`)、`schemas/`(Pydantic DTO)、`cli/`

`main.py`、`presentation/cli/`、`presentation/worker.py` は合成ルートで、infrastructure の実装を組み立てて application のポートの型として渡す。共有する組み立ての部品は `presentation/composition.py` に置く。API は `presentation/api/app.py` の `create_app` が組み立て済みのユースケースを受け取り(ADR 0029)、テストはフェイクを渡す。それ以外の presentation のコードは infrastructure を import しない。

frontend は API を呼んで表示するだけで、業務ロジックを置かない。バックエンドは Next.js の Route Handler(`src/app/api/`)経由で呼ぶ。Route Handler はログインを確かめ、`src/lib/backend.ts` で Google の sub を入れた JWT を付けて転送するだけ(ADR 0028)。画面は `src/app/` の入力(`/`)、結果(`/plans/[id]`)、一覧(`/plans`)で、どれも `LoginRequired` でログインを確かめてから、Client Component(`src/components/`)が Route Handler だけを呼ぶ(ADR 0030)。API の型は、openapi-typescript が生成した `schema.ts` から `src/lib/api/client.ts` が取り出し、表示の決まり(週の時間割の並べ方、ポーリングの打ち切り、ラベル、作成中の段の進み、見え方のクエリ、道のりの合計、駅番号、学期の読み、礎から柱への乗り換え)は `src/lib/` に置いて Vitest で確かめる。部品は Tailwind だけで書く。見た目は ADR 0031 の路線図を ADR 0033 の「しるべ線」に深めたもの(行先表示、乗換案内のような要約、学期は駅名標、授業は切符、礎は柱への乗り換えと柱より後の学期の注意、卒業は記念スタンプの終着駅)で、色は `src/app/globals.css` の CSS の変数(明るい見た目が既定、`data-theme="dark"` で暗い見た目)から Tailwind の色(paper、ink、pillar、route など)として引き、画面の言葉は中心を「柱」、土台を「礎」と呼ぶ。結果の画面の見え方(道のり / 時間割帳)と学期は `?view=timetable&semester=3-autumn` のクエリに持ち、`QueryLink` が `history.pushState` で変える(Next の useSearchParams と連動し、サーバーへ往復しない)。ログイン前のトップは `src/lib/sample-plan.ts` の見本の道標を見せる。動きは `motion-safe:` で付け、動きを減らす設定では出さない。

## 決まっていること(詳細は ADR)

- pgvector、セクション単位のチャンク、text-embedding-3-small(モデル名と次元数は設定値)
- 時間割は学期ごとの貪欲法。前提科目は制約にせず表示だけ
- 当年度のシラバスを翌年度以降の代理とみなす
- 職業名は、学科の授業に無い応用分野や道具で決まる細かい職種(Webエンジニアなど)なら授業で備えられる広い職業として読み、そう読んだことを前提に書く。学科の授業がそのまま備える職業はそのまま読む(ADR 0032)
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
