# ADR(設計判断の記録)

設計上の判断を、判断した時点の文脈と一緒に残す。後から「なぜこうなっているか」を読めるようにし、前提が変わったときに見直せるようにする。

## 書く契機

- 選択肢が2つ以上あり、後から戻しにくい判断をしたとき
- 実装より先に書く

## ルール

- 置き場は `docs/adr/NNNN-短いタイトル.md`。番号は4桁の連番で欠番を作らない
- 一度承認した ADR は書き換えない。覆すときは新しい ADR を書き、古い方のステータスを「廃止(Superseded by NNNN)」にする
- 1ファイル1テーマ。区切りは見出し階層で表し、水平線は使わない。図は Mermaid
- 項目は下のテンプレートに従う

## テンプレート

```markdown
# NNNN. 判断を一文で

- ステータス: 提案 / 承認 / 廃止(Superseded by NNNN)
- 日付: YYYY-MM-DD

## 文脈

## 検討した選択肢

## 決定

## 理由

## 受け入れたトレードオフ

## 再検討する条件
```

## 一覧

| 番号 | タイトル | ステータス |
|---|---|---|
| [0001](0001-monorepo.md) | フロントとバックエンドを1つのリポジトリで管理する | 承認 |
| [0002](0002-clean-architecture.md) | バックエンドをクリーンアーキテクチャの4層で構成する | 承認 |
| [0003](0003-playwright-scraping.md) | シラバスは Playwright で描画後の HTML を保存してから解析する | 承認 |
| [0004](0004-pgvector.md) | ベクトル検索に pgvector を使う | 承認 |
| [0005](0005-section-chunking.md) | シラバスはセクション単位でチャンク分割する | 承認 |
| [0006](0006-embedding-model.md) | 埋め込みモデルは text-embedding-3-small を使う | 承認 |
| [0007](0007-greedy-timetable.md) | 時間割は学期ごとに関連度順の貪欲法で組む | 承認 |
| [0008](0008-rest-api.md) | API は REST + OpenAPI 型生成、同期、Next.js Route Handler 経由とする | 廃止(Superseded by 0024) |
| [0009](0009-ec2-compose.md) | 本番は EC2 1台で docker compose を動かす | 承認 |
| [0010](0010-graduation-roadmap.md) | 回生を入力し、卒業までの学期ごとの道標を生成する | 承認 |
| [0011](0011-auth.md) | 認証は Auth.js の Google ログインとし、バックエンドへは署名付き JWT で本人性を渡す | 廃止(Superseded by 0027) |
| [0012](0012-timetable-source.md) | 学科・配当回生・コマは授業時間割表から取り、授業コードでシラバスと結合する | 承認 |
| [0013](0013-cross-listed-courses.md) | 合併科目は1ページ = 1つの Syllabus とし、主コードと別名で持つ | 承認 |
| [0014](0014-course-tables.md) | 科目は取り込み元ごとの表に年度単位で入れ替え、入れ子は JSONB で持つ | 承認 |
| [0015](0015-chunk-embeddings.md) | 埋め込みは本文のハッシュで引く別の表に置き、索引は張らずに全件で比べる | 承認 |
| [0016](0016-search-evaluation.md) | 検索は職業 10 件の評価データで、科目名単位の再現率@10 と @20 を測る | 廃止(Superseded by 0017) |
| [0017](0017-eval-judging.md) | 検索の評価の正解は、検索の候補の全科目を 3 体が職業名だけから独立に判定した多数決で作る | 承認 |
| [0018](0018-llm-pipeline.md) | 職業は LLM がスキルに直し、検索の上位を LLM が読み直して科目と理由を選ぶ | 承認(前提を書く場合は 0032 で広げた) |
| [0019](0019-course-selection.md) | 選び直しは、検索の上位 30 件から科目ごとに中心か土台かを付けて返す | 廃止(Superseded by 0020) |
| [0020](0020-course-selection-evaluated.md) | 選び直しは gpt-5.4-nano で中心か土台かを付けて返し、重複は中心を優先して 1 つにまとめる | 廃止(Superseded by 0021) |
| [0021](0021-foundation-tied-to-core.md) | 選び直しの土台は中心に選んだ授業の前提に限り、理由にどの中心の授業の前提かを書く | 廃止(Superseded by 0023) |
| [0022](0022-roadmap-placement.md) | 道標は 1 回の推薦を学期ごとに貪欲法で置き、学科で分かれたクラスは利用者が選ぶ | 廃止(Superseded by 0025) |
| [0023](0023-foundation-links-core.md) | 選び直しは中心と土台を分けて返し、土台は前提にする中心の授業を 1 つ指す | 承認 |
| [0024](0024-plan-api-and-storage.md) | Plan は同期の REST で作り、UUID の id で plans 表に JSONB で丸ごと保存する | 廃止(Superseded by 0029) |
| [0025](0025-roadmap-candidates-by-semester.md) | 道標は残りの学期に開講される科目から 1 回推薦し、学期ごとに貪欲法で置く | 承認 |
| [0026](0026-plan-api-endpoints.md) | Plan の API は組み立て済みのユースケースを create_app に渡し、エラーは detail と状態コードで返す | 廃止(Superseded by 0029) |
| [0027](0027-auth-backend.md) | バックエンドは HS256 の短い JWT で利用者を確かめ、users 表には Google の sub だけを持ち、他人の Plan は 404 にする | 承認 |
| [0028](0028-auth-frontend.md) | フロントは Auth.js v5 の Google ログインを暗号化したクッキーで持ち、エンドポイントごとの Route Handler が JWT を作ってバックエンドへ転送する | 承認 |
| [0029](0029-plan-jobs.md) | 道標は DB をキューにした worker が非同期に作り、API は状態を持つ Plan を 202 で受け付けてポーリングで返す | 承認 |
| [0030](0030-screens.md) | 画面は Tailwind だけの部品で作り、Route Handler だけを呼び、型は生成物をコミットして CI で照合する | 承認 |
| [0031](0031-route-design.md) | 画面は道標を路線に見立てた見た目にし、時間割帳と行き来でき、作成中は worker が書く段を見せる | 承認 |
| [0032](0032-broad-occupation.md) | 学科の授業より細かい専門の職業名は、授業で備えられる広い職業として読む | 承認 |
