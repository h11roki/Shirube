# 0096. 依存と CI の部品は、既知の脆弱性を CI で止め、Dependabot が 1 週間置いてから上げ、CodeQL でコードを調べる

- ステータス: 承認
- 日付: 2026-11-07

## 文脈

- 依存の既知の脆弱性を調べる仕組みが無かった。2026-11-07 に pip-audit をかけると、Pillow 12.3.0 に 40 件(13.0.0 で直る。dev と scraper のグループで、本番のイメージには入らない)、certifi 2026.7.22 に 1 件があった。pnpm audit は moderate が 1 件(eslint の下の minimatch。開発だけで使う)
- Dependabot の知らせも、更新の PR も、コードの静的な検査(CodeQL)も切っていた。秘密の値の走査と push の保護は、公開リポジトリの既定で入っていた
- ADR 0094 で、変わっていない側のイメージを使い回すことにし、土台のイメージ(`node:24-slim` など)の更新は Dockerfile の変更として届けると決めた。今の Dockerfile は動くタグを指していて、届かない
- CI は、GitHub 以外の人が出している Action(docker、pnpm、astral-sh)を動くタグで使っている。タグを付け替えられると、CI の権限(GHCR に置く `packages: write` を含む)で別のコードが動く
- 高橋さんの洗い出しで「Dependabot、CodeQL、pip-audit と pnpm audit」を、お金を使わずにやると決めた

## 決定

- CI に audit の job を 2 つ足す。`audit` は本番のイメージに入る依存だけ(backend は既定のグループを外した本体の依存、frontend は `--prod`)を、`audit-development` は開発と取り込みの依存も含めて調べる。backend は `uv export --locked` で依存を固定の版とハッシュで書き出して `pip-audit` にかけ、1 件でもあれば落とす(lock が pyproject とずれていれば書き出しで落とす)。frontend は `pnpm audit --audit-level high` で、high 以上があれば落とす(moderate 以下は Dependabot の知らせと更新の PR で追う)。pip-audit は既定では入らない audit のグループに入れ、その依存ごと lock で固定する(監査の道具が取り込み口にならないよう、ほかの依存と同じに Dependabot の cooldown を通して上げる。監査の道具自身の依存は調べない)。images の job は `audit` だけを待ち、本番に入る依存に既知の脆弱性のある版のイメージは置かない。開発だけの道具の勧告では本番の更新を止めない
- 直す版の無い脆弱性は、backend は ci.yml の pip-audit の行に `--ignore-vuln <ID>` を、frontend は `frontend/pnpm-workspace.yaml` の `auditConfig.ignoreGhsas` に GHSA を足して除き(pnpm 11 は設定を package.json でなくこのファイルから読む)、理由を ADR に書く
- Pillow を 13.0.0、certifi を 2026.10.23 に上げる
- `.github/dependabot.yml` で、uv(backend)、npm(frontend)、GitHub Actions、Dockerfile、compose の 5 つを毎週月曜に見る。出てから 7 日経った版だけを出し(cooldown。出たばかりの版が乗っ取られていたときに巻き込まれないため)、minor と patch はまとめて 1 本の PR にする。マージは人が CI を見て行う
- Dependabot の知らせ(alerts)と、脆弱性を直す PR(security updates)を有効にする
- `.github/workflows/codeql.yml` で、Python、JavaScript と TypeScript、GitHub Actions を、main への push、PR、毎週月曜に `security-extended` の問いで調べる。結果は GitHub のコードの走査に出る
- Dockerfile の土台のイメージを digest で固定する(`node:24-slim@sha256:…`、`ghcr.io/astral-sh/uv:python3.13-bookworm-slim@sha256:…`)。更新は Dependabot が digest を上げる PR で届く。frontend のイメージの pnpm は、Dockerfile に版を書かず、`corepack install` で package.json の `packageManager` から取る(Dependabot が package.json だけ上げて、CI とイメージの pnpm がずれないよう)。取ってきた pnpm は corepack が npm の署名で確かめる(`packageManager` に中身のハッシュを付けると、Dependabot が版を上げるときにハッシュを直せるかが分からないので付けない)
- Dockerfile と compose のイメージは、メジャーの版を上げる PR を出させない。Node の奇数の版は LTS でなく、25 からは corepack を同梱しない。`pgvector/pgvector:pg16` を pg17 にすると、本番の pg16 で作ったデータのボリュームで DB が起動しない。メジャーは ADR を書いて手で上げる
- GitHub 以外の人が出している Action は commit の SHA で固定し、行の後ろに版を書く(Dependabot がこの書き方を読んで、SHA と版を一緒に上げる。コードにコメントを書かない決まりの例外で、Dependabot が読む印として置く)。GitHub が出している Action(`actions/*`、`github/*`)はメジャーの版のタグのまま
- ワークフローの既定の権限を `contents: read` にし、要る job(images の `packages: write`、CodeQL の `security-events: write`)だけ足す
- 非公開で脆弱性を報告できるようにし(private vulnerability reporting)、`SECURITY.md` に報告の仕方を書く
- compose の DB と Caddy のイメージ(`pgvector/pgvector:pg16`、`caddy:2.10`)はタグのままにし、Dependabot に更新の PR を出させる。CI の結合試験の DB(ci.yml の services)も同じ `pg16` のタグで、メジャーを上げないので本番とずれない

## 理由

- 公開リポジトリでは、Dependabot、CodeQL、Actions は無料で、アカウントも要らない
- 既知の脆弱性は CI で止めると、直さずにマージすることが無くなる。frontend を high 以上にしたのは、開発だけで使う依存の moderate で、関係の無い PR が止まらないように
- 7 日の cooldown は、乗っ取られた版が出てから気づかれて取り下げられるまでの期間を避ける
- digest と SHA で固定すると、同じ commit からは同じ部品で作られ、更新は PR として見える

## 受け入れたトレードオフ

- 新しい脆弱性が見つかると、直す版が出るまで、関係の無い PR でも audit が落ちる。直す版が無いときは、その脆弱性を audit の除外に足し、理由を ADR に書く
- Dependabot の PR が毎週いくつか来る。まとめて減らすが、マージは人の手が要る
- 1 週間の cooldown のあいだは、脆弱性を直す版でも普通の更新としては出ない(security updates は cooldown を待たない)
- compose の DB と Caddy は digest で固定していない。更新の PR が来るまで、同じタグの中の差し替えはそのまま取り込む

## 再検討する条件

- Dependabot の PR が多すぎて追えなくなったとき(自動でマージする条件を決める)
- audit の除外が増えたとき

## 追記: 使う側の範囲が直す版を許さない脆弱性(2026-11-13)

minimatch の GHSA-g3hv-75wg-m249(moderate、7.0.0 以上 11.0.1 未満)は、lint だけで使う typescript-eslint の `@typescript-eslint/typescript-estree` が、最新の 8.72.2 でも `minimatch@^10.2.2` を求めるので、使う側を上げても直らない。直す版はあるので除外にはせず、使う側の範囲を越えて直す版に替える。

- `frontend/pnpm-workspace.yaml` の `overrides` で、7.0.0 以上 11.0.1 未満の minimatch を 11.0.5(7 日の cooldown を過ぎた版)に替える。11 で外れたのは `makeRe()` や `Minimatch#regexp` などで、typescript-estree は `minimatch(path, pattern, { dot: true })` しか呼ばない(それも `allowDefaultProject` を書いたときだけで、このリポジトリは書いていない)。3 系と 5 系の minimatch は脆弱な範囲の外なのでそのまま
- override は版を固定するので、使う側が直す版を許したら消す。上書きが増えたときも見直す
- 開発と取り込みの依存の beautifulsoup4 から入る soupsieve の CVE-2026-126190(high)は、4.0.1 に上げて直す(4.0.0 で直り、4.1 は出て 3 日で cooldown の前)。メジャーの上げなので、保存したシラバスの 530 頁を 3.0.3 と 4.0.1 で解析して、結果が全て同じことを確かめた

除外より上書きを先に考えるのは、除外は脆弱な版を入れたままにし、上書きは入れないで済むから。上書きできないとき(使う側が直す版の呼び方で動かないとき)だけ除外にする。
