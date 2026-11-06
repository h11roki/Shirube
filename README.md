# shirube 道標

**履修に迷ったら、なりたい職業から。** なりたい職業と回生を入れると、大学のシラバスから職業につながる授業を選び、取るべき理由を添えて、卒業までの学期ごとの時間割(道標)を組む Web アプリです。最初の対象は立命館大学 理工学部 電子情報工学科です。

[![CI](https://github.com/h11roki/Shirube/actions/workflows/ci.yml/badge.svg)](https://github.com/h11roki/Shirube/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**デモ: https://shirube.duckdns.org** ・ [English summary](#english-summary)

ログイン前のトップで、実際の出力の見本の道標を見られます。道標を作るには Google でのログインが要り、今はテストの利用者に限っています。

## 30 秒で

- **作ったもの**: 職業名からシラバスを RAG で引き、LLM が授業を選んで理由を書き、卒業までの時間割に並べる Web アプリ。AWS で公開しています
- **規模**(2026-11-06 時点): 個人開発、2026-10-14 から 3 週間あまりで、980 を超えるコミット、100 を超える PR、90 を超える ADR、試験 1,300 件ほど([品質](#品質))
- **作り方**: Claude Code と作り、設計の選択肢から選ぶのと改善を採るかを決めるのは作者です([作り方](#作り方))
- **見どころ**: LLM の出力を数字で直す評価の仕組みです(下の[技術の見どころ](#技術の見どころ))

## 技術の見どころ

- **LLM を数字で直す**: 開発用 50 職業と確かめ用 20 職業の評価データ(正解は LLM-as-a-Judge で、立場の違う判定者 3 体の多数決)、2 つの設定を交互に流す実験の道具、並べ替え検定で、指示文や検索の作りの変更を採るかを決めます。採る条件は測る前に ADR に書き、採らなかった改善も残しています([評価と改善のサイクル](#評価と改善のサイクル))
- **段ごとに測れる LLM ワークフロー**: 職業の読み取り(プロンプト設計と構造化出力)→ シラバスの RAG(pgvector)→ LLM が候補から授業を選ぶ段に分け、期待する科目をどの段で落としたかまで数えます。エージェントが道具を呼ぶ形にせず、段の決まった流れにしているのは、段ごとに測って直すためです([推薦の仕組み](#推薦の仕組み))
- **本番で動かす**: AWS EC2 と Docker Compose で公開し、main にマージすると CI が通った版のイメージをサーバーが取りに行って入れ替えます([ADR 0094](docs/adr/0094-pull-deploy.md))。1 件約 1 円、1 日の上限、前払いで費用を抑え、同じ職業と条件の推薦は 7 日使い回して LLM を呼ばずに作り([ADR 0092](docs/adr/0092-recommendation-cache.md))、道標を作るごとに費用、時間、失敗の種類を記録して日ごとに見ています。バックエンドはクリーンアーキテクチャで作り、型の厳しい検査と画面の通しの試験(axe で WCAG 2.2 AA)を CI で回しています([設計](#設計)、[品質](#品質)、[安全性](#安全性))

## 今の精度と費用

| 指標 | 開発用 50 職業 | 確かめ用 20 職業 |
|---|---|---|
| 選んだ科目のうち関係なし(誤りの目安) | 16.4% | 17.5% |
| 期待する科目を中心に選んだ割合(再現率にあたる) | 67.5% | 89.7% |
| 中心の適合率 | 37.5% | 42.3% |

- 正解(期待する科目)は、職業ごとに立場の違う 3 体の判定者が科目を判定した多数決で作りました。中心は画面の「柱」にあたります。指標と作り方は下の[評価と改善のサイクル](#評価と改善のサイクル)にあります
- どちらも [ADR 0080](docs/adr/0080-selection-coverage.md) で選ぶ授業を広げたあとに、1 回ずつ流した値です。確かめ用の 89.7% は、同じ時に流した前の設定の 69.0% から +20.7 ポイント跳ねた 1 回だけの値で、読み取りの揺れも入っています
- 中心の適合率が低めなのは、判定者の中心が選び手より狭いうえに、ADR 0080 で柱をわざと広げたためです
- [ADR 0090](docs/adr/0090-reason-wording.md) で柱の理由の書き方を替えたあと、開発用を 1 回流した値は、関係なし 15.1%、期待する科目を中心に選んだ割合 63.6%、中心の適合率 37.4% で、表の値からの動きは時刻による揺れの範囲です(1 職業に選んだ柱は 5.74 → 5.14 と減りました)。確かめ用は流していません
- 推薦 1 件は約 1 円(初めての職業で 1.07 円。同じ職業名の読み取りを覚えると下がります)、道標 1 件を作るのは 10〜30 秒です。道標の受け付けは 1 人 1 日 3 件、全体で 1 日 30 件までにし、OpenAI は前払いで自動の補充を切って、使いすぎの最後の歯止めにしています([ADR 0038](docs/adr/0038-plan-quota.md))

![トップから見本の道標までスクロールし、礎の切符の乗換の欄を押すと柱の切符へ移って戻る道が出て、戻るで元の切符に帰る様子](docs/images/demo.gif)

> 大学とは関係のない個人の非公式のアプリです。必修、卒業要件、履修の前提は見ていません。授業は AI が選ぶので、誤りや作るたびの違いがあります。

## 何を解決するか

履修を選ぶ学生は、シラバスを 1 つずつ読んでも「この授業が将来の仕事のどこに効くのか」が分かりにくく、時間割の重なりも自分で調べる必要があります。shirube は、なりたい職業から逆算して、次のことをまとめて行います。

- 職業に必要なスキルを読み取り、シラバスの中身から関係する授業を選ぶ
- 授業ごとに「なぜ取るか」を、シラバスの抜粋をもとに短く書く
- 職業の中心になる授業を「柱」、柱の前提になる授業を「礎」として分け、どの礎がどの柱につながるかを示す
- 卒業までの残りの学期に、曜日と時限が重ならず、1 学期の単位の上限に収まるように並べる

道標が自分で選ぶのは推薦の授業だけで、必修や卒業要件は見ていません。必修など先に取ると決めた授業は、入力の画面で選べば推薦の授業より先に置けますが、要件を満たしているかは確かめません([ADR 0093](docs/adr/0093-fixed-courses.md))。前提の授業を前の学期に置く制約もかけていないので、礎が柱より後の学期に来ることがあります([ADR 0007](docs/adr/0007-greedy-timetable.md)、[0034](docs/adr/0034-taken-courses.md))。理由の文は、150 件を Claude の判定者 3 体で測ると、柱の理由のうち職業のどの仕事に効くかを具体的に言えていたのは 28% でした([ADR 0088](docs/adr/0088-reason-evaluation.md))。柱の理由にも仕事のどこで使うかを書かせる指示文に替え、前と後を同じ判定で比べると 37% → 67% に上がりましたが、残りの 3 分の 1 はまだぼんやりか、職業に触れないままです(礎の理由は 77% が柱のどの内容の前提かを言えています。[ADR 0090](docs/adr/0090-reason-wording.md))。理由の文を自動で判定する判定器も gpt-5.4-nano と mini で作りましたが、確かめる用の 75 件での正解との一致(Cohen の κ)が 0.54 と、測る前に決めた 0.6 に届かなかったので採っていません([推薦の評価の記録](docs/evaluation-log.md#理由の文の判定器採らなかった))。

## 主な機能

![結果の画面。職業の行先、発・経由・所要の要約、学期ごとの駅名標と、授業ごとの切符(柱か礎かの判子、選んだ理由、コマ、単位、通し番号、乗換と乗り入れの欄)](docs/images/result-route-1280.png)

結果の画面は、学期を駅、授業を切符に見立てた路線図です。切符には柱か礎かの判子、選んだ理由、コマ、単位、シラバスの原ページへのリンクを載せ、礎から柱への乗り換えは、駅の路線記号のような英字の印を両方の切符に刷り、礎の切符の下の乗換の欄に柱の授業名、学期、何駅先かを、柱の切符の下に乗り入れる礎の一覧を載せます。欄には「前提になる柱へ」「この柱を前提にする礎」と一言添え、凡例にも柱と礎が何かを書いて、路線図の言葉を知らなくても読めるようにしています。欄を押すと相手の切符へ移り、戻るで元の切符に帰れます。動きは題材から出した 3 つ(駅名標の帯、完成の瞬間の方向幕、「もう取った」で半券が裂ける)に絞り、動きを減らす設定では止めます([ADR 0083](docs/adr/0083-ruled-refinement.md)、[0084](docs/adr/0084-route-motions.md)、[0086](docs/adr/0086-transfer-marks.md)、[0091](docs/adr/0091-legend-words.md))。

| 職業と回生を入れる | 学期ごとの時間割帳 |
|---|---|
| ![入力の画面。なりたい職業、いまの回生、始める学期を選び、開いた「先に入れる授業」の欄で「回路」と絞って電子回路Ⅰと電気回路Ⅰにチェックを入れ、選んだ 3 科目が上に並ぶ](docs/images/form-1280.png) | ![時間割帳。月〜金と 1〜5 限の表に授業を置き、右に授業の切符を並べる](docs/images/result-timetable-1280.png) |
| 職業は自由に入れられます。必修など先に取ると決めた授業は、開講される授業の一覧から名前で絞って選ぶと、推薦の授業より先に時間割へ置き、推薦の候補からは外します([ADR 0093](docs/adr/0093-fixed-courses.md))。学科で分かれたクラスの選択と、もう取った授業も入力の画面で扱えます | 学期ごとに、週の時間割の表で重なりなく並んでいることを確かめられます |

<p>
  <img src="docs/images/progress-375.png" width="260" alt="作成中の画面。4 つの段の進みと、待ち時間と目安の板">
  <img src="docs/images/result-375-top.png" width="260" alt="スマホの幅の結果の画面の上部。職業の表示と要約">
  <img src="docs/images/result-375-tickets.png" width="260" alt="スマホの幅の授業の切符。路線図の帯が上に付いてくる">
</p>

作成中の画面は、道標を作る 4 つの段(読み取り、検索、選び直し、配置。下の「推薦の仕組み」)の進みを路線の駅のように見せ、駅の発車案内のような板で待ち時間を出します([ADR 0031](docs/adr/0031-route-design.md)、[0079](docs/adr/0079-progress-board.md))。スマホの幅でも読めて、明るい見た目と暗い見た目を切り替えられます。キーボードだけで操作でき、作成の段と完成を読み上げの枠で伝え、WCAG 2.2 の AA を目安にしています([ADR 0056](docs/adr/0056-accessibility.md))。

ほかに、始める学期より前に開講された授業を「もう取った」と答えて道標から外す機能があります。答えた授業は覚えて、次に作る道標の候補からも除きます([ADR 0034](docs/adr/0034-taken-courses.md)、[0035](docs/adr/0035-taken-candidates.md))。自分の道標の一覧と削除、退会もあります。

## 推薦の仕組み

職業名から授業を選ぶまでを、読み取り、検索、選び直しの 3 段に分け、それぞれを別に測って直せるようにしています。選んだ授業は、最後の配置の段で時間割に並べます。LLM に段ごとの決まった仕事をさせ、道具を呼ぶエージェントにはしていません。段ごとに測って直すためで、LLM の出力は候補の科目名との突き合わせと画面に出す文にしか使いません([ADR 0018](docs/adr/0018-llm-pipeline.md)、[0089](docs/adr/0089-llm-safety.md))。道標は API が「待ち」で受け付け、worker が 1 件ずつ作ります(1 件 10〜30 秒、[ADR 0029](docs/adr/0029-plan-jobs.md))。

```mermaid
flowchart LR
  J[職業名] -->|gpt-5.4-mini| R[読み取り<br/>解釈と必要なスキル]
  R -->|text-embedding-3-large<br/>pgvector| S[検索<br/>職業全体と各スキルの順位から<br/>交互に 20 科目]
  S -->|gpt-5.4-nano × 3 回の多数決| C[選び直し<br/>柱と礎を理由つきで選ぶ]
  C --> T[配置<br/>学期ごとの貪欲法で<br/>重ならない時間割に]
```

- **読み取り**: LLM が職業名を、その職業の解釈と必要なスキルに直します。学科の授業に無い応用分野で決まる細かい職種(Web エンジニアなど)は、授業で備えられる広い職業として読み、そう読んだことを前提として画面に出します([ADR 0032](docs/adr/0032-broad-occupation.md))。同じ職業名の読み取りは覚えて使い回し、揺れと費用を減らします([ADR 0052](docs/adr/0052-reading-cache.md))
- **検索**: シラバスを節(授業概要、到達目標、授業計画)ごとに埋め込み、職業全体のクエリと各スキルのクエリの順位から交互に 20 件の候補を取ります([ADR 0005](docs/adr/0005-section-chunking.md)、[0063](docs/adr/0063-search-by-skill.md))
- **選び直し**: 検索の候補 20 件のシラバスの抜粋を LLM に読ませ、柱と礎を理由つきで選ばせます。職業に少しでも役立つ授業は、迷っても選ばせます([ADR 0080](docs/adr/0080-selection-coverage.md))。同じ問いを LLM に 3 回並行して投げ、2 回以上選ばれた授業だけを残します。何回で残すかは設定で替えられます([ADR 0049](docs/adr/0049-selection-votes.md)、[0081](docs/adr/0081-selection-min-votes.md))。2 回目からは少し遅らせて入力のキャッシュを効かせ、費用を下げています([ADR 0051](docs/adr/0051-vote-delay.md))
- **配置**: 学期ごとに、配当回生と開講学期を満たし、コマが重ならず、単位の上限に収まる授業を貪欲法で詰めます。前提科目は制約にせず表示だけにしています([ADR 0007](docs/adr/0007-greedy-timetable.md))

将来の学期のシラバスはまだ無いので、当年度のシラバスと時間割を翌年度以降の代理にして組んでいます([ADR 0010](docs/adr/0010-graduation-roadmap.md))。

## 評価と改善のサイクル

LLM の出力は「それらしく見える」ので、感覚ではなく数字で直すために、評価データ、実験の道具、統計の決まりを先に作りました。

```mermaid
flowchart LR
  D[評価データ<br/>開発用 50 職業<br/>確かめ用 20 職業] --> E[experiment run / pair<br/>本番と同じ道で推薦を流す]
  E --> M[compare<br/>ブートストラップの区間<br/>並べ替え検定]
  E --> A[analyze<br/>期待する科目を<br/>どの段で落としたか]
  M --> H[判断を ADR に書く<br/>採る / 採らない]
  A --> H
  H -->|直しを決めたあとだけ| V[確かめ用で<br/>平均と検定だけを見る]
```

- **期待する科目(正解)**: 職業ごとに、Claude のサブエージェントを判定者にして、科目ごとに中心・土台・関係なし(中心と土台は、画面の柱と礎にあたる)の票を入れさせ、その多数決で作りました。判定者は立場の違う 3 体(採用・育成担当のエンジニア、カリキュラムを設計する教員、進路を考える 3 回生)で、科目が多いので前半と後半を別の判定者に渡しています。中心の票が 1 つだけの科目は、作者が票と根拠を見て決めました(2 回目に足した 20 職業の 17 件は、判定者の多数に合わせて全て土台にしました。[ADR 0017](docs/adr/0017-eval-judging.md)、[0023](docs/adr/0023-foundation-links-core.md)、[0054](docs/adr/0054-thirty-occupations.md)、[0064](docs/adr/0064-fifty-occupations.md))。人が付けた正解ではなく、判定者 3 体は同じ Claude なので、判定者の癖は正解に残ります。アプリの LLM(OpenAI)とは系統を分け、答え合わせが循環しないようにしています
- **実験の道具**: `experiment run` が評価データの職業に本番と同じ道(読み取り → 検索 → 選び直し)で推薦を流し、精度、揺れ、1 件あたりの費用と時間を JSON に残します([ADR 0048](docs/adr/0048-recommendation-experiments.md))。揺れは、同じ職業を何回か作ったときに選んだ授業の重なり(Jaccard)で測ります。比べる 2 つの設定は `experiment pair` で職業と回ごとに交互に流し、流した時刻による指標のずれを差から消します。同じ設定を別の時刻に流すと、関係なしが 9 ポイントほど動くと分かったためです([ADR 0055](docs/adr/0055-interleaved-runs.md))
- **統計の決まり**: 差の 95% 信頼区間は職業を選び直すブートストラップで、差ありは職業ごとに前と後を入れ替える並べ替え検定(p < 0.05)で決めます。判定に使う指標と採る条件は、変える前に ADR に書きます([ADR 0053](docs/adr/0053-paired-bootstrap.md)、[0055](docs/adr/0055-interleaved-runs.md))
- **取りこぼしの内訳**: `experiment analyze` が、期待する科目を読み取り、検索、選び直しのどの段で落としたかを数え、次に直す段を決める材料にします([ADR 0073](docs/adr/0073-experiment-analysis.md))
- **確かめ用を分ける**: 開発用の取りこぼしを見て決めた直しは、決めるときに見た職業にだけ効いていることがありました(下の表の [ADR 0063](docs/adr/0063-search-by-skill.md) の行)。そこで確かめ用の 20 職業を取っておき、直しを決めて ADR に書いたあとに流して、職業ごとの結果は見ずに平均と検定を見ます([ADR 0067](docs/adr/0067-heldout-occupations.md))

| 指標 | 意味 |
|---|---|
| 選んだ科目のうち関係なし | 選んだ授業のうち、判定で関係なしになった授業の割合。誤りの目安 |
| 期待する科目を中心に選んだ割合 | 判定で中心になった授業(期待する科目)のうち、柱に選んだ割合。再現率にあたる |
| 中心の適合率 | 柱に選んだ授業のうち、期待する科目の割合。判定者の中心は選び手より狭く(0080 の前の分析で、柱の半分ほどが判定では土台)、0080 で柱をわざと広げたので、低めに出る |
| 候補の再現率(@20) | 期待する科目のうち、検索が 20 件の候補に入れた割合 |

### 採った改善と採らなかった改善

| 変えたこと | ねらい | 結果 | 判断 |
|---|---|---|---|
| 選び直しを 3 回の多数決に([ADR 0049](docs/adr/0049-selection-votes.md)) | 関係なし | 23% → 10%(差あり)。費用は約 1.9 倍。10 職業を別の時刻に流し、当時のブートストラップの区間で判定した比べで、時刻によるずれも入る | 採った |
| 職業の読み取りを覚える([ADR 0052](docs/adr/0052-reading-cache.md)) | 揺れと費用 | 回どうしの重なり 0.56 → 0.73(差あり)。費用は初めての職業で 1.00 円のまま、覚えた職業で 0.59 円。10 職業を別の時刻に流し、当時のブートストラップの区間で判定した比べ | 採った |
| 検索を職業全体と各スキルの交互に([ADR 0063](docs/adr/0063-search-by-skill.md)) | 候補の再現率 | 50 職業で +3.3 ポイント(p = 0.391、差なし)。上がったのは直しを決めるときに見た 30 職業だけで(+6.4)、足した 20 職業では上がらなかった(-1.2) | 30 職業の時点でねらいが差なし(p = 0.089)のまま、作者が承知で採った。3 つの測り方で再現率が同じ向きに上がり、悪化が無かったため |
| 読み取りに学科の分野を書く([ADR 0065](docs/adr/0065-department-fields.md)) | 候補の再現率(@20) | 0.910 → 0.865(丸める前の値で -4.4 ポイント、p = 0.105) | 採らなかった |
| 選び直しで迷った授業を選ばない([ADR 0069](docs/adr/0069-selection-restraint.md)) | 関係なし | 開発用 16.4% → 10.6%(p = 0.004)、確かめ用 15.0% → 12.2%(p = 0.210、下がる向き) | 採った。効き目は確かめ用で開発用の半分ほど。のちに 0080 で替えた |
| 少しでも役立つ授業は迷っても選ぶ([ADR 0080](docs/adr/0080-selection-coverage.md)) | 1 職業に選ぶ柱と礎の数 | 柱が開発用 4.60 → 5.44(p < 0.001)、確かめ用 4.35 → 6.15(p = 0.001)。関係なしは開発用 12.3% → 16.4%(p = 0.027) | 道標を広く取りたいので採った。増えた柱の多くは判定では土台か関係なしで、きっかけの職業(データサイエンティスト)に少し役立つ授業(深層学習の応用など)は、まだ選ばれなかった。確かめ用の条件は「増える向き」だけで、ほぼ必ず通るものだった |
| 選び直しの 3 回のうち 1 回でも選べば残す([ADR 0081](docs/adr/0081-selection-min-votes.md)) | 1 職業に選ぶ柱 | 5.66 → 6.20(p = 0.076、差なし)。増えたのは礎で、関係なしは 13.4% → 19.7%(p = 0.003) | 採らなかった。設定で切り替えられる形だけ残した |
| 柱の理由に、仕事のどの作業や対象に授業のどの内容を使うかを書かせる([ADR 0090](docs/adr/0090-reason-wording.md)) | 柱の理由のうち具体的な割合(Claude の判定者 3 体の中央値) | 36.8% → 67.1%(区間 +17.8〜+42.7、差あり)。関係なしは 16.7% → 15.1%(p = 0.478)、1 職業に選んだ柱は 5.74 → 5.14(p = 0.029、差あり) | 採った。理由を書きにくい授業を柱に選ばなくなったとみられ、選ぶ数が少し減った |

行ごとに、測った時刻と職業の数が違います。同じ設定でも流した時刻で関係なしが 9 ポイントほど動くので、行と行の数字はつながらず、比べられるのは各行の前と後だけです(上の 2 行は、前と後も別の時刻に流しています)。細かい数字と経緯は[推薦の評価の記録](docs/evaluation-log.md)に、今の値は上の[今の精度と費用](#今の精度と費用)にあります。

## まず読んでほしい ADR

設計の判断は [ADR](docs/adr/README.md) に残しています。評価と改善の考え方をつかむなら、次の 5 本から読んでください。

| ADR | 読みどころ |
|---|---|
| [0018 LLM の流れの全体](docs/adr/0018-llm-pipeline.md) | 職業をスキルに直し、検索の候補を LLM が読み直して理由つきで選ぶ、と段を分けた。段ごとに測って直せる形の出発点 |
| [0017 評価の正解の作り方](docs/adr/0017-eval-judging.md) | 検索の候補の全科目を、立場の違う 3 体が職業名だけから独立に判定し、その多数決を正解にした |
| [0067 確かめ用を分けた理由](docs/adr/0067-heldout-occupations.md) | 開発用の取りこぼしを見て決めた直しが、決めるときに見た職業にだけ効いていた。確かめ用の 20 職業を取っておき、直しを決めて ADR に書いたあとにだけ、平均と検定で測る |
| [0065 測って採らなかった案](docs/adr/0065-department-fields.md) | 職業の読み取りに学科の分野を書く案を、変える前に決めた測り方で比べ、候補の再現率が下がる向き(-4.4 ポイント)だったので前の文面に戻した |
| [0080 精度と網羅のどちらを取るか](docs/adr/0080-selection-coverage.md) | 「迷ったら選ばない」を「少しでも役立てば選ぶ」に替え、関係なしが増えるのを受け入れて網羅を取った。確かめ用の採る条件が甘かった反省も残した |

## 設計

バックエンドはクリーンアーキテクチャの 4 層で、依存は内側にだけ向けています。大学ごとのシラバスの取得元や LLM は application のポート(Protocol)の向こうに置き、infrastructure に実装を足して差し替える形にしています(今は 1 大学だけで、2 つ目の取得元はまだ作っていません)。

```mermaid
flowchart TB
  P[presentation<br/>FastAPI ルータ、CLI、worker] --> A[application<br/>ユースケースとポート]
  A --> D[domain<br/>エンティティと純粋ロジック<br/>標準ライブラリだけ]
  I[infrastructure<br/>SQLAlchemy、OpenAI、Playwright、PyJWT] -. ポートを実装 .-> A
```

- フロントは API を呼んで表示するだけで、業務ロジックを置きません。Next.js の Route Handler がログインを確かめ、Google の利用者の番号を入れた JWT を付けて backend に転送します([ADR 0027](docs/adr/0027-auth-backend.md)、[0028](docs/adr/0028-auth-frontend.md))
- API の型は OpenAPI から生成してコミットし、backend の試験が OpenAPI との食い違いを見つけます([ADR 0030](docs/adr/0030-screens.md))
- 設計の判断は、選択肢、決定、理由、受け入れたトレードオフ、見直す条件を [ADR](docs/adr/README.md) に書いています

## 作り方

このリポジトリは Claude Code(Anthropic のコーディングエージェント)と作りました。コード、試験、文書の多くは Claude Code が書き、何を作るか、設計の選択肢からどれを選ぶか、改善を採るかどうかは作者が決めて ADR に残しています。ADR の中では、作者を「高橋さん」と書いています。

1 つの変更は、次の順に進めます。

1. 選択肢が 2 つ以上ある判断は、Claude Code が選択肢と良し悪しを並べ、作者が選ぶ。決めたことは実装より先に ADR に書く
2. 変更は git の worktree の上でブランチを切って作り、PR にする
3. PR ごとに、Claude Code にレビューを数周させて指摘を直し、CI を通してからマージする。LLM の振る舞いを変える PR は、評価の数字と検定の結果も ADR に残す

Claude Code に守らせる決まり(層の依存の向き、ADR を先に書くこと、コメントを書かず経緯はコミットメッセージに書くことなど)は [CLAUDE.md](CLAUDE.md) にあります。

## 品質

- **CI**(GitHub Actions): backend の ruff、mypy(strict)、pytest(DB の結合試験を含む)、frontend の lint、型、Vitest、整形、画面の通しの試験、本番の構成を本番と同じ Arm で組み立てて起動し HTTPS とログインの戻り先を確かめる job、デプロイのスクリプトの shellcheck と場面ごとの試験(戻し、マイグレーションの失敗、途中で止まった版のやり直しなど)。main では全て通った版だけイメージを作って置く
- **画面の通しの試験**(Playwright): 全ての画面を幅 375px と 1280px、明るい見た目と暗い見た目で開き、axe で WCAG 2.2 の A と AA の違反が無いか、幅 320px で横にはみ出さないか、文字を 200% にしても切れないかを確かめます([ADR 0056](docs/adr/0056-accessibility.md)、[0070](docs/adr/0070-text-resize-test.md))。Chromium のほかに WebKit(iPhone の幅)でも流します
- 試験の数(2026-11-06): backend 904、Vitest 160、e2e 236

## 安全性

LLM を使う部分の守りは、入口を狭くし、出口を限ることにしています([ADR 0089](docs/adr/0089-llm-safety.md))。

- 利用者の入力のうち LLM に渡るのは職業名(100 字まで)だけです。学科、回生、学期、クラスは決まった値から選びます
- LLM の出力は構造化出力で受け、選ぶ授業は候補の科目名の enum に限ります。LLM の出力を道具の呼び出しや DB の問い合わせには使わず、本人の画面に文として出すだけです
- 指示を混ぜた職業名(「これまでの指示を無視して…」など 3 件)を流して何が起きるかを記録しました。指示には従わず、候補に無い授業も鍵も出ませんでした。保証ではなく、その日の振る舞いの記録です。読み取りや選び直しの指示文かモデルを替えたときは、同じ 3 件を流し直して記録します(手順は [docs/development.md](docs/development.md#llm-の安全性の確認))
- 失敗の文は決まった文だけを返し、LLM や例外の文は見せません。道標の受け付けは 1 人 1 日 3 件、全体 30 件までで、OpenAI は前払いで自動の補充を切っています([ADR 0038](docs/adr/0038-plan-quota.md))
- 画面の転送は送り元を確かめて他のサイトからの要求を断り、CSP などのヘッダーを付け、バックエンドは 5 分の JWT でだけ呼べます([ADR 0027](docs/adr/0027-auth-backend.md)、[0039](docs/adr/0039-request-guard.md))。鍵はサーバーの `.env` にだけ置き、ログと DB の例外から伏せています

## 本番の構成

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/architecture-dark.png">
  <img src="docs/images/architecture.png" alt="構成図。利用者は DuckDNS の名前で、HTTPS で AWS シドニーの EC2 の Caddy に届き、Caddy は Let's Encrypt から証明書を取る。EC2 の中の Docker Compose で、Caddy から Next.js、JWT を付けて FastAPI、SQL で PostgreSQL(pgvector)へつながる。Next.js は Google でログインさせる。Worker は DB の待ちの道標を取り、OpenAI の gpt-5.4-mini(職業からスキル)、text-embedding-3-large(検索の埋め込み)、gpt-5.4-nano(3 回の多数決で授業を選ぶ)を呼ぶ。cron が毎日 pg_dump で DB を残す。下の段は、GitHub Actions の CI(Ruff、mypy、pytest、Vitest、Playwright、本番の compose の確かめ)が通った版のイメージを GHCR に置き、EC2 がそれを取りに行くデプロイと、手元の開発機で Playwright がシラバスを取り BeautifulSoup で解析して埋め込み、本番の DB へ移す流れ">
</picture>

AWS EC2 の 1 台(t4g.small、シドニー)で Docker Compose を動かし、Caddy が証明書を自動で取って HTTPS を受けます。ドメインは DuckDNS の無料のサブドメインです。DB と backend のポートは外に出さず、バックアップは毎日取って 7 日分を残します。main にマージすると、CI が通った版だけ Arm のイメージを作って GHCR に置き、サーバーの cron が 5 分おきに新しい版を見つけて取りに行き、マイグレーション、入れ替え、ヘルスチェックまでを行い、応えなければ前の版に戻します。サーバーへ入る口と鍵を CI に持たせず、AWS の機能にも頼らないので、別のサーバーへ移ってもそのまま使えます([ADR 0094](docs/adr/0094-pull-deploy.md))。シラバスの取得、解析、埋め込みは手元の開発機で行い、科目の表の中身だけを本番の DB へ移すので、本番のイメージには取り込みの依存がありません。道標を作るごとに、費用、待ちと作る時間、失敗の種類(残高切れを見分ける)を、利用者の番号も入力も持たない形で残し、サーバーの CLI で日ごとに見ます([ADR 0087](docs/adr/0087-build-records.md))。手順は[開発と本番の手順](docs/development.md#本番)、判断は [ADR 0075](docs/adr/0075-production-setup.md)〜[0077](docs/adr/0077-auth-url.md) と [0094](docs/adr/0094-pull-deploy.md) にあります。図は [stack-diagram](https://github.com/caru-ini/stack-diagram) で描いた [`docs/images/architecture.html`](docs/images/architecture.html) を撮ったものです。

## 技術

| 領域 | 技術 |
|---|---|
| フロント | Next.js(App Router、TypeScript)、Tailwind CSS、Auth.js、pnpm、Vitest、Playwright + axe |
| バックエンド | Python 3.13、FastAPI、SQLAlchemy、Alembic、LangChain、uv、ruff、mypy |
| DB | PostgreSQL + pgvector |
| LLM / 埋め込み | OpenAI API(gpt-5.4-mini、gpt-5.4-nano、text-embedding-3-large) |
| 評価データの判定 | Claude のサブエージェント |
| シラバスの取り込み | Playwright、BeautifulSoup |
| 開発環境 | Docker Compose |
| 本番 | AWS EC2、Docker Compose、Caddy、DuckDNS |
| CI / CD | GitHub Actions、GHCR、サーバーの cron が取りに行くデプロイ |

## 開発者向け

- [開発と本番の手順](docs/development.md): 手元での起動、本番の用意とデプロイと更新とバックアップ、データの取り扱い、開発のルール
- [推薦の評価の記録](docs/evaluation-log.md): 基準、改善ごとの数字、30 職業と 50 職業での比べ、取りこぼしの内訳
- コマンドの一覧と、Claude Code に守らせる決まりは [CLAUDE.md](CLAUDE.md) にあります

前の ADR が「README の「本番」」「README の「50 職業で比べ直す」」のように書いている節は、見出しの名前のまま、この 2 つの文書に移しました。

## English summary

shirube ("signpost") helps university students choose courses backwards from the job they want. Given a target occupation and the student's current year, it retrieves related courses from the university syllabi (RAG with pgvector), has an LLM pick the courses and explain why each one matters for that job, and lays them out into a clash-free timetable for every remaining semester until graduation. It currently covers the Department of Electronic and Computer Engineering at Ritsumeikan University, and is live at https://shirube.duckdns.org (sign-in is limited to test users; the landing page shows a real sample plan).

- **Evaluation-driven LLM development**: a development set of 50 occupations and a held-out set of 20, with expected courses labelled by majority vote of three Claude judges with different viewpoints (a different model family from the OpenAI models the app uses, so the app is not graded by itself); two configurations are run interleaved, and changes are accepted by bootstrap confidence intervals and permutation tests. Acceptance criteria are written down before measuring, and rejected changes are documented as well. Last measured on both sets (dev / held-out): 16.4% / 17.5% of chosen courses judged irrelevant and 67.5% / 89.7% of expected courses chosen as core. The held-out 89.7% is a single run that jumped from 69.0% for the previous settings measured at the same time, so read it with care. After the latest prompt change (ADR 0090), one dev run gave 15.1% and 63.6%; the held-out set has not been re-run. A recommendation costs about 1 JPY
- **A staged pipeline, not an agent**: occupation reading with structured output, retrieval, selection by a 3-vote majority, and greedy timetable placement. Each stage is measured on its own, so a missed course can be traced to the stage that dropped it. LLM output is only matched against candidate course names and shown to its owner; it never drives tool calls or queries
- **Running in production**: FastAPI (clean architecture, mypy strict) and Next.js on a single AWS EC2 instance with Docker Compose and Caddy, pull-based continuous deployment (CI pushes arm64 images to GHCR only when every check passes; the server picks up the new version, migrates, health-checks and rolls back on failure), a PostgreSQL-backed job queue with a worker, daily quotas and prepaid billing as cost limits, a 7-day recommendation cache, and per-build records of cost, latency and failure type
- **Quality**: CI runs pytest (with database integration tests), Vitest, and Playwright end-to-end tests that check every screen against WCAG 2.2 AA with axe at two widths in light and dark themes, and check that nothing overflows at 320px or is clipped at 200% text size
- **Decisions on record**: more than 90 ADRs list the options, the decision, the trade-offs accepted and when to revisit. The code was written with Claude Code; the author made the product and design decisions recorded in the ADRs

The documentation is in Japanese.

## ライセンス

コードは [MIT License](LICENSE) です。取り込んだシラバスと時間割表の内容(`backend/data/`、git 管理外)と画面に出す引用は、このライセンスの対象外です(大学と担当教員のもの)。テストには実ページを置かず、科目名・教員名・本文が架空の合成のページ(`backend/tests/unit/syllabus_pages.py` がテストの中で組み立てる)と PDF(`backend/tests/fixtures/timetable/make_sample.py` が作る)を使います([ADR 0043](docs/adr/0043-license-and-fixtures.md))。
