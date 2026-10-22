# shirube

なりたい職業と回生から、卒業までの学期ごとの時間割(道標)を組む Web アプリ。対象は立命館大学 理工学部 電子情報工学科から始め、他学部・他大学へ広げる。設計判断は `docs/adr/`、コードの規約は README の「開発ルール」にある。

## コマンド

backend(`backend/` で実行)

- `uv sync`(dev と scraper の両グループが入る。Web 用イメージは `--no-default-groups` で本体の依存だけ)
- `uv run playwright install chromium`(取り込みや fixture 生成で Playwright を使うとき)
- `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest`(CI と同じ。DB の結合テストは `DATABASE_URL` があるときだけ走り、そのデータベース名に `_test` を付けた別のデータベースを作って使うので、手元の実データには触れない。手元では `docker compose up -d db` のあと `DATABASE_URL=postgresql+psycopg://shirube:shirube@localhost:5432/shirube` を付ける)
- `DATABASE_URL=... uv run alembic upgrade head` でマイグレーション。モデルを変えたら `DATABASE_URL=... uv run alembic revision --autogenerate --rev-id <次の4桁> -m "<内容>"` で `migrations/versions/<4桁>_<内容>.py` を生成する(テンプレートと ruff の hook で整形済みになる。拡張機能の作成など autogenerate が拾わない操作は手で足す)
- `DATABASE_URL=... uv run python -m app.presentation.cli.ingest timetable data/curriculum/<時間割表>.pdf ...` でその年度の時間割表を全てまとめて、`... ingest syllabi` で保存済みシラバスを全て、それぞれ年度単位で DB に入れ替える(ADR 0014)。片方だけ取り直せる。`ingest syllabi` は保存した検索結果のリンクから原ページの URL もシラバスの表に入れる(ADR 0040。URL を足したあとは一度流し直す)。シラバスを入れ替えると検索のチャンクも消えるので、`ingest syllabi` のあとは必ず `embed` も流す
- `DATABASE_URL=... uv run python -m app.presentation.cli.embed`(`OPENAI_API_KEY` が要る)で、その年度のシラバスをチャンクにして埋め込む(ADR 0015)。`ingest syllabi` の後に実行する。埋め込み済みの本文は API を呼ばずに再利用する。`--prune` で今のモデル以外と使われなくなった埋め込みを消す(今のモデルで埋め込み終わっていない年度があれば断る)。embed を 2 つ同時に走らせない
- `DATABASE_URL=... uv run python -m app.presentation.cli.evaluate`(`OPENAI_API_KEY` が要る)で、`eval/occupations.json` の職業ごとに検索の再現率@10 と @20 を出す(ADR 0017)。`--skills llm` で手書きのスキルの代わりに LLM が職業名から出したスキルを使う(ADR 0018、モデルは `CHAT_MODEL`)。`embed` の後に実行する。チャンクの切り方、モデル、クエリを変えたら測り直す。期待する科目は手で書き換えず、`eval/judgments.json` の判定の多数決と高橋さんの決定から作る(テストが一致を確かめる)
- `DATABASE_URL=... uv run python -m app.presentation.cli.recommend 職業名`(`OPENAI_API_KEY` が要る)で、LLM が職業をスキルに直し(`CHAT_MODEL`)、検索の上位 30 件(`SELECTION_CANDIDATE_LIMIT`)から中心と土台の科目を理由つきで選ぶ(`SELECTION_MODEL`、ADR 0018、0023)。土台は前提にする中心の科目を 1 つ指し、中心に選ばれていなければ外して表示する。`--year`、`--department`(既定は情)、`--grades` で候補を絞る。土台は中心に選んだ授業の前提に限るので、低い回生だけに絞って候補に中心が無いと空になる。1 回に LLM を 2 回呼び、数円かかる
- `DATABASE_URL=... uv run python -m app.presentation.cli.evaluate_selection`(`OPENAI_API_KEY` が要る)で、評価データの職業ごとに選び直しの結果を判定の票(期待・土台・少数・関係なし)と比べる(ADR 0023)。中心につながらず外した土台と、その判定の内訳も出す。スキルは評価データの手書きのものを使う。選び手は土台の意味が判定者より狭く、迷ったときの決め方も違うので、中心と土台の内訳は判定と同じ物差しではない。判定の関係なしを誤りの目安に見る。1 回 10 職業で約 15 円(nano)。指示文や `SELECTION_MODEL` を変えたら測り直す
- `DATABASE_URL=... uv run python -m app.presentation.cli.plan create 職業名 --grade 3`(`OPENAI_API_KEY` が要る)で、道標を待ちで保存し、worker を待たずにその場で取って、推薦して始める学期から 4 回生の秋学期までの道標を作って表示する(ADR 0029)。失敗したら失敗の文を出して 1 で終わる。`--term`(spring / autumn、既定は今日の月から)、`--department`、`--year`、`--class 科目名=クラス記号`(学科で分かれたクラスの選択、繰り返せる。記号の無いクラスは `科目名=`)。1 学期の単位の上限は `SEMESTER_CREDIT_LIMIT`(既定 16)。`... plan show <id>` で保存した道標を状態つきで表示する。CLI で作った道標は sub が cli:local の利用者のもの(ADR 0027)。CLI も API と同じ 1 日の上限と作成中の上限を受ける(ADR 0038。手元で多く作るときは設定値を上げる。途中で止めた道標は `PLAN_STALL_MINUTES` が過ぎるまで作成中のままで、それまで次の `plan create` は断られる)
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
- `DATABASE_URL=... uv run python -m app.presentation.worker`(`OPENAI_API_KEY` が要る)で、待ちの道標を古い順に 1 件ずつ取って作る(ADR 0029)。待ちが無ければ `WORKER_POLL_SECONDS`(既定 1)秒待ち、作成中のまま `PLAN_STALL_MINUTES`(既定 20)分を過ぎた道標を失敗にし、日が変わったら、日本時間のその日より前に作った消した道標の日時(`deleted_plans`)を消す(ADR 0041)。SIGTERM か Ctrl-C を受けたら作っている 1 件を終えて止まる(Ctrl-C をもう 1 回押すとすぐ止まる)。compose では worker のサービスが watchfiles の下で動かし、`app/` の Python を変えると読み直す。止める猶予は 1 件の最悪の所要時間に合わせて 16 分(compose が待つのは 17 分)。CLI の `plan create` も始める前に止まった道標を失敗にする。20 分と 16 分は 1 件の最悪の所要時間(4 回の呼び出し(職業の読み取りの聞き直しを含む) × (2 回の試行 × `OPENAI_TIMEOUT_SECONDS` + `Retry-After` の 120 秒) ≒ 14 分)から決めたので、`OPENAI_TIMEOUT_SECONDS` か `OPENAI_MAX_RETRIES` を変えたら `PLAN_STALL_MINUTES` と compose の猶予も見直す
- API: `POST /api/v1/plans`(本文は occupation、grade、department、省ける term と chosen_classes。選べないクラスと候補の無いときは 422、待ちか作成中の道標があれば 409、日本時間の 0 時からの道標が 1 人 `DAILY_PLAN_LIMIT_PER_USER`(既定 3)件(失敗を除く)か全体で `DAILY_PLAN_LIMIT_TOTAL`(既定 30)件(失敗も含む)に達していれば 429 と次の 0 時までの `Retry-After`、そうでなければ待ちで保存して 202 と Location を返す。数えて入れるまでを advisory lock の下で行う。ADR 0038)と `GET /api/v1/plans/{id}`(status が pending / running / succeeded / failed、作成中なら今の段 stage(analyzing / searching / selecting / placing、ADR 0031)、完了なら result、失敗なら failure を返す。ADR 0029)。道標を返す API は、結果の授業ごとに原ページの URL `syllabus_url`(無ければ null)をシラバスの表から引いて付ける(`SyllabusLinks`、ADR 0040)。`PUT /api/v1/plans/{id}/taken-courses/{科目名}`(もう取った)と `DELETE`(戻す)は、保存した道標の外した授業に 1 つ足すか除いて、保存した推薦から置き直した道標を返し、利用者ごとに科目名で覚える(聞いていない授業は 422、完了していない道標、時間割表が変わった道標、ほかの画面の答えで変わった道標は 409。ADR 0034)。結果の offered_earlier が聞く授業(始める学期より前に開講された推薦の授業)、taken が外した授業。`GET /api/v1/taken-courses` は自分の覚え(取ったと答えた科目名)を名前の順で、`DELETE /api/v1/taken-courses/{科目名}` は覚えから除いて残りを返す。道標を受け付けるときと worker が作るとき、持ち主の覚えを推薦の候補から除く(合併科目はページごと。除いて候補が無ければ受け付けで 422、作るときなら理由の文で失敗。クラスの選択にも出さない。ADR 0035)。`DELETE /api/v1/plans/{id}` は自分の道標を消し、その日に作った道標なら作った日時だけを上限に数えるために `deleted_plans` に翌日まで残す(204、無いか他人は 404、作成中は 409。失敗した道標は持ち主を外して全体の上限だけに数える)。`DELETE /api/v1/me` は受け付けと同じ鍵の下で、利用者と道標と覚えを消し、その日の道標の作った日時だけを持ち主なしで翌日まで残す(204、作成中があれば 409。全体の上限に数える。ADR 0041)。`GET /api/v1/plans` は自分の道標を新しい順に 50 件の要約と全件数 total で、`GET /api/v1/class-choices?department=&grade=&term=` は決めた始める学期と、残りの学期に学科で分かれたクラスのある科目と選べるクラスの記号を返す(画面はその学期を POST に送り返す。ADR 0030)。エラーはどれも `{"detail": 文}` で、OpenAPI にも ErrorOut として書く。この行の API はどれも `Authorization: Bearer <JWT>` が要り(HS256、鍵は `AUTH_JWT_SECRET`、iss は shirube-frontend、aud は shirube-backend、5 分まで、ADR 0027)、無ければ 401、他人の Plan は 404。年度は設定 `CURRICULUM_YEAR`(既定 2026)、OpenAI のタイムアウトは `OPENAI_TIMEOUT_SECONDS`(既定 45)、再試行は `OPENAI_MAX_RETRIES`(既定 1)。CLI の `--year` も省けば `CURRICULUM_YEAR`。5xx は決まった文だけを返し、中身はログに出す。OpenAPI は `/docs`
- `OPENAI_API_KEY` は README の「起動」のとおりリポジトリ直下の `.envrc` から読む。worktree にこのファイルは無いが、`.claude/worktrees/` の下なら direnv が親をたどって読む。セッションの環境変数に無いときは `direnv exec . <コマンド>` で読み込んで実行する。キーの値はコマンドにも出力にも書かない

## 構成と依存の向き

`backend/app` は4層。依存は presentation → application → domain の一方向で、infrastructure は application のポート(Protocol)を実装する。

- domain: エンティティ(CourseSection, Audience, TimeSlot, Syllabus, SyllabusChunk, OccupationProfile, Recommendation, Semester, Roadmap, SemesterPlan, ClassChoice, Plan, PlanResult, PlanSummary, PlanQuota)と純粋ロジック(チャンクの組み立て、科目の順位付け、時間割生成)。標準ライブラリ以外を import しない
- application: ユースケース(RequestPlan, BuildPlans, GetPlan, ListPlans, DeletePlan, DeleteAccount, SyllabusLinks, ListClassChoices, AnswerTakenCourses, TakenCourses, IdentifyUser, IngestTimetable, IngestSyllabi, FetchSyllabus, EmbedSyllabi, SearchCourses, EvaluateSearch, RecommendCourses, EvaluateSelection)とポート(`ports.py`)。ポートは差し替え先が実在するものだけ(時間割表の取得元、シラバスの取得元、LLM、埋め込み、科目リポジトリ、チャンクの保存、チャンクの検索、Plan リポジトリ、JWT の検証、利用者リポジトリ)
- infrastructure: `db/`(SQLAlchemy, Alembic)、`llm/`(OpenAI, LangChain)、`curriculum/<university>/`(時間割表の解析)、`scrapers/<university>/`(シラバスの取得と解析)、`auth/`(JWT の検証、PyJWT)
- presentation: `api/`(FastAPI ルータ、接頭辞 `/api/v1`)、`schemas/`(Pydantic DTO)、`cli/`

`main.py`、`presentation/cli/`、`presentation/worker.py` は合成ルートで、infrastructure の実装を組み立てて application のポートの型として渡す。共有する組み立ての部品は `presentation/composition.py` に置く。API は `presentation/api/app.py` の `create_app` が組み立て済みのユースケースを受け取り(ADR 0029)、テストはフェイクを渡す。それ以外の presentation のコードは infrastructure を import しない。

frontend は API を呼んで表示するだけで、業務ロジックを置かない。バックエンドは Next.js の Route Handler(`src/app/api/`)経由で呼ぶ。Route Handler はログインを確かめ、`src/lib/backend.ts` で Google の sub を入れた JWT を付けて転送するだけ(ADR 0028)。転送の前に、状態を変える要求(GET、HEAD、OPTIONS 以外)の送り元を `Sec-Fetch-Site`(無ければ `Origin` と、Next が付ける `X-Forwarded-Host` のホスト名)で確かめてほかのサイトからなら 403、本文は 64KB まで(超えれば 413)にする(ADR 0039)。画面は `src/app/` の入力(`/`)、結果(`/plans/[id]`)、一覧(`/plans`)と、ログインの要らない利用規約(`/terms`)とプライバシーポリシー(`/privacy`、どちらも `LegalDocument` と `ContactSection` の部品で同じ体裁)、ログイン(`/login`)で、前の 3 つはどれも `LoginRequired` でログインを確かめてから、Client Component(`src/components/`)が Route Handler だけを呼ぶ(ADR 0030)。API の型は、openapi-typescript が生成した `schema.ts` から `src/lib/api/client.ts` が取り出し、表示の決まり(週の時間割の並べ方、ポーリングの打ち切り、ラベル、作成中の段の進み、見え方のクエリ、道のりの合計、駅番号、学期の読み、礎から柱への乗り換え)は `src/lib/` に置いて Vitest で確かめる。部品は Tailwind だけで書く。見た目は ADR 0031 の路線図を ADR 0033 の「しるべ線」に深めたもの(行先表示、乗換案内のような要約、学期は駅名標、授業は切符、礎は柱への乗り換え、道のりの終わりと帯の終点と要約の到着は行き先(職業)で駅番号を付けない(ADR 0036)、道のりの上に車内の路線図の帯、切符に触れると乗り換えでつながる切符が光る、前の学期に開講された授業の切符に「もう取った」、外した授業は「もう取った授業」に並べて戻せる、入力の画面に「もう取ったと答えた授業」を畳んで置き取り消せる、行先表示のすぐ下に非公式で必修や卒業要件を見ていないことの注意、切符に原ページへの「シラバス ↗」、終わりに出典。ADR 0040。結果の画面と一覧に「消す」(作成中でも置き、backend の 409 の文をその場に出す)、一覧の下に退会(作った道標の全件数ともう取ったと答えた授業の数を出す)。どちらもその場で「本当に消す / やめる」を出し、やめるにフォーカスを置く。退会したらサーバーアクションでログアウトしてトップへ。ADR 0041。全ページの下にフッター(非公式の断り、利用規約、プライバシーポリシー、GitHub と Issue)。ログインのボタンは同意の文と組で、ヘッダーのログインはそのボタンを置いた `/login` へのリンク(ログイン済みで開いたら入力の画面へ移す。ログインのあとも Auth.js が `/login` に戻すので、そこから移る)。ADR 0042)で、色は `src/app/globals.css` の CSS の変数(明るい見た目が既定、`data-theme="dark"` で暗い見た目)から Tailwind の色(paper、ink、pillar、route など)として引き、画面の言葉は中心を「柱」、土台を「礎」と呼ぶ。結果の画面の見え方(道のり / 時間割帳)と学期は `?view=timetable&semester=3-autumn` のクエリに持ち、`QueryLink` が `history.pushState` で変える(Next の useSearchParams と連動し、サーバーへ往復しない)。ログイン前のトップは `src/lib/sample-plan.ts` の見本の道標を見せる。無いページは `not-found.tsx`、描けなかったときは `error.tsx`(root layout が壊れたときは `global-error.tsx`。見た目の script とフォント(`src/lib/fonts.ts`)は root layout と共有)で日本語に出す。API の失敗は `FailureNotice`(何を読めなかったかの文、失敗の文、読み直すボタン。読み直す前に前の失敗を消す)か同じ文(`messageOf`)で出し、英語の文を見せない。ログインが切れたとき(401)は `lib/api/client.ts` が購読者に知らせ、`LoginRequired` の中の `SignedOutGate` が 1 か所でページの中身を「ログインが切れました」と「ログインし直す」(ページを読み直す)に替える。無い道標(404)は読み直すボタンを出さず一覧への導線(ADR 0044)。動きは `motion-safe:` で付け、動きを減らす設定では出さない。

## 決まっていること(詳細は ADR)

- pgvector、セクション単位のチャンク、text-embedding-3-small(モデル名と次元数は設定値)
- 時間割は学期ごとの貪欲法。前提科目は制約にせず表示だけ
- 当年度のシラバスを翌年度以降の代理とみなす
- 職業名は、学科の授業に無い応用分野や道具で決まる細かい職種(Webエンジニアなど)なら授業で備えられる広い職業として読み、そう読んだことを前提に書く。学科の授業がそのまま備える職業はそのまま読む(ADR 0032)。前提の無い解釈は入力した職業名のままにし、使えない文字が混ざった答えは 1 回だけ聞き直す(ADR 0037)
- 道標の受け付けは、1 人 1 日 3 件(失敗は数えない)、全体 1 日 30 件(失敗も数える)。日本時間の 0 時で戻る、待ちと作成中は 1 人 1 件まで。最後の上限として OpenAI は前払いで自動の補充を切る(ADR 0038)
- 礎が柱より後の学期になっても配置で避けない。始める学期より前に開講された推薦の授業は結果の画面で取ったかを聞き、取った授業は利用者ごとに科目名で覚えて道標から外す(ADR 0034)。覚えた授業は次に作る道標の推薦の候補から除き、入力の画面で取り消せる(ADR 0035)
- 認証は Auth.js の Google ログイン。バックエンドは JWT を検証し、認可はバックエンドで行う
- 本番は EC2 1台 + compose。設定は環境変数、アプリはステートレス

## データの取り扱い

- シラバス(https://syllabus.ritsumei.ac.jp/syllabus/s)は Salesforce 製で JavaScript 描画。取得は Playwright、解析は BeautifulSoup。取得と解析を分け、取得した HTML は `backend/data/raw/` に保存して再取得しない(`backend/data/` は git 管理外)
- 1リクエスト 2〜3 秒以上、単一スレッド、リポジトリの URL を入れた User-Agent(メールアドレスは入れない。ADR 0042)。教員の連絡先は保存しない
- 画面に出すシラバス本文は短い引用にとどめ、原ページへリンクする
- テストには実ページを置かず、構造を写した合成のページ(`backend/tests/unit/syllabus_pages.py` がテストの中で組み立てる。ラベルは解析のモジュールから取らず書き写す)と合成の時間割表の PDF(`backend/tests/fixtures/timetable/make_sample.py` が作る)を使う。科目名・教員名・本文は架空。実ページの癖を見つけたら合成のページにも足す(ADR 0043)

## 進め方

- フェーズ順: 2 データ取得の検証、3 取り込み、4 検索、5 LLM パイプライン、6 道標生成、7 認証、8 フロント、9 本番化、10 汎用化。フェーズ1(起票)は完了
- 新しい設計判断は先に ADR を書き、`docs/adr/README.md` の一覧を更新する
- Python 3.13、mypy strict。TypeScript strict。コメントは書かず、経緯はコミットメッセージに書く
