# 0008. API は REST + OpenAPI 型生成、同期、Next.js Route Handler 経由とする

- ステータス: 廃止(Superseded by 0024)
- 日付: 2026-10-14

## 文脈

ビジネスロジックは全てバックエンドに置き、フロントは API を呼んで表示するだけにする。LLM を含む処理は 10〜30 秒かかる。

## 検討した選択肢

1. REST + OpenAPI 型生成、同期、ブラウザ → Next.js Route Handler → FastAPI
2. REST + OpenAPI 型生成、同期、ブラウザ → FastAPI 直接
3. 最初から非同期ジョブ(202 + ポーリング / SSE)

## 決定

選択肢1。`/api/v1` を接頭辞とし、`POST /api/v1/plans` が道標を生成して保存し、`GET /api/v1/plans/{id}` で再表示する。Plan は id と status を持つ。FastAPI の OpenAPI から openapi-typescript でフロントの型を生成する。

## 理由

- バックエンドを非公開ネットワークに置け、CORS が不要
- 型生成で API 契約のズレをビルド時に検出できる
- 同期で始めても Plan に id と status があれば、後からジョブ化や SSE を追加で導入できる

## 受け入れたトレードオフ

- 処理中は画面が待つ。ロードバランサ経由ではタイムアウトに当たる可能性がある
- Route Handler の分だけ往復が1段増える

## 再検討する条件

- ALB や API Gateway の背後に置き、タイムアウトが実際に発生したとき
- 進捗表示が必要になったとき
